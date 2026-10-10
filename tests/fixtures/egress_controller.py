"""Real containment around the guard; DNS substitution never leaves loopback."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import mission_egress as egress


if sys.argv[1:2] == ['--dns']:
    if sys.argv[2] == 'hang':
        time.sleep(10)
    print('x'*17000 if sys.argv[2] == 'oversized' else '["8.8.8.8"]', flush=True)
    raise SystemExit()

if sys.argv[1:2] in (['--guard-local'],['--guard-echo'],['--guard-echo-no-injection']):
    config = json.loads(sys.stdin.buffer.readline(16385))
    def connect(*args, **kwargs):
        if sys.argv[1] == '--guard-local' and len(sys.argv) == 3:
            upstream = socket.create_connection(('127.0.0.1', int(sys.argv[2])), timeout=5)
            return upstream, dict(host=egress.HOST,port=443,resolved=['8.8.8.8'],selected_ip='8.8.8.8',
                peer='8.8.8.8',peer_port=443,family='IPv4',decision='connected')
        upstream, peer = socket.socketpair()
        count = Path.cwd()/'upstream-count'
        count.write_text('0')
        def echo():
            with peer:
                received = peer.recv(1024)
                if sys.argv[1] != '--guard-local':
                    while received and b'\r\n\r\n' not in received:
                        part=peer.recv(1024)
                        if not part: break
                        received+=part
                count.write_text(str(len(received)))
                if not received:
                    return
                response=b'local-response'
                if sys.argv[1] != '--guard-local':
                    target=received.split(b' ',2)[1].decode('ascii')
                    marker=next(line.split(b': ',1)[1].decode('ascii') for line in received.split(b'\r\n')
                                if line.startswith(b'X-Youngcrow-Probe: '))
                    assert marker.startswith('youngcrow-probe-')
                    injected=marker if sys.argv[1]=='--guard-echo-no-injection' else 'disposable-test-injection'
                    args={k:v[0] for k,v in parse_qs(urlsplit(target).query).items()}
                    body=json.dumps(dict(args=args,headers={'x-youngcrow-probe':injected},
                                         url='https://postman-echo.com'+target)).encode()
                    response=(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '
                              +str(len(body)).encode()+b'\r\n\r\n'+body)
                peer.sendall(response)
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
    observer = None
    offered_bytes = 0
    if request['mode'].startswith('guard_domain'):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(5)
        upstream_port = listener.getsockname()[1]
        observation = dict(accepted=False, eof=False, bytes=0, complete=False)
        guard_closed = threading.Event()
        def observe():
            try:
                peer, _ = listener.accept()
                with peer:
                    peer.settimeout(5)
                    observation['accepted'] = True
                    while True:
                        chunk = peer.recv(1024)
                        if not chunk:
                            observation['eof'] = True
                            break
                        first = observation['bytes'] == 0
                        observation['bytes'] += len(chunk)
                        if first:
                            peer.sendall(b'local-response')
                            peer.shutdown(socket.SHUT_WR)
                # Force the receipt to finish after collection of the guard.
                observation['complete'] = guard_closed.wait(5)
            except OSError as error:
                observation['error'] = type(error).__name__
        observer = threading.Thread(target=observe)
        observer.start()
    try:
        class LocalGuard(egress.Guard):
            def command(self):
                return [sys.executable,'-I','-B',str(Path(__file__).resolve()),'--guard-local',str(upstream_port)]
        guard_type = LocalGuard if request['mode'].startswith('guard_domain') else egress.Guard
        guard = guard_type(request['config'], persist, cwd=Path.cwd())
        port = guard.port
        with socket.create_connection(('127.0.0.1', port), timeout=1) as client:
            client.sendall(b'\x05\x01\x00')
            assert client.recv(2) == b'\x05\x00'
            if request['mode'].startswith('guard_domain'):
                host = egress.HOST.encode()
                early_payload = b'local-request' if request['mode']=='guard_domain_persistfail' else b''
                client.sendall(b'\x05\x01\x00\x03'+bytes([len(host)])+host+b'\x01\xbb'+early_payload)
                offered_bytes += len(early_payload)
                reply = client.recv(10)
                if request['mode']=='guard_domain_persistfail':
                    assert reply == b''
                    raise ValueError('receipt_refused')
                assert reply[:2]==b'\x05\x00'
                client.sendall(b'local-request')
                offered_bytes += len(b'local-request')
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
        try:
            if guard:
                guard.close()
        finally:
            if observer:
                guard_closed.set()
                try:
                    observer.join(6)
                    assert not observer.is_alive(), 'upstream observer leaked'
                finally:
                    listener.close()
    result['events'] = events
    if observer:
        result['upstream_observation'] = observation
        result.update(upstream_bytes=observation['bytes'],
                      upstream_observed_after_close=(observation['accepted'] and observation['eof']
                                                     and observation['complete']
                                                     and 'error' not in observation),
                      offered_bytes=offered_bytes)
        # Emit the observation before validation so CI can diagnose a rejected
        # receipt without exposing the subprocess traceback or accepting it.
        print(json.dumps(result), flush=True)
        assert observation['accepted'] and observation['eof'] and observation['complete'], observation
        assert 'error' not in observation, observation
        # Successful fixtures still emit one JSON document on stdout.
        raise SystemExit()
print(json.dumps(result), flush=True)
