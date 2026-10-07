"""Local launcher stand-in. Only tests select this transport; no Docker commands."""
import base64
import hashlib
import json
import socket
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def injection_exchange(manifest, port):
    """Real fixture -> relay -> SOCKS guard; only TLS/upstream injection is simulated."""
    sys.path.insert(0,str(ROOT/'runtime/sbx'))
    import fixture
    import relay
    connect=socket.create_connection
    def upstream(proxy,host,timeout,register,context):
        sock=connect(('127.0.0.1',port),timeout=timeout)
        register(sock)
        sock.sendall(b'\x05\x01\x00');assert sock.recv(2)==b'\x05\x00'
        name=host.encode('ascii')
        sock.sendall(b'\x05\x01\x00\x03'+bytes([len(name)])+name+b'\x01\xbb')
        assert sock.recv(10)[:2]==b'\x05\x00'
        return sock
    policy=manifest['relay']
    with patch.object(relay,'PORT',0):
        bridge=relay.Relay(deadline_ms=manifest['deadline_ms'],proxy_ipv4=manifest['network']['proxy_ipv4'],
            policy=relay.echo_policy(manifest['nonce'],policy['phase'],policy['placeholder']),claim=lambda:None,context=None)
    endpoint=bridge.port;bridge.port=62143  # Separate native namespaces share this fixed logical port.
    def namespace(address,timeout):
        assert address==('127.0.0.1',62143)
        return connect(('127.0.0.1',endpoint),timeout=timeout)
    try:
        with patch.object(relay,'open_upstream',side_effect=upstream),patch.object(fixture.socket,'create_connection',side_effect=namespace):
            bridge.start()
            try:
                result=fixture.request(manifest['nonce'],policy['phase'],policy['placeholder'],
                    manifest['deadline_ms'],injection_sha256=policy['injection_sha256'])
                code=0
            except (ValueError,OSError):
                result=dict(kind='fixture_refused',reason='request_failed');code=126
            assert bridge.done.wait(2)
    finally:
        stopped=bridge.stop()
    return result,dict(bridge.result(),stopped=stopped),code


class Launcher:
    def __init__(self, mode, directory):
        self.mode, self.root = mode, Path(directory)

    def prepare(self, image, manifest):
        self.manifest = manifest
        with (self.root/'launch.json').open('xb') as stream:
            stream.write(encoded(manifest))
        record = dict(schema_version=1, container_id='a'*64, image=image,
                      operation_id=manifest['operation_id'], nonce=manifest['nonce'],
                      manifest_sha256=hashlib.sha256(encoded(manifest)).hexdigest())
        if self.mode == 'prepare_identity':
            record['image'] = 'sha256:'+'b'*64
        return record

    def start(self, manifest):
        import mission_controller as controller
        return controller.Channel([sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                                   '--launcher', self.mode], cwd=self.root,
                                  deadline_ms=manifest['deadline_ms'])

    def network(self, manifest, phase):
        gate = dict(operation_id=manifest['operation_id'], nonce=manifest['nonce'], phase=phase,
                    manifest_sha256=hashlib.sha256(encoded(manifest)).hexdigest(),
                    network_namespace='net:[123]')
        if self.mode == 'gate_identity' and phase == 'initialize':
            gate['nonce'] = '0'*32
        if self.mode == 'namespace_changed' and phase == 'dispatch':
            gate['network_namespace'] = 'net:[456]'
        (self.root/('network-'+phase+'.json')).write_bytes(encoded(gate))
        return gate


