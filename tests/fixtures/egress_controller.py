"""Real containment around the guard; DNS substitution never leaves loopback."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import mission_egress as egress


if sys.argv[1:2] == ['--dns']:
    if sys.argv[2] == 'hang':
        time.sleep(10)
    print('x'*17000 if sys.argv[2] == 'oversized' else '["8.8.8.8"]', flush=True)
    raise SystemExit()

if sys.argv[1:] == ['--guard-local']:
    config = json.loads(sys.stdin.buffer.readline(16385))
    def connect(*args, **kwargs):
        upstream, peer = socket.socketpair()
        count = Path.cwd()/'upstream-count'
        count.write_text('0')
        def echo():
            with peer:
                received = peer.recv(1024)
                count.write_text(str(len(received)))
                if not received:
                    return
                peer.sendall(b'local-response')
                peer.shutdown(socket.SHUT_WR)
        threading.Thread(target=echo).start()
        return upstream, dict(host=egress.HOST,port=443,resolved=['8.8.8.8'],selected_ip='8.8.8.8',
            peer='8.8.8.8',peer_port=443,family='IPv4',decision='connected')
    egress.connect_checked = connect
    def emit(kind, **row):
        print(json.dumps(dict(kind='egress',event=kind,**row)),flush=True)
        assert json.loads(sys.stdin.buffer.readline(1025)) == dict(event=kind)
    raise SystemExit(egress.serve(config,emit))

request = json.load(sys.stdin)
if request['mode'].startswith('dns_'):
    mode = request['mode'].removeprefix('dns_')
    spawned = []
    popen = subprocess.Popen
    def local_dns(argv, **kwargs):
        if '--resolve' in argv:
            argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--dns', mode]
        process = popen(argv, **kwargs)
        spawned.append(process)
        return process
    egress.subprocess = subprocess
    subprocess.Popen = local_dns
    try:
        addresses = egress.resolve_addresses(egress.HOST, .1 if mode == 'hang' else 2)
        result = dict(addresses=addresses)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result = dict(error=type(error).__name__)
    result.update(children=len(spawned), collected=all(p.poll() is not None for p in spawned))
else:
    events = []
    def persist(kind, payload):
        events.append(dict(kind=kind, payload=json.loads(json.dumps(payload))))
        if request['mode'] == 'persist_failure' and kind == 'guard_started':
            raise ValueError('disk')
        if request['mode'] == 'kill_before_config' and kind == 'guard_started':
            os._exit(71)  # Abrupt controller death: only the outer owner can collect the helper.
        if request['mode'] == 'guard_domain_persistfail' and kind == 'guard_destination':
            raise ValueError('disk')
    guard = None
    try:
        class LocalGuard(egress.Guard):
            def command(self):
                return [sys.executable,'-I','-B',str(Path(__file__).resolve()),'--guard-local']
        guard_type = LocalGuard if request['mode'].startswith('guard_domain') else egress.Guard
        guard = guard_type(request['config'], persist, cwd=Path.cwd())
        port = guard.port
        with socket.create_connection(('127.0.0.1', port), timeout=1) as client:
            client.sendall(b'\x05\x01\x00')
            assert client.recv(2) == b'\x05\x00'
            if request['mode'].startswith('guard_domain'):
                host = egress.HOST.encode()
                client.sendall(b'\x05\x01\x00\x03'+bytes([len(host)])+host+b'\x01\xbb')
                reply = client.recv(10)
                if request['mode']=='guard_domain_persistfail':
                    assert reply == b''
                    raise ValueError('receipt_refused')
                assert reply[:2]==b'\x05\x00'
                client.sendall(b'local-request')
                if request['mode']=='guard_domain':
                    client.shutdown(socket.SHUT_WR)
                assert client.recv(64)==b'local-response'
                assert client.recv(64)==b''
            else:
                client.sendall(b'\x05\x01\x00\x01'+b'\x7f\x00\x00\x01\x01\xbb')
        result = guard.finish()
        result['port_free'] = egress.port_available(port)
    except (ValueError, OSError) as error:
        result = dict(error=type(error).__name__)
    finally:
        if guard:
            guard.close()
    result['events'] = events
    if (Path.cwd()/'upstream-count').exists():
        result['upstream_bytes'] = int((Path.cwd()/'upstream-count').read_text())
print(json.dumps(result), flush=True)
