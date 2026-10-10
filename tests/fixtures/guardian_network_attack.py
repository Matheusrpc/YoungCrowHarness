"""Unpaid network-gate client: local identity and pinned DNS only."""
import ctypes
import json
import os
from pathlib import Path
import socket
import sys
import time

assert socket.gethostbyname('api.openai.com') == '1.1.1.1'
status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
assert os.getuid() == 1000 and int(status['CapBnd'], 16) == 0 and status['NoNewPrivs'].strip() == '1'
assert set(os.environ) == {'HOME', 'LANG', 'PATH', 'PYTHONDONTWRITEBYTECODE'}
# Creating a new network namespace or obtaining a raw socket needs capabilities.
libc = ctypes.CDLL(None, use_errno=True)
assert libc.unshare(0x40000000) == -1 and ctypes.get_errno() == 1
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
except PermissionError:
    pass
else:
    sock.close()
    raise AssertionError('raw socket was allowed')
for phase in ('initialize', 'dispatch'):
    try:
        (Path('/control') / ('network-'+phase+'.json')).read_bytes()
    except PermissionError:
        pass
    else:
        raise AssertionError('network gate was accessible')
print(json.dumps({'uid':1000,'caps_empty':True,'network_mutation_denied':True,'pinned_dns':True}),flush=True)
if sys.argv[1] == 'wait':time.sleep(30)
