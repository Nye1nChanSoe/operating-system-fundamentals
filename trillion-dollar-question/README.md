### NVDA Stock Price Tracker Daemon

This script is a long-running Python daemon designed to monitor and log the price
of NVDA (NVIDIA) stock during regular NASDAQ trading hours.

---

#### Behavior:
- Runs continuously as a background process (suitable for systemd service)
- During NASDAQ trading hours (New York time), it fetches the latest NVDA price every minute
- Prints the current price along with the difference from the previous value
- Sleeps between ticks to align with minute boundaries

#### End-of-Day (EOD) Features:
- Tracks and prints daily OPEN, CLOSE, MIN, and MAX prices
- Ensures EOD summary is printed once per trading day
- Persists state to disk so it can recover after restarts
- If restarted mid-day or after market close, it resumes correctly and still prints EOD

#### Reliability:
- Uses persistent state file to survive crashes or restarts
- Handles system signals (SIGINT, SIGTERM) for graceful shutdown
- Timezone-safe: trading logic is based on `America/New_York` (handles DST correctly)
- Output timestamps are displayed in `Asia/Bangkok` (with optional NY reference)

#### Intended Usage:
- Run as a Linux service

#### Installation
1. Install `uv` package manager on your system
2. Run `uv sync` to install dependencies
3. Install and start the service using `systemctl`:
```bash
   sudo cp nvda-tracker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable nvda-tracker.service
   sudo systemctl start nvda-tracker.service
```

   **Check service status:**
```bash
   sudo systemctl status nvda-tracker.service
```

   **Check logs:**
```bash
   journalctl -u nvda-tracker.service -f
```