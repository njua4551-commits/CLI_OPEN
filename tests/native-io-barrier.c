#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

/* Test only. Withhold one successful libc I/O result in the synthetic sandbox. */
static void hold_result(int fd, const char *operation)
{
    int saved = errno;
    const char *target = getenv("CLI_OPEN_TEST_IO_TARGET");
    const char *marker = getenv("CLI_OPEN_TEST_IO_MARKER");
    char descriptor[64], path[PATH_MAX], executable[PATH_MAX];
    if (target && marker) {
        snprintf(descriptor, sizeof descriptor, "/proc/self/fd/%d", fd);
        ssize_t length = readlink(descriptor, path, sizeof path - 1);
        ssize_t executable_length = readlink("/proc/self/exe", executable, sizeof executable - 1);
        if (length >= 0 && executable_length > 0) {
            path[length] = '\0';
            executable[executable_length] = '\0';
            const char *name = strrchr(executable, '/');
            if (name && strcmp(name + 1, "rg") == 0 && strcmp(path, target) == 0) {
                snprintf(descriptor, sizeof descriptor, "%ld %s\n", (long)getpid(), operation);
                int evidence = open(marker, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
                if (evidence >= 0) {
                    ssize_t written = write(evidence, descriptor, strlen(descriptor));
                    close(evidence);
                    if (written > 0)
                        for (;;) pause();
                }
            }
        }
    }
    errno = saved;
}

ssize_t read(int fd, void *buf, size_t count)
{
    ssize_t (*next)(int, void *, size_t) = dlsym(RTLD_NEXT, "read");
    ssize_t result = next(fd, buf, count);
    if (result > 0) hold_result(fd, "read");
    return result;
}

struct dirent *readdir(DIR *directory)
{
    struct dirent *(*next)(DIR *) = dlsym(RTLD_NEXT, "readdir");
    struct dirent *result = next(directory);
    if (result) hold_result(dirfd(directory), "readdir");
    return result;
}

struct dirent64 *readdir64(DIR *directory)
{
    struct dirent64 *(*next)(DIR *) = dlsym(RTLD_NEXT, "readdir64");
    struct dirent64 *result = next(directory);
    if (result) hold_result(dirfd(directory), "readdir64");
    return result;
}

void *mmap(void *address, size_t length, int protection, int flags, int fd, off_t offset)
{
    void *(*next)(void *, size_t, int, int, int, off_t) = dlsym(RTLD_NEXT, "mmap");
    void *result = next(address, length, protection, flags, fd, offset);
    if (result != MAP_FAILED && fd >= 0) hold_result(fd, "mmap");
    return result;
}

void *mmap64(void *address, size_t length, int protection, int flags, int fd, off64_t offset)
{
    void *(*next)(void *, size_t, int, int, int, off64_t) = dlsym(RTLD_NEXT, "mmap64");
    void *result = next(address, length, protection, flags, fd, offset);
    if (result != MAP_FAILED && fd >= 0) hold_result(fd, "mmap64");
    return result;
}
