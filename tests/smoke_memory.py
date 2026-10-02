"""Opt-in smoke using synthetic notes and the actual optional Graphify runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from memory_fixture import seed

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--provider', choices=('markdown', 'graphify'), default='markdown')
    args = parser.parse_args()
    root = args.root.resolve()
    marker = root / 'memory-smoke.json'
    if not marker.exists():
        if root.exists() and any(root.iterdir()):
            parser.error('Use an empty disposable project; existing data will not be overwritten.')
        root.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        data = seed(root)
        marker.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    data = json.loads(marker.read_text(encoding='utf-8'))

    def cli(*arguments):
        started = time.perf_counter()
        process = subprocess.run([sys.executable, str(REPO / 'scripts/memory.py'), '--root', str(root), *arguments],
                                 capture_output=True, timeout=150, check=True)
        result = json.loads(process.stdout)
        return result, dict(milliseconds=round((time.perf_counter() - started) * 1000, 3),
                            bytes_returned=len(process.stdout), characters_returned=len(process.stdout.decode()))

    index_args = ['index', '--provider', args.provider]
    for path in data['paths']:
        index_args.extend(['--note', path])
    built, build_measurement = cli(*index_args)
    assert built['state'] == 'ready', built
    measured = []
    for run in ('cold', 'repeated'):
        for expected in data['expected']:
            result, measurement = cli('query', expected['question'])
            assert result['provider'] == args.provider, result
            stale = [hit['path'] for hit in result['results'] if hit['revision'] != hashlib.sha256((root / hit['path']).read_bytes()).hexdigest()]
            assert not stale, stale
            correct = any(hit['path'] == expected['path'] and expected['quote'] in hit['excerpt'] for hit in result['results'])
            measured.append(dict(run=run, question=expected['question'], correct=int(correct), expected=1,
                                 stale_references=len(stale), paths=[hit['path'] for hit in result['results']],
                                 revisions=[hit['revision'] for hit in result['results']], **measurement))
    actual, _ = cli('status')
    assert actual['state'] == 'ready', actual
    duplicate_titles = None
    if args.provider == 'graphify':
        sys.path.insert(0, str(REPO / 'scripts'))
        import memory
        snap = memory.snapshot(root, data['paths'], 'graphify')
        snap['notes'][1]['title'] = snap['notes'][0]['title']
        snap['fingerprint'] = memory.fingerprint(snap)
        duplicate = memory.run_graphify(root, 'build', dict(snapshot=snap))
        assert duplicate['state'] == 'ready', duplicate
        memory.validate_graph(snap, duplicate['graph'])
        duplicate_titles = len(duplicate['graph']['nodes']) == len(data['paths'])
        assert duplicate_titles
    report = dict(provider=args.provider, fingerprint=built['fingerprint'], build=build_measurement,
                  notes=len(data['paths']), duplicate_titles_preserved=duplicate_titles, measurements=measured)
    (root / ('smoke-' + args.provider + '.json')).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
