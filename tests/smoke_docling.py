"""Opt-in proof with the real SDK; never part of unittest discovery."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
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


def review_smoke(root, run):
    """Real SDK with a disposable consumer; only the isolated converter is reused."""
    import vault
    runtime = root / documents.BASE / 'venv'
    fixtures(run / 'inputs', runtime)
    consumer = run / 'consumer'
    consumer.mkdir()
    env = {k: v for k, v in os.environ.items() if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATHEXT')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    def git(*args):
        return subprocess.run(['git', '-C', str(consumer), *args], env=env, check=True, capture_output=True, timeout=30)
    git('init', '-q')
    for arguments in (['init', '--mode', 'existing', '--run', 'review-proof'],
                      ['feature', '--slug', 'source-proof', '--run', 'first']):
        subprocess.run([sys.executable, str(ROOT / 'scripts/personalize.py'), *arguments], cwd=consumer,
                       check=True, capture_output=True, timeout=30)
    documents.store.prepare_storage(consumer)
    # This records the real converter configuration used by the test adapter;
    # consumers still install their own runtime through the normal setup command.
    shutil.copyfile(root / documents.BASE / 'environment.json', consumer / documents.BASE / 'environment.json')
    source = run / 'inputs/private-customer-contract.pdf'
    (run / 'inputs/sample.pdf').rename(source)
    def real_converter(source, output, unused_runtime, profile):
        return documents.run_worker(source, output, runtime, profile)
    receipt = documents.ingest(consumer, source, convert=real_converter)
    assert receipt['state'] == 'ready'
    feature = consumer / 'vault/features/source-proof/index.md'
    feature_id = vault.metadata(feature.read_text(encoding='utf-8'))[0]['id']
    decision_id = str(uuid.uuid4())
    decision = 'vault/decisions/source-proof.md'
    documents.store.atomic_write(consumer, decision, documents.store.markdown(decision_id, 'decision',
        'Source proof', 'index.md', '# Source proof\n\nUse reviewed evidence for this controlled feature.\n'))
    documents.store.append_link(consumer, 'vault/decisions/index.md', '[Source proof](source-proof.md)')
    def command(*arguments):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/documents.py'), '--root', str(consumer),
                                  *arguments, '--json'], check=True, capture_output=True, timeout=30)
        return json.loads(result.stdout)
    before = feature.read_bytes()
    for target, relation in ((feature_id, 'supports'), (decision_id, 'used-in')):
        command('relate', '--source-id', receipt['source_id'], '--revision', receipt['revision'],
                '--target-id', target, '--relation', relation, '--evidence', PHRASE)
    assert feature.read_bytes() == before
    review = command('prepare-review', '--source-id', receipt['source_id'], '--revision', receipt['revision'])
    reviewed_note = Path(review['directory']) / 'index.md'
    with reviewed_note.open('a', encoding='utf-8') as output:
        output.write('\nPublic provenance: controlled fixture generated by the harness smoke test.\n')
    reviewed = command('review-status', '--review-id', review['review_id'])
    published = command('promote', '--review-id', review['review_id'], '--approved-digest', reviewed['digest'])
    for note in (feature.relative_to(consumer), Path(decision)):
        target = Path(os.path.relpath(published['note_path'], note.parent)).as_posix()
        documents.store.append_link(consumer, note, f'[Reviewed evidence]({target})')
    local_check = vault.check(consumer)
    assert not local_check['issues']
    assert git('diff', '--cached', '--name-only').stdout == b''  # Commands never stage material.
    git('add', '--', 'vault', '.gitignore')
    tracked = git('ls-files', '-z').stdout
    assert b'vault/local/' not in tracked and b'.operacao-local/' not in tracked
    assert b'private-customer-contract' not in git('diff', '--cached').stdout
    git('-c', 'user.name=Matheus Couto', '-c', 'user.email=88406767+Matheusrpc@users.noreply.github.com',
        'commit', '-qm', 'test: reviewed source fixture')
    clone = run / 'clone'
    subprocess.run(['git', 'clone', '-q', '--no-hardlinks', str(consumer), str(clone)],
                   env=env, check=True, capture_output=True, timeout=30)
    clone_check = vault.check(clone)
    report = dict(converter='docling ' + documents.VERSION, source_format='PDF', source_state=receipt['state'],
                  relations=['supports feature', 'used-in decision'], shared_feature_preserved_before_publication=True,
                  public_copy_state=published['state'], private_files_tracked=False,
                  private_filename_in_shared_diff=False, local_vault=local_check, cloned_vault=clone_check)
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if not clone_check['issues'] else 1


def url_smoke(root):
    import vault
    source = 'https://raw.githubusercontent.com/mozilla/pdf.js/4c9b65f0e13fd290c326b38cb97436fa50b930f5/test/pdfs/basicapi.pdf'
    started = time.monotonic()
    result = documents.ingest(root, source)
    note = root / result['note_path'] if result.get('note_path') else None
    found = bool(note and 'Table Of Content' in re.sub(r'\s+', ' ', note.read_text(encoding='utf-8')))
    report = dict(source=source, converter='docling ' + documents.VERSION, state=result['state'],
                  phrase_found=found, warnings=result['warnings'], coverage=result['coverage'],
                  seconds=round(time.monotonic() - started, 2), vault=vault.check(root))
    run = root / '.runtime' / ('url-' + uuid.uuid4().hex[:12])
    run.mkdir(parents=True)
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if result['state'] == 'ready' and found and not report['vault']['issues'] else 1


def media_smoke(root, manifest_path):
    import vault
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    run = root / '.runtime' / ('media-' + uuid.uuid4().hex[:12])
    run.mkdir(parents=True)
    results = []
    for kind in ('audio', 'video', 'video_without_audio'):
        source = (manifest_path.parent / manifest[kind]).resolve(strict=True)
        started = time.monotonic()
        result = documents.ingest(root, source)
        note = root / result['note_path'] if result.get('note_path') else None
        text = re.sub(r'[^a-z0-9]+', ' ', note.read_text(encoding='utf-8').lower()) if note else ''
        found = re.sub(r'[^a-z0-9]+', ' ', manifest['phrase'].lower()).strip() in text
        results.append(dict(kind=kind, state=result['state'], phrase_found=found,
                            warnings=result['warnings'], coverage=result['coverage'],
                            seconds=round(time.monotonic() - started, 2)))
    # Exercise the real video pipeline's partial result under a tiny explicit
    # test budget. Production conversion still gets its full 1,800 seconds.
    runtime = documents.profile_base(root, 'media') / 'venv'
    timeout_output = run / 'partial'
    timeout_output.mkdir()
    source = (manifest_path.parent / manifest['video']).resolve()
    env = documents.worker_environment(runtime.parent)
    request = dict(source=str(source), output=str(timeout_output), models=str(runtime.parent / 'models'),
                   profile='media', media=documents.probe_media(source, env))
    request_path = run / 'request.json'
    request_path.write_text(json.dumps(request), encoding='utf-8')
    driver = run / 'partial.py'
    driver.write_text('import json,sys\nfrom pathlib import Path\nfrom contextlib import redirect_stdout\n'
        f'sys.path.insert(0, {str(ROOT / "scripts")!r})\nimport docling_worker\n'
        'with redirect_stdout(sys.stderr):\n result=docling_worker.convert(json.loads(Path(sys.argv[1]).read_text()),document_timeout=0.001)\n'
        'print(json.dumps(result))\n', encoding='utf-8')
    timed = documents.run_process([str(documents.runtime_python(runtime)), str(driver), str(request_path)],
                                    timeout=1800, env=env)
    (run / 'partial-stderr.log').write_bytes(timed.stderr)
    partial = json.loads(timed.stdout) if timed.returncode == 0 else {'state': 'failed'}
    assert partial.get('converter', {}).get('options', {}).get('timeout') == 0.001
    report = dict(converter='docling ' + documents.VERSION, model='Whisper Base native CPU',
                  fixture=manifest.get('provenance', 'operator-provided speech recording'),
                  results=results, real_pipeline_timeout=partial, vault=vault.check(root))
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    good = all(item['state'] == 'ready' and item['phrase_found'] and item['coverage'].get('transcript_intervals')
               for item in results[:2])
    good = good and bool(results[1]['coverage'].get('sampled_frames'))
    good = good and results[2]['state'] == 'partial' and 'audio_track_absent' in results[2]['warnings']
    return 0 if good and partial['state'] == 'partial' and not report['vault']['issues'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=['documents', 'media'], default='documents')
    parser.add_argument('--media-manifest', type=Path, help='Local JSON with audio, video, video_without_audio and expected phrase.')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--ingest', action='store_true', help='Verify storage and resumption through the public ingestion API.')
    parser.add_argument('--interrupt', action='store_true', help='Kill a controlled run after real conversion, recover and resume.')
    parser.add_argument('--interrupt-child', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--review', action='store_true', help='Verify real PDF, feature, decision, reviewed copy and shared clone.')
    parser.add_argument('--url', action='store_true', help='Acquire the public PDF.js fixture and convert it with the real SDK.')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.interrupt_child:
        return interruption_child(root, args.interrupt_child)
    diagnostic = documents.doctor(root, args.profile)
    if diagnostic['state'] != 'ready':
        print(json.dumps(diagnostic))
        return 1
    if args.profile == 'media':
        if args.media_manifest is None:
            parser.error('--profile media requires --media-manifest')
        return media_smoke(root, args.media_manifest.resolve(strict=True))
    if args.review:
        return review_smoke(root, root / '.runtime' / ('review-' + uuid.uuid4().hex[:12]))
    if args.url:
        return url_smoke(root)
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
