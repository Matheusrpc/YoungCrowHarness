"""Local lifetime proof only: no model, credentials or network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def identity(pid='self'):
    raw = Path(f'/proc/{pid}/stat').read_text()
    fields = raw.rsplit(')', 1)[1].split()
    return dict(pid=int(raw.split()[0]), start=fields[19], group=int(fields[2]))


mode = sys.argv[1]
if mode in ('controller', 'before-dispatch'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import mission_process
    plan = dict(argv=[sys.executable, '-I', '-S', __file__, 'hang'], cwd=os.getcwd(),
                stdin=b'', timeout_seconds=2, output_limit_bytes=4096,
                connection='authenticated', execution_contract='isolated-tools', environment_overrides={})
    def started(owner):
        Path('owner.json').write_text(json.dumps(owner))
        if mode == 'before-dispatch':
            os._exit(0)
    result = mission_process.supervise(plan, on_started=started, stop_requested=lambda: False)
    print(result['reason'])
elif mode == 'orphan':
    Path('orphan.json').write_text(json.dumps(identity()))
    time.sleep(15)
elif mode == 'detached':
    Path('detached.json').write_text(json.dumps(identity()))
    subprocess.Popen([sys.executable, '-I', '-S', __file__, 'orphan'], start_new_session=True)
else:
    # Same operation that Codex performs before spawning exec-server.
    os.setpgid(0, 0)
    Path('client.json').write_text(json.dumps(identity()))
    parent = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[1]
    Path('guardian.json').write_text(json.dumps(identity(parent)))
    subprocess.Popen([sys.executable, '-I', '-S', __file__, 'detached'], start_new_session=True)
    deadline = time.monotonic() + 5
    while not Path('orphan.json').exists() and time.monotonic() < deadline:
        time.sleep(.01)
    print('groups-ready', flush=True)
    if mode == 'hang':
        time.sleep(15)
