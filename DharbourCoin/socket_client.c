#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>
#include <arpa/inet.h>

#define PORT 8080
#define SLICE_SIZE 1000000
#define LOWER_BITS_MASK 0xfffffff

typedef struct {
    uint64_t seed;
    uint64_t slice_base;
} task_t;

typedef struct {
    char name[32];
    uint64_t solution;
} result_t;

uint64_t hash(uint64_t x) {
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;
    x = (x ^ (x >> 27)) * 0x94d049bb133111eb;
    x = x ^ (x >> 31);
    return x;
}

int mine(uint64_t seed, uint64_t base, uint64_t *result) {
    for (uint64_t i = base; i < base + SLICE_SIZE; i++) {
        uint64_t h = i ^ seed;

        for (int j = 0; j < 10; j++)
            h = hash(h);

        if ((h & LOWER_BITS_MASK) == 0) {
            *result = i;
            return 1;
        }
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <name>\n", argv[0]);
        return 1;
    }

    char *name = argv[1];

    while (1) {
        int sockfd;
        struct sockaddr_in servaddr;

        sockfd = socket(AF_INET, SOCK_STREAM, 0);

        servaddr.sin_family = AF_INET;
        servaddr.sin_port = htons(PORT);
        servaddr.sin_addr.s_addr = inet_addr("127.0.0.1");

        connect(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr));

        task_t task;
        recv(sockfd, &task, sizeof(task), 0);

        close(sockfd);

        printf("Got slice: %lu\n", task.slice_base);

        uint64_t solution;

        if (mine(task.seed, task.slice_base, &solution)) {
            printf("FOUND: %lu\n", solution);

            sockfd = socket(AF_INET, SOCK_STREAM, 0);
            connect(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr));

            result_t res;
            memset(&res, 0, sizeof(res));
            strncpy(res.name, name, 31);
            res.solution = solution;

            send(sockfd, &res, sizeof(res), 0);

            close(sockfd);
            break;
        }
    }

    return 0;
}