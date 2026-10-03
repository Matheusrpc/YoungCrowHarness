"""Executable fixture; used only by tests, never a production client option."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode = sys.argv[1]
if mode == 'version':
    print('fixture 1.0.0')
elif mode == 'help':
    print('--json --ephemeral --sandbox --ignore-user-config')
elif mode == 'metadata-child':
    print('fixture 1.0.0', flush=True)
    child = subprocess.Popen([sys.executable, '-I', '-S', __file__, 'hang'])
    Path('child.pid').write_text(str(child.pid))
elif mode == 'metadata-rpc':
    for line in sys.stdin:
        query = json.loads(line)
        print(json.dumps({'id': query['id'], 'result': {'ready': True}}), flush=True)
elif mode == 'discover-exchange':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import mission_clients
    mission_clients.DISCOVERY_SECONDS = 2
    try:
        mission_clients._exchange(Path(sys.executable), ['-I', '-S', __file__, 'metadata-child'], Path.cwd())
    except ValueError:
        print('exchange-finished', flush=True)
elif mode in ('hang', 'child'):
    if mode == 'child':
        child = subprocess.Popen([sys.executable, '-I', '-S', __file__, 'hang'])
        Path('child.pid').write_text(str(child.pid))
    time.sleep(120)
elif mode == 'flood':
    while True:
        os.write(1, b'x' * 65536)
elif mode == 'crash':
    sys.exit(9)
elif mode == 'malformed':
    print('{"type":')
elif mode == 'secret':
    print('fixture-secret-never-print', file=sys.stderr)
    sys.exit(1)
elif mode == 'escape':
    try:
        os.setsid()
    except PermissionError:
        print('escape_refused')
    else:
        print('escaped')
else:
    nonce = json.loads(sys.stdin.read().split(': ', 1)[1])['probe_id']
    marker = Path('dispatches.txt')
    marker.write_text(marker.read_text() + '1\n' if marker.exists() else '1\n')
    if mode == 'effect-crash':
        sys.exit(9)
    if mode == 'effect-truncated':
        print('{"type":')
        sys.exit(0)
    print(json.dumps({'type': 'thread.started', 'thread_id': 'fixture'}))
    print(json.dumps({'type': 'turn.started'}))
    print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps({'probe_id': nonce})}}))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}))
    if mode == 'after-effect':
        sys.stdout.flush()
        time.sleep(120)
