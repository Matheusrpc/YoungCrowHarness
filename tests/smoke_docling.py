"""Opt-in proof with the real SDK; never part of unittest discovery."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import documents

PHRASE = 'Young Crow keeps source evidence.'


def interruption_child(root, run):
    if not run.resolve().is_relative_to(root / '.runtime/docling-smoke'):
        raise ValueError('Controlled smoke directory required.')
    def convert_then_pause(source, output, runtime, profile):
        result = documents.run_worker(source, output, runtime, profile)
        if result['state'] != 'ready':
            return result
        (run / 'converted.json').write_text(json.dumps({'state': result['state']}))
        time.sleep(1800)  # Parent terminates this test process before note activation.
        return result
    result = documents.ingest(root, run / 'interrupt.html', convert=convert_then_pause)
    print(json.dumps(result))
    return 1


def interruption_smoke(root, run):
    run.mkdir(parents=True)
    source = run / 'interrupt.html'
    source.write_text(f'<html><body><p>{PHRASE}</p><p>Controlled run {run.name}</p></body></html>')
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--root', str(root),
                              '--interrupt-child', str(run)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 1800
        while not (run / 'converted.json').exists():
            if child.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Controlled real conversion did not reach the interruption point.')
            time.sleep(0.2)
        child.terminate()
        child.wait(timeout=30)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
        child.communicate()
    lock = documents.store.lock_status(root)
    assert lock['state'] == 'locked' and not lock['owner_alive']
    documents.store.recover_lock(root, lock['token'])
    record = next(r for r in documents.store.source_records(root) if r['locator'] == source.as_uri())
    pending = documents.status(root, record['source_id'])[0]['latest_attempt']
    assert pending['state'] == 'pending' and pending['note_path'] is None
    resumed = documents.ingest(root, source, source_id=record['source_id'])
    import vault
    report = dict(conversion_before_interruption='ready', state_after_recovery=pending['state'],
                  state_after_retry=resumed['state'], same_source_id=resumed['source_id'] == record['source_id'],
                  phrase_found=bool(resumed['note_path']) and PHRASE in (root / resumed['note_path']).read_text(encoding='utf-8'),
                  vault=vault.check(root))
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['state_after_retry'] == 'ready' and report['phrase_found'] and not report['vault']['issues'] else 1


def fixtures(directory, runtime):
    directory.mkdir(parents=True)
    (directory / 'sample.html').write_text(f'<html><body><h1>{PHRASE}</h1><p>Controlled local fixture.</p>'
        '<img src="http://127.0.0.1:9/must-not-fetch.png"></body></html>', encoding='utf-8')
    stream = f'BT /F1 18 Tf 60 720 Td ({PHRASE}) Tj ET'.encode()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    data, offsets = b'%PDF-1.4\n', [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    (directory / 'sample.pdf').write_bytes(data)
    with zipfile.ZipFile(directory / 'sample.docx', 'w') as docx:
        docx.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        docx.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        docx.writestr('word/document.xml', '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>{PHRASE}</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
    drawing = ('from PIL import Image,ImageDraw,ImageFont; import sys; '
               'im=Image.new("RGB",(1240,1754),"white"); d=ImageDraw.Draw(im); f=ImageFont.load_default(size=30); '
               'd.text((70,100),sys.argv[2],font=f,fill="black"); '
               'd.text((70,155),"Controlled local document for conversion testing.",font=f,fill="black"); '
               'im.save(sys.argv[1])')
    subprocess.run([str(documents.runtime_python(runtime)), '-c', drawing, str(directory / 'sample.png'), PHRASE],
                   check=True, timeout=30, env=documents.worker_environment(runtime.parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=['documents'], default='documents')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--ingest', action='store_true', help='Verify storage and resumption through the public ingestion API.')
    parser.add_argument('--interrupt', action='store_true', help='Kill a controlled run after real conversion, recover and resume.')
    parser.add_argument('--interrupt-child', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.interrupt_child:
        return interruption_child(root, args.interrupt_child)
    diagnostic = documents.doctor(root)
    if diagnostic['state'] != 'ready':
        print(json.dumps(diagnostic))
        return 1
    run = root / '.runtime/docling-smoke' / str(uuid.uuid4())
    if args.interrupt:
        return interruption_smoke(root, run)
    runtime = root / documents.BASE / 'venv'
    fixtures(run / 'inputs', runtime)
    results = []
    for source in sorted((run / 'inputs').iterdir()):
        output = run / source.suffix[1:]
        started = time.monotonic()
        original_digest = documents.store.file_digest(source)
        result = documents.ingest(root, source) if args.ingest else documents.run_worker(source, output, runtime, args.profile)
        content = root / result['note_path'] if args.ingest and result.get('note_path') else output / 'content.md'
        found = content.is_file() and PHRASE.lower() in re.sub(r'\s+', ' ', content.read_text(encoding='utf-8')).lower()
        item = dict(format=source.suffix, state=result['state'], phrase_found=found,
                            seconds=round(time.monotonic() - started, 2), warnings=result.get('warnings', []),
                            coverage=result.get('coverage', {}), output=content.relative_to(root).as_posix())
        if args.ingest:
            repeated = documents.ingest(root, source)
            item.update(original_unchanged=documents.store.file_digest(source) == original_digest,
                        source_id=result['source_id'], revision=result['revision'],
                        resumed=repeated['state'] == 'ready' and repeated['note_path'] == result['note_path'])
        results.append(item)
    report = dict(doctor=diagnostic, results=results)
    if args.ingest:
        import vault
        report['vault'] = vault.check(root)
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if (all(r['state'] == 'ready' and r['phrase_found'] and r.get('resumed', True)
                    and r.get('original_unchanged', True) for r in results)
                 and not report.get('vault', {}).get('issues')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
