"""Explicit local Git workspaces. No worker dispatch or delivery acceptance."""
import os
from pathlib import Path
import subprocess
import sys


def git_environment():
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0',
               GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1', LC_ALL='C')
    return env


# The owned process wrapper uses -I -S: no project imports or startup hooks here.
if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] != '--git':
        raise SystemExit(2)
    raise SystemExit(subprocess.call(sys.argv[2:], env=git_environment()))

import hashlib
import json
import re
import shutil

import adoption
import adoption_fs as fs
from capabilities import canonical, text
from document_store import safe_path
from mission_backlog import identity, require
import mission_process as processes
import mission_queue
import mission_store as store

WORKSPACE_VERSION = 1
SCHEMA = (
    'CREATE TABLE workspaces (id TEXT PRIMARY KEY, pbi_id TEXT NOT NULL, state TEXT NOT NULL, snapshot TEXT NOT NULL)',
    "CREATE UNIQUE INDEX workspace_one_pbi ON workspaces(pbi_id) WHERE state != 'released'",
    'CREATE TABLE workspace_operations (operation_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, workspace_id TEXT NOT NULL REFERENCES workspaces(id), receipt TEXT)',
)
GIT_OPTIONS = ('-c', 'core.hooksPath=' + os.devnull, '-c', 'core.fsmonitor=false',
               '-c', 'protocol.allow=never', '-c', 'submodule.recurse=false', '-c', 'gc.auto=0',
               '-c', 'maintenance.auto=false')



def migrate(conn):
    mission_queue.migrate(conn)
    if conn.execute('SELECT schema_version FROM metadata').fetchone()[0] == 5:
        for statement in SCHEMA:
            conn.execute(statement)
        conn.execute('UPDATE metadata SET schema_version=6')


def available(conn):
    return conn is not None and conn.execute('SELECT schema_version FROM metadata').fetchone()[0] == 6


def git(root, *args, check=True):
    result = subprocess.run(['git', *GIT_OPTIONS, '-C', str(root), *args], env=git_environment(),
                            capture_output=True, timeout=30)
    require(not check or result.returncode == 0, 'workspace_git_failed')
    return result.stdout.decode('utf-8', errors='strict').strip() if check else result


def repository(root):
    root = fs.checked_path(root)
    admin = fs.checked_path(root / '.git')
    require(admin.is_dir(), 'unsupported_workspace_repository')
    for name in ('config', 'HEAD', 'packed-refs', 'index', 'objects', 'objects/info', 'objects/pack',
                 'refs', 'logs', 'worktrees'):
        fs.checked_path(admin / name)
    require(Path(git(root, 'rev-parse', '--show-toplevel')) == root and
            Path(git(root, 'rev-parse', '--absolute-git-dir')) == admin,
            'unsupported_workspace_repository')
    for name in ('commondir', 'modules', 'objects/info/alternates', 'shallow', 'config.worktree'):
        require(not (admin / name).exists(), 'unsupported_workspace_repository')
    config = git(root, 'config', '--local', '--no-includes', '--list', '-z')
    for item in config.split('\0'):
        key = item.split('\n', 1)[0].lower()
        require(not (key.startswith(('include.', 'includeif.', 'filter.')) or key in
                    ('core.worktree', 'extensions.worktreeconfig', 'extensions.partialclone', 'core.sparsecheckout', 'core.sparsecheckoutcone') or
                    key.endswith('.promisor')), 'unsupported_workspace_repository')
    require(not list((admin / 'objects/pack').glob('*.promisor')), 'unsupported_workspace_repository')
    require(not git(root, 'ls-files', '-z', '--', '.runtime/workspaces'), 'unsupported_workspace_repository')
    ignored = git(root, 'check-ignore', '--', '.runtime/workspaces/.probe', check=False)
    require(ignored.returncode == 0 and ignored.stdout.strip() == b'.runtime/workspaces/.probe',
            'unsupported_workspace_repository')
    return dict(root=str(root), root_identity=fs.identity(root), git_identity=fs.identity(admin))


def find(conn, workspace_id):
    row = conn.execute('SELECT snapshot FROM workspaces WHERE id=?', (workspace_id,)).fetchone()
    require(row is not None, 'unknown_workspace')
    return json.loads(row[0])


def status(root, workspace_id):
    identity(workspace_id)
    with store.reader(root) as conn:
        require(available(conn), 'unknown_workspace')
        return find(conn, workspace_id)


