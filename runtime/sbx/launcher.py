"""Trusted, root-only VM launcher for the unpaid guardian proof.

Creation and start are separately consumed before effects. Uncertain operations
remain on disk; this launcher never retries, removes or approves a runtime profile.
"""
import hashlib
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guardian

DOCKER = '/usr/bin/docker'
STATE = Path('/var/lib/youngcrow/operations')
HOME_OPTIONS = 'rw,noexec,nosuid,nodev,size=16m,uid=1000,gid=1000,mode=0700'


def identity(operation_id):
    try:
        if type(operation_id) is not str or str(uuid.UUID(operation_id)) != operation_id:
            raise ValueError()
    except (ValueError, AttributeError) as error:
        raise guardian.Refused('invalid_identity') from error
    return operation_id


def protected(path, directory=False):
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode):
        raise guardian.Refused('unprotected_control')
    if os.name == 'posix' and (info.st_uid != 0 or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)):
        raise guardian.Refused('unprotected_control')


def save(directory, name, value):
    guardian.claim(directory, name, value)
    path = directory / name
    path.chmod(0o600)
    with path.open('r+b') as stream:
        os.fsync(stream.fileno())
    guardian.sync_directory(directory)


def read(path):
    protected(path)
    with path.open('rb') as stream:
        raw = stream.read(guardian.MESSAGE_LIMIT + 1)
    if len(raw) > guardian.MESSAGE_LIMIT:
        raise guardian.Refused('invalid_record')
    return guardian.decode(raw)


def docker(*args):
    # No inherited Docker endpoint, context, config or credentials.
    result = subprocess.run([DOCKER, *args], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=10, shell=False,
                            env={'PATH': '/usr/bin:/bin', 'HOME': '/root'})
    if result.returncode or len(result.stdout) > 1024 * 1024:
        raise guardian.Refused('docker_observation_failed')
    return result.stdout


def verify(directory, record, manifest, *, running=False, networks=None, recovering=False):
    if manifest['schema_version'] == 3:
        try:
            guardian.relay.read_ca(directory/'control/relay-ca.pem', manifest['relay']['ca_sha256'])
        except (guardian.relay.Refused, OSError, ValueError) as error:
            raise guardian.Refused('relay_ca_unverified') from error
    cid = record['container_id']
    if type(cid) is not str or not re.fullmatch('[0-9a-f]{64}', cid):
        raise guardian.Refused('invalid_container')
    values = guardian.decode(docker('inspect', cid))
    if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
        raise guardian.Refused('invalid_inspection')
    value = values[0]
    config, host, state = (value.get(key) for key in ('Config', 'HostConfig', 'State'))
    if any(type(item) is not dict for item in (config, host, state)):
        raise guardian.Refused('invalid_inspection')
    expected_config = dict(User='0:0', Entrypoint=['/usr/bin/python3.14'],
                           Cmd=['-I', '-B', '/opt/youngcrow/guardian.py'], OpenStdin=True, Tty=False,
                           WorkingDir='/', Healthcheck={'Test': ['NONE']})
    expected_host = dict(ReadonlyRootfs=True, Privileged=False, NetworkMode='none',
                         NanoCpus=2000000000, Memory=4294967296, MemorySwap=4294967296, PidsLimit=64,
                         RestartPolicy=dict(Name='no', MaximumRetryCount=0), CapDrop=['ALL'],
                         CapAdd=['CAP_SETGID', 'CAP_SETPCAP', 'CAP_SETUID'],
                         SecurityOpt=['no-new-privileges=true'], Tmpfs={'/home/client': HOME_OPTIONS},
                         PidMode='', IpcMode='private', CgroupnsMode='private', UsernsMode='',
                         LogConfig={'Type': 'none', 'Config': {}}, PublishAllPorts=False, AutoRemove=False)
    if manifest['schema_version'] == 2:
        expected_host['ExtraHosts'] = [manifest['network']['host']+':'+manifest['network']['ipv4']]
    elif manifest['schema_version'] == 3 and host.get('ExtraHosts') not in (None, []):
        raise guardian.Refused('unsafe_container')
    def matches(observed, expected):
        return all(guardian.encode(observed.get(key)) == guardian.encode(item) for key, item in expected.items())
    labels = config.get('Labels', {})
    mounts = value.get('Mounts')
    expected_state = dict(Status='running', Running=True) if running else dict(Status='created', Running=False, Pid=0)
    if recovering:
        active = state.get('Status') == 'running'
        if (state.get('Status') not in ('created', 'running', 'exited', 'dead')
                or state.get('Running') is not active or type(state.get('Pid')) is not int
                or (state['Pid'] <= 0 if active else state['Pid'] != 0)
                or any(state.get(key) not in (None, False) for key in ('Paused', 'Restarting'))):
            raise guardian.Refused('unsafe_container')
        expected_state = {}
    if (value.get('Id') != cid or value.get('Image') != record['image']
            or not matches(state, expected_state)
            or (running and (type(state.get('Pid')) is not int or state['Pid'] <= 0
                             or set(value.get('NetworkSettings', {}).get('Networks', {})) != set(networks)))
            or not matches(config, expected_config) or not matches(host, expected_host)
            or type(labels) is not dict or labels.get('youngcrow.operation') != manifest['operation_id']
            or labels.get('youngcrow.nonce') != manifest['nonce']
            or any(host.get(key) not in (None, [], {}) for key in
                   ('Binds', 'PortBindings', 'Devices', 'DeviceRequests', 'VolumesFrom'))
            or type(mounts) is not list or len(mounts) != 1 or type(mounts[0]) is not dict
            or not matches(mounts[0], dict(Type='bind', Source=str(directory/'control'),
                                          Destination='/control', RW=True))):
        raise guardian.Refused('unsafe_container')
    return value if running or recovering else hashlib.sha256(guardian.encode(value)).hexdigest()


