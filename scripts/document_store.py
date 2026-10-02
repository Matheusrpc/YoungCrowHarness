"""Project-local document storage. No conversion, network or Git staging."""
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit
import uuid

from integrations import check_path, project_identity

PRIVATE = ('vault/local', '.operacao-local/docling')
BASE = '.operacao-local/docling'


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


def atomic_write(root, relative, data):
    destination = safe_path(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=destination.parent, prefix='.yc-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(data.encode('utf-8') if isinstance(data, str) else data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(root, relative, value):
    atomic_write(root, relative, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_json(root, relative):
    return json.loads(safe_path(root, relative).read_text(encoding='utf-8'))


@contextmanager
def project_lock(root):
    # ponytail: one writer per project; introduce finer locks only for measured contention.
    path = safe_path(root, Path(BASE) / 'lock.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    token = str(uuid.uuid4())
    try:
        with path.open('x', encoding='utf-8') as output:
            json.dump(dict(pid=os.getpid(), token=token, started=datetime.now(timezone.utc).isoformat()), output)
    except FileExistsError:
        raise ValueError('Project is locked; inspect the lock owner before explicit recovery.') from None
    try:
        yield
    finally:
        if read_json(root, path.relative_to(root)).get('token') == token:
            path.unlink()


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        raise ValueError('Invalid lock owner.')
    if os.name == 'nt':
        # os.kill(pid, 0) terminates processes on Windows; query a handle instead.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied is conservatively alive.
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            return result != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def lock_status(root):
    path = safe_path(root, Path(BASE) / 'lock.json')
    if not path.exists():
        return dict(state='unlocked', owner_alive=False)
    lock = read_json(root, Path(BASE) / 'lock.json')
    return dict(state='locked', pid=lock['pid'], token=str(uuid.UUID(lock['token'])),
                owner_alive=process_alive(lock['pid']))


def recover_lock(root, token):
    token = str(uuid.UUID(token))
    lock = lock_status(root)
    if lock['state'] != 'locked' or lock['token'] != token or lock['owner_alive']:
        raise ValueError('Recovery requires the exact token of a dead lock owner.')
    path = safe_path(root, Path(BASE) / 'lock.json')
    if read_json(root, path.relative_to(root))['token'] != token:
        raise ValueError('Lock changed during inspection.')
    path.unlink()
    with project_lock(root):
        for record in source_records(root):
            receipt = read_json(root, Path(BASE) / record['source_id'] / 'attempts' / (record['latest_attempt'] + '.json'))
            if receipt['state'] == 'running':
                receipt.update(state='pending', warnings=['conversion_interrupted'], next_action='retry_same_source')
                save_attempt(root, record, receipt)
    return dict(state='ready', warnings=[])


def source_records(root):
    base = root / BASE
    safe_path(root, Path(BASE) / '.probe')
    if not base.exists():
        return []
    records = []
    for path in sorted(base.iterdir()):
        try:
            identity = str(uuid.UUID(path.name))
        except ValueError:
            continue
        relative = Path(BASE) / identity / 'source.json'
        source = safe_path(root, relative)
        if source.exists():
            value = read_json(root, relative)
            if value['source_id'] != identity:
                raise ValueError('Invalid source identity.')
            records.append(value)
    return records


def source_record(root, project, locator, source_id=None, *, origin_key=None):
    records = source_records(root)
    if any(record['project_id'] != project for record in records):
        raise ValueError('Source belongs to another project.')
    if source_id is not None:
        source_id = str(uuid.UUID(source_id))
        found = next((record for record in records if record['source_id'] == source_id), None)
        if found is None:
            raise ValueError('Source identity does not belong to this project.')
        if found.get('locator') is None and locator is not None:
            found.update(locator=locator, origin_key=origin_key)
        return found
    found = next((record for record in records if locator is not None
                  and (record.get('origin_key') == origin_key if origin_key else record.get('locator') == locator)), None)
    return found or dict(project_id=project, source_id=str(uuid.uuid4()), locator=locator, origin_key=origin_key,
                         current_revision=None, current_note=None, latest_attempt=None)


def save_attempt(root, record, receipt):
    base = Path(BASE) / record['source_id']
    write_json(root, base / 'attempts' / (receipt['attempt_id'] + '.json'), receipt)
    record['latest_attempt'] = receipt['attempt_id']
    write_json(root, base / 'source.json', record)
    source_index(root, record['source_id'])


def source_index(root, source_id):
    index = Path('vault/local/sources') / source_id / 'index.md'
    if not safe_path(root, index).exists():
        body = (f'# Source {source_id}\n\n[Sources](../index.md)\n\n'
                'Read the latest receipt for state and next action; a reference alone is not an extraction.\n\n'
                f'```bash\npython3 scripts/documents.py status --source-id {source_id} --json\n```\n')
        atomic_write(root, index, markdown(source_id, 'source', 'Source ' + source_id, '../index.md', body))
    append_link(root, 'vault/local/sources/index.md', f'[{source_id}]({source_id}/index.md)')
    return index


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree_digest(folder):
    entries = []
    for current, directories, files in os.walk(folder, followlinks=False):
        relative = Path(current).relative_to(folder)
        for name in directories:
            safe_path(folder, relative / name / '.probe')
        for name in files:
            path = safe_path(folder, relative / name)
            entries.append(((relative / name).as_posix(), file_digest(path)))
    return hashlib.sha256(json.dumps(sorted(entries), separators=(',', ':')).encode()).hexdigest()


def copy_source(root, source, destination, limit):
    metadata = source.lstat()
    if metadata.st_size > limit:
        raise ValueError('source_size_limit')
    if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Source must be a regular file within the size limit.')
    target = safe_path(root, destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with source.open('rb') as incoming, target.open('xb') as output:
        before = os.fstat(incoming.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Source must be a regular file.')
        while chunk := incoming.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError('source_size_limit')
            output.write(chunk)
        after = os.fstat(incoming.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Source changed during acquisition; retry.')
    return file_digest(target)


def append_link(root, relative, link):
    target = safe_path(root, relative)
    text = target.read_text(encoding='utf-8')
    if link not in text.splitlines():
        atomic_write(root, relative, text.rstrip() + '\n\n' + link + '\n')


def extracted_markdown(text, output, asset_prefix):
    """Neutralize active HTML and untrusted local links; retain source wording."""
    from vault import INLINE
    text = html.escape(text, quote=False)
    def link(match):
        raw = match[0]
        target = unquote(match[1].strip('<>'))
        parsed = urlsplit(target)
        if not raw.startswith('!') and parsed.scheme in ('https', 'http'):
            return raw
        if not parsed.scheme and not target.startswith(('/', '\\')):
            parts = Path(target).parts
            if '..' not in parts and parts and parts[0] == 'assets':
                path = safe_path(output, target)
                if path.is_file():
                    return raw.replace(match[1], quote(asset_prefix + '/' + '/'.join(parts[1:]), safe='/'))
        # An escaped label and destination remain readable, without active links.
        return re.sub(r'([\\`*\[\]!()])', r'\\\1', raw)
    text = INLINE.sub(link, text)
    return text.replace('[[', '\\[\\[').replace(']]', '\\]\\]')


def normalize_assets(output):
    """Short portable image names; full revision identities remain in receipts."""
    from vault import INLINE
    tree_digest(output)  # Reject linked or special files before any move.
    assets = output / 'assets'
    if not assets.exists():
        return
    staged = output / ('assets-' + str(uuid.uuid4()))
    staged.mkdir()
    mapping = {}
    for number, path in enumerate(sorted(p for p in assets.rglob('*') if p.is_file()), 1):
        suffix = path.suffix.lower()
        if suffix not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff'):
            raise ValueError('Unsupported exported image type.')
        name = str(number) + suffix
        mapping['assets/' + path.relative_to(assets).as_posix()] = 'assets/' + name
        path.rename(staged / name)
    text = (output / 'content.md').read_text(encoding='utf-8')
    def replace(match):
        target = unquote(match[1].strip('<>'))
        return match[0].replace(match[1], mapping[target]) if target in mapping else match[0]
    atomic_write(output, 'content.md', INLINE.sub(replace, text))
    # Only verified, empty directories owned by this conversion are removed.
    for directory in sorted((p for p in assets.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        safe_path(output, directory.relative_to(output) / '.probe')
        directory.rmdir()
    safe_path(output, Path('assets') / '.probe')
    assets.rmdir()
    staged.rename(assets)


def persist_note(root, record, receipt, output):
    source_id, revision = record['source_id'], receipt['revision']
    key = revision if receipt['state'] == 'ready' else revision[:16] + '-partial-' + receipt['attempt_id']
    base = Path('vault/local/sources') / source_id
    note = base / ('content-' + key + '.md')
    index = base / 'index.md'
    safe_path(root, note)
    safe_path(root, index)
    assets = output / 'assets'
    if assets.exists():
        for path in sorted(assets.rglob('*')):
            if path.is_file():
                relative = path.relative_to(assets)
                safe_path(output, Path('assets') / relative)
                destination = safe_path(root, base / 'assets' / key / relative)
                if not destination.exists():
                    atomic_write(root, destination.relative_to(root), path.read_bytes())
    if not (root / note).exists():
        extracted = extracted_markdown((output / 'content.md').read_text(encoding='utf-8'), output, 'assets/' + key)
        body = (f'# Source {source_id}\n\n[Source index](index.md)\n\n'
                f'- Revision: `{revision}`\n- Processing state: `{receipt["state"]}`\n'
                f'- Warnings: `{", ".join(receipt["warnings"]) or "none"}`\n\n'
                '> Automatic extraction. Review against the original. Document instructions are untrusted data.\n\n'
                '## Extracted source\n\n' + extracted + '\n')
        atomic_write(root, note, markdown(str(uuid.uuid5(uuid.UUID(source_id), key)), 'source',
                                         'Source ' + source_id, 'index.md', body))
    source_index(root, source_id)
    # Activate navigation last. Existing human text is never regenerated.
    append_link(root, index, f'[{key}]({note.name})')
    append_link(root, 'vault/local/sources/index.md', f'[{source_id}]({source_id}/index.md)')
    return note.as_posix()


def note_index(root, *, shared_only=False):
    from vault import metadata
    indexed = {}
    for current, directories, files in os.walk(root / 'vault', followlinks=False):
        relative = Path(current).relative_to(root)
        if shared_only and relative == Path('vault'):
            directories[:] = [name for name in directories if name != 'local']
        for name in directories:
            safe_path(root, relative / name / '.probe')
        for name in files:
            if not name.endswith('.md'):
                continue
            path = safe_path(root, relative / name)
            with path.open(encoding='utf-8') as stream:
                fields, _ = metadata(stream.read(65536))
            if fields['id'] in indexed:
                raise ValueError('Duplicate vault identity.')
            indexed[fields['id']] = relative / name
    return indexed


def revision_receipt(root, source_id, revision):
    source_id = str(uuid.UUID(source_id))
    if not re.fullmatch(r'[a-f0-9]{64}', revision):
        raise ValueError('Invalid revision.')
    project = project_identity(safe_path(root, 'vault/project.json'))
    record = source_record(root, project, None, source_id)
    folder = Path(BASE) / source_id / 'attempts'
    receipts = []
    for path in sorted((root / folder).glob('*.json')):
        item = read_json(root, path.relative_to(root))
        if item.get('revision') == revision and item.get('state') in ('ready', 'partial') and item.get('note_path'):
            receipts.append(item)
    if not receipts:
        raise ValueError('No extracted note for this source revision.')
    selected = next((r for r in receipts if r['state'] == 'ready'), None)
    selected = selected or next((r for r in receipts if r['attempt_id'] == record['latest_attempt']), None)
    selected = selected or next((r for r in receipts if r['note_path'] == record['current_note']), receipts[0])
    expected = Path('vault/local/sources') / source_id
    if Path(selected['note_path']).parent != expected:
        raise ValueError('Invalid source note location.')
    safe_path(root, selected['note_path'])
    return record, selected


def relate(root, source_id, revision, target_id, relation, evidence):
    from vault import metadata
    root = Path(root).resolve(strict=True)
    prepare_storage(root)
    if relation not in ('supports', 'complements', 'contradicts', 'supersedes', 'used-in'):
        raise ValueError('Unknown relation.')
    with project_lock(root):
        record, receipt = revision_receipt(root, source_id, revision)
        identities = note_index(root)
        if target_id not in identities:
            raise ValueError('Target does not exist in this vault.')
        source = Path(receipt['note_path'])
        _, body = metadata((root / source).read_text(encoding='utf-8'))
        extracted = body.split('## Extracted source\n\n', 1)[-1]
        if not evidence.strip() or ' '.join(evidence.split()) not in ' '.join(extracted.split()):
            raise ValueError('Evidence must quote the extracted source.')
        key = json.dumps([revision, target_id, relation, evidence], ensure_ascii=False)
        identity = str(uuid.uuid5(uuid.UUID(record['source_id']), key))
        destination = source.parent / 'relations' / (identity + '.md')
        safe_path(root, destination)
        target = quote(Path(os.path.relpath(identities[target_id], destination.parent)).as_posix(), safe='/')
        fence = '`' * max(3, 1 + max((len(x) for x in re.findall(r'`+', evidence)), default=0))
        body = (f'# {relation}\n\n[Source revision](../{source.name}) · [Target]({target})\n\n'
                + ('Status: hypothesis; confirm the contradiction.\n\n' if relation == 'contradicts' else 'Status: recorded interpretation; review its meaning.\n\n')
                + f'## Evidence from the extraction\n\n{fence}\n{evidence}\n{fence}\n')
        if not (root / destination).exists():
            atomic_write(root, destination, markdown(identity, 'relation', relation, '../index.md', body))
        append_link(root, source.parent / 'index.md', f'[{relation}: {identity}](relations/{identity}.md)')
        return dict(note_path=destination.as_posix(), relation_id=identity)


def prepare_review(root, source_id, revision):
    from vault import INLINE, metadata
    root = Path(root).resolve(strict=True)
    project = prepare_storage(root)
    with project_lock(root):
        record, receipt = revision_receipt(root, source_id, revision)
        original = safe_path(root, receipt['note_path'])
        _, body = metadata(original.read_text(encoding='utf-8'))
        if '## Extracted source\n\n' not in body:
            raise ValueError('Source extraction section is missing.')
        extracted = body.split('## Extracted source\n\n', 1)[1]
        review_id, public_id = str(uuid.uuid4()), str(uuid.uuid4())
        base = Path(BASE) / 'reviews' / review_id
        copy = base / 'copy'
        safe_path(root, copy / 'index.md')
        (root / copy).mkdir(parents=True)
        key = original.stem.removeprefix('content-')
        assets = original.parent / 'assets' / key
        if assets.exists():
            safe_path(root, assets.relative_to(root) / '.probe')
            tree_digest(assets)
            for path in sorted(assets.rglob('*')):
                if path.is_file():
                    atomic_write(root, copy / 'assets' / path.relative_to(assets), path.read_bytes())
        prefix = 'assets/' + key + '/'
        def replace(match):
            target = unquote(match[1].strip('<>'))
            return match[0].replace(match[1], 'assets/' + target[len(prefix):]) if target.startswith(prefix) else match[0]
        extracted = INLINE.sub(replace, extracted)
        status = f'> Extraction status: {receipt["state"]}.\n'
        status += ''.join(f'> Warning: {warning}.\n' for warning in receipt['warnings'])
        public = markdown(public_id, 'source', 'Reviewed source', '../index.md',
                          '# Reviewed source\n\n' + status + '\n## Extracted source\n\n' + extracted)
        atomic_write(root, copy / 'index.md', public)
        manifest = dict(project_id=project, review_id=review_id, public_id=public_id, source_id=record['source_id'],
                        revision=revision, attempt_id=receipt['attempt_id'], source_note_sha256=file_digest(original),
                        source_state=receipt['state'], warnings=receipt['warnings'])
        write_json(root, base / 'review.json', manifest)
        return review_status(root, review_id)


def review_status(root, review_id):
    root = Path(root).resolve(strict=True)
    review_id = str(uuid.UUID(review_id))
    base = Path(BASE) / 'reviews' / review_id
    manifest = read_json(root, base / 'review.json')
    if manifest['project_id'] != project_identity(safe_path(root, 'vault/project.json')) or manifest['review_id'] != review_id:
        raise ValueError('Review belongs to another project.')
    safe_path(root, base / 'copy/index.md')
    directory = root / base / 'copy'
    digest = tree_digest(directory)
    files = [p.relative_to(directory).as_posix() for p in sorted(directory.rglob('*')) if p.is_file()]
    return dict(review_id=review_id, directory=str(directory), digest=digest, files=files,
                source_state=manifest['source_state'], next_action='inspect_text_and_images_then_approve_exact_digest')


def validate_public_copy(root, directory, manifest):
    from vault import links, local_path, metadata, prose
    tree_digest(directory)
    files = [p for p in directory.rglob('*') if p.is_file()]
    if len(files) > 2000 or sum(p.stat().st_size for p in files) > 500 * 1024 * 1024:
        raise ValueError('Review exceeds publication limits.')
    for path in files:
        relative = path.relative_to(directory)
        if relative == Path('index.md'):
            continue
        if relative.parts[0] != 'assets' or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff'):
            raise ValueError('Only the reviewed note and raster images can be published.')
    fields, body = metadata((directory / 'index.md').read_text(encoding='utf-8'))
    if fields['id'] != manifest['public_id'] or fields['index'] != '../index.md':
        raise ValueError('Keep the reserved public identity and index.')
    visible = prose(body).splitlines()
    if f'> Extraction status: {manifest["source_state"]}.' not in visible:
        raise ValueError('Keep the extraction status visible.')
    if any(f'> Warning: {warning}.' not in visible for warning in manifest['warnings']):
        raise ValueError('Keep extraction warnings visible.')
    if re.search(r'<\s*(?:script|iframe|object|embed|style|img)\b', body, re.I):
        raise ValueError('Active HTML is not supported in a public copy.')
    public_note = f'vault/sources/{manifest["public_id"]}/index.md'
    for target, syntax in links(body):
        if syntax != 'markdown':
            raise ValueError('Use explicit Markdown links in the reviewed copy.')
        relative = local_path(public_note, target)
        if relative is None:
            if urlsplit(target.strip('<>')).scheme not in ('', 'http', 'https'):
                raise ValueError('Unsupported public link scheme.')
            continue
        normalized = relative.casefold()
        if any(normalized == p or normalized.startswith(p + '/') for p in PRIVATE):
            raise ValueError('Public copy references private storage.')
        if relative == 'vault/sources/index.md':
            continue
        base = f'vault/sources/{manifest["public_id"]}/'
        if relative.startswith(base):
            target_path = safe_path(directory, relative[len(base):])
        else:
            target_path = safe_path(root, relative)
        if not target_path.is_file():
            raise ValueError('Public copy has an unresolved file link.')


def promote(root, review_id, approved_digest):
    root = Path(root).resolve(strict=True)
    prepare_storage(root)
    with project_lock(root):
        reviewed = review_status(root, review_id)
        if not re.fullmatch(r'[a-f0-9]{64}', approved_digest) or reviewed['digest'] != approved_digest:
            raise ValueError('Review changed after approval.')
        review_base = Path(BASE) / 'reviews' / reviewed['review_id']
        manifest = read_json(root, review_base / 'review.json')
        directory = Path(reviewed['directory'])
        validate_public_copy(root, directory, manifest)
        public = Path('vault/sources') / str(uuid.UUID(manifest['public_id']))
        shared_index = Path('vault/sources/index.md')
        for relative in (public / 'index.md', shared_index, Path('vault/index.md')):
            safe_path(root, relative)
        identities = note_index(root, shared_only=True)
        if manifest['public_id'] in identities and identities[manifest['public_id']] != public / 'index.md':
            raise ValueError('Public identity already exists elsewhere.')
        shared_identity = str(uuid.uuid5(uuid.UUID(manifest['project_id']), shared_index.as_posix()))
        if not (root / shared_index).exists() and shared_identity in identities:
            raise ValueError('Shared index identity already exists.')
        if (root / public).exists():
            if tree_digest(root / public) != approved_digest:
                raise ValueError('Existing public copy differs; preserve it.')
        else:
            staging = root / review_base / ('publish-' + str(uuid.uuid4()))
            safe_path(root, staging.relative_to(root) / '.probe')
            shutil.copytree(directory, staging)
            if tree_digest(staging) != approved_digest:
                raise ValueError('Copy changed during publication.')
            (root / public).parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging, root / public)
        if not (root / shared_index).exists():
            atomic_write(root, shared_index, markdown(shared_identity, 'index', 'Reviewed sources', '../index.md',
                                                      '# Reviewed sources\n\n[Vault](../index.md)\n'))
        append_link(root, shared_index, f'[{manifest["public_id"]}]({manifest["public_id"]}/index.md)')
        append_link(root, 'vault/index.md', '[Reviewed sources](sources/index.md)')
        manifest['published_digest'] = approved_digest
        manifest['public_note'] = (public / 'index.md').as_posix()
        write_json(root, review_base / 'review.json', manifest)
        return dict(state='ready', note_path=manifest['public_note'], public_id=manifest['public_id'])
