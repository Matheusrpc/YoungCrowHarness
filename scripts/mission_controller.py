"""Internal guardian channel controller; not a native dispatch entry point.

The installation coordinator must provide its owned launcher and durable journal.
This module runs inside mission_process containment, never starts another supervisor,
and cannot certify VM cleanup, native egress attribution or an execution profile.
"""
import base64
import hashlib
import ipaddress
import json
import queue
import re
import subprocess
import threading
import time
import uuid

from capabilities import parse_json

CONTROLLER_VERSION = 1
FRAME_LIMIT = 16384
CAPTURE_LIMIT = 65536
FIXTURE_ARGV = ['/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/fixture.py']


class Refused(Exception):
    pass


def require(condition, reason='protocol_failed'):
    if not condition:
        raise Refused(reason)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def phase_manifest(*, operation_id, nonce, deadline_ms, phase, proxy_ipv4, ca_sha256, placeholder, injection_sha256=None):
    require(type(deadline_ms) is int and 1000 < deadline_ms-time.time()*1000 <= 120000, 'invalid_manifest')
    return _manifest(operation_id=operation_id, nonce=nonce, deadline_ms=deadline_ms, phase=phase,
                     proxy_ipv4=proxy_ipv4, ca_sha256=ca_sha256, placeholder=placeholder, injection_sha256=injection_sha256)


