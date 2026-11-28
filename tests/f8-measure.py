"""Measure fixed synthetic regressions without changing their permissions or concurrency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
INTERVAL = 0.1
TIMEOUT = 75
FIXTURES = {
    "context": "tests/fase7-contexto.py",
    "review": "tests/fase5-review.py",
    "recovery": "tests/fase6-d07-restart.py",
}


def command(workload):
    if workload == "context":
        return [sys.executable, "-I", "-B", FIXTURES[workload]]
    suite = runpy.run_path(str(ROOT / "tests/run-suite.py"))
    paths = []
    for name, expected in suite["ARTIFACTS"].items():
        path = ROOT / ".fase1" / name
        with path.open("rb") as artifact:
            if hashlib.file_digest(artifact, "sha256").hexdigest() != expected:
                raise SystemExit(f"Unexpected pinned artifact: {name}")
        paths.append(path)
    bun, opencode = paths
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    if backend is None:
        raise SystemExit("Bubblewrap is required for the OpenCode workloads")
    if workload != "search":
        return [sys.executable, "-I", "-B", FIXTURES[workload]]
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    return supervisor["bubblewrap_command"](backend, [
        (bun, "/fixture/bun"), (opencode, "/fixture/opencode"),
        (ROOT / "tests", "/tests"), (ROOT / "implementacion", "/implementacion"),
    ], ["/usr/bin/env", "HOME=/tmp", "/fixture/bun", "/tests/fase7-contexto-selectivo.ts", "/fixture/opencode"])


def process_tree(root_pid):
    table = {}
    with os.scandir("/proc") as entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                with open(entry.path + "/stat", "rb") as stat_file:
                    values = stat_file.read().rsplit(b")", 1)[1].split()
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
            if values[0] != b"Z":
                table[int(entry.name)] = (
                    int(values[1]), max(0, int(values[21])), int(values[19]), int(values[11]), int(values[12]),
                )
    seen = {root_pid} & table.keys()
    pending = list(seen)
    children = {}
    for pid, (parent, *_) in table.items():
        children.setdefault(parent, []).append(pid)
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return (
        len(seen), sum(table[pid][1] for pid in seen) * os.sysconf("SC_PAGE_SIZE"),
        {(pid, table[pid][2]): table[pid][3:] for pid in seen},
    )


def measure(args, home):
    with tempfile.TemporaryFile() as log:
        start = time.monotonic()
        with subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=log, start_new_session=True,
                              env={"PATH": "/usr/bin:/bin", "HOME": home}) as child:
            peak_count = peak_tree_rss = 0
            samples = 0
            sampling_cpu = 0.0
            observed_cpu = {}
            try:
                while True:
                    pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                    if pid:
                        child.returncode = os.waitstatus_to_exitcode(status)
                        break
                    if time.monotonic() - start >= TIMEOUT:
                        raise TimeoutError("Synthetic workload exceeded its deadline")
                    sample_started = time.process_time()
                    count, rss, cpu = process_tree(child.pid)
                    sampling_cpu += time.process_time() - sample_started
                    samples += 1
                    observed_cpu.update(cpu)
                    peak_count = max(peak_count, count)
                    peak_tree_rss = max(peak_tree_rss, rss)
                    time.sleep(INTERVAL)
            finally:
                if child.returncode is None:
                    # The unreaped child still owns this process-group ID.
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=5)
        wall = time.monotonic() - start
        ticks_per_second = os.sysconf("SC_CLK_TCK")
        sampled_user = sum(usage[0] for usage in observed_cpu.values()) / ticks_per_second
        sampled_system = sum(usage[1] for usage in observed_cpu.values()) / ticks_per_second
        log.seek(0)
        output = log.read().decode(errors="replace")
        if child.returncode:
            raise SystemExit(output)
        evidence = [line for line in output.splitlines() if line.startswith("PASS")]
        tokens = [json.loads(line) for line in output.splitlines() if line.startswith('{"baselineToolBytes":')]
        restart = [json.loads(line)["restartTiming"] for line in output.splitlines()
                   if line.startswith('{"restartTiming":')]
        return {
            "wall_seconds": round(wall, 3),
            "wait4_user_cpu_seconds": round(usage.ru_utime, 3),
            "wait4_system_cpu_seconds": round(usage.ru_stime, 3),
            "sampled_tree_user_cpu_seconds": round(sampled_user, 3),
            "sampled_tree_system_cpu_seconds": round(sampled_system, 3),
            "sampled_cpu_percent_one_core": round(100 * (sampled_user + sampled_system) / wall, 1),
            "wait4_peak_rss_kib": usage.ru_maxrss,
            "sampled_peak_processes": peak_count,
            "sampled_peak_tree_rss_bytes": peak_tree_rss,
            "process_tree_samples": samples,
            "sampler_cpu_seconds": round(sampling_cpu, 6),
            "tool_output_estimates": tokens,
            "restart_timing": restart,
            "evidence": evidence,
        }


def summarize(results):
    metrics = (
        "wall_seconds", "wait4_user_cpu_seconds", "wait4_system_cpu_seconds",
        "sampled_cpu_percent_one_core", "sampled_peak_tree_rss_bytes",
        "sampled_peak_processes", "sampler_cpu_seconds",
    )
    summary = {}
    for metric in metrics:
        values = [result[metric] for result in results]
        summary[metric] = {
            "min": min(values), "median": statistics.median(values), "max": max(values),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workload", choices=(*FIXTURES, "search"))
    parser.add_argument("--runs", type=int, choices=(1, 2, 3), default=2)
    options = parser.parse_args()
    if platform.system() != "Linux":
        raise SystemExit("The current measurement harness requires Linux")
    args = command(options.workload)
    results = []
    for _ in range(options.runs):
        with tempfile.TemporaryDirectory(prefix="cli-open-measure-") as home:
            results.append(measure(args, home))
    print(json.dumps({
        "workload": options.workload, "sample_interval_seconds": INTERVAL,
        "host": {"architecture": platform.machine(), "logical_cpus": os.cpu_count(),
                 "affinity_cpus": len(os.sched_getaffinity(0)),
                 "ram_bytes": os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")},
        "runs": results,
        "summary": summarize(results),
    }, indent=2))


if __name__ == "__main__":
    main()