def context(root, workspace_id, expected_revision):
    """Read the original vault using an owned workspace's pinned mission/PBI."""
    from missions import mission_context
    require(type(expected_revision) is int and expected_revision > 0, 'revision_conflict')
    record = status(root, workspace_id)
    require(record['revision'] == expected_revision, 'revision_conflict')
    require(record['state'] == 'prepared', 'workspace_not_ready')
    owned(root, record)
    _, head = inspect_worktree(root, record)
    selected = mission_context(root, record['mission_id'], record['pbi_id'], record['mission_revision'])
    pbi = next(item for item in selected['items'] if item['id'] == record['pbi_id'])
    require(pbi['revision'] == record['pbi_revision'], 'revision_conflict')
    owned(root, record)
    require(inspect_worktree(root, record)[1] == head, 'workspace_changed')
    with store.reader(root) as conn:
        require(available(conn), 'unknown_workspace')
        conn.execute('BEGIN')
        require(find(conn, workspace_id) == record, 'workspace_changed')
        revisions = dict(conn.execute('SELECT id,revision FROM records'))
        require(revisions.get(record['mission_id']) == record['mission_revision'], 'revision_conflict')
        require(all(revisions.get(item['id']) == item['revision'] for item in selected['items']), 'stale_context')
    observed = {key: record[key] for key in ('id', 'revision', 'mission_id', 'mission_revision',
                                           'pbi_id', 'pbi_revision', 'path', 'branch', 'base')}
    result = dict(schema_version=1, context=selected, workspace=dict(observed, head=head),
                  runtime_available=False, runnable=False)
    return dict(result, workspace_context_sha256=hashlib.sha256(canonical(result)).hexdigest())


def save(root, record):
    with store.transaction(root) as conn:
        conn.execute('UPDATE workspaces SET state=?,snapshot=? WHERE id=?',
                     (record['state'], canonical(record).decode(), record['id']))


def git_write(root, record, *args, data=b''):
    repository(root)
    for relative in (record['ownership_ref'], 'refs/heads/' + record['branch']):
        for prefix in ('', 'logs/'):
            fs.checked_path(root / '.git' / (prefix + relative))
            fs.checked_path(root / '.git' / (prefix + relative + '.lock'))
    fs.checked_path(root / '.git/worktrees' / record['id'])
    if args[0] == 'hash-object':
        algorithm = 'sha1' if len(record['base']) == 40 else 'sha256'
        oid = hashlib.new(algorithm, b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        fs.checked_path(root / '.git/objects' / oid[:2] / oid[2:])
    def started(owner):
        record['owner'] = owner
        save(root, record)
    executable = shutil.which('git')
    require(executable is not None, 'workspace_git_failed')
    plan = dict(argv=[sys.executable, '-I', '-S', str(Path(__file__).resolve()), '--git', executable,
                      *GIT_OPTIONS, '-C', str(root), *args], cwd=str(root), stdin=data,
                connection='local', timeout_seconds=30, output_limit_bytes=1024 * 1024)
    result = processes.supervise(plan, on_started=started, stop_requested=lambda: False)
    require(result['tree_reaped'], 'workspace_busy')
    require(result['reason'] == 'completed' and result['exit_code'] == 0, 'workspace_git_failed')
    return result['stdout'].decode().strip()


def operation(conn, operation_id, digest):
    row = conn.execute('SELECT request_hash,workspace_id,receipt FROM workspace_operations WHERE operation_id=?',
                       (operation_id,)).fetchone() if available(conn) else None
    if row:
        require(row[0] == digest, 'operation_conflict')
        return row[1], json.loads(row[2]) if row[2] else None
    return None


def request_digest(action, operation_id, actor_id, expected_revision, **fields):
    identity(operation_id)
    require(text(actor_id, 200) and actor_id.strip(), 'invalid_actor')
    require(type(expected_revision) is int and expected_revision > 0, 'revision_conflict')
    return hashlib.sha256(canonical(dict(action=action, actor_id=actor_id,
                                         expected_revision=expected_revision, **fields))).hexdigest()


def finish(root, record, operation_id, state):
    record.update(state=state, revision=record['revision'] + 1, owner=None)
    with store.transaction(root) as conn:
        conn.execute('UPDATE workspaces SET state=?,snapshot=? WHERE id=?',
                     (state, canonical(record).decode(), record['id']))
        conn.execute('UPDATE workspace_operations SET receipt=? WHERE operation_id=?',
                     (canonical(record).decode(), operation_id))
    return record


def guard_path(root):
    store.preflight(root)
    path = safe_path(root, 'vault/local/operations/workspaces/reclaim.lock').parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def owned(root, record):
    require(repository(root) == record['repository'], 'workspace_changed')
    require(record['owner'] is None or processes.owner_gone(record['owner']), 'workspace_busy')
    fs.checked_path(record['path'])


def ref(root, name):
    symbolic = git(root, 'symbolic-ref', '-q', name, check=False)
    require(symbolic.returncode == 1, 'workspace_collision')
    result = git(root, 'show-ref', '--verify', '--hash', name, check=False)
    require(result.returncode in (0, 1, 128), 'workspace_git_failed')
    return result.stdout.decode().strip() if result.returncode == 0 else None


def clean(root):
    entries = git(root, 'ls-files', '-v', '-z').split('\0')
    require(all(not e or e.startswith('H ') for e in entries), 'workspace_changed')
    observation = git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored=matching',
                      '--ignore-submodules=none', check=False)
    require(observation.returncode == 0 and not observation.stderr, 'workspace_uncertain')
    require(not observation.stdout, 'workspace_dirty')
    admin = Path(git(root, 'rev-parse', '--absolute-git-dir'))
    require(not any((admin / name).exists() for name in
                    ('index.lock', 'HEAD.lock', 'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
                     'rebase-apply', 'rebase-merge', 'sequencer')), 'workspace_changed')


