"""Project-local document storage. No conversion, network or Git staging."""
from datetime import datetime, timezone
import json
from pathlib import Path
import stat
import subprocess
import uuid

from integrations import check_path, project_identity

PRIVATE = ('vault/local', '.operacao-local/docling')


def safe_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or ':' in str(relative) or '\x00' in str(relative):
        raise ValueError('Path must stay inside the project.')
    check_path(root, relative)
    target = root / relative
    if target.exists() and not stat.S_ISREG(target.lstat().st_mode):
        raise ValueError('Expected a regular file.')
    return target


def markdown(identity, kind, title, parent, body):
    fields = dict(id=identity, type=kind, title=title, origin='youngcrow/docling',
                  updated=datetime.now(timezone.utc).isoformat(timespec='seconds'), index=parent)
    return '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fields.items()) + '---\n\n' + body


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=15)


def prepare_storage(root):
    """Verify private destinations before creating notes; preserve existing bytes."""
    root = Path(root).resolve(strict=True)
    notes = {
        'vault/index.md': ('index.md', '# Vault\n\nLocal documents: `local/index.md`.\n'),
        'vault/local/index.md': ('index.md', '# Local knowledge\n\n[Sources](sources/index.md)\n'),
        'vault/local/sources/index.md': ('../index.md', '# Sources\n\n[Local knowledge](../index.md)\n'),
    }
    for relative in [*notes, 'vault/project.json', '.gitignore', '.operacao-local/docling/inbox/.probe']:
        safe_path(root, relative)
    project_file = root / 'vault/project.json'
    identity = project_identity(project_file) if project_file.exists() else str(uuid.uuid4())
    detected = git(root, 'rev-parse', '--show-toplevel')
    if detected.returncode and b'not a git repository' not in detected.stderr.lower():
        raise ValueError('Cannot verify Git storage boundaries.')
    in_git = detected.returncode == 0
    if in_git:
        tracked = git(root, 'ls-files', '-z', '--', *PRIVATE)
        if tracked.returncode or tracked.stdout:
            raise ValueError('Private storage is already tracked or cannot be checked.')
    ignore = root / '.gitignore'
    data = ignore.read_bytes() if ignore.exists() else b''
    additions = []
    for relative in PRIVATE:
        probe = relative + '/.youngcrow-ignore-check'
        result = git(root, 'check-ignore', '--quiet', '--', probe) if in_git else None
        if result is not None and result.returncode not in (0, 1):
            raise ValueError('Cannot check private ignore rules.')
        # Keep own rules even if a parent repository ignores this whole project.
        if (result is not None and result.returncode != 0) or ('/' + relative + '/').encode() not in data.splitlines():
            additions.append('/' + relative + '/')
    if additions:
        with ignore.open('ab') as output:
            output.write((('\n' if data and not data.endswith(b'\n') else '')
                          + '\n'.join(additions) + '\n').encode())
    if in_git:
        for relative in PRIVATE:
            if git(root, 'check-ignore', '--quiet', '--', relative + '/.youngcrow-ignore-check').returncode:
                raise ValueError('Private storage is not ignored.')
    for relative, (parent, body) in notes.items():
        path = root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as output:
                output.write(markdown(str(uuid.uuid5(uuid.UUID(identity), relative)), 'index', 'Vault', parent, body))
    if not project_file.exists():
        with project_file.open('x', encoding='utf-8', newline='\n') as output:
            json.dump({'project_id': identity}, output)
            output.write('\n')
    (root / '.operacao-local/docling/inbox').mkdir(parents=True, exist_ok=True)
    return identity
