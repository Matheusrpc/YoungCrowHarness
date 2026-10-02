"""Project-scoped vault retrieval. Derived state is private and reconstructible."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
from document_store import safe_path, prepare_storage, project_lock, write_json, file_digest
from integrations import project_identity
from vault import metadata, links, local_path, prose
from documents import runtime_python, worker_environment, run_process

BASE = '.operacao-local/memory'
VERSION = '0.9.73'
WORKER = Path(__file__).with_name('graphify_worker.py')


def failure(code, state='failed'):
    return dict(state=state, warnings=[code])


def run_graphify(root: Path, action: str, request: dict) -> dict:
    base = Path(root) / BASE / 'runtime'
    executable = runtime_python(base / 'venv')
    path = None
    try:
        safe_path(root, base.relative_to(root) / 'venv/pyvenv.cfg')
        safe_path(root, executable.relative_to(root))
        if not executable.is_file():
            return failure('runtime_missing', 'pending')
        prepare_storage(root)
        env = worker_environment(base)
        env.update(GRAPHIFY_QUERY_LOG_DISABLE='1', PYTHONHASHSEED='0')
        relative = BASE + '/runtime/request-' + str(uuid.uuid4()) + '.json'
        write_json(root, relative, dict(request, action=action))
        path = safe_path(root, relative)
        process = run_process([str(executable), '-I', str(WORKER), str(path)],
                              timeout=120 if action == 'build' else 30, env=env)
        if process.returncode or len(process.stdout) > 2 * 1024 * 1024:
            return failure('worker_failed')
        data = json.loads(process.stdout)
        if not isinstance(data, dict):
            return failure('invalid_worker_result')
        if data.get('state') != 'ready':
            code = data.get('code')
            if code in ('runtime_version_mismatch', 'package_missing'):
                return failure(code, 'unsupported' if code == 'runtime_version_mismatch' else 'pending')
            return failure('vendor_failed')
        if data.get('version') != VERSION:
            return failure('runtime_version_mismatch', 'unsupported')
        return data
    except subprocess.TimeoutExpired:
        return failure('worker_timeout')
    except (ValueError, OSError, TypeError):
        return failure('invalid_worker_result')
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def doctor(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    result = run_graphify(root, 'doctor', {})
    if result['state'] != 'ready':
        return result
    if not str(result.get('python', '')).startswith('3.12.'):
        return failure('python_312_required', 'unsupported')
    try:
        manifest = read(root, BASE + '/runtime/environment.json')
        if manifest.get('packages') != result.get('packages'):
            return failure('runtime_changed', 'unsupported')
    except FileNotFoundError:
        return failure('runtime_manifest_missing', 'pending')
    except (ValueError, OSError):
        return failure('invalid_runtime_manifest')
    return result


def setup_graphify(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    if sys.version_info[:2] != (3, 12):
        return failure('run_setup_with_python_312', 'unsupported')
    prepare_storage(root)
    with project_lock(root):
        base = root / BASE / 'runtime'
        for relative in ('venv/pyvenv.cfg', 'environment.json', 'setup.log', 'cache/.probe', 'home/.probe', 'temp/.probe'):
            safe_path(root, base.relative_to(root) / relative)
        if (base / 'environment.json').exists():
            return doctor(root)
        env = worker_environment(base, offline=False)
        executable = runtime_python(base / 'venv')
        commands = []
        if executable.exists():
            actual = run_graphify(root, 'doctor', {})
            if actual['state'] == 'unsupported':
                return actual
        else:
            commands.append([sys.executable, '-m', 'venv', '--copies', str(base / 'venv')])
        requirements = Path(__file__).resolve().parents[1] / 'requirements/graphify.txt'
        commands.append([str(executable), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(requirements)])
        for command in commands:
            try:
                result = run_process(command, timeout=600, env=env)
            except subprocess.TimeoutExpired:
                return failure('setup_timeout')
            with safe_path(root, BASE + '/runtime/setup.log').open('ab') as output:
                output.write(result.stdout + result.stderr)
            if result.returncode:
                return failure('setup_failed')
        actual = run_graphify(root, 'doctor', {})
        if actual['state'] != 'ready':
            return actual
        write_json(root, BASE + '/runtime/environment.json', actual)
        return doctor(root)


def validate_graph(snapshot: dict, graph: dict) -> None:
    try:
        if (not isinstance(graph, dict) or graph.get('directed') is not True or graph.get('multigraph') is not False
                or graph['graph']['project_id'] != snapshot['project_id']
                or graph['graph']['fingerprint'] != snapshot['fingerprint']):
            raise ValueError('invalid_graph_identity')
        expected = {n['source_file']: n for n in snapshot['notes']}
        found, identifiers = {}, {}
        for node in graph['nodes']:
            source, identity = node['source_file'], node['id']
            if not isinstance(identity, str) or source not in expected or source in found or identity in identifiers:
                raise ValueError('invalid_graph_node')
            original = expected[source]
            if (node['youngcrow_id'] != original['id'] or node['youngcrow_revision'] != original['revision']
                    or node['label'] != original['title'] or node['file_type'] != 'document'
                    or node['source_location'] != 'L1'):
                raise ValueError('invalid_graph_provenance')
            found[source], identifiers[identity] = node, original
        if found.keys() != expected.keys():
            raise ValueError('incomplete_graph')
        expected_edges = {(r['source_id'], r['target_id']) for r in snapshot['relations']}
        edges = set()
        for edge in graph['links']:
            source, target = identifiers[edge['source']], identifiers[edge['target']]
            pair = (source['id'], target['id'])
            if (pair not in expected_edges or pair in edges or edge['relation'] != 'references'
                    or edge['confidence'] != 'EXTRACTED' or edge['confidence_score'] != 1.0
                    or edge['source_file'] != source['source_file']):
                raise ValueError('invalid_graph_relation')
            edges.add(pair)
        if edges != expected_edges:
            raise ValueError('incomplete_graph_relations')
    except (KeyError, TypeError, AttributeError):
        raise ValueError('invalid_graph') from None


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
    prepare_storage(root)
    with project_lock(root):
        snap = snapshot(root, paths, provider)
        try:
            _, current, state, _, _ = load_state(root)
            if state == 'ready' and current['fingerprint'] == snap['fingerprint']:
                return dict(state='ready', fingerprint=snap['fingerprint'], notes=len(snap['notes']), reused=True)
        except (ValueError, OSError, KeyError, TypeError):
            pass
        generation = str(uuid.uuid4())
        folder = BASE + '/builds/' + generation
        write_json(root, folder + '/snapshot.json', snap)
        selection = dict(project_id=snap['project_id'], paths=[n['path'] for n in snap['notes']], provider=provider)
        write_json(root, BASE + '/selection.json', selection)
        write_json(root, BASE + '/status.json', dict(state='pending'))
        active = dict(generation=generation, fingerprint=snap['fingerprint'],
                      snapshot_hash=file_digest(safe_path(root, folder + '/snapshot.json')))
        if provider == 'graphify':
            result = run_graphify(root, 'build', dict(snapshot=snap))
            if result['state'] == 'ready':
                try:
                    validate_graph(snap, result.get('graph'))
                except ValueError:
                    result = failure('invalid_graph')
            if result['state'] != 'ready':
                write_json(root, BASE + '/status.json', result)
                return result
            write_json(root, folder + '/graph.json', result['graph'])
            active['graph_hash'] = file_digest(safe_path(root, folder + '/graph.json'))
        try:
            if snapshot(root, paths, provider)['fingerprint'] != snap['fingerprint']:
                raise ValueError('changed')
        except (ValueError, OSError, KeyError, TypeError):
            result = failure('sources_changed_during_build')
            write_json(root, BASE + '/status.json', result)
            return result
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
        if state == 'ready' and snap['provider'] == 'graphify':
            graph_path = BASE + '/builds/' + generation + '/graph.json'
            if file_digest(safe_path(root, graph_path)) != active['graph_hash']:
                raise ValueError('graph_hash_mismatch')
            validate_graph(snap, read(root, graph_path))
    except FileNotFoundError:
        state = 'missing'
    except (ValueError, OSError, KeyError, TypeError):
        state, active = 'failed', None
        warnings.append('invalid_cached_index')
    try:
        recorded = read(root, BASE + '/status.json')
        if recorded.get('state') in ('pending', 'failed', 'unsupported'):
            state = recorded['state']
            warnings.extend(w for w in recorded.get('warnings', []) if isinstance(w, str) and re.fullmatch('[a-z_]+', w))
    except FileNotFoundError:
        pass
    except (ValueError, OSError, TypeError, AttributeError):
        state = 'failed'
        warnings.append('invalid_index_status')
    return selection, snap, state, warnings, active


def rebuild(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    selection, snap, _, _, _ = load_state(root)
    paths = [n['path'] for n in snap['notes']]
    return dict(index(root, paths, selection['provider']), removed=[p for p in selection['paths'] if p not in paths])


def disable(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    _, snap, _, _, _ = load_state(root)
    return index(root, [n['path'] for n in snap['notes']], 'markdown')


def clear_index(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    prepare_storage(root)
    with project_lock(root):
        builds = safe_path(root, BASE + '/builds/.probe').parent
        active = safe_path(root, BASE + '/active.json')
        files, folders = [], []
        if builds.exists():
            for folder in builds.iterdir():
                if str(uuid.UUID(folder.name)) != folder.name:
                    raise ValueError('invalid_generation')
                safe_path(root, folder.relative_to(root) / '.probe')
                if not folder.resolve(strict=True).is_relative_to(builds.resolve(strict=True)):
                    raise ValueError('generation_outside_builds')
                for path in folder.iterdir():
                    if path.name not in ('snapshot.json', 'graph.json'):
                        raise ValueError('unknown_generation_file')
                    files.append(safe_path(root, path.relative_to(root)))
                folders.append(folder)
        # All contents and resolved boundaries pass before any removal.
        for path in files:
            path.unlink()
        for folder in folders:
            folder.rmdir()
        active.unlink(missing_ok=True)
        write_json(root, BASE + '/status.json', dict(state='missing'))
    return dict(state='missing', removed_generations=len(folders))


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
        _, snap, state, warnings, active = load_state(root)
    except FileNotFoundError:
        return result
    except (ValueError, KeyError, TypeError, OSError):
        return dict(result, index_state='failed', warnings=['invalid_memory_state'])
    terms = set(re.findall(r'[^\W_]+', question.casefold()))
    def ranked(current):
        def score(note):
            _, body = metadata(note['text'])
            return sum(3 * note['title'].casefold().count(t) + body.casefold().count(t) for t in terms)
        return sorted((n for n in current['notes'] if score(n)), key=lambda n: (-score(n), n['path']))
    ordered = ranked(snap)
    provider = 'markdown'
    if state == 'ready' and snap['provider'] == 'graphify':
        try:
            graph_path = BASE + '/builds/' + str(uuid.UUID(active['generation'])) + '/graph.json'
            graph_file = safe_path(root, graph_path)
            if file_digest(graph_file) != active['graph_hash']:
                raise ValueError('graph_changed')
            validate_graph(snap, read(root, graph_path))
            response = run_graphify(root, 'query', dict(graph_path=str(graph_file), question=question))
            if response['state'] != 'ready':
                state = response['state']
                warnings.extend(response['warnings'])
            else:
                sources = response.get('source_files')
                by_source = {n['source_file']: n for n in snap['notes']}
                if not isinstance(sources, list) or any(not isinstance(s, str) or s not in by_source for s in sources):
                    raise ValueError('invalid_query_sources')
                ordered = [by_source[s] for s in dict.fromkeys(sources)]
                provider = 'graphify'
            _, after, after_state, after_warnings, _ = load_state(root)
            if after['fingerprint'] != snap['fingerprint'] or after_state != 'ready':
                snap, state = after, after_state if after_state != 'ready' else 'stale'
                warnings.extend([*after_warnings, 'sources_changed_during_query'])
                provider, ordered = 'markdown', ranked(snap)
        except (ValueError, OSError, KeyError, TypeError):
            state, warnings, provider = 'failed', [*warnings, 'invalid_graph_result'], 'markdown'
            try:
                _, snap, _, _, _ = load_state(root)
                ordered = ranked(snap)
            except (ValueError, OSError, KeyError, TypeError):
                ordered = []
    return dict(result, state='ready' if state == 'ready' else 'fallback', index_state=state,
                provider=provider, project_id=snap['project_id'], warnings=warnings, results=render_results(snap, ordered, limit))


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
    sub.add_parser('setup-graphify')
    sub.add_parser('doctor')
    sub.add_parser('rebuild')
    sub.add_parser('disable')
    sub.add_parser('clear-index')
    args = parser.parse_args()
    try:
        if args.command == 'index':
            result = index(args.root, args.note, args.provider)
        elif args.command == 'query':
            result = query(args.root, args.question, args.limit)
        elif args.command == 'setup-graphify':
            result = setup_graphify(args.root)
        elif args.command == 'doctor':
            result = doctor(args.root)
        elif args.command == 'rebuild':
            result = rebuild(args.root)
        elif args.command == 'disable':
            result = disable(args.root)
        elif args.command == 'clear-index':
            result = clear_index(args.root)
        else:
            result = status(args.root)
    except (ValueError, OSError, KeyError, TypeError):
        result = dict(state='failed', warnings=['invalid_request_or_storage'])
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result['state'] in ('failed', 'unsupported', 'pending') else 0


if __name__ == '__main__':
    sys.exit(main())