def observe(root, operation_id, nonce):
    """Inspect an existing owned container; never create or start it for recovery."""
    try:
        directory = root / identity(operation_id)
        for path in (root, directory, directory/'control'):
            protected(path, directory=True)
        manifest = read(directory/'control/launch.json')
        try:
            record = read(directory/'created.json')
        except FileNotFoundError:
            # A create response may be lost after Docker committed it. Resolve
            # the fixed name against the protected pre-create identity, then
            # inspect the full effective configuration by CID below.
            intent = read(directory/'create-intent.json')
            values = guardian.decode(docker('inspect', 'yc-'+operation_id))
            if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
                raise guardian.Refused('invalid_inspection')
            record = dict(intent, container_id=values[0].get('Id'))
        if (type(record) is not dict or type(manifest) is not dict
                or record.get('operation_id') != operation_id or manifest.get('operation_id') != operation_id
                or type(nonce) is not str or not re.fullmatch('[0-9a-f]{32}', nonce)
                or record.get('nonce') != nonce or manifest.get('nonce') != nonce
                or hashlib.sha256(guardian.encode(manifest)).hexdigest() != record.get('manifest_sha256')):
            raise guardian.Refused('changed_operation')
        value = verify(directory, record, manifest, recovering=True)
        state = value['State']
        return dict(record, state={k: state[k] for k in ('Status', 'Running', 'Pid')},
                    inspection_sha256=hashlib.sha256(guardian.encode(value)).hexdigest(),
                    workload_reaped=state['Running'] is False and state['Pid'] == 0)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise guardian.Refused('recovery_observation_failed') from error


def stop(root, operation_id, nonce):
    """One stop attempt; a lost response is resolved by inspection, never replay."""
    observed = observe(root, operation_id, nonce)
    if observed['workload_reaped']:
        return observed
    directory = root / operation_id
    try:
        save(directory, 'stop.json', observed)
        # Stop is bounded separately from the expired workload's execution deadline.
        docker('stop', '--time', '1', observed['container_id'])
        final = observe(root, operation_id, nonce)
        if not final['workload_reaped']:
            raise guardian.Refused('workload_stop_unverified')
        return final
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise guardian.Refused('stop_failed_or_consumed') from error


