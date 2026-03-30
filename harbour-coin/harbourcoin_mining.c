#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <inttypes.h>
#include <time.h>

#define N_MINERS 100


void *manager(void*);
void *miner(void*);

uint64_t solution = 0;
pthread_mutex_t solution_mutex = PTHREAD_MUTEX_INITIALIZER;

typedef struct {
    uint64_t items[10];
    size_t length;

    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} queue_t;

void queue_init(queue_t *q) {
    q->length = 0;
    pthread_mutex_init(&q->mutex, NULL);
    pthread_cond_init(&q->not_empty, NULL);
    pthread_cond_init(&q->not_full, NULL);
}

void queue_add(queue_t *q, uint64_t item) {
    pthread_mutex_lock(&q->mutex);

    while (q->length == 10 && !solution) {
        pthread_cond_wait(&q->not_full, &q->mutex);
    }

    if (solution) {
        pthread_mutex_unlock(&q->mutex);
        return;
    }

    q->items[q->length++] = item;

    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->mutex);
}

uint64_t queue_pop(queue_t *q) {
    pthread_mutex_lock(&q->mutex);

    while (q->length == 0 && !solution) {
        pthread_cond_wait(&q->not_empty, &q->mutex);
    }

    if (solution) {
        pthread_mutex_unlock(&q->mutex);
        return 0;
    }

    uint64_t result = q->items[0];
    q->length--;

    for (size_t i = 0; i < q->length; i++) {
        q->items[i] = q->items[i+1];
    }

    pthread_cond_signal(&q->not_full);
    pthread_mutex_unlock(&q->mutex);

    return result;
}

uint64_t hash(uint64_t x) {
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    x = x ^ (x >> 31);
    return x;
}

const uint64_t SLICE_SIZE = 1000000;
const uint64_t LOWER_BITS_MASK = 0xfffffff;

uint64_t seed;
queue_t queue;

int main() {
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
    uint64_t slice_base = SLICE_SIZE;

    while (1) {
        pthread_mutex_lock(&solution_mutex);
        if (solution) {
            pthread_mutex_unlock(&solution_mutex);
            break;
        }
        pthread_mutex_unlock(&solution_mutex);

        queue_add(&queue, slice_base);
        slice_base += SLICE_SIZE;
    }

    return NULL;
}

void *miner(void* _) {
    while (1) {
        pthread_mutex_lock(&solution_mutex);
        if (solution) {
            pthread_mutex_unlock(&solution_mutex);
            break;
        }
        pthread_mutex_unlock(&solution_mutex);

        uint64_t base = queue_pop(&queue);

        for (uint64_t i = base; i < base + SLICE_SIZE; i++) {

            pthread_mutex_lock(&solution_mutex);
            if (solution) {
                pthread_mutex_unlock(&solution_mutex);
                return NULL;
            }
            pthread_mutex_unlock(&solution_mutex);

            uint64_t hashed = i ^ seed;
            for (int j = 0; j < 10; j++) {
                hashed = hash(hashed);
            }

            if ((hashed & LOWER_BITS_MASK) == 0) {
                pthread_mutex_lock(&solution_mutex);

                if (solution == 0) {
                    solution = i;
                    printf("miner found solution %" PRIu64 "\n", i);

                    // wake all waiting threads
                    pthread_mutex_lock(&queue.mutex);
                    pthread_cond_broadcast(&queue.not_empty);
                    pthread_cond_broadcast(&queue.not_full);
                    pthread_mutex_unlock(&queue.mutex);
                }

                pthread_mutex_unlock(&solution_mutex);
                return NULL;
            }
        }
    }

    return NULL;
}