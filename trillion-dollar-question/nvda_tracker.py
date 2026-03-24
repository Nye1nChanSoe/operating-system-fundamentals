#!/usr/bin/env python3
"""
NVDA Stock Price Tracker Daemon

This script is a long-running Python daemon designed to monitor and log the price
of NVDA (NVIDIA) stock during regular NASDAQ trading hours.

Behavior:
- Runs continuously as a background process (suitable for systemd service)
- During NASDAQ trading hours (New York time), it fetches the latest NVDA price every minute
- Prints the current price along with the difference from the previous value
- Sleeps between ticks to align with minute boundaries

End-of-Day (EOD) Features:
- Tracks and prints daily OPEN, CLOSE, MIN, and MAX prices
- Ensures EOD summary is printed once per trading day
- Persists state to disk so it can recover after restarts
- If restarted mid-day or after market close, it resumes correctly and still prints EOD

Reliability:
- Uses persistent state file to survive crashes or restarts
- Handles system signals (SIGINT, SIGTERM) for graceful shutdown
- Timezone-safe: trading logic is based on America/New_York (handles DST correctly)
- Output timestamps are displayed in Asia/Bangkok (with optional NY reference)

Intended Usage:
- Run as a Linux service (e.g., systemd)
"""

from __future__ import annotations

import yfinance as yf
import signal
import sys
import time
import json
import math

from typing import Optional
from zoneinfo import ZoneInfo
from pathlib import Path

from datetime import datetime, time as dtime
from dataclasses import asdict, dataclass


SYMBOL = "NVDA"


NY = ZoneInfo("America/New_York")
BKK = ZoneInfo("Asia/Bangkok")  # display tz
STATE_PATH = Path("/var/lib/nvda-tracker/state.json")


# Regular NASDAQ trading session only: DST NY time
MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)


# graceful shutdown for this process
shutdown_requested = False


def handle_signal(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    print(f"[{timestamp()}] Received signal {signum}, shutting down...", flush=True)


# OS hooks
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


# persistence | will store in STATE_PATH
# to survive service being stopped or restarts
@dataclass
class State:
    date: str
    open_price: Optional[float] = None
    last_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    eod_printed: bool = False

    @staticmethod
    def empty_for(date_str: str) -> "State":
        return State(date=date_str)


def timestamp() -> str:
    now_bkk = datetime.now(BKK).strftime("%Y-%m-%d %H:%M:%S BKK")
    now_ny = datetime.now(NY).strftime("%H:%M:%S NY")
    return f"{now_bkk} ({now_ny})"


# dt helper functions
def now_ny() -> datetime:
    return datetime.now(NY)


def today_ny_str() -> str:
    return now_ny().date().isoformat()


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_market_open(dt: datetime) -> bool:
    t = dt.timetz().replace(tzinfo=None)
    # NASDAQ trading hours: market OPEN
    return is_weekday(dt) and MARKET_OPEN <= t < MARKET_CLOSE


def is_market_closed_for_day(dt: datetime) -> bool:
    # EOD detection logic: market CLOSE
    t = dt.timetz().replace(tzinfo=None)
    return (not is_weekday(dt)) or t >= MARKET_CLOSE


# load state from disk if exists
# if new: create fresh state
def load_state() -> State:
    if not STATE_PATH.exists():
        return State.empty_for(today_ny_str())

    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return State(
            date=raw["date"],
            open_price=raw.get("open_price"),
            last_price=raw.get("last_price"),
            min_price=raw.get("min_price"),
            max_price=raw.get("max_price"),
            eod_printed=raw.get("eod_printed", False),
        )
    except Exception as exc:
        print(f"[{timestamp()}] WARNING: failed to read state file: {exc}", flush=True)
        return State.empty_for(today_ny_str())


# I/O chores and sleep
def save_state(state: State) -> None:
    ensure_state_dir()
    tmp_path = STATE_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2)
    tmp_path.replace(STATE_PATH)


