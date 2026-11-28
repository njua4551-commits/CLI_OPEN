#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/syscall.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

/* Test only. Hold a successful positional read before userspace resumes. */
static bool matches(pid_t thread, const char *target, bool paginated)
{
    struct user_regs_struct regs;
    if (ptrace(PTRACE_GETREGS, thread, 0, &regs) == -1)
        return false;
    if (regs.orig_rax != SYS_pread64 || (long long)regs.rax <= 0 ||
        (paginated && regs.r10 == 0))
        return false;
    char descriptor[64], path[PATH_MAX];
    snprintf(descriptor, sizeof descriptor, "/proc/%ld/fd/%llu", (long)thread, regs.rdi);
    ssize_t size = readlink(descriptor, path, sizeof path - 1);
    if (size < 0)
        return false;
    path[size] = '\0';
    return strcmp(path, target) == 0;
}

static int failed(const char *operation)
{
    perror(operation);
    return 1;
}

int main(int argc, char **argv)
{
    if (argc < 5 || (strcmp(argv[3], "first") && strcmp(argv[3], "page")))
        return 2;
    pid_t child = fork();
    if (child < 0)
        return failed("fork");
    if (child == 0) {
        if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1)
            _exit(failed("PTRACE_TRACEME"));
        raise(SIGSTOP);
        execv(argv[4], argv + 4);
        _exit(failed("execv"));
    }
    int status;
    if (waitpid(child, &status, 0) != child || !WIFSTOPPED(status))
        return 1;
    long options = PTRACE_O_EXITKILL | PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACEEXEC |
                   PTRACE_O_TRACECLONE | PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK;
    if (ptrace(PTRACE_SETOPTIONS, child, 0, options) == -1 ||
        ptrace(PTRACE_SYSCALL, child, 0, 0) == -1)
        return failed("start tracing");
    for (;;) {
        pid_t thread = waitpid(-1, &status, __WALL);
        if (thread < 0) {
            if (errno == EINTR)
                continue;
            return failed("waitpid");
        }
        if (!WIFSTOPPED(status)) {
            if (thread != child)
                continue;
            return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
        }
        int signal = WSTOPSIG(status);
        if (signal == (SIGTRAP | 0x80) && matches(thread, argv[1], strcmp(argv[3], "page") == 0)) {
            int marker = open(argv[2], O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
            if (marker < 0)
                return failed("open marker");
            int result = dprintf(marker, "%ld pread64\n", (long)thread);
            close(marker);
            if (result < 0)
                return failed("write marker");
            for (;;)
                pause();
        }
        if (signal == (SIGTRAP | 0x80) || status >> 16 || signal == SIGSTOP)
            signal = 0;
        if (ptrace(PTRACE_SYSCALL, thread, 0, signal) == -1 && errno != ESRCH)
            return failed("continue tracing");
    }
}
