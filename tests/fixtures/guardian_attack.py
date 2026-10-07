"""Synthetic client for the unpaid guardian proof; never calls a provider."""
import json
import os
from pathlib import Path
import signal
import sys
import time

mode = sys.argv[1]
if mode in {'discover', 'discover-fails'}:
    print(json.dumps({'synthetic_catalog': True}), flush=True)
    sys.exit(1 if mode == 'discover-fails' else 0)


def denied(action):
    try:
        action()
    except PermissionError:
        return True
    return False


status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
home = Path(os.environ['HOME']) / 'writable'
home.write_text('synthetic')
result = dict(kind='synthetic_worker', uid=os.getuid(), gid=os.getgid(),
              caps={k: status[k].strip() for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')},
              no_new_privs=status['NoNewPrivs'].strip(), stdin_closed=os.read(0, 1) == b'',
              control_read_denied=denied(lambda: Path('/control/launch.json').read_bytes()),
              control_write_denied=denied(lambda: Path('/control/dispatch.json').write_text('bad')),
              signal_denied=denied(lambda: os.kill(1, signal.SIGKILL)),
              parent_fds_denied=denied(lambda: list(Path('/proc/1/fd').iterdir())),
              sockets_absent=not any(Path(p).exists() for p in ('/var/run/docker.sock', '/run/docker.sock')),
              home_writable=home.read_text() == 'synthetic',
              env_keys=sorted(os.environ), fds=sorted(os.listdir('/proc/self/fd')),
              cpu_max=Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
              memory_max=Path('/sys/fs/cgroup/memory.max').read_text().strip(),
              pids_max=Path('/sys/fs/cgroup/pids.max').read_text().strip())
print(json.dumps(result), flush=True)
if mode == 'wait':
    time.sleep(30)
elif mode == 'output-limit':
    while True:
        os.write(1, b'x' * 4096)