def _manifest(*, operation_id, nonce, deadline_ms, phase, proxy_ipv4, ca_sha256, placeholder, injection_sha256=None):
    try:
        require(type(operation_id) is str and str(uuid.UUID(operation_id)) == operation_id)
        require(type(nonce) is str and re.fullmatch('[0-9a-f]{32}', nonce))
        require(type(ca_sha256) is str and re.fullmatch('[0-9a-f]{64}', ca_sha256))
        require(type(placeholder) is str and re.fullmatch('youngcrow-probe-[0-9a-f]{32}', placeholder))
        require(injection_sha256 is None or (type(injection_sha256) is str
                and re.fullmatch('[0-9a-f]{64}', injection_sha256)
                and injection_sha256 != hashlib.sha256(placeholder.encode()).hexdigest()))
        require(type(deadline_ms) is int and deadline_ms > 0)
        require(phase in ('A', 'B', 'A2') and type(proxy_ipv4) is str)
        address = ipaddress.IPv4Address(proxy_ipv4)
        require(str(address) == proxy_ipv4 and any(address in ipaddress.IPv4Network(cidr)
                for cidr in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
    except (Refused, ValueError, TypeError, AttributeError):
        raise Refused('invalid_manifest') from None
    manifest = dict(schema_version=3, operation_id=operation_id, nonce=nonce, deadline_ms=deadline_ms,
                init_argv=FIXTURE_ARGV+['initialize'],
                dispatch_prefix=FIXTURE_ARGV+['request', nonce, phase, placeholder, str(deadline_ms)],
                network=dict(proxy_ipv4=proxy_ipv4),
                relay=dict(kind='echo', phase=phase, placeholder=placeholder, ca_sha256=ca_sha256))
    if injection_sha256 is not None:
        manifest['schema_version'] = 4
        manifest['relay']['injection_sha256'] = injection_sha256
        manifest['dispatch_prefix'].append(injection_sha256)
    return manifest


def validate_manifest(manifest):
    """Structural validation also works on expired durable recovery plans."""
    try:
        expected = _manifest(operation_id=manifest['operation_id'], nonce=manifest['nonce'],
            deadline_ms=manifest['deadline_ms'], phase=manifest['relay']['phase'],
            proxy_ipv4=manifest['network']['proxy_ipv4'], ca_sha256=manifest['relay']['ca_sha256'],
            placeholder=manifest['relay']['placeholder'], injection_sha256=manifest['relay'].get('injection_sha256'))
        require(encoded(manifest) == encoded(expected), 'invalid_manifest')
    except (KeyError, TypeError, ValueError, Refused):
        raise ValueError('invalid_manifest') from None


class Deadline:
    def __init__(self, deadline_ms):
        self.wall = deadline_ms/1000-1
        self.monotonic = time.monotonic() + self.wall-time.time()

    def remaining(self):
        value = min(self.wall-time.time(), self.monotonic-time.monotonic())
        require(value > 0, 'deadline')
        return value


class Channel:
    """A private child pipe inside an already-owned group/job. No public argv input."""
    def __init__(self, argv, *, cwd, deadline_ms):
        self.deadline = Deadline(deadline_ms)
        self.deadline.remaining()
        self.queue, self.stop = queue.Queue(maxsize=16), threading.Event()
        self.buffer, self.total, self.ended = bytearray(), 0, set()
        self.hashes = {name: hashlib.sha256() for name in ('stdout', 'stderr')}
        self.threads = []
        # Inherit the outer supervisor's containment and allowlisted environment.
        self.process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0, close_fds=True, shell=False)
        try:
            for name in ('stdout', 'stderr'):
                thread = threading.Thread(target=self._read, args=(name,), daemon=True)
                thread.start()
                self.threads.append(thread)
        except BaseException as error:
            self.close()
            if isinstance(error, RuntimeError):
                raise Refused('transport_start_failed') from None
            raise

    def _read(self, name):
        try:
            while not self.stop.is_set():
                chunk = getattr(self.process, name).read(4096)
                while not self.stop.is_set():
                    try:
                        self.queue.put((name, chunk), timeout=.05)
                        break
                    except queue.Full:
                        pass
                if not chunk:
                    return
        except (OSError, ValueError):
            # A missing EOF remains incomplete and expires under the original deadline.
            return

    def send(self, value):
        self.deadline.remaining()
        raw = encoded(value)+b'\n'
        require(len(raw) <= FRAME_LIMIT, 'output_limit')
        require(self.process.stdin.write(raw) == len(raw), 'control_write_failed')

    def receive(self):
        while True:
            require(not self.stop.is_set(), 'transport_closed')
            self.deadline.remaining()
            if b'\n' in self.buffer:
                line, _, rest = self.buffer.partition(b'\n')
                require(len(line)+1 <= FRAME_LIMIT, 'output_limit')
                self.buffer = bytearray(rest)
                try:
                    event = parse_json(bytes(line))
                except (ValueError, RecursionError):
                    raise Refused('protocol_failed') from None
                require(type(event) is dict)
                require(event.get('kind') != 'refused', 'guardian_refused')
                return event
            require(len(self.buffer) < FRAME_LIMIT, 'output_limit')
            if self.ended == {'stdout', 'stderr'}:
                require(not self.buffer)
                return None
            try:
                name, chunk = self.queue.get(timeout=min(.05, self.deadline.remaining()))
            except queue.Empty:
                continue
            if not chunk:
                self.ended.add(name)
                continue
            self.total += len(chunk)
            require(self.total <= CAPTURE_LIMIT, 'output_limit')
            self.hashes[name].update(chunk)
            if name == 'stdout':
                self.buffer.extend(chunk)

    def exit_code(self):
        try:
            return self.process.wait(timeout=self.deadline.remaining())
        except subprocess.TimeoutExpired:
            raise Refused('deadline') from None

    def close(self):
        terminate_before = time.monotonic()+.2
        self.stop.set()
        self.process.stdin.close()
        if self.process.poll() is None:
            # EOF lets cooperative helpers close sockets before forced exit.
            # This grace consumes part of the existing termination budget.
            try:
                grace = min(.1, self.deadline.remaining(),
                            max(0, terminate_before-time.monotonic()))
            except Refused:
                grace = 0
            running = True
            if grace > 0:
                try:
                    self.process.wait(timeout=grace)
                    running = False
                except subprocess.TimeoutExpired:
                    pass
            if running:
                self.process.terminate()
                try:
                    self.process.wait(timeout=max(0, terminate_before-time.monotonic()))
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=.2)
        for thread in self.threads:
            thread.join(timeout=.1)
        # The outer group/job owns descendants even after this direct child exits.
        if not any(thread.is_alive() for thread in self.threads):
            self.process.stdout.close()
            self.process.stderr.close()


