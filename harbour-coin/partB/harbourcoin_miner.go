package main

import (
	"fmt"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"
)

const (
	N_MINERS        = 100
	SLICE_SIZE      = 1_000_000
	LOWER_BITS_MASK = 0xfffffff
)

var solution uint64 = 0
var seed uint64

func hash(x uint64) uint64 {
	x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9
	x = (x ^ (x >> 27)) * 0x94d049bb133111eb
	x = x ^ (x >> 31)
	return x
}

func manager(queue chan uint64, done chan struct{}) {
	var sliceBase uint64 = SLICE_SIZE

	for {
		select {
		case <-done:
			return
		case queue <- sliceBase:
			sliceBase += SLICE_SIZE
		}
	}
}

func miner(queue chan uint64, done chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()

	for {
		select {
		case <-done:
			return
		case base := <-queue:
			for i := base; i < base+SLICE_SIZE; i++ {

				if atomic.LoadUint64(&solution) != 0 {
					return
				}

				hashed := i ^ seed
				for j := 0; j < 10; j++ {
					hashed = hash(hashed)
				}

				if (hashed & LOWER_BITS_MASK) == 0 {

					if atomic.CompareAndSwapUint64(&solution, 0, i) {
						fmt.Println("miner found solution", i)
						close(done) // broadcast stop
					}
					return
				}
			}
		}
	}
}

func main() {
	rand.Seed(time.Now().UnixNano())
	seed = uint64(rand.Int63())

	queue := make(chan uint64, 10) // replaces queue_t
	done := make(chan struct{})    // stop signal

	var wg sync.WaitGroup

	// start manager
	go manager(queue, done)

	// start miners
	for i := 0; i < N_MINERS; i++ {
		wg.Add(1)
		go miner(queue, done, &wg)
	}

	wg.Wait()

	fmt.Println("Final solution:", solution)
}