def print_eod(state: State, label: str = "EOD") -> None:
    if state.open_price is None or state.last_price is None:
        print(
            f"[{timestamp()}] {label}: no data collected for {state.date}", flush=True
        )
        return

    print(
        f"[{timestamp()}] {label} {state.date} | "
        f"OPEN={state.open_price:.2f} "
        f"CLOSE={state.last_price:.2f} "
        f"MIN={state.min_price:.2f} "
        f"MAX={state.max_price:.2f}",
        flush=True,
    )


def print_tick(price: float, diff: Optional[float]) -> None:
    if diff is None:
        diff_str = "N/A"
    else:
        sign = "+" if diff >= 0 else ""
        diff_str = f"{sign}{diff:.2f}"

    print(
        f"[{timestamp()}] {SYMBOL} {price:.2f} | diff={diff_str}",
        flush=True,
    )


def sleep_until_next_minute() -> None:
    now = time.time()
    next_boundary = math.floor(now / 60.0) * 60.0 + 60.0
    delay = max(0.0, next_boundary - now)
    end = time.time() + delay

    while not shutdown_requested and time.time() < end:
        time.sleep(min(0.5, end - time.time()))


# state helper functions
def reset_state_for_today() -> State:
    state = State.empty_for(today_ny_str())
    save_state(state)
    return state


def maybe_finalize_previous_day(state: State, current_date: str) -> State:
    if state.date != current_date and not state.eod_printed:
        print_eod(state, label="LATE-EOD")
    if state.date != current_date:
        return reset_state_for_today()
    return state


def update_state_with_price(
    state: State, price: float
) -> tuple[State, Optional[float]]:
    previous = state.last_price

    if state.open_price is None:
        state.open_price = price

    if state.min_price is None or price < state.min_price:
        state.min_price = price

    if state.max_price is None or price > state.max_price:
        state.max_price = price

    state.last_price = price
    diff = None if previous is None else price - previous
    return state, diff


def ensure_state_dir() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


# yahoo-finance fetches
def fetch_current_price() -> float:
    ticker = yf.Ticker(SYMBOL)
    hist = ticker.history(
        period="1d",
        interval="1m",
        prepost=False,
        auto_adjust=False,
        actions=False,
    )

    if hist.empty:
        raise RuntimeError("No market data returned")

    price = hist["Close"].dropna().iloc[-1]
    value = float(price)

    if math.isnan(value) or value <= 0:
        raise RuntimeError(f"Invalid price returned: {value}")

    return value


# app logic
def run() -> None:
    print(f"[{timestamp()}] Starting {SYMBOL} tracker", flush=True)
    ensure_state_dir()

    # idle loop after market hours
    # shutdown_requested: signals are also respected for graceful shutdowns
    while not shutdown_requested:
        current_dt = now_ny()
        current_date = current_dt.date().isoformat()
        state = load_state()
        state = maybe_finalize_previous_day(state, current_date)

        # outside NASDAQ hours
        if (
            state.date == current_date
            and is_market_closed_for_day(current_dt)
            and not state.eod_printed
        ):
            if state.open_price is not None:
                print_eod(state)
            else:
                print(
                    f"[{timestamp()}] EOD: no data collected for {state.date}",
                    flush=True,
                )
            state.eod_printed = True
            save_state(state)

        # during NASDAQ hours
        if is_market_open(current_dt):
            try:
                price = fetch_current_price()
                state, diff = update_state_with_price(state, price)
                state.eod_printed = False
                save_state(state)
                print_tick(price, diff)
            except Exception as exc:
                print(f"[{timestamp()}] ERROR: price fetch failed: {exc}", flush=True)

        sleep_until_next_minute()

    print(f"[{timestamp()}] Exiting cleanly", flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"[{timestamp()}] FATAL: {exc}", file=sys.stderr, flush=True)
        raise