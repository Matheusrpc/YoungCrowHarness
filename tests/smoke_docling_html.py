"""Opt-in HTML regression with the installed Docling SDK; no downloads or models."""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import documents


def worker(request_path):
    import docling_worker
    request = json.loads(Path(request_path).read_text(encoding='utf-8'))
    watched = Path(request.pop('watched')).resolve()
    events = []

    def audit(event, args):
        if event == 'socket.connect':
            events.append('network_connect')
            raise PermissionError('Unexpected network access in HTML conversion.')
        if event == 'open' and isinstance(args[0], (str, bytes)):
            if Path(args[0]).resolve() == watched:
                events.append('linked_file_open')
                raise PermissionError('Unexpected linked file access.')

    sys.addaudithook(audit)
    with redirect_stdout(sys.stderr):
        result = docling_worker.convert(request)
    print(json.dumps(dict(result=result, forbidden_access=events)))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(sys.argv[2])
        return
    run = ROOT / '.runtime/docling-html' / uuid.uuid4().hex
    run.mkdir(parents=True)
    linked = run / 'linked.txt'
    linked.write_text('CANARY_MUST_NOT_BE_READ', encoding='utf-8')
    source = run / 'source.html'
    source.write_text('<!doctype html><html><head><base href="file:///untrusted/"></head><body>'
        '<h1>HTML evidence survives links.</h1><p><a href="/llms.txt">Root reference</a> '
        '<a href="../guide">Parent reference</a> <a href="guide">Relative reference</a> '
        '<a href="https://example.invalid/guide">Public reference</a> '
        '<a href="#section">Section reference</a> '
        f'<a href="{linked.as_uri()}">Local reference</a></p>'
        f'<img src="{linked.as_uri()}"><iframe src="{linked.as_uri()}"></iframe>'
        '<img src="https://127.0.0.1:9/never.png"><script src="https://127.0.0.1:9/never.js"></script>'
        '<table><tr><th>State</th><th>Result</th></tr><tr><td>Local</td><td>Preserved</td></tr></table>'
        '</body></html>', encoding='utf-8')
    original = source.read_bytes()
    output = run / 'output'
    output.mkdir()
    runtime = ROOT / documents.BASE / 'venv'
    request = run / 'request.json'
    request.write_text(json.dumps(dict(source=str(source), output=str(output),
        models=str(runtime.parent / 'models'), watched=str(linked))), encoding='utf-8')
    started = time.monotonic()
    process = documents.run_process([str(documents.runtime_python(runtime)), str(Path(__file__).resolve()),
        '--worker', str(request)], timeout=180, env=documents.worker_environment(runtime.parent))
    (run / 'stderr.log').write_bytes(process.stderr)
    assert process.returncode == 0, 'Worker failed; see private stderr.log'
    report = json.loads(process.stdout)
    report['seconds'] = round(time.monotonic() - started, 2)
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    assert report['result']['state'] == 'ready', report
    assert report['forbidden_access'] == [], report
    text = (output / 'content.md').read_text(encoding='utf-8')
    for phrase in ('HTML evidence survives links.', 'Root reference', 'Parent reference',
                   'Relative reference', 'Public reference', 'Local reference', 'State', 'Preserved'):
        assert phrase in text, phrase
    assert 'https://example.invalid/guide' in text
    assert 'CANARY_MUST_NOT_BE_READ' not in text
    assert source.read_bytes() == original
    # Exercise the existing vault boundary with the real SDK output.
    note = documents.store.extracted_markdown(text, output, 'assets/revision')
    assert '[Public reference](https://example.invalid/guide)' in note
    for label in ('Root reference', 'Parent reference', 'Relative reference', 'Local reference'):
        assert '\\[' + label + '\\]\\(' in note, label
    print('HTML text/table retained; linked files and network untouched; vault links neutralized.')


if __name__ == '__main__':
    main()
