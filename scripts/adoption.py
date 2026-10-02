"""Private reversible-adoption records. Restore never runs as a setup side effect."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import adoption_fs as fs
from document_store import atomic_write, process_alive, safe_path

RUNNER_FILES = ('adoption.py', 'adoption_fs.py', 'adoption_acl.ps1', 'document_store.py', 'integrations.py')
PHASES = ('capturing', 'ready', 'installing', 'installed', 'install_failed', 'restoring', 'restored')
MAX_RECORD = 32 * 1024**2


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def root_key(root):
    return os.path.normcase(str(fs.checked_path(root)))


def store_for(root, base):
    return fs.checked_path(base / hashlib.sha256(root_key(root).encode()).hexdigest())


def duplicate_guard(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('invalid_record')
        result[key] = value
    return result


def read_record(store, relative):
    path = safe_path(store, relative)
    if path.stat().st_size > MAX_RECORD:
        raise ValueError('invalid_record')
    try:
        wrapped = json.loads(path.read_bytes(), object_pairs_hook=duplicate_guard,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError('invalid_record')))
        if set(wrapped) != {'payload', 'sha256'} or fs.tree_digest(wrapped['payload']) != wrapped['sha256']:
            raise ValueError('invalid_record')
        return wrapped['payload']
    except (UnicodeError, json.JSONDecodeError, TypeError, KeyError) as error:
        raise ValueError('invalid_record') from error


def write_record(store, relative, payload):
    data = fs.canonical(dict(payload=payload, sha256=fs.tree_digest(payload)))
    if len(data) > MAX_RECORD:
        raise ValueError('record_limit')
    atomic_write(store, relative, data)
    if os.name != 'nt':
        os.chmod(safe_path(store, relative), 0o600)
        descriptor = os.open(safe_path(store, relative).parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def read_state(store):
    state = read_record(store, 'state.json')
    if (not isinstance(state, dict) or state.get('schema') != 1 or state.get('state') not in PHASES
            or type(state.get('revision')) is not int or state['revision'] < 1
            or type(state.get('root_exists')) is not bool
            or not isinstance(state.get('root'), str)):
        raise ValueError('invalid_record')
    try:
        uuid.UUID(state['adoption_id'])
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('invalid_record') from error
    return state


def write_state(store, previous, **changes):
    state = dict(previous, **changes)
    state['revision'] = state.get('revision', 0) + 1
    state['updated'] = now()
    write_record(store, 'state.json', state)
    return state


@contextmanager
def lock_guard(store):
    """OS advisory lock releases on process death; the recovery record is persistent."""
    path = safe_path(store, 'reclaim.lock')
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(descriptor, 'r+b') as guard:
        guard.seek(0, os.SEEK_END)
        if guard.tell() == 0:
            guard.write(b'0')
            guard.flush()
        guard.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('locked') from error
        try:
            yield
        finally:
            guard.seek(0)
            if os.name == 'nt':
                msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(guard, fcntl.LOCK_UN)


def process_start(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            values = [wintypes.FILETIME() for _ in range(4)]
            if kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in values)):
                return str((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
        return None
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip() + ':' + fields[19]
    except (OSError, IndexError):
        return None


def owner_alive(lock, *, child=False):
    pid = lock.get('child_pid' if child else 'pid')
    if pid is None or not process_alive(pid):
        return False
    recorded = lock.get('child_start' if child else 'owner_start')
    current = process_start(pid)
    return recorded is None or current is None or recorded == current


def new_lock():
    return dict(schema=1, lock_id=str(uuid.uuid4()), token=str(uuid.uuid4()),
                pid=os.getpid(), child_pid=None, owner_start=process_start(os.getpid()), started=now())


@contextmanager
def adoption_lease(store):
    lock = new_lock()
    with lock_guard(store):
        path = safe_path(store, 'lock.json')
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(fs.canonical(dict(payload=lock, sha256=fs.tree_digest(lock))))
                output.flush()
                os.fsync(output.fileno())
        except FileExistsError as error:
            raise ValueError('locked') from error
    try:
        yield lock
    finally:
        # A stopped controller may leave a child alive: never release that lease.
        with lock_guard(store):
            current = read_record(store, 'lock.json')
            if current.get('token') == lock['token'] and not owner_alive(current, child=True):
                safe_path(store, 'lock.json').unlink()


def recover_lock(root, base, confirmation):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not store.is_dir():
        raise ValueError('missing_baseline')
    with lock_guard(store):
        lock = read_record(store, 'lock.json')
        if lock.get('lock_id') != str(uuid.UUID(confirmation)):
            raise ValueError('lock_changed')
        if owner_alive(lock) or owner_alive(lock, child=True):
            raise ValueError('owner_alive')
        destination = safe_path(store, 'locks/' + confirmation + '.json')
        destination.parent.mkdir(exist_ok=True)
        if destination.exists():
            raise ValueError('lock_changed')
        os.rename(safe_path(store, 'lock.json'), destination)
    return dict(state='lock_recovered', next_action='inspect_status')


def git_preflight(root, tree):
    if not tree['exists']:
        result = fs.git_read(root.parent, 'rev-parse', '--absolute-git-dir')
        if result.returncode == 0:
            raise ValueError('unsupported_git')
        if b'not a git repository' not in result.stderr.lower():
            raise ValueError('git_boundary_unknown')
        return
    paths = {entry['path'] for entry in tree['entries']}
    for relative in paths:
        parts = relative.lower().split('/')
        if '.git' in parts and (parts[0] != '.git' or '.git' in parts[1:]):
            raise ValueError('unsupported_git')
    if any(name in paths for name in ('.git/commondir', '.git/worktrees', '.git/modules',
                                      '.git/objects/info/alternates')):
        raise ValueError('unsupported_git')
    markers = ('.git/index.lock', '.git/HEAD.lock', '.git/config.lock', '.git/packed-refs.lock',
               '.git/shallow.lock', '.git/rebase-apply', '.git/rebase-merge', '.git/MERGE_HEAD',
               '.git/CHERRY_PICK_HEAD', '.git/REVERT_HEAD')
    if any(name in paths for name in markers) or any(p.startswith('.git/refs/') and p.endswith('.lock') for p in paths):
        raise ValueError('git_operation_in_progress')
    result = fs.git_read(root, 'rev-parse', '--show-toplevel')
    if result.returncode:
        if '.git' in paths or b'not a git repository' not in result.stderr.lower():
            raise ValueError('unsupported_git')
        return
    if root_key(Path(os.fsdecode(result.stdout).strip())) != root_key(root) or not (root / '.git').is_dir():
        raise ValueError('unsupported_git')
    for query in ('--git-common-dir', '--git-dir'):
        response = fs.git_read(root, 'rev-parse', query)
        path = Path(os.fsdecode(response.stdout).strip())
        if not path.is_absolute():
            path = root / path
        if response.returncode or root_key(path) != root_key(root / '.git'):
            raise ValueError('unsupported_git')
    config = fs.git_read(root, 'config', '--local', '--no-includes', '--list', '--null')
    if config.returncode:
        raise ValueError('unsupported_git')
    keys = [item.split(b'\n', 1)[0].lower() for item in config.stdout.split(b'\0')]
    if any(k.startswith((b'include.', b'includeif.')) or k in (b'core.worktree', b'extensions.worktreeconfig') for k in keys):
        raise ValueError('unsupported_git')
    staged = fs.git_read(root, 'ls-files', '--stage', '-z')
    if staged.returncode or any(item.startswith(b'160000 ') for item in staged.stdout.split(b'\0')):
        raise ValueError('unsupported_git')


def verify_binding(root, state):
    if state['root'] != root_key(root) or state.get('parent_identity') != fs.identity(root.parent):
        raise ValueError('root_identity_changed')
    if state.get('active_identity') != fs.identity(root):
        raise ValueError('root_identity_changed')


def verify_baseline(store, state):
    inventory = read_record(store, 'baseline/inventory.json')
    if (fs.tree_digest(inventory) != state.get('baseline_digest')
            or fs.tree_digest(fs.inspect_tree(store / 'baseline/tree')) != state.get('baseline_digest')):
        raise ValueError('baseline_corrupt')
    fs.inspect_permissions(store / 'baseline/tree', role='snapshot')
    hashes = state.get('runner_hashes', {})
    if set(hashes) != set(RUNNER_FILES):
        raise ValueError('runner_corrupt')
    for name in RUNNER_FILES:
        try:
            if fs.hash_file(store / 'runner' / name) != hashes[name]:
                raise ValueError('runner_corrupt')
        except OSError as error:
            raise ValueError('runner_corrupt') from error
    return inventory


def public_status(store, state):
    return dict(adoption_id=state['adoption_id'], state=state['state'],
                root_exists=state['root_exists'], baseline_digest=state.get('baseline_digest'),
                runner=str(store / 'runner/adoption.py'), revision=state['revision'])


def status(root, base):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not (store / 'state.json').exists():
        return dict(state='missing_baseline')
    state = read_state(store)
    if state['state'] not in ('restoring', 'restored'):
        verify_binding(root, state)
    if state['state'] != 'capturing':
        verify_baseline(store, state)
    result = public_status(store, state)
    if (store / 'lock.json').exists():
        lock = read_record(store, 'lock.json')
        result.update(lock_id=lock['lock_id'], owner_alive=owner_alive(lock),
                      child_alive=owner_alive(lock, child=True))
    return result


def prepare(root, base):
    root = fs.checked_path(root)
    tree = fs.inspect_tree(root)
    git_preflight(root, tree)
    policy = fs.inspect_permissions(root, role='project')
    base = fs.validate_storage(root, base, create=True)
    store = store_for(root, base)
    if not (store / 'state.json').exists() and all((root / name).is_file() for name in
            ('skills-lock.json', 'scripts/vault.py', 'skills/personalizer/SKILL.md')):
        raise ValueError('legacy_without_baseline')
    fs.ensure_space(base, tree['total_bytes'])
    if not store.exists():
        fs.private_dir(store)
    with adoption_lease(store):
        if (store / 'state.json').exists():
            state = read_state(store)
            verify_binding(root, state)
            if state['state'] != 'capturing':
                verify_baseline(store, state)
                return public_status(store, state)
            # No setup could run while capturing; retain incomplete attempts.
            incomplete = store / 'incomplete'
            incomplete.mkdir(exist_ok=True)
            for name in ('baseline', 'runner'):
                if (store / name).exists():
                    os.rename(store / name, incomplete / (name + '-' + str(uuid.uuid4())))
        else:
            state = dict(schema=1, adoption_id=str(uuid.uuid4()), revision=0, root=root_key(root),
                         state='capturing', root_exists=tree['exists'], active_identity=fs.identity(root),
                         parent_identity=fs.identity(root.parent), created=now())
        state = write_state(store, state, state='capturing', parent_policy=policy,
                            root_exists=tree['exists'], baseline_digest=None)
        fs.private_dir(store / 'baseline')
        fs.copy_verified(root, store / 'baseline/tree', tree)
        write_record(store, 'baseline/inventory.json', tree)
        fs.private_dir(store / 'runner')
        hashes = {}
        for name in RUNNER_FILES:
            path = fs.checked_path(Path(__file__).parent / name)
            if path.stat().st_size > MAX_RECORD:
                raise ValueError('runner_corrupt')
            payload = path.read_bytes()
            atomic_write(store, 'runner/' + name, payload)
            hashes[name] = hashlib.sha256(payload).hexdigest()
        candidate = dict(state, baseline_digest=fs.tree_digest(tree), runner_hashes=hashes)
        verify_baseline(store, candidate)
        verify_binding(root, state)
        if fs.inspect_permissions(root, role='project') != policy:
            raise ValueError('parent_permissions_changed')
        state = write_state(store, candidate, state='ready')
        return public_status(store, state)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Private local adoption records; stop project writers first.')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--backup-root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'status', 'recover-lock'):
        command = sub.add_parser(name)
        command.add_argument('--json', action='store_true')
        if name == 'recover-lock':
            command.add_argument('--confirm', required=True)
    args = parser.parse_args(argv)
    try:
        root = fs.checked_path(args.root)
        base = fs.checked_path(args.backup_root or root.parent / '.youngcrow-recovery')
        if args.command == 'recover-lock':
            result = recover_lock(root, base, args.confirm)
        else:
            result = globals()[args.command](root, base)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z_]+', str(error)) else 'operation_failed'
        print(json.dumps(dict(state='failed', code=code)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
