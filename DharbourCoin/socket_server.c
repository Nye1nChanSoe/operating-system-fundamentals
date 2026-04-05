#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>
#include <arpa/inet.h>
#include <time.h>

#define PORT 8080
#define SLICE_SIZE 1000000

typedef struct {
    uint64_t seed;
    uint64_t slice_base;
} task_t;

typedef struct {
    char name[32];
    uint64_t solution;
} result_t;

int main() {
    int sockfd, connfd;
    struct sockaddr_in servaddr, cli;

    sockfd = socket(AF_INET, SOCK_STREAM, 0);

    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = INADDR_ANY;
    servaddr.sin_port = htons(PORT);

    bind(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr));
    listen(sockfd, 5);

    printf("Server started...\n");

    srand(time(NULL));
    uint64_t seed = rand();
    uint64_t slice_base = 0;

    while (1) {
        socklen_t len = sizeof(cli);
        connfd = accept(sockfd, (struct sockaddr*)&cli, &len);

        // Try to receive result (blocking but fine)
        result_t res;
        int n = recv(connfd, &res, sizeof(res), MSG_DONTWAIT);

        if (n > 0) {
            printf("\n🏆 SOLUTION FOUND!\n");
            printf("Winner: %s\n", res.name);
            printf("Nonce: %lu\n", res.solution);
            close(connfd);
            break;
        }

        // Otherwise send task
        task_t task;
        task.seed = seed;
        task.slice_base = slice_base;

        send(connfd, &task, sizeof(task), 0);

        printf("Assigned slice: %lu\n", slice_base);

        slice_base += SLICE_SIZE;

        close(connfd);
    }

    close(sockfd);
    return 0;
}