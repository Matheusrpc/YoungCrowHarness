"""Bounded local snapshots. No network, Git writes, or recursive deletion."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

MAX_ENTRIES = 100_000
MAX_BYTES = 64 * 1024**3
BLOCK = 1024**2
RESERVE = 64 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def tree_digest(tree):
    return hashlib.sha256(canonical(tree)).hexdigest()


def identity(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    return [info.st_dev, info.st_ino]


def checked_path(path):
    path = Path(os.path.abspath(path))
    if os.name == 'nt' and (str(path).startswith('\\\\') or ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) != 3):
        raise ValueError('unsupported_volume')
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
                or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            raise ValueError('unsupported_entry')
        if item != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError('unsupported_entry')
    return path


def git_read(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
    return subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args],
                          env=env, capture_output=True, timeout=30)


def outside_git(path):
    existing = path
    while not existing.exists():
        existing = existing.parent
    result = git_read(existing, 'rev-parse', '--absolute-git-dir')
    if result.returncode == 0:
        raise ValueError('storage_in_git')
    if b'not a git repository' not in result.stderr.lower():
        raise ValueError('git_boundary_unknown')


def acl(mode, root):
    shell = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    env = dict(os.environ, PSModulePath=str(shell.parent / 'Modules'))
    result = subprocess.run([str(shell), '-NoLogo', '-NoProfile', '-NonInteractive',
                             '-ExecutionPolicy', 'Bypass', '-File',
                             str(Path(__file__).with_name('adoption_acl.ps1')),
                             '-Mode', mode, '-LiteralPath', str(root)],
                            capture_output=True, timeout=120, encoding='utf-8', env=env)
    if result.returncode:
        raise ValueError('unsupported_permissions')
    return json.loads(result.stdout)


def private_dir(path):
    path = checked_path(path)
    if path.exists():
        raise ValueError('destination_exists')
    if not path.parent.is_dir():
        raise ValueError('missing_parent')
    if os.name == 'nt':
        acl('private-create', path)
    else:
        path.mkdir(mode=0o700)


def validate_storage(root, base, *, create):
    root, base = checked_path(root), checked_path(base)
    if root == base or root in base.parents or base in root.parents or root == Path(root.anchor):
        raise ValueError('unsafe_storage_boundary')
    if not root.parent.is_dir():
        raise ValueError('missing_parent')
    outside_git(base)
    ancestor = base
    while not ancestor.exists():
        ancestor = ancestor.parent
    if ancestor.stat().st_dev != root.parent.stat().st_dev:
        raise ValueError('different_volume')
    if not base.exists():
        if not create:
            return base
        # ponytail: require an existing parent, avoiding unowned intermediate folders.
        private_dir(base)
    if not base.is_dir():
        raise ValueError('unsafe_storage_boundary')
    if os.name == 'nt':
        acl('private-check', base)
    else:
        info = base.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('storage_not_private')
        if os.listxattr(base):
            raise ValueError('unsupported_permissions')
    return base


def stamp(info):
    # Windows stat/fstat expose different ctime semantics on some Python versions.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def hash_file(path):
    checked_path(path)
    before = path.lstat()
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as source:
        if stamp(before) != stamp(os.fstat(source.fileno())):
            raise ValueError('source_changed')
        while chunk := source.read(BLOCK):
            digest.update(chunk)
        if stamp(before) != stamp(os.fstat(source.fileno())):
            raise ValueError('source_changed')
    if stamp(before) != stamp(path.lstat()):
        raise ValueError('source_changed')
    return digest.hexdigest()


def metadata(info):
    return dict(mode=stat.S_IMODE(info.st_mode),
                attributes=getattr(info, 'st_file_attributes', 0) & 7 if os.name == 'nt' else 0)


def relative_path(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value or '\x00' in value
            or value.startswith('/') or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('invalid_inventory_path')
    return Path(value)


def check_streams(path):
    """FindFirstStream includes directory ADS, unlike Windows PowerShell 5.1."""
    if os.name != 'nt':
        return
    from ctypes import wintypes
    class StreamData(ctypes.Structure):
        _fields_ = [('size', ctypes.c_longlong), ('name', wintypes.WCHAR * 296)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    kernel.FindFirstStreamW.restype = wintypes.HANDLE
    kernel.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]
    kernel.FindNextStreamW.restype = wintypes.BOOL
    kernel.FindClose.argtypes = [wintypes.HANDLE]
    stream = StreamData()
    handle = kernel.FindFirstStreamW(str(path), 0, ctypes.byref(stream), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() != 38:
            raise ValueError('unsupported_permissions')
        return
    try:
        while True:
            if stream.name != '::$DATA':
                raise ValueError('unsupported_permissions')
            if not kernel.FindNextStreamW(handle, ctypes.byref(stream)):
                if ctypes.get_last_error() != 38:
                    raise ValueError('unsupported_permissions')
                break
    finally:
        kernel.FindClose(handle)


def inspect_tree(root):
    root = checked_path(root)
    tree = dict(schema=1, exists=root.exists(), root_metadata=None, entries=[], total_bytes=0)
    if not tree['exists']:
        return tree
    if not root.is_dir():
        raise ValueError('unsupported_entry')
    root_info = root.stat()
    check_streams(root)
    tree['root_metadata'] = metadata(root_info)
    stack = [root]
    while stack:
        directory = stack.pop()
        checked_path(directory)
        before_dir = directory.stat()
        for path in sorted(directory.iterdir()):
            checked_path(path)
            check_streams(path)
            before = path.lstat()
            if before.st_dev != root_info.st_dev:
                raise ValueError('unsupported_volume')
            relative = path.relative_to(root).as_posix()
            relative_path(relative)
            entry = dict(path=relative, type='dir' if path.is_dir() else 'file', **metadata(before))
            if entry['type'] == 'dir':
                stack.append(path)
            else:
                tree['total_bytes'] += before.st_size
                if tree['total_bytes'] > MAX_BYTES:
                    raise ValueError('inventory_limit')
                entry.update(size=before.st_size, sha256=hash_file(path))
                if stamp(before) != stamp(path.lstat()):
                    raise ValueError('source_changed')
            tree['entries'].append(entry)
            if len(tree['entries']) > MAX_ENTRIES:
                raise ValueError('inventory_limit')
        if stamp(before_dir) != stamp(directory.stat()):
            raise ValueError('source_changed')
    tree['entries'].sort(key=lambda entry: entry['path'])
    return tree


def inspect_permissions(root, *, role):
    root = checked_path(root)
    if role not in ('project', 'snapshot'):
        raise ValueError('invalid_role')
    if os.name == 'nt':
        stack = [root] if root.exists() else []
        count = 0
        while stack:
            path = checked_path(stack.pop())
            check_streams(path)
            count += 1
            if count > MAX_ENTRIES + 1:
                raise ValueError('inventory_limit')
            if path.is_dir():
                stack.extend(path.iterdir())
        return acl('profile-check' if role == 'project' else 'private-check', root)
    if not hasattr(os, 'listxattr'):
        raise ValueError('unsupported_permissions')
    for directory, dirs, files in os.walk(root, followlinks=False):
        for path in [Path(directory), *(Path(directory) / name for name in dirs + files)]:
            checked_path(path)
            info = path.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o7000 or os.listxattr(path):
                raise ValueError('unsupported_permissions')
    parent = root.parent.stat()
    if os.listxattr(root.parent):
        raise ValueError('unsupported_permissions')
    if role == 'snapshot':
        if not any(p.is_dir() and p.stat().st_uid == os.getuid() and stat.S_IMODE(p.stat().st_mode) == 0o700
                   for p in root.parents):
            raise ValueError('storage_not_private')
        return dict(private=True)
    return dict(platform='posix', parent_uid=parent.st_uid, parent_gid=parent.st_gid,
                parent_mode=stat.S_IMODE(parent.st_mode))


def protect_for_storage(root):
    if not root.exists():
        return
    checked_path(root)
    if os.name == 'nt':
        acl('private-apply', root)
    else:
        inspect_permissions(root, role='snapshot')


def apply_metadata(path, value):
    checked_path(path)
    if os.name == 'nt':
        attributes = value['attributes'] | (16 if path.is_dir() else 0)
        if not ctypes.windll.kernel32.SetFileAttributesW(str(path), attributes or 128):
            raise OSError('attribute_restore_failed')
    else:
        os.chmod(path, value['mode'])


def restore_permissions(root, expected, parent_policy):
    root = checked_path(root)
    if not expected['exists']:
        if root.exists():
            raise ValueError('unexpected_root')
        return
    if os.name == 'nt':
        observed = acl('parent-check', root)
        if observed != parent_policy:
            raise ValueError('parent_permissions_changed')
        acl('restore-inheritance', root)
    elif inspect_permissions(root, role='project') != parent_policy:
        raise ValueError('parent_permissions_changed')
    for entry in reversed(expected['entries']):
        apply_metadata(root / relative_path(entry['path']), entry)
    apply_metadata(root, expected['root_metadata'])
    if inspect_permissions(root, role='project') != parent_policy:
        raise ValueError('permission_restore_failed')


def ensure_space(base, size):
    if shutil.disk_usage(base).free < size + RESERVE:
        raise ValueError('insufficient_space')


def copy_verified(source, destination, expected):
    source, destination = checked_path(source), checked_path(destination)
    for entry in expected['entries']:
        relative_path(entry['path'])
    if destination.exists():
        raise ValueError('destination_exists')
    if tree_digest(inspect_tree(source)) != tree_digest(expected):
        raise ValueError('source_changed')
    if not expected['exists']:
        return
    inspect_permissions(destination.parent, role='snapshot')
    ensure_space(destination.parent, expected['total_bytes'])
    private_dir(destination)
    for entry in expected['entries']:
        src = checked_path(source / relative_path(entry['path']))
        dst = checked_path(destination / relative_path(entry['path']))
        if entry['type'] == 'dir':
            dst.mkdir(mode=0o777 if os.name == 'nt' else 0o700)
            continue
        before = src.stat()
        descriptor = os.open(src, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as reader, dst.open('xb') as writer:
            if stamp(before) != stamp(os.fstat(reader.fileno())):
                raise ValueError('source_changed')
            while chunk := reader.read(BLOCK):
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
            if stamp(before) != stamp(os.fstat(reader.fileno())):
                raise ValueError('source_changed')
        if stamp(before) != stamp(src.stat()):
            raise ValueError('source_changed')
    for entry in reversed(expected['entries']):
        apply_metadata(destination / relative_path(entry['path']), entry)
    apply_metadata(destination, expected['root_metadata'])
    if (tree_digest(inspect_tree(source)) != tree_digest(expected)
            or tree_digest(inspect_tree(destination)) != tree_digest(expected)):
        raise ValueError('copy_not_verified')
    inspect_permissions(destination, role='snapshot')
