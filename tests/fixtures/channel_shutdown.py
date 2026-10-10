"""Exercise child cleanup inside the test's existing process containment."""
import json
from pathlib import Path
import signal
import sys
import time

if sys.argv[1] == '--child':
    mode = sys.argv[2]
    if mode == 'stubborn':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print('{"kind":"ready"}', flush=True)
    assert sys.stdin.buffer.read(1) == b''
    if mode == 'stubborn':
        time.sleep(10)
    else:
        time.sleep(.02)
        Path('closed-after-eof').write_text('closed')
    raise SystemExit()

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from mission_controller import Channel

channel = Channel([sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                   '--child', sys.argv[1]], cwd=Path.cwd(),
                  deadline_ms=int(time.time()*1000)+5000)
try:
    assert channel.receive() == dict(kind='ready')
    started = time.monotonic()
    channel.close()
    print(json.dumps(dict(exit_code=channel.process.poll(),
        elapsed_seconds=time.monotonic()-started,
        readers_collected=all(not thread.is_alive() for thread in channel.threads),
        cooperative_cleanup=Path('closed-after-eof').exists())), flush=True)
finally:
    channel.close()
