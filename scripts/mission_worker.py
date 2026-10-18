"""Local OCI tool boundary. No provider credentials, model calls or host shell."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import stat
import subprocess
import tarfile
import time
import uuid
import math
from datetime import datetime

import adoption_fs as fs

DATA_LIMIT = 8 * 1024 * 1024
ARCHIVE_LIMIT = DATA_LIMIT + 1024 * 1024
FILE_LIMIT = 128
SOCKET = '--host=unix:///var/run/docker.sock'
SENSITIVE = {'.git', '.env', '.claude', '.codex', '.ssh', '.aws', 'auth.json',
             '.credentials.json', 'id_rsa', 'id_ed25519', 'registry.json',
             '.runtime', 'node_modules', '__pycache__'}


def require(condition, reason='invalid_worker_input'):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    require(type(name) is str and 0 < len(name) <= 512 and '\\' not in name and '\x00' not in name)
    path = PurePosixPath(name)
    require(bool(path.parts) and not path.is_absolute() and str(path) == name
            and all(p not in ('..', '.') for p in path.parts))
    return name


def archive_files(data):
    """Parse regular data only; never delegate extraction or follow archive links."""
    require(type(data) is bytes and len(data) <= ARCHIVE_LIMIT, 'worker_output_limit')
    result, total, entries, directories = {}, 0, 0, set()
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            for info in archive:
                entries += 1
                require(entries <= 2 * FILE_LIMIT, 'worker_output_limit')
                name = info.name
                if info.isdir() and name in ('.', './'):
                    continue
                if name.startswith('./'):
                    name = name[2:]
                relative(name.rstrip('/') if info.isdir() else name)
                name = name.rstrip('/') if info.isdir() else name
                parents = {str(p) for p in PurePosixPath(name).parents if str(p) != '.'}
                require(not parents.intersection(result), 'invalid_worker_archive')
                directories.update(parents)
                if info.isdir():
                    require(name not in result, 'invalid_worker_archive')
                    directories.add(name)
                    continue
                require(info.isreg() and not info.issparse() and name not in result
                        and name not in directories, 'invalid_worker_archive')
                total += info.size
                require(0 <= info.size <= DATA_LIMIT and total <= DATA_LIMIT and len(result) < FILE_LIMIT,
                        'worker_output_limit')
                result[name] = archive.extractfile(info).read(info.size + 1)
                require(len(result[name]) == info.size, 'invalid_worker_archive')
    except (tarfile.TarError, OSError, EOFError) as error:
        raise ValueError('invalid_worker_archive') from error
    return result


def archive_bytes(files, *, uid=1000, mode=0o600):
    require(type(files) is dict and len(files) <= FILE_LIMIT)
    stream = io.BytesIO()
    directories = {str(p) for name in files for p in PurePosixPath(relative(name)).parents if str(p) != '.'}
    require(not directories.intersection(files), 'invalid_worker_archive')
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name in sorted(directories):
            info = tarfile.TarInfo(name)
            info.type, info.mode, info.uid, info.gid = tarfile.DIRTYPE, 0o555 if uid == 0 else 0o700, uid, uid
            archive.addfile(info)
        for name, content in sorted(files.items()):
            relative(name)
            require(type(content) is bytes)
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.uid, info.gid = len(content), mode, uid, uid
            archive.addfile(info, io.BytesIO(content))
    data = stream.getvalue()
    archive_files(data)
    return data


def read_source(path):
    """Open each ancestor by descriptor: an exchanged symlink is never followed."""
    descriptors = []
    try:
        current = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(current)
        for part in path.parts[1:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(current)
        before = os.stat(path.name, dir_fd=current, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'invalid_worker_input')
        require(before.st_size <= DATA_LIMIT, 'worker_output_limit')
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        with os.fdopen(descriptor, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            require(fs.stamp(before) == fs.stamp(opened), 'worker_input_changed')
            content = stream.read(DATA_LIMIT + 1)
            require(fs.stamp(opened) == fs.stamp(os.fstat(stream.fileno())), 'worker_input_changed')
        fs.checked_path(path)
        require(fs.stamp(before) == fs.stamp(path.lstat()) and len(content) == before.st_size,
                'worker_input_changed')
        return content
    except OSError as error:
        raise ValueError('worker_input_changed') from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def pack(root, paths, destination):
    root = fs.checked_path(Path(root).absolute())
    destination = fs.checked_path(Path(destination).absolute())
    require(type(paths) is list and 0 < len(paths) <= FILE_LIMIT and len(paths) == len(set(paths)))
    files, total = {}, 0
    for name in paths:
        relative(name)
        require(not any(p in SENSITIVE or p.startswith('.env.') for p in PurePosixPath(name).parts),
                'sensitive_worker_input')
        path = fs.checked_path(root / name)
        content = read_source(path)
        total += len(content)
        require(total <= DATA_LIMIT, 'worker_output_limit')
        files[name] = content
    data = archive_bytes(files)
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError('worker_destination_exists') from error
    with os.fdopen(descriptor, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return dict(sha256=sha(data), files={k: sha(v) for k, v in files.items()}, bytes=total)


def docker_env():
    return {k: v for k, v in os.environ.items() if k not in
            {'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'}}


def call(docker, args, *, data=None, seconds=10, limit=ARCHIVE_LIMIT, buildx_config=None):
    """Bounded streams and time; do not print daemon errors or inherited environment."""
    require(Path(docker).is_absolute() and Path(docker).is_file())
    env = docker_env()
    if buildx_config is not None:
        env['BUILDX_CONFIG'] = str(buildx_config)
    process = subprocess.Popen([str(docker), SOCKET, *args], env=env,
                               stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    selector, chunks, total = selectors.DefaultSelector(), {'out': bytearray(), 'err': bytearray()}, 0
    deadline = time.monotonic() + max(0.01, seconds)
    try:
        for stream, label in ((process.stdout, 'out'), (process.stderr, 'err')):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        if data is not None:
            require(len(data) <= ARCHIVE_LIMIT, 'worker_output_limit')
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, 'in')
            pending = memoryview(data)
        while selector.get_map():
            require(time.monotonic() < deadline, 'worker_command_timeout')
            for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                if key.data == 'in':
                    if pending:
                        count = os.write(key.fd, pending[:65536])
                        pending = pending[count:]
                    if not pending:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    part = os.read(key.fd, 65536)
                    if not part:
                        selector.unregister(key.fileobj)
                    else:
                        total += len(part)
                        require(total <= limit, 'worker_output_limit')
                        chunks[key.data].extend(part)
        code = process.wait(timeout=max(.01, deadline - time.monotonic()))
        if code != 0:
            error = ValueError('worker_command_failed')
            error.private_stderr = bytes(chunks['err'])
            raise error
        return bytes(chunks['out'])
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('worker_command_failed') from error
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def engine(docker):
    value = json.loads(call(docker, ['info', '--format', '{{json .}}']))
    require(value.get('OSType') == 'linux' and value.get('Architecture') in ('x86_64', 'amd64'),
            'unsupported_worker_runtime')
    return dict(id=value['ID'], version=value['ServerVersion'],
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def workspace(operation_id):
    require(type(operation_id) is str and str(uuid.UUID(operation_id)) == operation_id)
    return '/tmp/youngcrow-' + operation_id + '/cwd'


def exec_argv(handle, argv):
    require(type(handle.get('container_id')) is str and re.fullmatch('[a-f0-9]{64}', handle['container_id']))
    require(type(argv) is list and 0 < len(argv) <= 128 and all(type(a) is str and '\0' not in a for a in argv))
    require(argv[0].startswith('/'))
    return [str(handle['docker']), SOCKET, 'exec', '-i', '--user=1000:1000', '--workdir=' + workspace(handle['operation_id']),
            handle['container_id'], *argv]


def validate_plan(plan):
    # This is the minimal runtime envelope; the mission coordinator binds its larger plan separately.
    require(type(plan) is dict and set(plan) == {'contract', 'schema_version', 'operation_id',
            'deadline_ms', 'image_digest', 'package_sha256', 'engine'})
    require(plan['contract'] == 'isolated-tools' and type(plan['schema_version']) is int
            and plan['schema_version'] == 1)
    require(type(plan['operation_id']) is str and str(uuid.UUID(plan['operation_id'])) == plan['operation_id'])
    require(type(plan['deadline_ms']) is int and 1000 < plan['deadline_ms'] - time.time()*1000 <= 120000,
            'invalid_worker_deadline')
    require(type(plan['image_digest']) is str and re.fullmatch('sha256:[a-f0-9]{64}', plan['image_digest']))
    require(type(plan['package_sha256']) is str and re.fullmatch('[a-f0-9]{64}', plan['package_sha256']))
    require(type(plan['engine']) is dict and set(plan['engine']) == {'id', 'version', 'boot_id'}
            and all(type(v) is str and v for v in plan['engine'].values()))


def _inspection(handle):
    require(engine(handle['docker']) == handle['engine'], 'worker_engine_changed')
    rows = json.loads(call(handle['docker'], ['inspect', handle['container_id']]))
    require(type(rows) is list and len(rows) == 1)
    row = rows[0]
    require(row['Id'] == handle['container_id'] and row['Image'] == handle['image_digest'],
            'worker_identity_changed')
    config, host = row['Config'], row['HostConfig']
    require(host['NetworkMode'] == 'none' and host['ReadonlyRootfs'] is True
            and host['Privileged'] is False and host['CapDrop'] == ['ALL']
            and not host['CapAdd'] and host['PidMode'] == '' and host['IpcMode'] == 'private'
            and host['RestartPolicy']['Name'] == 'no' and not host['Binds']
            and not host['Devices'] and not host['PortBindings']
            and host['PidsLimit'] == 128 and host['Memory'] == 1073741824
            and host['MemorySwap'] == 1073741824 and host.get('OomKillDisable') in (False, None)
            and host['NanoCpus'] == 2000000000
            and 'no-new-privileges' in host['SecurityOpt'] and config['User'] == '0:0',
            'worker_boundary_changed')
    require(config['Labels'].get('youngcrow.operation') == handle['operation_id']
            and config['Labels'].get('youngcrow.plan') == handle['plan_sha256'], 'worker_identity_changed')
    require(not any(m['Type'] == 'bind' for m in row['Mounts']), 'worker_boundary_changed')
    # Engine28 changes the equivalent false value to null after starting.
    normalized_host = dict(host, OomKillDisable=False)
    stamp = sha(fs.canonical(dict(config=config, host=normalized_host, created=row['Created'])))
    if 'config_sha256' in handle:
        require(stamp == handle['config_sha256'], 'worker_boundary_changed')
    return row, stamp


def start(plan, package, docker, persist):
    validate_plan(plan)
    data = Path(package).read_bytes()
    require(len(data) <= ARCHIVE_LIMIT and sha(data) == plan['package_sha256'], 'worker_input_changed')
    archive_files(data)
    require(engine(docker) == plan['engine'], 'worker_engine_changed')
    plan_hash = sha(fs.canonical(plan))
    cwd = workspace(plan['operation_id'])
    manifest = dict(operation_id=plan['operation_id'], deadline_ms=plan['deadline_ms'], plan_sha256=plan_hash)
    args = ['create', '--network=none', '--ipc=private', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--user=0:0', '--restart=no', '--pids-limit=128',
            '--memory=1g', '--memory-swap=1g', '--cpus=2', '--workdir=' + cwd,
            '--tmpfs=/snapshot:rw,nosuid,nodev,noexec,size=16777216,mode=0755',
            '--tmpfs=/tmp:rw,nosuid,nodev,size=16777216,mode=1777',
            '--tmpfs=' + cwd + ':rw,nosuid,nodev,exec,size=67108864,uid=1000,gid=1000,mode=0700',
            '--tmpfs=/control:rw,nosuid,nodev,noexec,size=65536,mode=0700',
            '--label=youngcrow.operation=' + plan['operation_id'], '--label=youngcrow.plan=' + plan_hash,
            '--env=HOME=' + cwd, '--env=CODEX_HOME=/tmp/codex',
            '--env=YC_WORKER_MANIFEST=' + fs.canonical(manifest).decode()]
    for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'):
        args.append('--env=' + key + '=')
    persist('create_intent', dict(plan_sha256=plan_hash))
    container_id = call(docker, [*args, plan['image_digest']]).decode().strip()
    require(re.fullmatch('[a-f0-9]{64}', container_id) is not None, 'worker_identity_unknown')
    handle = dict(container_id=container_id, docker=str(docker), engine=plan['engine'],
                  image_digest=plan['image_digest'], operation_id=plan['operation_id'],
                  plan_sha256=plan_hash, deadline_ms=plan['deadline_ms'])
    # Record identity before any further query: recovery can preserve ambiguous resources.
    persist('created', handle.copy())
    row, handle['config_sha256'] = _inspection(handle)
    env = dict(v.split('=', 1) for v in row['Config']['Env'])
    allowed = {'PATH', 'LANG', 'PYTHON_VERSION', 'PYTHON_SHA256', 'GPG_KEY', 'HOME', 'CODEX_HOME', 'YC_WORKER_MANIFEST',
               'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'}
    require(set(env) <= allowed and all(not v for k, v in env.items() if 'proxy' in k.lower()),
            'worker_environment_unexpected')
    persist('start_intent', handle.copy())
    call(docker, ['start', container_id])
    end = min(time.monotonic()+5, time.monotonic()+(plan['deadline_ms']/1000-time.time())-1)
    while time.monotonic() < end:
        logs = call(docker, ['logs', container_id], limit=16384).strip()
        if logs:
            ready = json.loads(logs)
            require(ready == dict(kind='ready', plan_sha256=plan_hash), 'worker_guardian_failed')
            break
        time.sleep(.02)
    else:
        raise ValueError('worker_guardian_failed')
    _import(handle, data, snapshot=False)
    require(observe(handle)['running'], 'worker_not_running')
    persist('ready', handle.copy())
    return handle


def observe(handle):
    row, _ = _inspection(handle)
    state = row['State']
    finished = state['FinishedAt']
    finished_ms = None
    if not finished.startswith('0001'):
        finished_ms = math.ceil(datetime.fromisoformat(finished.replace('Z', '+00:00')).timestamp()*1000)
    return dict(running=state['Running'], paused=state['Paused'], pid=state['Pid'],
                exit_code=state['ExitCode'], finished_ms=finished_ms, network_mode=row['HostConfig']['NetworkMode'],
                tool_uid=1000, host_bind_mounts=[m for m in row['Mounts'] if m['Type'] == 'bind'])


def execute(handle, argv, *, uid=1000, limit=DATA_LIMIT):
    current = observe(handle)
    require(current['running'] and not current['paused'], 'worker_not_running')
    remaining = handle['deadline_ms']/1000-time.time()-1
    require(remaining > 0, 'invalid_worker_deadline')
    require(uid in (1000, 2000))
    require(type(limit) is int and 0 < limit <= ARCHIVE_LIMIT)
    command = exec_argv(handle, argv)[2:]
    if uid == 2000:
        command[2] = '--user=2000:2000'
        command[3] = '--workdir=/snapshot'
    return call(handle['docker'], command, seconds=min(remaining, 30), limit=limit)


def stop(handle, persist):
    current = observe(handle)
    if current['running']:
        persist('stop_intent', dict(container_id=handle['container_id']))
        call(handle['docker'], ['kill', handle['container_id']])
        current = observe(handle)
    require(not current['running'] and current['pid'] == 0, 'worker_stop_uncertain')
    persist('stopped', current)
    return current


def remove(handle, persist):
    require(not observe(handle)['running'], 'worker_not_stopped')
    persist('remove_intent', dict(container_id=handle['container_id']))
    call(handle['docker'], ['rm', handle['container_id']])
    persist('removed', dict(container_id=handle['container_id']))


def _import(handle, data, *, snapshot):
    require(observe(handle)['running'], 'worker_not_running')
    remaining = handle['deadline_ms']/1000-time.time()-1
    require(remaining > 0, 'invalid_worker_deadline')
    result = call(handle['docker'], ['exec', '-i', '--user=0:0' if snapshot else '--user=1000:1000',
                  '--workdir=/', handle['container_id'], '/usr/local/bin/python3', '-I', '-B',
                  '/opt/youngcrow/transfer.py'], data=data, seconds=remaining)
    require(result == b'imported\n', 'worker_import_failed')


def collect(handle, destination, persist):
    require(observe(handle)['running'], 'worker_artifact_unavailable')
    captured = execute(handle, ['/usr/local/bin/python3', '-I', '-B', '/opt/youngcrow/transfer.py', '--export'], limit=ARCHIVE_LIMIT)
    files = archive_files(captured)
    snapshot = archive_bytes(files, uid=0, mode=0o444)
    _import(handle, snapshot, snapshot=True)
    test_output = execute(handle, ['/usr/local/bin/python3', '-I', '-B', '/opt/youngcrow/check.py'], uid=2000)
    test = json.loads(test_output)
    require(test == {'cases': 3, 'exit_code': 0}, 'worker_test_failed')
    stopped = stop(handle, persist)
    require(stopped['finished_ms'] <= handle['deadline_ms'], 'worker_deadline_exceeded')
    destination = fs.checked_path(Path(destination).absolute())
    fs.private_dir(destination)
    for name, content in files.items():
        path = destination / relative(name)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open('xb') as output:
            output.write(content)
    result = dict(files={k: sha(v) for k, v in files.items()}, snapshot_sha256=sha(snapshot),
                  test=test, worker_stopped_before_publish=True, finished_ms=stopped['finished_ms'])
    persist('collected', result)
    return result
