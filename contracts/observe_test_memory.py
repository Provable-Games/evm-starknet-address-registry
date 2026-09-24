"""Observe the existing test command without changing its output or success status."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time


def read(path):
    try:
        return path.read_text().strip()
    except OSError as error:
        return f'unavailable: {error.strerror}'


def host_snapshot():
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree', 'CommitLimit', 'Committed_AS'}:
            memory[key] = value.strip()
    membership = Path('/proc/self/cgroup').read_text()
    roots = {Path('/sys/fs/cgroup'), Path('/sys/fs/cgroup/memory')}
    directories = set(roots)
    for line in membership.splitlines():
        _, controllers, relative = line.split(':', 2)
        root = Path('/sys/fs/cgroup') if not controllers else Path('/sys/fs/cgroup/memory')
        if controllers and 'memory' not in controllers.split(','):
            continue
        parts = Path(relative.lstrip('/')).parts
        if '..' in parts:
            continue
        current = root.joinpath(*parts)
        while current != root:
            directories.add(current)
            current = current.parent
    cgroups = {}
    for directory in sorted(directories):
        for name in ['memory.max', 'memory.current', 'memory.peak', 'memory.events', 'cpu.max',
                     'memory.limit_in_bytes', 'memory.max_usage_in_bytes']:
            path = directory / name
            if path.is_file():
                cgroups[str(path)] = read(path)
    return {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'architecture': platform.machine(), 'logical_cpus': os.cpu_count(),
            'affinity_cpus': len(os.sched_getaffinity(0)), 'memory': memory,
            'cgroup_membership': membership, 'cgroup_observations': cgroups}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A test command is required')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'host-before.json').write_text(json.dumps(host_snapshot(), indent=2) + '\n')
    start = time.monotonic()
    result = subprocess.run(command, check=False)
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    observation = {
        'command': command, 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start,
        'maximum_child_rss_kib': usage.ru_maxrss, 'child_user_seconds': usage.ru_utime,
        'child_system_seconds': usage.ru_stime,
        'scope': 'Linux waited-child resource accounting; maximum RSS is not simultaneous process-tree total. Cgroup peaks/events may predate this command.',
    }
    (args.output / 'test-resources.json').write_text(json.dumps(observation, indent=2) + '\n')
    (args.output / 'host-after.json').write_text(json.dumps(host_snapshot(), indent=2) + '\n')
    print(json.dumps(observation), flush=True)
    raise SystemExit(result.returncode if result.returncode >= 0 else 128 - result.returncode)


if __name__ == '__main__':
    main()
