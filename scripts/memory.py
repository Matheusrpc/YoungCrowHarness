"""Project-scoped vault retrieval. Derived state is private and reconstructible."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

sys.dont_write_bytecode = True
from document_store import safe_path, prepare_storage, project_lock, write_json, file_digest
from integrations import project_identity
from vault import metadata, links, local_path, prose

BASE = '.operacao-local/memory'
VERSION = '0.9.73'


def read(root, relative):
    path = safe_path(root, relative)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('state_size_limit')
    return json.loads(path.read_text(encoding='utf-8'))


def note_path(root, value):
    if not isinstance(value, str) or '\\' in value or len(value) > 1024:
        raise ValueError('invalid_note_path')
    path = safe_path(root, value)
    relative = path.relative_to(root).as_posix()
    if not relative.startswith('vault/') or not relative.endswith('.md'):
        raise ValueError('select_vault_markdown')
    return relative


def fingerprint(snap):
    fields = ('schema', 'project_id', 'provider', 'provider_version', 'notes', 'relations')
    raw = json.dumps({k: snap[k] for k in fields}, sort_keys=True,
                     ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def snapshot(root: Path, paths: list[str], provider: str = 'markdown') -> dict:
    root = Path(root).resolve(strict=True)
    if provider not in ('markdown', 'graphify') or not isinstance(paths, list) or len(paths) > 100:
        raise ValueError('invalid_selection')
    project = project_identity(safe_path(root, 'vault/project.json'))
    notes, identities, size = {}, set(), 0
    for relative in sorted({note_path(root, p) for p in paths}):
        path = safe_path(root, relative)
        if path.stat().st_size > 256 * 1024:
            raise ValueError('note_size_limit')
        raw = path.read_bytes()
        size += len(raw)
        if len(raw) > 256 * 1024 or size > 8 * 1024 * 1024:
            raise ValueError('corpus_size_limit')
        text = raw.decode('utf-8')
        fields, _ = metadata(text)
        identity = str(uuid.UUID(fields['id']))
        if identity in identities:
            raise ValueError('duplicate_note_uuid')
        identities.add(identity)
        notes[relative] = dict(id=identity, path=relative, title=fields['title'], text=text,
                               revision=hashlib.sha256(raw).hexdigest(),
                               scope='local' if relative.startswith('vault/local/') else 'shared',
                               source_file='notes/' + uuid.UUID(identity).hex + '.md')
    relations, seen = [], set()
    for relative, note in notes.items():
        _, body = metadata(note['text'])
        for original, kind in links(body):
            target = original
            if kind == 'missing_reference':
                raise ValueError('missing_markdown_reference')
            if kind == 'wiki':
                target = target.split('#', 1)[0]
                if not target:
                    continue
                if not Path(target).suffix:
                    target += '.md'
                destination = local_path(relative if target.startswith(('./', '../')) else 'vault/index.md', target)
                if '/' not in target and destination not in notes:
                    matches = [p for p in notes if p.rsplit('/', 1)[-1] == target]
                    if len(matches) > 1:
                        raise ValueError('ambiguous_wiki_link')
                    if matches:
                        destination = matches[0]
            else:
                destination = local_path(relative, target)
            if destination not in notes:
                continue
            if note['scope'] == 'shared' and notes[destination]['scope'] == 'local':
                raise ValueError('shared_note_references_private')
            pair = (note['id'], notes[destination]['id'])
            if pair in seen:
                continue
            seen.add(pair)
            # Citation uses source text, never reconstructed Markdown.
            quote = next((line for line in prose(body).splitlines() if original in line), '')
            if not quote:
                raise ValueError('relation_evidence_missing')
            offset = max(0, quote.find(original) - 100)
            quote = quote[offset:offset + len(original) + 200]
            relations.append(dict(source_id=pair[0], target_id=pair[1], origin='markdown_link',
                                  evidence_path=relative, evidence_revision=note['revision'], quote=quote,
                                  target_path=destination, target_revision=notes[destination]['revision']))
    snap = dict(schema=1, project_id=project, provider=provider,
                provider_version=VERSION if provider == 'graphify' else None,
                notes=list(notes.values()), relations=relations)
    snap['fingerprint'] = fingerprint(snap)
    return snap


def index(root: Path, paths: list[str], provider: str = 'markdown') -> dict:
    root = Path(root).resolve(strict=True)
    if provider != 'markdown':
        raise ValueError('provider_unavailable')
    prepare_storage(root)
    with project_lock(root):
        snap = snapshot(root, paths, provider)
        generation = str(uuid.uuid4())
        folder = BASE + '/builds/' + generation
        write_json(root, folder + '/snapshot.json', snap)
        selection = dict(project_id=snap['project_id'], paths=[n['path'] for n in snap['notes']], provider=provider)
        write_json(root, BASE + '/selection.json', selection)
        active = dict(generation=generation, fingerprint=snap['fingerprint'],
                      snapshot_hash=file_digest(safe_path(root, folder + '/snapshot.json')))
        write_json(root, BASE + '/active.json', active)
        write_json(root, BASE + '/status.json', dict(state='ready'))
    return dict(state='ready', fingerprint=snap['fingerprint'], notes=len(snap['notes']))


def load_state(root):
    """Re-read selected notes; never present cached content as current evidence."""
    selection = read(root, BASE + '/selection.json')
    project = project_identity(safe_path(root, 'vault/project.json'))
    if not isinstance(selection, dict) or selection.get('project_id') != project:
        raise ValueError('selection_project_mismatch')
    paths = selection.get('paths')
    if not isinstance(paths, list) or len(paths) > 100:
        raise ValueError('invalid_selection')
    present, warnings = [], []
    for relative in paths:
        note_path(root, relative)
        if safe_path(root, relative).exists():
            present.append(relative)
        else:
            warnings.append('selected_note_missing')
    snap = snapshot(root, present, selection.get('provider'))
    active, state = None, 'missing'
    try:
        active = read(root, BASE + '/active.json')
        generation = str(uuid.UUID(active['generation']))
        stored = safe_path(root, BASE + '/builds/' + generation + '/snapshot.json')
        if file_digest(stored) != active['snapshot_hash']:
            raise ValueError('snapshot_hash_mismatch')
        state = 'ready' if not warnings and active['fingerprint'] == snap['fingerprint'] else 'stale'
    except FileNotFoundError:
        state = 'missing'
    return selection, snap, state, warnings, active


def status(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    try:
        _, snap, state, warnings, _ = load_state(root)
        return dict(state=state, project_id=snap['project_id'], fingerprint=snap['fingerprint'],
                    notes=len(snap['notes']), warnings=warnings)
    except FileNotFoundError:
        return dict(state='missing', warnings=['selection_missing'])
    except (ValueError, KeyError, TypeError, OSError):
        return dict(state='failed', warnings=['invalid_memory_state'])


def render_results(snap, ordered, limit):
    result = []
    for note in ordered[:limit]:
        _, body = metadata(note['text'])
        excerpt = ' '.join(body.split())
        relations = [r for r in snap['relations'] if note['id'] in (r['source_id'], r['target_id'])]
        title = ' '.join(note['title'].split())
        result.append(dict(id=note['id'], path=note['path'], revision=note['revision'], scope=note['scope'],
                           title=title[:240], excerpt=excerpt[:400],
                           relations=[dict(r, quote=r['quote'][:200]) for r in relations[:5]],
                           truncated=len(title) > 240 or len(excerpt) > 400 or len(relations) > 5
                           or any(len(r['quote']) > 200 for r in relations[:5])))
    return result


def query(root: Path, question: str, limit: int = 5) -> dict:
    root = Path(root).resolve(strict=True)
    if not isinstance(question, str) or not question.strip() or len(question) > 512 or not 1 <= limit <= 5:
        raise ValueError('invalid_query')
    navigation = [p for p in ('vault/index.md', 'vault/local/index.md') if safe_path(root, p).exists()]
    result = dict(state='fallback', index_state='missing', provider='markdown', project_id=None,
                  warnings=[], navigation=navigation, results=[])
    try:
        _, snap, state, warnings, _ = load_state(root)
    except FileNotFoundError:
        return result
    except (ValueError, KeyError, TypeError, OSError):
        return dict(result, index_state='failed', warnings=['invalid_memory_state'])
    terms = set(re.findall(r'[^\W_]+', question.casefold()))
    def score(note):
        _, body = metadata(note['text'])
        return sum(3 * note['title'].casefold().count(t) + body.casefold().count(t) for t in terms)
    ordered = sorted((n for n in snap['notes'] if score(n)), key=lambda n: (-score(n), n['path']))
    return dict(result, state='ready' if state == 'ready' else 'fallback', index_state=state,
                project_id=snap['project_id'], warnings=warnings, results=render_results(snap, ordered, limit))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    select = sub.add_parser('index')
    select.add_argument('--note', action='append', required=True)
    select.add_argument('--provider', choices=('markdown', 'graphify'), default='markdown')
    find = sub.add_parser('query')
    find.add_argument('question')
    find.add_argument('--limit', type=int, default=5)
    sub.add_parser('status')
    args = parser.parse_args()
    try:
        if args.command == 'index':
            result = index(args.root, args.note, args.provider)
        elif args.command == 'query':
            result = query(args.root, args.question, args.limit)
        else:
            result = status(args.root)
    except (ValueError, OSError, KeyError, TypeError):
        result = dict(state='failed', warnings=['invalid_request_or_storage'])
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result['state'] in ('failed', 'unsupported', 'pending') else 0


if __name__ == '__main__':
    sys.exit(main())