def launch(mode):
    root = Path.cwd()
    manifest = json.loads((root/'launch.json').read_bytes())
    def emit(event):
        raw = encoded(event)+b'\n'
        for at in range(0, len(raw), 17):
            sys.stdout.buffer.write(raw[at:at+17])
            sys.stdout.buffer.flush()
    def output(phase, value):
        raw = encoded(value)+b'\n'
        for at in range(0, len(raw), 23):
            emit(dict(kind='output', phase=phase, stream='stdout',
                      data=base64.b64encode(raw[at:at+23]).decode()))
    if mode == 'truncated':
        sys.stdout.write('{')
        return 0
    if mode == 'oversized':
        sys.stdout.write('x'*20000)
        return 0
    emit(dict(kind='listening', operation_id=('00000000-0000-0000-0000-000000000000'
                                             if mode == 'listening_identity' else manifest['operation_id'])))
    for phase in ('initialize', 'dispatch'):
        line = sys.stdin.buffer.readline()
        if not line:
            emit(dict(kind='refused', reason='control_closed', errno=None))
            return 125
        message = json.loads(line)
        expected = dict(schema_version=1, operation_id=manifest['operation_id'],
                        nonce=manifest['nonce'], action=phase)
        if phase == 'dispatch':
            expected['argv'] = manifest['dispatch_prefix']
        if message != expected or not (root/('network-'+phase+'.json')).is_file():
            return 125
        if mode == 'hang' and phase == 'initialize':
            child = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(30)'])
            (root/'helper.pid').write_text(str(child.pid))
            time.sleep(30)
        if mode == 'early_ready':
            emit(dict(kind='ready'))
            return 0
        emit(dict(kind='started', phase=phase))
        if mode == 'duplicate_started':
            emit(dict(kind='started', phase=phase))
        if phase == 'initialize':
            output(phase, dict(schema_version=1, fixture_id='isolated-egress-v1', stage=phase,
                               network_requests=0, model_calls=0))
            emit(dict(kind='finished', phase=phase, exit_code=0))
            if mode == 'discovery_descendants':
                emit(dict(kind='refused', reason='discovery_descendants', errno=None))
                return 125
            emit(dict(kind='ready'))
        else:
            with (root/'dispatches').open('ab') as stream:
                stream.write(b'1\n')
            blocked = mode == 'unattributed_block'
            network_path = root/'loopback-network.json'
            if network_path.exists() and manifest['schema_version'] != 4:
                network = json.loads(network_path.read_bytes())
                if blocked:
                    try:
                        with socket.create_connection(('127.0.0.1',network['port']),timeout=1):
                            raise AssertionError('B unexpectedly connected')
                    except ConnectionRefusedError:
                        pass
                else:
                    with socket.create_connection(('127.0.0.1',network['port']),timeout=1) as sock:
                        sock.sendall(b'\x05\x01\x00')
                        assert sock.recv(2) == b'\x05\x00'
                        host = b'postman-echo.com'
                        sock.sendall(b'\x05\x01\x00\x03'+bytes([len(host)])+host+b'\x01\xbb')
                        assert sock.recv(10)[:2] == b'\x05\x00'
                        sock.sendall(b'local-request')
                        assert sock.recv(64) == b'local-response'
                        assert sock.recv(64) == b''  # Upstream closes first, exercising TIME_WAIT.
                (root/'loopback-result.json').write_bytes(encoded(dict(network, blocked=blocked)))
            value = (dict(kind='fixture_refused', reason='request_failed') if blocked else
                     dict(schema_version=1, fixture_id='isolated-egress-v1', stage=phase,
                          nonce=manifest['nonce'], phase=manifest['relay']['phase'], http_status=200,
                          echo_matches=True, response_sha256='b'*64, network_requests=1, model_calls=0))
            if manifest['schema_version'] == 4 and not blocked and mode != 'legacy_echo':
                value.pop('echo_matches')
                value.update(schema_version=2,injection_matches=True,
                    injected_value_sha256='0'*64 if mode=='wrong_injection_hash' else manifest['relay']['injection_sha256'])
            if mode == 'bad_echo':
                value['nonce'] = '0'*32
            relay_result=dict(state='refused' if blocked else 'succeeded',
                reason='proxy_connect_refused' if blocked else None,requests=1,
                bytes_forwarded=0 if blocked else 300,stopped=True)
            code=126 if blocked else 0
            if manifest['schema_version']==4 and network_path.exists():
                network=json.loads(network_path.read_bytes())
                value,relay_result,code=injection_exchange(manifest,network['port'])
                (root/'injection-result.json').write_bytes(encoded(value))
            output(phase, value)
            emit(dict(kind='relay_finished',**relay_result))
            emit(dict(kind='finished', phase=phase, exit_code=code))
            if mode == 'extra_event':
                emit(dict(kind='ready'))
            return code


def control(mode):
    import mission_controller as controller
    root = Path.cwd()
    request = json.load(sys.stdin)
    def persist(kind, payload):
        if not (root/'owner.json').is_file():
            raise ValueError('ownership missing')
        if ((mode == 'persist_failure' and kind == 'initialize_intent') or
                (mode == 'dispatch_persist_failure' and kind == 'dispatch_authorization') or
                (mode == 'observation_persist_failure' and kind == 'observed')):
            raise OSError('private-error-canary')
        with (root/(kind+'.json')).open('xb') as stream:
            stream.write(encoded(payload))
    result = controller.run_phase(Launcher(mode, root), request, 'sha256:'+'c'*64, persist)
    print(json.dumps(result), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(launch(sys.argv[2]) if sys.argv[1] == '--launcher' else control(sys.argv[2]))
