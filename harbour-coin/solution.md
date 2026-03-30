# Harbourcoin Miner Analysis

## Q1: Why does the program show multiple solutions and then hang?

- `solution` is shared but not synchronized → multiple threads read it as 0 and update it → multiple solutions printed  
- queue is not thread-safe → race conditions on `length`  
- spinlocks (`while(...) {}`) waste CPU and do not properly coordinate threads  
- some threads get stuck waiting in queue loops → program hangs during `pthread_join`  

---

## Q2: Synchronization differences between C and Go

- C uses `pthread_mutex` and `pthread_cond` → manual locking and signaling  
- queue must be implemented and protected manually  
- Go uses channels and goroutines → built-in synchronization  
- no need for condition variables or manual locks for queue  
- atomic operations replace mutex for shared variables  
- closing a channel acts as broadcast to stop all workers  