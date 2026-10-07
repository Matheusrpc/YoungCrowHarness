"""Linux PID 1 supervisor. Private control and durable claims precede child effects.

This module is not a supported runtime profile. The launcher must verify the
container boundary and preserve /control across restarts of the same operation.
"""
import base64
import ctypes
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay

MESSAGE_LIMIT = 16 * 1024
OUTPUT_LIMIT = 8 * 1024 * 1024
MAX_SECONDS = 120
SHUTDOWN_SECONDS = 1


class Refused(Exception):
    """Fail closed; messages deliberately exclude input, paths and credentials."""


def execution_remaining(deadline_ms):
    remaining = deadline_ms / 1000 - time.time()
    if not SHUTDOWN_SECONDS < remaining <= MAX_SECONDS:
        raise Refused('invalid_deadline')
    return remaining - SHUTDOWN_SECONDS


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refused('invalid_json')
            result[key] = value
        return result
    def constant(_):
        raise Refused('invalid_json')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise Refused('invalid_json') from error


def sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def claim(directory, name, value):
    # Never replace or remove a failed claim: uncertain operations stay consumed.
    try:
        with (directory / name).open('xb') as output:
            output.write(encode(value) + b'\n')
            output.flush()
            os.fsync(output.fileno())
        sync_directory(directory)
    except (OSError, ValueError) as error:
        raise Refused('claim_failed_or_consumed') from error


def valid_argv(value):
    return (type(value) is list and 0 < len(value) <= 128
            and all(type(arg) is str and '\0' not in arg for arg in value)
            and value[0].startswith('/') and len(encode(value)) <= MESSAGE_LIMIT)


def valid_network(value):
    if (type(value) is not dict or set(value) != {'host', 'ipv4'}
            or type(value['host']) is not str or len(value['host']) > 253
            or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', value['host'])
            or type(value['ipv4']) is not str):
        return False
    try:
        address = ipaddress.IPv4Address(value['ipv4'])
        return (str(address) == value['ipv4'] and address.is_global
                and not address.is_multicast and not address.is_reserved)
    except ValueError:
        return False


def network_namespace():
    return os.readlink('/proc/self/ns/net')