def stage(channel, phase):
    require(channel.receive() == dict(kind='started', phase=phase))
    output, relay = bytearray(), None
    while True:
        event = channel.receive()
        require(type(event) is dict)
        if event.get('kind') == 'output':
            require(set(event) == {'kind', 'phase', 'stream', 'data'} and event['phase'] == phase
                    and event['stream'] in ('stdout', 'stderr') and type(event['data']) is str
                    and relay is None)
            try:
                chunk = base64.b64decode(event['data'], validate=True)
            except ValueError:
                raise Refused('protocol_failed') from None
            require(0 < len(chunk) <= 4096 and len(output)+len(chunk) <= 4096, 'output_limit')
            require(event['stream'] == 'stdout')  # The fixed fixture emits no diagnostic stderr.
            output.extend(chunk)
        elif event.get('kind') == 'relay_finished':
            require(phase == 'dispatch' and relay is None
                    and set(event) == {'kind', 'state', 'reason', 'requests', 'bytes_forwarded', 'stopped'}
                    and event['state'] in ('succeeded', 'refused', 'cancelled', 'deadline')
                    and (event['reason'] is None or type(event['reason']) is str)
                    and type(event['requests']) is int and 0 <= event['requests'] <= 1
                    and type(event['bytes_forwarded']) is int and 0 <= event['bytes_forwarded'] <= 8*1024*1024
                    and event['stopped'] is True)
            relay = event
        else:
            require(set(event) == {'kind', 'phase', 'exit_code'} and event['kind'] == 'finished'
                    and event['phase'] == phase and type(event['exit_code']) is int
                    and -255 <= event['exit_code'] <= 255 and (phase == 'initialize' or relay is not None))
            try:
                value = parse_json(bytes(output))
            except (ValueError, RecursionError):
                raise Refused('fixture_result_invalid') from None
            return event['exit_code'], value, relay