def snapshot_ca(control, digest):
    try:
        raw, _ = guardian.relay.read_ca(Path('/etc/ssl/certs/ca-certificates.crt'), digest, snapshot=False)
        descriptor = os.open(control/'relay-ca.pem', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        guardian.sync_directory(control)
    except (guardian.relay.Refused, OSError, ValueError) as error:
        raise guardian.Refused('relay_ca_unverified') from error


def prepare(root, image, manifest):
    try:
        if type(image) is not str or not re.fullmatch('sha256:[0-9a-f]{64}', image):
            raise guardian.Refused('unpinned_image')
        if type(manifest) is not dict:
            raise guardian.Refused('invalid_manifest')
        directory = root / identity(manifest.get('operation_id'))
        protected(root, directory=True)
        directory.mkdir(mode=0o700)  # Existing intent, even incomplete, is never reused.
        guardian.sync_directory(root)
        protocol = guardian.Protocol(directory, manifest)
        manifest = protocol.config
        control = directory/'control'
        control.mkdir(mode=0o700)
        guardian.sync_directory(directory)
        save(control, 'launch.json', manifest)
        if manifest['schema_version'] == 3:
            snapshot_ca(control, manifest['relay']['ca_sha256'])
        intent = dict(schema_version=1, image=image, **protocol.identity, nonce=manifest['nonce'])
        save(directory, 'create-intent.json', intent)
        host_args = (['--add-host', manifest['network']['host']+':'+manifest['network']['ipv4']]
                     if manifest['schema_version'] == 2 else [])
        cid = docker('create', '--pull', 'never', '-i', '--name', 'yc-'+manifest['operation_id'],
                     '--label', 'youngcrow.operation='+manifest['operation_id'],
                     '--label', 'youngcrow.nonce='+manifest['nonce'],
                     '--restart', 'no', '--read-only', '--network', 'none', '--cpus', '2',
                     '--memory', '4g', '--memory-swap', '4g', '--pids-limit', '64',
                     '--cap-drop', 'ALL', '--cap-add', 'SETUID', '--cap-add', 'SETGID', '--cap-add', 'SETPCAP',
                     '--security-opt', 'no-new-privileges=true', '--user', '0:0',
                     '--ipc', 'private', '--cgroupns', 'private', '--no-healthcheck', '--workdir', '/',
                     '--mount', 'type=bind,src='+str(control)+',dst=/control',
                     '--tmpfs', '/home/client:'+HOME_OPTIONS, '--log-driver', 'none',
                     '--entrypoint', '/usr/bin/python3.14', *host_args, image,
                     '-I', '-B', '/opt/youngcrow/guardian.py').decode('ascii').strip()
        record = dict(schema_version=1, container_id=cid, image=image, **protocol.identity,
                      nonce=manifest['nonce'])
        # Preserve a known ID even if effective configuration subsequently fails.
        save(directory, 'created.json', record)
        verify(directory, record, manifest)
        return record
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise guardian.Refused('prepare_failed_or_consumed') from error


def start_command(root, operation_id, nonce):
    try:
        directory = root / identity(operation_id)
        for path in (root, directory, directory/'control'):
            protected(path, directory=True)
        if (directory/'start.json').exists():
            raise guardian.Refused('start_consumed')
        record, manifest = read(directory/'created.json'), read(directory/'control/launch.json')
        if (type(record) is not dict or type(manifest) is not dict
                or record.get('operation_id') != operation_id or manifest.get('operation_id') != operation_id
                or type(nonce) is not str or not re.fullmatch('[0-9a-f]{32}', nonce)
                or record.get('nonce') != nonce or manifest.get('nonce') != nonce
                or hashlib.sha256(guardian.encode(manifest)).hexdigest() != record.get('manifest_sha256')
                or type(manifest.get('deadline_ms')) is not int):
            raise guardian.Refused('changed_or_expired_operation')
        guardian.execution_remaining(manifest['deadline_ms'])
        inspection = verify(directory, record, manifest)
        save(directory, 'start.json', dict(container_id=record['container_id'], inspection_sha256=inspection))
        guardian.execution_remaining(manifest['deadline_ms'])
        return [DOCKER, 'start', '-ai', record['container_id']]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise guardian.Refused('start_failed_or_consumed') from error


@contextmanager
def network_handle(pid):
    descriptor = os.open('/proc/'+str(pid)+'/ns/net', os.O_RDONLY)
    try:
        yield descriptor, os.readlink('/proc/self/fd/'+str(descriptor))
    finally:
        os.close(descriptor)


def net_command(descriptor, tool, *args, deadline):
    remaining = guardian.execution_remaining(deadline)
    result = subprocess.run(['/usr/bin/nsenter', '--net=/proc/self/fd/'+str(descriptor),
                             '/usr/sbin/'+tool, *args], pass_fds=(descriptor,),
                            stdin=subprocess.DEVNULL, capture_output=True, shell=False,
                            env={'PATH':'/usr/sbin:/usr/bin:/bin', 'LANG':'C'}, timeout=min(5, remaining))
    if result.returncode or len(result.stdout) > 65536:
        raise guardian.Refused('network_command_failed')
    return result.stdout


def network_rules(manifest):
    policies = [('-P', chain, 'DROP') for chain in ('INPUT', 'FORWARD', 'OUTPUT')]
    if manifest['schema_version'] == 2:
        address = manifest['network']['ipv4']+'/32'
        return policies + [('-A','INPUT','-s',address,'-p','tcp','-m','tcp','--sport','443',
                            '-m','conntrack','--ctstate','ESTABLISHED','-j','ACCEPT'),
                           ('-A','OUTPUT','-d',address,'-p','tcp','-m','tcp','--dport','443','-j','ACCEPT')], policies
    address, port = manifest['network']['proxy_ipv4']+'/32', str(guardian.relay.PORT)
    new = ('-m','conntrack','--ctstate','NEW,ESTABLISHED','-j','ACCEPT')
    established = ('-m','conntrack','--ctstate','ESTABLISHED','-j','ACCEPT')
    tcp = ('-p','tcp','-m','tcp')
    root = ('-m','owner','--uid-owner','0')
    client = ('-m','owner','--uid-owner','1000')
    rules = [('-A','OUTPUT','-o','lo','-d','127.0.0.1/32',*tcp,'--dport',port,*client,*new),
             ('-A','INPUT','-i','lo','-d','127.0.0.1/32',*tcp,'--dport',port,*new),
             ('-A','OUTPUT','-o','lo','-s','127.0.0.1/32',*tcp,'--sport',port,*root,*established),
             ('-A','INPUT','-i','lo','-s','127.0.0.1/32',*tcp,'--sport',port,*established),
             ('-A','OUTPUT','-d',address,*tcp,'--dport','3128',*root,*new),
             ('-A','INPUT','-s',address,*tcp,'--sport','3128',*established)]
    return policies + rules, policies


def configure_network(root, operation_id, nonce, phase):
    """One attempt per phase. Failure leaves the claim consumed and guardian gated."""
    try:
        if phase not in ('initialize', 'dispatch'):
            raise guardian.Refused('invalid_network_phase')
        directory = root / identity(operation_id)
        for path in (root, directory, directory/'control'):
            protected(path, directory=True)
        record, manifest = read(directory/'created.json'), read(directory/'control/launch.json')
        digest = hashlib.sha256(guardian.encode(manifest)).hexdigest()
        version = manifest.get('schema_version')
        valid = ((version == 2 and guardian.valid_network(manifest.get('network')))
                 or (version == 3 and guardian.valid_relay(manifest)))
        if (not valid
                or manifest.get('operation_id') != operation_id or record.get('operation_id') != operation_id
                or manifest.get('nonce') != nonce or record.get('nonce') != nonce
                or record.get('manifest_sha256') != digest
                or read(directory/'start.json').get('container_id') != record['container_id']):
            raise guardian.Refused('changed_network_operation')
        guardian.execution_remaining(manifest['deadline_ms'])
        gate = dict(operation_id=operation_id, manifest_sha256=digest, nonce=nonce, phase=phase)
        save(directory, 'network-'+phase+'-intent.json', gate)
        expected_networks = ['none'] if phase == 'initialize' else ['bridge']
        value = verify(directory, record, manifest, running=True, networks=expected_networks)
        pid = value['State']['Pid']
        cid = record['container_id']
        if version == 3:
            guardian.require_unmapped(pid)
        with network_handle(pid) as (descriptor, namespace):
            if verify(directory, record, manifest, running=True, networks=expected_networks)['State']['Pid'] != pid:
                raise guardian.Refused('network_identity_changed')
            rules, policies = network_rules(manifest)
            def check_rules():
                for tool, expected in (('iptables', rules), ('ip6tables', policies)):
                    actual = net_command(descriptor, tool, '-S', deadline=manifest['deadline_ms']).decode('ascii').splitlines()
                    if sorted(actual) != sorted(' '.join(rule) for rule in expected):
                        raise guardian.Refused('network_rules_changed')
            if phase == 'initialize':
                for tool, commands in (('iptables', rules), ('ip6tables', policies)):
                    for args in commands:
                        net_command(descriptor, tool, *args, deadline=manifest['deadline_ms'])
                check_rules()
                guardian.execution_remaining(manifest['deadline_ms'])
                docker('network', 'disconnect', 'none', cid)
                guardian.execution_remaining(manifest['deadline_ms'])
                docker('network', 'connect', 'bridge', cid)
            check_rules()
            final = verify(directory, record, manifest, running=True, networks=['bridge'])
            if final['State']['Pid'] != pid:
                raise guardian.Refused('network_identity_changed')
            if version == 3:
                guardian.require_unmapped(pid)
            with network_handle(pid) as (_, current):
                if current != namespace:
                    raise guardian.Refused('network_identity_changed')
            guardian.execution_remaining(manifest['deadline_ms'])
            gate['network_namespace'] = namespace
            save(directory/'control', 'network-'+phase+'.json', gate)
            return gate
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise guardian.Refused('network_failed_or_consumed') from error


def main():
    if sys.platform != 'linux' or os.getuid() != 0:
        return 125
    os.umask(0o077)
    try:
        if len(sys.argv) == 3 and sys.argv[1] == 'prepare':
            raw = sys.stdin.buffer.read(guardian.MESSAGE_LIMIT+1)
            if len(raw) > guardian.MESSAGE_LIMIT:
                raise guardian.Refused('invalid_manifest')
            result = prepare(STATE, sys.argv[2], guardian.decode(raw))
            print(guardian.encode(result).decode(), flush=True)
            return 0
        if len(sys.argv) == 4 and sys.argv[1] == 'run':
            command = start_command(STATE, sys.argv[2], sys.argv[3])
            os.execve(command[0], command, {'PATH': '/usr/bin:/bin', 'HOME': '/root'})
        if len(sys.argv) == 5 and sys.argv[1] == 'network':
            result = configure_network(STATE, sys.argv[2], sys.argv[3], sys.argv[4])
            print(guardian.encode(result).decode(), flush=True)
            return 0
        if len(sys.argv) == 4 and sys.argv[1] in ('observe', 'stop'):
            action = observe if sys.argv[1] == 'observe' else stop
            result = action(STATE, sys.argv[2], sys.argv[3])
            print(guardian.encode(result).decode(), flush=True)
            return 0
        raise guardian.Refused('invalid_arguments')
    except (guardian.Refused, OSError) as error:
        print(guardian.encode(dict(kind='refused', reason=str(error) if isinstance(error, guardian.Refused)
                                   else type(error).__name__)).decode(), flush=True)
        return 125


if __name__ == '__main__':
    sys.exit(main())
