"""Read the explicitly staged file inside the task namespace."""
import os
from pathlib import Path
import sys

state, host_net, host_pid, start, count = sys.argv[1:]
if (os.readlink("/proc/self/ns/net") == host_net or os.readlink("/proc/self/ns/pid") == host_pid
        or set(os.environ) - {"PATH", "LC_CTYPE", "PWD"} or Path(state).exists()):
    raise SystemExit(3)
offset, length = int(start), int(count)
if not 0 <= offset <= 262144 or not 0 <= length <= 262144:
    raise SystemExit(2)
with open("/input.txt", "rb") as file:
    file.seek(offset)
    sys.stdout.buffer.write(file.read(length))