def run_phase(launcher, manifest, image, persist):
    """Coordinate one consumed phase. persist must commit or raise before returning.

    The caller owns installation reservation and subsequent restoration. A result
    from this function is protocol evidence, never permission to close that ledger.
    """
    result = dict(state='refused', reason='invalid_manifest', model_calls=0,
                  proof_accepted=False, workload_reaped=False)
    channel = None
    try:
        require(type(manifest) is dict, 'invalid_manifest')
        expected = phase_manifest(operation_id=manifest['operation_id'], nonce=manifest['nonce'],
            deadline_ms=manifest['deadline_ms'], phase=manifest['relay']['phase'],
            proxy_ipv4=manifest['network']['proxy_ipv4'], ca_sha256=manifest['relay']['ca_sha256'],
            placeholder=manifest['relay']['placeholder'], injection_sha256=manifest['relay'].get('injection_sha256'))
        require(encoded(manifest) == encoded(expected), 'invalid_manifest')
        manifest = expected  # Private copy; later caller mutations cannot change commands.
        require(type(image) is str and re.fullmatch('sha256:[0-9a-f]{64}', image), 'invalid_manifest')
        deadline = Deadline(manifest['deadline_ms'])
        identity = dict(operation_id=manifest['operation_id'], nonce=manifest['nonce'],
                        manifest_sha256=hashlib.sha256(encoded(manifest)).hexdigest())
        result.update(operation_id=identity['operation_id'], phase=manifest['relay']['phase'])
        def record(kind, **fields):
            deadline.remaining()
            try:
                persist(kind, dict(identity, **fields))
            except Exception:
                raise Refused('persistence_failed') from None
            deadline.remaining()
        record('prepare_intent', image=image, manifest=manifest)
        prepared = launcher.prepare(image, manifest)
        require(type(prepared) is dict and set(prepared) ==
                {'schema_version', 'container_id', 'image', *identity}
                and type(prepared['schema_version']) is int and prepared['schema_version'] == 1
                and type(prepared['container_id']) is str and re.fullmatch('[0-9a-f]{64}', prepared['container_id'])
                and prepared['image'] == image and all(prepared[k] == v for k, v in identity.items()), 'identity_changed')
        record('prepared', observation=prepared)
        record('run_intent', container_id=prepared['container_id'])
        channel = launcher.start(manifest)
        require(channel.receive() == dict(kind='listening', operation_id=identity['operation_id']), 'identity_changed')
        namespace = None
        for phase in ('initialize', 'dispatch'):
            record(phase+'_intent')
            gate = launcher.network(manifest, phase)
            require(type(gate) is dict and set(gate) == {*identity, 'phase', 'network_namespace'}
                    and all(gate[k] == v for k, v in identity.items()) and gate['phase'] == phase
                    and type(gate['network_namespace']) is str
                    and re.fullmatch(r'net:\[[1-9][0-9]*\]', gate['network_namespace'])
                    and namespace in (None, gate['network_namespace']), 'identity_changed')
            namespace = gate['network_namespace']
            record(phase+'_gate', observation=gate)
            message = dict(schema_version=1, operation_id=identity['operation_id'], nonce=identity['nonce'], action=phase)
            if phase == 'dispatch':
                message['argv'] = manifest['dispatch_prefix']
            record(phase+'_authorization', message_sha256=hashlib.sha256(encoded(message)).hexdigest())
            channel.send(message)
            code, value, relay = stage(channel, phase)
            if phase == 'initialize':
                require(code == 0 and encoded(value) == encoded(dict(schema_version=1,
                    fixture_id='isolated-egress-v1', stage='initialize', network_requests=0, model_calls=0)),
                    'initialize_failed')
                require(channel.receive() == dict(kind='ready'))
        require(channel.receive() is None)
        exit_code = channel.exit_code()
        if code != 0:
            require(manifest['relay']['phase'] == 'B' and code == 126 and exit_code == 126
                    and relay['state'] != 'succeeded', 'dispatch_failed')
            result.update(state='blocked_unattributed', reason='native_attribution_required')
        else:
            require(exit_code == 0 and relay['state'] == 'succeeded' and relay['reason'] is None
                    and relay['requests'] == 1 and relay['bytes_forwarded'] > 0, 'relay_failed')
            require(type(value) is dict and type(value.get('response_sha256')) is str
                    and re.fullmatch('[0-9a-f]{64}', value['response_sha256']), 'fixture_result_invalid')
            expected = dict(schema_version=1, fixture_id='isolated-egress-v1', stage='dispatch',
                            nonce=manifest['nonce'], phase=manifest['relay']['phase'], http_status=200,
                            echo_matches=True, response_sha256=value['response_sha256'], network_requests=1, model_calls=0)
            if manifest['schema_version'] == 4:
                expected.pop('echo_matches')
                expected.update(schema_version=2, injection_matches=True,
                                injected_value_sha256=manifest['relay']['injection_sha256'])
            require(encoded(value) == encoded(expected), 'fixture_result_invalid')
            result.update(state='unexpected_allow' if manifest['relay']['phase'] == 'B' else 'observed',
                          reason='phase_observed', fixture=value)
        result['transport'] = dict(exit_code=exit_code, captured_bytes=channel.total,
                                    **{name+'_sha256': digest.hexdigest() for name, digest in channel.hashes.items()})
        record('observed', result=result)
    except Refused as error:
        result.update(state='refused', reason=str(error))
    except (KeyError, TypeError, ValueError):
        result.update(state='refused', reason='invalid_manifest')
    except (OSError, subprocess.SubprocessError):
        result.update(state='refused', reason='transport_failed')
    finally:
        if channel is not None:
            try:
                channel.close()
            except (OSError, ValueError, subprocess.SubprocessError):
                result.update(state='refused', reason='transport_close_failed')
    return result
