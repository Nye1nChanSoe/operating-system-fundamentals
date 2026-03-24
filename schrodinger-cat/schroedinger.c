#include <stdio.h>
#include <stdlib.h>
#include <spawn.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <signal.h>

extern char **environ;

int main() {

    const int NUM_CATS = 100;
    pid_t child_pids[100];

    for (int i = 0; i < NUM_CATS; i++) {
        // Argv are command line arguments.
        // By convention, the first arguments needs to be the command name.
        char* argv[] = {"cat", NULL};
        pid_t last_child_pid;

        // The first argument to posix_spawn is a pointer - figure out why.
        int status = posix_spawn(&last_child_pid, "./cat", NULL, NULL, argv, environ);
        if (status < 0) {
            printf("failed to spawn a cat, terminating the experiment\n");
            return 1;
        }

        // store each cat's process id
        child_pids[i] = last_child_pid;
    }
    sleep(1);

    // checking process with Wait No Hang option: WNOHANG
    int cats_alive;
    for (int i = 0; i < NUM_CATS; i++) {
        int status;
        pid_t result = waitpid(child_pids[i], &status, WNOHANG);

        // when the process is still running -> alive
        if (result == 0) {
            cats_alive++;
        }
    }

    printf("%d cats are ok\n", cats_alive);

    // cleanup
    for (int i = 0; i < NUM_CATS; i++) {
        kill(child_pids[i], SIGKILL);
    }
}