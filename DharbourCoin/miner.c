#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <inttypes.h>
#include <time.h>
#include <stdatomic.h>
#include <stdbool.h>

#define N_MINERS 100

void *manager(void*);
void *miner(void*);


/*
 * Global stop/result flag:
 * - 0 means "still mining"
 * - non-zero is the winning nonce
 * Atomic access avoids per-iteration mutex contention in miners.
 */
_Atomic uint64_t solution = 0;


enum {
    QUEUE_CAPACITY = 256
};

// Bounded work queue of slice bases, implemented as an O(1) ring buffer.
typedef struct {
    uint64_t items[QUEUE_CAPACITY];
    size_t head;
    size_t tail;
    size_t count;

    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} queue_t;

void queue_init(queue_t *q) {
    q->head = 0;
    q->tail = 0;
    q->count = 0;
    pthread_mutex_init(&q->mutex, NULL);
    pthread_cond_init(&q->not_empty, NULL);
    pthread_cond_init(&q->not_full, NULL);
}

// Wake all producers/consumers so they can observe stop state and exit.
void queue_wake_all(queue_t *q) {
    pthread_mutex_lock(&q->mutex);
    pthread_cond_broadcast(&q->not_empty);
    pthread_cond_broadcast(&q->not_full);
    pthread_mutex_unlock(&q->mutex);
}

void queue_add(queue_t *q, uint64_t item) {
    pthread_mutex_lock(&q->mutex);

    while (q->count == QUEUE_CAPACITY &&
           atomic_load_explicit(&solution, memory_order_relaxed) == 0) {
        pthread_cond_wait(&q->not_full, &q->mutex);
    }

    if (atomic_load_explicit(&solution, memory_order_relaxed) != 0) {
        pthread_mutex_unlock(&q->mutex);
        return;
    }

    q->items[q->tail] = item;
    q->tail = (q->tail + 1) % QUEUE_CAPACITY;
    q->count++;

    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->mutex);
}

bool queue_pop(queue_t *q, uint64_t *out) {
    pthread_mutex_lock(&q->mutex);

    while (q->count == 0 &&
           atomic_load_explicit(&solution, memory_order_relaxed) == 0) {
        pthread_cond_wait(&q->not_empty, &q->mutex);
    }

    if (atomic_load_explicit(&solution, memory_order_relaxed) != 0) {
        pthread_mutex_unlock(&q->mutex);
        return false;
    }

    *out = q->items[q->head];
    q->head = (q->head + 1) % QUEUE_CAPACITY;
    q->count--;

    pthread_cond_signal(&q->not_full);
    pthread_mutex_unlock(&q->mutex);

    return true;
}

static inline uint64_t hash(uint64_t x) {
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    x = x ^ (x >> 31);
    return x;
}

const uint64_t SLICE_SIZE = 1000000;
const uint64_t LOWER_BITS_MASK = 0xfffffff;

uint64_t seed;
queue_t queue;

int main(void) {
    pthread_t thread_manager;
    pthread_t threads_miners[N_MINERS];

    srandom(time(NULL));
    seed = random();

    queue_init(&queue);

    assert(!pthread_create(&thread_manager, NULL, &manager, NULL));
    for (int i = 0; i < N_MINERS; i++) {
        assert(!pthread_create(&threads_miners[i], NULL, &miner, NULL));
    }

    pthread_join(thread_manager, NULL);

    for (int i = 0; i < N_MINERS; i++) {
        pthread_join(threads_miners[i], NULL);
    }

    printf("Final solution: %" PRIu64 "\n", solution);
    return 0;
}

void *manager(void* _) {
    // Start from 0 so the full nonce space is covered.
    uint64_t slice_base = 0;

    while (atomic_load_explicit(&solution, memory_order_relaxed) == 0) {
        queue_add(&queue, slice_base);
        slice_base += SLICE_SIZE;
    }

    return NULL;
}

void *miner(void* _) {
    while (atomic_load_explicit(&solution, memory_order_relaxed) == 0) {
        uint64_t base;
        if (!queue_pop(&queue, &base)) {
            return NULL;
        }

        const uint64_t end = base + SLICE_SIZE;
        for (uint64_t i = base; i < end; i++) {
            /*
             * Poll the stop flag periodically to reduce overhead in the hot path
             * while still exiting quickly after another miner finds a result.
             */
            if ((i & 0x3ff) == 0 &&
                atomic_load_explicit(&solution, memory_order_relaxed) != 0) {
                return NULL;
            }

            uint64_t hashed = i ^ seed;
            for (int j = 0; j < 10; j++) {
                hashed = hash(hashed);
            }

            if ((hashed & LOWER_BITS_MASK) == 0) {
                uint64_t expected = 0;
                if (atomic_compare_exchange_strong_explicit(
                        &solution,
                        &expected,
                        i,
                        memory_order_release,
                        memory_order_relaxed)) {
                    printf("miner found solution %" PRIu64 "\n", i);
                    queue_wake_all(&queue);
                }

                return NULL;
            }
        }
    }

    return NULL;
}