def inspect_worktree(root, record, *, preparing=False):
    path = fs.checked_path(record['path'])
    require(fs.identity(path) == record['directory_identity'], 'workspace_changed')
    require(path.is_dir() and fs.checked_path(path / '.git').is_file(), 'workspace_changed')
    admin = fs.checked_path(Path(git(path, 'rev-parse', '--absolute-git-dir')))
    require(admin.parent == root / '.git/worktrees' and admin.is_dir(), 'workspace_changed')
    require(Path((admin / 'gitdir').read_text().strip()) == path / '.git' and
            (admin / 'commondir').read_text().strip() == '../..', 'workspace_changed')
    for name in ('HEAD', 'index', 'commondir', 'gitdir', 'logs/HEAD', 'locked'):
        fs.checked_path(admin / name)
    info = dict(path=str(admin), identity=fs.identity(admin))
    if record.get('admin'):
        require(info == record['admin'], 'workspace_changed')
    require(git(path, 'symbolic-ref', '-q', 'HEAD', check=False).stdout.decode().strip() ==
            'refs/heads/' + record['branch'], 'workspace_changed')
    head = git(path, 'rev-parse', 'HEAD')
    require(ref(root, 'refs/heads/' + record['branch']) == head and
            ref(root, record['ownership_ref']) == record['ownership_oid'], 'workspace_changed')
    if preparing:
        require(head == record['base'], 'workspace_changed')
        clean(path)
        # Empty/partial indexes must not masquerade as a finished checkout.
        require(git(path, 'diff-index', '--cached', '--quiet', record['base'], '--', check=False).returncode == 0,
                'workspace_changed')
    return info, head


