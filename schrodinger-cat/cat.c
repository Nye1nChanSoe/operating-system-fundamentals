#define _GNU_SOURCE // needed for execvp
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
     // initialize random number generator from system timer with nanosecond precision
    struct timespec current_time;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &current_time);
    srand(current_time.tv_nsec);

    int alive = rand() % 2;

    if (alive) {
        printf("alive! =^o.o^=\n");
        for (;;) sleep(1);
    } else {
        printf("dead   =^x.x^=\n");
        _exit(EXIT_FAILURE);
    }
}