def valid_relay(config):
    network, policy = config.get('network'), config.get('relay')
    fields = {'kind', 'phase', 'placeholder', 'ca_sha256'}
    if config.get('schema_version') == 4:
        fields.add('injection_sha256')
    if (type(network) is not dict or set(network) != {'proxy_ipv4'}
            or type(network['proxy_ipv4']) is not str or type(policy) is not dict
            or set(policy) != fields
            or policy['kind'] != 'echo' or type(policy['ca_sha256']) is not str
            or not re.fullmatch('[0-9a-f]{64}', policy['ca_sha256'])):
        return False
    try:
        address = ipaddress.IPv4Address(network['proxy_ipv4'])
        relay.echo_policy(config['nonce'], policy['phase'], policy['placeholder'])
        if config.get('schema_version') == 4:
            digest = policy['injection_sha256']
            argv = ['/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/fixture.py']
            if (type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest)
                    or digest == hashlib.sha256(policy['placeholder'].encode()).hexdigest()
                    or config.get('init_argv') != argv+['initialize']
                    or config.get('dispatch_prefix') != argv+['request', config['nonce'], policy['phase'],
                        policy['placeholder'], str(config['deadline_ms']), digest]):
                return False
        return str(address) == network['proxy_ipv4'] and any(address in ipaddress.IPv4Network(cidr)
                   for cidr in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
    except (ValueError, TypeError, KeyError, relay.Refused):
        return False


def require_unmapped(pid='self'):
    for name in ('uid_map', 'gid_map'):
        if (Path('/proc')/str(pid)/name).read_text().split() != ['0','0','4294967295']:
            raise Refused('uid_gid_remapping')


def protected_network_gate(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise Refused('network_unverified')


class Protocol:
    def __init__(self, directory, config):
        keys = {'schema_version', 'operation_id', 'nonce', 'deadline_ms', 'init_argv', 'dispatch_prefix'}
        if type(config) is dict and config.get('schema_version') in (2, 3, 4):
            keys.add('network')
            if config['schema_version'] in (3, 4):
                keys.add('relay')
        if (type(config) is not dict or set(config) != keys
                or type(config['schema_version']) is not int or config['schema_version'] not in (1, 2, 3, 4)
                or (config['schema_version'] == 2 and not valid_network(config['network']))
                or (config['schema_version'] in (3, 4) and not valid_relay(config))
                or type(config['deadline_ms']) is not int
                or type(config['operation_id']) is not str
                or type(config['nonce']) is not str
                or not re.fullmatch('[0-9a-f]{32}', config['nonce'])
                or not valid_argv(config['init_argv']) or not valid_argv(config['dispatch_prefix'])):
            raise Refused('invalid_manifest')
        try:
            if str(uuid.UUID(config['operation_id'])) != config['operation_id']:
                raise ValueError()
        except ValueError as error:
            raise Refused('invalid_identity') from error
        remaining = execution_remaining(config['deadline_ms'])
        self.config = decode(encode(config))  # Caller cannot mutate the bound manifest.
        self.monotonic_deadline = time.monotonic() + remaining
        self.directory = directory
        self.state = 'new'
        self.identity = dict(operation_id=config['operation_id'],
                             manifest_sha256=hashlib.sha256(encode(config)).hexdigest())
        claim(directory, 'consumed.json', self.identity)

    def remaining(self):
        return min(self.config['deadline_ms'] / 1000 - time.time() - SHUTDOWN_SECONDS,
                   self.monotonic_deadline - time.monotonic())

    def accept(self, raw):
        try:
            if self.remaining() <= 0:
                raise Refused('deadline')
            if (not raw.endswith(b'\n') or raw.count(b'\n') != 1 or len(raw) > MESSAGE_LIMIT):
                raise Refused('invalid_frame')
            message = decode(raw)
            if type(message) is not dict:
                raise Refused('invalid_message')
            action = message.get('action')
            keys = {'schema_version', 'operation_id', 'nonce', 'action'}
            if action == 'dispatch':
                keys.add('argv')
            if (set(message) != keys or type(message.get('schema_version')) is not int
                    or message['schema_version'] != 1
                    or message.get('nonce') != self.config['nonce']
                    or message.get('operation_id') != self.config['operation_id']):
                raise Refused('invalid_identity_or_fields')
            if action == 'initialize' and self.state == 'new':
                argv = self.config['init_argv']
            elif action == 'dispatch' and self.state == 'ready':
                argv = message['argv']
                prefix = self.config['dispatch_prefix']
                if (not valid_argv(argv) or argv[:len(prefix)] != prefix
                        or (self.config['schema_version'] == 4 and argv != prefix)):
                    raise Refused('invalid_command')
            else:
                raise Refused('invalid_transition')
            if self.config['schema_version'] in (2, 3, 4):
                self.require_network(action)
            self.state = action
            claim(self.directory, action + '.json', dict(self.identity, action=action))
            if self.remaining() <= 0:
                raise Refused('deadline')
            return list(argv)
        except Refused:
            self.state = 'terminal'
            raise

    def require_network(self, phase):
        try:
            path = self.directory / ('network-' + phase + '.json')
            protected_network_gate(path.lstat())
            flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
            with os.fdopen(os.open(path, flags), 'rb') as stream:
                protected_network_gate(os.fstat(stream.fileno()))
                raw = stream.read(MESSAGE_LIMIT + 1)
            expected = dict(self.identity, nonce=self.config['nonce'], phase=phase,
                            network_namespace=network_namespace())
            if len(raw) > MESSAGE_LIMIT or decode(raw) != expected:
                raise Refused('network_unverified')
        except (OSError, ValueError) as error:
            raise Refused('network_unverified') from error

    def finished(self, exit_code):
        if self.state not in {'initialize', 'dispatch'}:
            self.state = 'terminal'
            raise Refused('invalid_transition')
        self.state = 'ready' if self.state == 'initialize' and exit_code == 0 else 'terminal'


def child_identity():
    # preexec_fn is used only by this single-threaded PID 1 process.
    libc = ctypes.CDLL(None, use_errno=True)
    cap_last = int(Path('/proc/sys/kernel/cap_last_cap').read_text())
    for capability in range(cap_last + 1):
        if libc.prctl(24, capability, 0, 0, 0) != 0:  # PR_CAPBSET_DROP
            raise OSError('capability_drop_failed')
    os.setgroups([])
    os.setgid(1000)
    os.setuid(1000)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError('no_new_privs_failed')
    os.umask(0o077)
    os.chdir('/home/client')


def emit(value):
    value = encode(value) + b'\n'
    while value:
        value = value[os.write(1, value):]


def spawn_child(argv, bridge=None):
    # Binding the relay is safe before fork. Starting its threads is not.
    try:
        if threading.active_count() != 1:
            raise Refused('threaded_fork')
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 close_fds=True, shell=False,
                                 env={'HOME':'/home/client', 'PATH':'/usr/local/bin:/usr/bin:/bin',
                                      'LANG':'C.UTF-8', 'PYTHONDONTWRITEBYTECODE':'1'},
                                 preexec_fn=child_identity, start_new_session=True)
        if bridge is not None:
            bridge.start()
        return child
    except BaseException:
        if bridge is not None:
            bridge.stop()
        raise


def prepare_relay(protocol):
    require_unmapped()
    config = protocol.config
    policy = config['relay']
    _, context = relay.read_ca(protocol.directory/'relay-ca.pem', policy['ca_sha256'])
    def reserve():
        claim(protocol.directory, 'relay-request.json', dict(protocol.identity, phase=policy['phase']))
    return relay.Relay(deadline_ms=config['deadline_ms'], proxy_ipv4=config['network']['proxy_ipv4'],
                       policy=relay.echo_policy(config['nonce'], policy['phase'], policy['placeholder']),
                       claim=reserve, context=context)


def supervise(protocol):
    bridges = []
    try:
        return supervise_loop(protocol, bridges)
    finally:
        for bridge in bridges:
            bridge.stop()


def supervise_loop(protocol, bridges):
    selector = selectors.DefaultSelector()
    selector.register(0, selectors.EVENT_READ, 'control')
    control = b''
    child = None
    streams = 0
    total = 0
    phase = None
    while protocol.remaining() > 0:
        for key, _ in selector.select(min(0.05, max(0, protocol.remaining()))):
            chunk = os.read(key.fd, 4096)
            if key.data == 'control':
                if not chunk:
                    raise Refused('control_closed')
                control += chunk
                while b'\n' in control:
                    line, control = control.split(b'\n', 1)
                    argv = protocol.accept(line + b'\n')
                    phase = protocol.state
                    bridge = None
                    if phase == 'dispatch' and protocol.config['schema_version'] in (3, 4):
                        bridge = prepare_relay(protocol)
                        bridges.append(bridge)
                    child = spawn_child(argv, bridge)
                    selector.register(child.stdout, selectors.EVENT_READ, 'stdout')
                    selector.register(child.stderr, selectors.EVENT_READ, 'stderr')
                    streams = 2
                    emit(dict(kind='started', phase=phase))
                if len(control) >= MESSAGE_LIMIT:
                    raise Refused('invalid_frame')
            else:
                if not chunk:
                    selector.unregister(key.fd)
                    key.fileobj.close()
                    streams -= 1
                else:
                    total += len(chunk)
                    if total > OUTPUT_LIMIT:
                        return 122
                    emit(dict(kind='output', phase=phase, stream=key.data,
                              data=base64.b64encode(chunk).decode('ascii')))
        if child is not None and streams == 0 and child.poll() is not None:
            code = child.returncode
            if bridges:
                stopped = bridges[0].stop()
                result = bridges[0].result()
                emit(dict(kind='relay_finished', **result, stopped=stopped))
                if not stopped or result['state'] != 'succeeded':
                    code = 126
            protocol.finished(code)
            emit(dict(kind='finished', phase=phase, exit_code=code))
            if protocol.state == 'terminal':
                return 0 if code == 0 else 126
            # Discovery must not leave work behind to interfere with dispatch.
            if any(p.name.isdecimal() and p.name != '1' for p in Path('/proc').iterdir()):
                raise Refused('discovery_descendants')
            child = None
            emit(dict(kind='ready'))
    return 124


def main():
    if sys.platform != 'linux' or os.getpid() != 1 or os.getuid() != 0:
        return 125
    # Python signal delivery is not an unconditional bound on C code or suspension.
    signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
    # Reserve termination time inside the original deadline; never add tolerance.
    signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS - SHUTDOWN_SECONDS)
    try:
        directory = Path('/control')
        manifest = directory / 'launch.json'
        for path, permissions, directory_expected in ((directory, 0o700, True), (manifest, 0o600, False)):
            info = path.lstat()
            if (info.st_uid != 0 or stat.S_IMODE(info.st_mode) != permissions
                    or (stat.S_ISDIR(info.st_mode) if directory_expected else stat.S_ISREG(info.st_mode)) is False):
                raise Refused('unprotected_control')
        if manifest.stat().st_size > MESSAGE_LIMIT:
            raise Refused('invalid_manifest')
        config = decode(manifest.read_bytes())
        if type(config) is not dict or type(config.get('deadline_ms')) is not int:
            raise Refused('invalid_deadline')
        remaining = execution_remaining(config['deadline_ms'])
        signal.setitimer(signal.ITIMER_REAL, remaining)
        protocol = Protocol(directory, config)
        emit(dict(kind='listening', operation_id=config['operation_id']))
        return supervise(protocol)
    except (Refused, relay.Refused, OSError, ValueError, subprocess.SubprocessError) as error:
        emit(dict(kind='refused', reason=str(error) if isinstance(error, (Refused, relay.Refused)) else type(error).__name__,
                  errno=error.errno if isinstance(error, OSError) else None))
        return 125


if __name__ == '__main__':
    os._exit(main())
