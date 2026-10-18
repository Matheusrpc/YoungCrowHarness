"""PID 1 lifetime boundary for unprivileged tool servers; no command dispatch."""
import json
import os
from pathlib import Path
import signal
import time


def main():
    if os.getpid() != 1 or os.getuid() != 0:
        return 125
    signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
    signal.setitimer(signal.ITIMER_REAL, 1)
    manifest = json.loads(os.environ.pop('YC_WORKER_MANIFEST'))
    remaining = manifest['deadline_ms']/1000-time.time()-1
    if type(manifest['deadline_ms']) is not int or not 0 < remaining <= 119:
        return 125
    signal.setitimer(signal.ITIMER_REAL, remaining)
    deadline = time.monotonic()+remaining
    with Path('/control/consumed.json').open('x') as stream:
        json.dump(manifest, stream)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(dict(kind='ready', plan_sha256=manifest['plan_sha256'])), flush=True)
    while min(deadline-time.monotonic(), manifest['deadline_ms']/1000-time.time()-1) > 0:
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            pass
        time.sleep(.02)
    return 124


if __name__ == '__main__':
    try:
        status = main()
    except Exception:
        status = 125
    os._exit(status)