def prepare(root, *, mission, pbi, base, expected_revision, operation_id, actor_id):
    identity(pbi)
    digest = request_digest('prepare', operation_id, actor_id, expected_revision,
                            mission=mission, pbi=pbi, base=base)
    with store.reader(root) as conn:
        repeated = operation(conn, operation_id, digest) if conn else None
        if repeated and repeated[1]:
            return repeated[1]
    from missions import mission_status
    if not repeated:
        current_status = mission_status(root, mission)
        require(current_status.get('revision') == expected_revision, 'revision_conflict')
        require(current_status.get('check_available'), 'mission_not_ready')
    observed = repository(root)
    require(isinstance(base, str) and re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', base), 'invalid_base')
    result = git(root, 'cat-file', '-t', base, check=False)
    require(result.returncode == 0 and result.stdout.strip() == b'commit', 'invalid_base')
    require(not any(line.startswith('160000 ') for line in git(root, 'ls-tree', '-r', base).splitlines()),
            'unsupported_workspace_repository')
    with adoption.lock_guard(guard_path(root)):
        with store.transaction(root) as conn:
            migrate(conn)
            repeated = operation(conn, operation_id, digest)
            if repeated:
                if repeated[1]:
                    return repeated[1]
                record = find(conn, repeated[0])
            else:
                row = conn.execute('SELECT * FROM records WHERE id=? OR code=?', (mission, mission)).fetchone()
                require(row and row[1] == 'mission', 'unknown_mission')
                current = store.record_dict(row)
                require(current['revision'] == expected_revision, 'revision_conflict')
                require(current['snapshot']['state'] == 'prepared', 'mission_not_ready')
                item = next((r for r in current['snapshot']['items'] if r['id'] == pbi and r['kind'] == 'pbi'), None)
                require(item is not None, 'invalid_request')
                require(not conn.execute("SELECT 1 FROM workspaces WHERE pbi_id=? AND state!='released'", (pbi,)).fetchone(), 'workspace_busy')
                require(conn.execute("SELECT COUNT(*) FROM workspaces WHERE state!='released'").fetchone()[0] < 3, 'workspace_busy')
                record = dict(schema_version=1, id=operation_id, state='preparing', revision=0,
                    mission_id=current['id'], mission_revision=expected_revision, pbi_id=pbi,
                    pbi_revision=item['revision'], base=base, repository=observed,
                    branch='youngcrow/' + item['code'].lower() + '-' + operation_id,
                    path=str(root / '.runtime/workspaces' / operation_id), directory_identity=None,
                    admin=None, owner=None, ownership_ref='refs/youngcrow/workspaces/' + operation_id,
                    ownership_oid=None, prepare_operation=operation_id,
                    runtime_available=False, development='not_started', qa='not_started', production='not_verified')
                conn.execute('INSERT INTO workspaces VALUES (?,?,?,?)', (record['id'], pbi, record['state'], canonical(record).decode()))
                conn.execute('INSERT INTO workspace_operations VALUES (?,?,?,NULL)', (operation_id, digest, record['id']))
        return resume_prepare(root, record)


def resume_prepare(root, record):
    owned(root, record)
    path = fs.checked_path(record['path'])
    branch = 'refs/heads/' + record['branch']
    marker = ref(root, record['ownership_ref'])
    tip = ref(root, branch)
    if marker is None:
        require(tip is None, 'workspace_collision')
        # Only an opaque identity/digest goes into Git's object database.
        blob = canonical(dict(workspace_id=record['id'], intent_sha256=hashlib.sha256(canonical(
            {k: record[k] for k in ('mission_id', 'mission_revision', 'pbi_id', 'pbi_revision', 'base')})).hexdigest()))
        oid = git_write(root, record, 'hash-object', '-w', '--stdin', data=blob)
        record['ownership_oid'] = oid
        save(root, record)
        git_write(root, record, 'update-ref', '--no-deref', '--stdin', data=(f'start\ncreate {branch} {record["base"]}\n'
                  f'create {record["ownership_ref"]} {oid}\nprepare\ncommit\n').encode())
    else:
        require(record['ownership_oid'] is not None and marker == record['ownership_oid'] and tip == record['base'],
                'workspace_collision')
    if record['directory_identity'] is None:
        require(not path.exists(), 'workspace_collision')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()  # Exclusive: never adopt a pre-existing directory, even empty.
        record['directory_identity'] = fs.identity(path)
        save(root, record)
    require(fs.identity(path) == record['directory_identity'], 'workspace_changed')
    if not (path / '.git').exists():
        require(not any(path.iterdir()) and not (root / '.git/worktrees' / record['id']).exists(),
                'workspace_uncertain')
        git_write(root, record, 'worktree', 'add', '--', str(path), record['branch'])
    admin, _ = inspect_worktree(root, record, preparing=True)
    record['admin'] = admin
    return finish(root, record, record['prepare_operation'], 'prepared')


def release(root, workspace_id, *, expected_revision, operation_id, actor_id):
    identity(workspace_id)
    digest = request_digest('release', operation_id, actor_id, expected_revision, workspace_id=workspace_id)
    with store.reader(root) as conn:
        repeated = operation(conn, operation_id, digest) if conn else None
        if repeated and repeated[1]:
            return repeated[1]
    with adoption.lock_guard(guard_path(root)):
        with store.reader(root) as conn:
            require(available(conn), 'unknown_workspace')
            repeated = operation(conn, operation_id, digest)
            if repeated and repeated[1]:
                return repeated[1]
            record = find(conn, workspace_id)
        owned(root, record)
        path = fs.checked_path(record['path'])
        if not repeated:
            require(record['revision'] == expected_revision, 'revision_conflict')
            require(record['state'] == 'prepared', 'workspace_busy')
            _, head = inspect_worktree(root, record)
            clean(path)
            record.update(state='releasing', last_commit=head)
            with store.transaction(root) as conn:
                conn.execute('INSERT INTO workspace_operations VALUES (?,?,?,NULL)', (operation_id, digest, workspace_id))
                conn.execute('UPDATE workspaces SET state=?,snapshot=? WHERE id=?', ('releasing', canonical(record).decode(), workspace_id))
        require(record['state'] == 'releasing', 'workspace_changed')
        if path.exists():
            _, head = inspect_worktree(root, record)
            require(head == record['last_commit'], 'workspace_changed')
            clean(path)
            git_write(root, record, 'worktree', 'remove', '--', str(path))
        require(not path.exists() and not Path(record['admin']['path']).exists() and
                ref(root, 'refs/heads/' + record['branch']) == record['last_commit'] and
                ref(root, record['ownership_ref']) == record['ownership_oid'], 'workspace_changed')
        parent = fs.checked_path(root / '.git/worktrees')
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()  # Empty only; never prune or recursively remove another worktree.
        return finish(root, record, operation_id, 'released')
