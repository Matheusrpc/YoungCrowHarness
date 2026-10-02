"""Private reversible-adoption records. Restore never runs as a setup side effect."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

import adoption_fs as fs
from document_store import atomic_write, process_alive, safe_path

RUNNER_FILES = ('adoption.py', 'adoption_fs.py', 'adoption_acl.ps1', 'document_store.py', 'integrations.py')
PHASES = ('capturing', 'ready', 'installing', 'installed', 'install_failed', 'restoring', 'restored')
# Minimum revision of each phase, allowing optional Windows and existing-root steps.
TRANSACTION_PHASES = dict(copying=1, prepared=2, privatizing_current=3, current_private=4,
                          moving_current=3, current_moved=4, activating_baseline=5,
                          baseline_activated=5, complete=6, invalidated=2)
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
    previous_observer = fs.child_observer
    def observe(pid):
        current = read_record(store, 'lock.json')
        if current.get('token') != lock['token']:
            raise ValueError('lock_changed')
        current.update(child_pid=pid, child_start=process_start(pid) if pid is not None else None)
        write_record(store, 'lock.json', current)
    fs.child_observer = observe
    try:
        yield lock
    finally:
        fs.child_observer = previous_observer
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
        state = read_state(store)
        if state['state'] == 'installing':
            verify_binding(root, state)
            write_state(store, state, state='install_failed')
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
    result = dict(adoption_id=state['adoption_id'], state=state['state'],
                root_exists=state['root_exists'], baseline_digest=state.get('baseline_digest'),
                runner=str(store / 'runner/adoption.py'), revision=state['revision'])
    if state.get('transaction_id'):
        result['transaction_id'] = state['transaction_id']
    return result


def status(root, base):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not (store / 'state.json').exists():
        return dict(state='missing_baseline')
    state = read_state(store)
    if state['root'] != root_key(root):
        raise ValueError('root_identity_changed')
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


def create_and_bind_root_if_absent(root, store, state):
    verify_binding(root, state)
    verify_baseline(store, state)
    if root.exists():
        return state
    if state.get('root_creation') == 'pending':
        raise ValueError('root_creation_unresolved')
    state = write_state(store, state, root_creation='pending')
    root.mkdir()
    state = write_state(store, state, root_creation='bound', active_identity=fs.identity(root))
    return state


def verify_child(root, base):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    state = read_state(store)
    lock = read_record(store, 'lock.json')
    if (state['state'] != 'installing' or not os.environ.get('YOUNGCROW_ADOPTION_TOKEN')
            or lock.get('token') != os.environ['YOUNGCROW_ADOPTION_TOKEN']
            or not owner_alive(lock) or not owner_alive(lock, child=True)):
        raise ValueError('invalid_install_child')
    verify_binding(root, state)
    verify_baseline(store, state)
    return dict(state='install_child_verified')


def run_install(root, base, source, options):
    root, source = fs.checked_path(root), fs.checked_path(source)
    if root == source or root in source.parents or source in root.parents:
        raise ValueError('invalid_install_source')
    # Reserve space for bundled paths before creating the baseline or the project.
    trial_target = store_for(root, fs.checked_path(base)) / 'transactions' / str(uuid.UUID(int=0)) / 'trial-copy'
    fs.ensure_paths_fit(trial_target, ['x' * 64, *[e['path'] for e in fs.inspect_tree(root)['entries']]])
    prepare(root, base)
    base = fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    with adoption_lease(store) as lease:
        state = read_state(store)
        verify_binding(root, state)
        verify_baseline(store, state)
        if state['state'] not in ('ready', 'installed', 'install_failed'):
            raise ValueError('adoption_not_ready')
        if state['state'] == 'ready' and fs.tree_digest(fs.inspect_tree(root)) != state['baseline_digest']:
            raise ValueError('source_changed')
        if fs.inspect_permissions(root, role='project') != state['parent_policy']:
            raise ValueError('parent_permissions_changed')
        state = create_and_bind_root_if_absent(root, store, state)
        state = write_state(store, state, state='installing')
        bash = shutil.which('bash')
        if not bash:
            write_state(store, state, state='install_failed')
            raise ValueError('missing_bash')
        env = {k: v for k, v in os.environ.items()
               if k not in ('BASH_ENV', 'ENV') and not k.startswith('PYTHON')}
        env.update(YOUNGCROW_ADOPTION_TOKEN=lease['token'], YOUNGCROW_ADOPTION_BASE=str(base))
        child = None
        try:
            child = subprocess.Popen([bash, '--noprofile', '--norc', str(source / 'setup.sh'),
                                      str(root), '--trial-child', *options],
                                     cwd=source, env=env, stdin=subprocess.PIPE)
            fs.child_observer(child.pid)
            child.stdin.write(b'ready\n')
            child.stdin.close()
            code = child.wait()
            fs.child_observer(None)
            state = write_state(store, state, state='installed' if code == 0 else 'install_failed')
            print(json.dumps(public_status(store, state), ensure_ascii=True))
            return code
        except BaseException:
            # Stop only the start pipe. A released child keeps its persistent lease until it exits.
            if child is not None and child.stdin and not child.stdin.closed:
                child.stdin.close()
            if child is None or child.poll() is not None:
                write_state(store, state, state='install_failed')
            raise


def proposal_for(root, store, state):
    if state['state'] not in ('ready', 'installed', 'install_failed'):
        raise ValueError('adoption_not_ready')
    verify_binding(root, state)
    baseline = verify_baseline(store, state)
    current = fs.inspect_tree(root)
    if not current['exists']:
        raise ValueError('missing_trial_root')
    git_preflight(root, current)
    policy = fs.inspect_permissions(root, role='project')
    if policy != state['parent_policy']:
        raise ValueError('parent_permissions_changed')
    old = {entry['path']: entry for entry in baseline['entries']}
    new = {entry['path']: entry for entry in current['entries']}
    changes = dict(added=sorted(new.keys() - old.keys()), removed=sorted(old.keys() - new.keys()),
                   modified=sorted(name for name in new.keys() & old.keys() if new[name] != old[name]))
    proposal = dict(schema=1, adoption_id=state['adoption_id'], revision=state['revision'],
                    baseline_digest=state['baseline_digest'], current_digest=fs.tree_digest(current),
                    root_identity=fs.identity(root), parent_policy=policy, changes=changes,
                    permission_step='private_before_move' if os.name == 'nt' else 'private_container')
    return proposal, current


def preview(root, base):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not (store / 'state.json').is_file():
        raise ValueError('missing_baseline')
    with adoption_lease(store):
        proposal, _ = proposal_for(root, store, read_state(store))
        digest = fs.tree_digest(proposal)
        path = 'previews/' + digest + '.json'
        if not (store / path).exists():
            write_record(store, path, proposal)
        elif read_record(store, path) != proposal:
            raise ValueError('preview_corrupt')
        return dict(digest=digest, counts={name: len(paths) for name, paths in proposal['changes'].items()},
                    report=str(store / path), runner=str(store / 'runner/adoption.py'),
                    permission_step=proposal['permission_step'])


def validate_journal(journal):
    if (not isinstance(journal, dict) or not isinstance(journal.get('phase'), str)
            or journal['phase'] not in TRANSACTION_PHASES
            or type(journal.get('revision')) is not int
            or not TRANSACTION_PHASES[journal['phase']] <= journal['revision'] < 2**63):
        raise ValueError('invalid_transaction')


def write_journal(transaction, previous, phase):
    journal = dict(previous, phase=phase, revision=previous.get('revision', 0) + 1)
    validate_journal(journal)
    write_record(transaction, 'journal.json', journal)
    return journal


def transaction_for(store, identity):
    try:
        if str(uuid.UUID(identity)) != identity:
            raise ValueError('invalid_transaction')
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('invalid_transaction') from error
    return fs.checked_path(store / 'transactions' / identity)


def recovery_result(root, store, state, journal, *, historical=False):
    validate_journal(journal)
    transaction = transaction_for(store, state['transaction_id'])
    recovery = transaction / 'trial-copy'
    if fs.tree_digest(fs.inspect_tree(recovery)) != journal['trial_digest']:
        raise ValueError('recovery_corrupt')
    fs.inspect_permissions(recovery, role='snapshot')
    result = public_status(store, state)
    result.update(recovery_path=str(recovery), displaced_path=str(transaction / 'displaced'),
                  historical=historical, drift=fs.tree_digest(fs.inspect_tree(root)) != state['baseline_digest'])
    return result


def ensure_snapshot(source, target, inventory, transaction):
    if target.exists():
        if fs.tree_digest(fs.inspect_tree(target)) == fs.tree_digest(inventory):
            fs.inspect_permissions(target, role='snapshot')
            return
        archive = fs.checked_path(transaction.parent.parent / 'incomplete')
        archive.mkdir(exist_ok=True)
        # Both paths are fixed descendants of this owned transaction; retain the partial copy.
        os.rename(fs.checked_path(target), fs.checked_path(archive / str(uuid.uuid4())))
    fs.copy_verified(source, target, inventory)


def resume_transaction(root, store, state, transaction, journal):
    validate_journal(journal)
    baseline = verify_baseline(store, state)
    trial = read_record(transaction, 'trial.json')
    if (journal.get('schema') != 1 or journal.get('phase') not in TRANSACTION_PHASES
            or journal.get('adoption_id') != state['adoption_id']
            or journal.get('baseline_digest') != state['baseline_digest']
            or journal.get('trial_digest') != fs.tree_digest(trial)
            or journal.get('transaction_id') != state['transaction_id']
            or state['root'] != root_key(root) or state['parent_identity'] != fs.identity(root.parent)):
        raise ValueError('invalid_transaction')
    if journal['phase'] == 'invalidated':
        raise ValueError('stale_preview')
    displaced, install = transaction / 'displaced', transaction / 'install'
    if journal['phase'] == 'copying':
        if fs.identity(root) != journal['current_identity']:
            raise ValueError('root_identity_changed')
        if fs.tree_digest(fs.inspect_tree(root)) != journal['trial_digest']:
            write_journal(transaction, journal, 'invalidated')
            write_state(store, state, state=journal['previous_state'], transaction_id=None)
            raise ValueError('stale_preview')
        fs.ensure_space(store, trial['total_bytes'] + baseline['total_bytes'])
        ensure_snapshot(root, transaction / 'trial-copy', trial, transaction)
        ensure_snapshot(store / 'baseline/tree', install, baseline, transaction)
        journal['install_identity'] = fs.identity(install)
        journal = write_journal(transaction, journal, 'prepared')
    if fs.tree_digest(fs.inspect_tree(transaction / 'trial-copy')) != journal['trial_digest']:
        raise ValueError('recovery_corrupt')
    fs.inspect_permissions(transaction / 'trial-copy', role='snapshot')

    if not displaced.exists():
        if journal['phase'] not in ('prepared', 'privatizing_current', 'current_private', 'moving_current'):
            raise ValueError('ambiguous_transaction')
        if fs.identity(root) != journal['current_identity']:
            raise ValueError('root_identity_changed')
        observed = fs.inspect_tree(root)
        if fs.tree_digest(observed) != journal['trial_digest']:
            if os.name == 'nt' and journal['phase'] != 'prepared':
                fs.inspect_permissions(root, role='transition')
                fs.restore_permissions(root, observed, state['parent_policy'])
            write_journal(transaction, journal, 'invalidated')
            write_state(store, state, state=journal['previous_state'], transaction_id=None)
            raise ValueError('stale_preview')
        git_preflight(root, observed)
        role = 'project' if journal['phase'] == 'prepared' else 'transition'
        if fs.inspect_permissions(root, role=role) != state['parent_policy']:
            raise ValueError('parent_permissions_changed')
        if (fs.identity(install) != journal['install_identity'] or
                fs.tree_digest(fs.inspect_tree(install)) != state['baseline_digest']):
            raise ValueError('install_corrupt')
        if os.name == 'nt':
            journal = write_journal(transaction, journal, 'privatizing_current')
            fs.protect_for_storage(root)
            journal = write_journal(transaction, journal, 'current_private')
        if fs.identity(root) != journal['current_identity']:
            raise ValueError('root_identity_changed')
        observed = fs.inspect_tree(root)
        if fs.tree_digest(observed) != journal['trial_digest']:
            fs.restore_permissions(root, observed, state['parent_policy'])
            write_journal(transaction, journal, 'invalidated')
            write_state(store, state, state=journal['previous_state'], transaction_id=None)
            raise ValueError('stale_preview')
        journal = write_journal(transaction, journal, 'moving_current')
        # No deletion or overwrite: exact validated source, absent destination, same volume.
        os.rename(fs.checked_path(root), fs.checked_path(displaced))
        journal = write_journal(transaction, journal, 'current_moved')

    if (fs.identity(displaced) != journal['current_identity'] or
            fs.tree_digest(fs.inspect_tree(displaced)) != journal['trial_digest']):
        raise ValueError('displaced_changed')
    fs.inspect_permissions(displaced, role='snapshot')
    if baseline['exists']:
        if not root.exists():
            if journal['phase'] not in ('moving_current', 'current_moved', 'activating_baseline'):
                raise ValueError('ambiguous_transaction')
            if (fs.identity(install) != journal['install_identity'] or
                    fs.tree_digest(fs.inspect_tree(install)) != state['baseline_digest']):
                raise ValueError('install_corrupt')
            journal = write_journal(transaction, journal, 'activating_baseline')
            os.rename(fs.checked_path(install), fs.checked_path(root))
        elif (install.exists() or fs.identity(root) != journal['install_identity']
              or fs.tree_digest(fs.inspect_tree(root)) != state['baseline_digest']):
            raise ValueError('ambiguous_transaction')
    elif root.exists() or install.exists():
        raise ValueError('ambiguous_transaction')
    journal = write_journal(transaction, journal, 'baseline_activated')
    fs.restore_permissions(root, baseline, state['parent_policy'])
    if fs.tree_digest(fs.inspect_tree(root)) != state['baseline_digest']:
        raise ValueError('restore_not_verified')
    journal = write_journal(transaction, journal, 'complete')
    state = write_state(store, state, state='restored', active_identity=fs.identity(root))
    return recovery_result(root, store, state, journal)


def restore(root, base, confirmation):
    if not isinstance(confirmation, str) or not re.fullmatch('[0-9a-f]{64}', confirmation):
        raise ValueError('invalid_confirmation')
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not (store / 'state.json').is_file():
        raise ValueError('missing_baseline')
    with adoption_lease(store):
        state = read_state(store)
        if state['state'] == 'restored':
            transaction = transaction_for(store, state['transaction_id'])
            journal = read_record(transaction, 'journal.json')
            if journal['preview_digest'] != confirmation or state['root'] != root_key(root):
                raise ValueError('stale_preview')
            verify_baseline(store, state)
            return recovery_result(root, store, state, journal, historical=True)
        expected_path = 'previews/' + confirmation + '.json'
        if not (store / expected_path).is_file():
            raise ValueError('missing_preview')
        expected = read_record(store, expected_path)
        proposal, trial = proposal_for(root, store, state)
        if fs.tree_digest(expected) != confirmation or proposal != expected:
            raise ValueError('stale_preview')
        fs.ensure_space(store, trial['total_bytes'] + read_record(store, 'baseline/inventory.json')['total_bytes'])
        transaction_id = str(uuid.uuid4())
        transaction = transaction_for(store, transaction_id)
        fs.ensure_paths_fit(transaction / 'trial-copy', [e['path'] for e in trial['entries']])
        fs.ensure_paths_fit(transaction / 'install', [e['path'] for e in read_record(store, 'baseline/inventory.json')['entries']])
        transaction.parent.mkdir(exist_ok=True)
        fs.private_dir(transaction)
        write_record(transaction, 'trial.json', trial)
        journal = dict(schema=1, transaction_id=transaction_id, adoption_id=state['adoption_id'],
                       preview_digest=confirmation, trial_digest=proposal['current_digest'],
                       baseline_digest=state['baseline_digest'], current_identity=fs.identity(root),
                       previous_state=state['state'], install_identity=None)
        journal = write_journal(transaction, journal, 'copying')
        state = write_state(store, state, state='restoring', transaction_id=transaction_id)
        return resume_transaction(root, store, state, transaction, journal)


def recover(root, base, transaction):
    root, base = fs.checked_path(root), fs.validate_storage(root, base, create=False)
    store = store_for(root, base)
    if not (store / 'state.json').is_file():
        raise ValueError('missing_baseline')
    with adoption_lease(store):
        state = read_state(store)
        directory = transaction_for(store, transaction)
        if state.get('transaction_id') != transaction or state['state'] not in ('restoring', 'restored'):
            raise ValueError('invalid_transaction')
        journal = read_record(directory, 'journal.json')
        if state['state'] == 'restored':
            return recovery_result(root, store, state, journal, historical=True)
        return resume_transaction(root, store, state, directory, journal)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Private local adoption records; stop project writers first.')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--backup-root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'status', 'recover-lock', 'restore', 'recover', 'verify-child', 'install'):
        command = sub.add_parser(name)
        command.add_argument('--json', action='store_true')
        if name in ('recover-lock', 'recover'):
            command.add_argument('--confirm', required=True)
        elif name == 'restore':
            group = command.add_mutually_exclusive_group(required=True)
            group.add_argument('--confirm')
            group.add_argument('--dry-run', action='store_true')
        elif name == 'install':
            command.add_argument('--source', type=Path, required=True)
            command.add_argument('--client', choices=('claude', 'codex', 'both'), default='both')
            command.add_argument('--name')
            command.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = fs.checked_path(args.root)
        base = fs.checked_path(args.backup_root or root.parent / '.youngcrow-recovery')
        if args.command == 'install':
            options = ['--client', args.client]
            if args.name:
                options += ['--name', args.name]
            if args.force:
                options += ['--force']
            return run_install(root, base, args.source, options)
        if args.command == 'verify-child':
            print(json.dumps(verify_child(root, base)))
            return 0
        if args.command in ('restore', 'recover') and not getattr(args, 'dry_run', False):
            store = store_for(root, fs.validate_storage(root, base, create=False))
            state = read_state(store)
            verify_baseline(store, state)
            runner = store / 'runner/adoption.py'
            if Path(__file__).resolve() != runner.resolve():
                # The immutable external runner survives the removal of project scripts.
                return subprocess.run([sys.executable, '-B', '-E', '-s', '-S', str(runner),
                                       '--root', str(root), '--backup-root', str(base), args.command,
                                       '--confirm', args.confirm, '--json'], cwd=base).returncode
            os.chdir(base)
        if args.command == 'recover-lock':
            result = recover_lock(root, base, args.confirm)
        elif args.command == 'restore':
            result = preview(root, base) if args.dry_run else restore(root, base, args.confirm)
        elif args.command == 'recover':
            result = recover(root, base, args.confirm)
        else:
            result = globals()[args.command](root, base)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z_]+', str(error)) else 'operation_failed'
        print(json.dumps(dict(state='failed', code=code)), file=sys.stderr)
        return 1 if code == 'stale_preview' else 2


if __name__ == '__main__':
    sys.exit(main())
