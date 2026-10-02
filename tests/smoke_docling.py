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
    args = parser.parse_args()
    root = args.root.resolve()
    diagnostic = documents.doctor(root)
    if diagnostic['state'] != 'ready':
        print(json.dumps(diagnostic))
        return 1
    run = root / '.runtime/docling-smoke' / str(uuid.uuid4())
    runtime = root / documents.BASE / 'venv'
    fixtures(run / 'inputs', runtime)
    results = []
    for source in sorted((run / 'inputs').iterdir()):
        output = run / source.suffix[1:]
        started = time.monotonic()
        result = documents.run_worker(source, output, runtime, args.profile)
        content = output / 'content.md'
        found = content.is_file() and PHRASE.lower() in re.sub(r'\s+', ' ', content.read_text(encoding='utf-8')).lower()
        results.append(dict(format=source.suffix, state=result['state'], phrase_found=found,
                            seconds=round(time.monotonic() - started, 2), warnings=result.get('warnings', []),
                            coverage=result.get('coverage', {}), output=output.relative_to(root).as_posix()))
    report = dict(doctor=diagnostic, results=results)
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if all(r['state'] == 'ready' and r['phrase_found'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
