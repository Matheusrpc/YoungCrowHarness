"""Pinned Graphify bridge; executed only inside the optional project runtime."""
from contextlib import redirect_stdout
from importlib import metadata
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys
import uuid

VERSION = '0.9.73'


def parse_query(text):
    if len(text.encode('utf-8')) > 2 * 1024 * 1024:
        raise ValueError('output_limit')
    sources = []
    for line in text.splitlines():
        if not line.startswith('NODE '):
            continue
        match = re.search(r' \[src=(notes/[0-9a-f]{32}\.md) loc=L1 community=[^\[\]\r\n]*\]$', line)
        if not match:
            raise ValueError('invalid_query_output')
        if match[1] not in sources:
            sources.append(match[1])
    return sources


def build(snap):
    from graphify.build import build_from_json
    from graphify.validate import validate_extraction
    from networkx.readwrite import json_graph
    ids = {n['id']: 'notes_' + uuid.UUID(n['id']).hex + '_note' for n in snap['notes']}
    sources = {n['id']: n['source_file'] for n in snap['notes']}
    extraction = dict(nodes=[dict(id=ids[n['id']], label=n['title'], file_type='document',
                                  source_file=n['source_file'], source_location='L1',
                                  youngcrow_id=n['id'], youngcrow_revision=n['revision']) for n in snap['notes']],
                      edges=[dict(source=ids[r['source_id']], target=ids[r['target_id']], relation='references',
                                  confidence='EXTRACTED', confidence_score=1.0, weight=1.0,
                                  source_file=sources[r['source_id']], source_location=None) for r in snap['relations']],
                      hyperedges=[], input_tokens=0, output_tokens=0)
    if validate_extraction(extraction):
        raise ValueError('invalid_extraction')
    graph = build_from_json(extraction, directed=True)
    graph.graph.update(project_id=snap['project_id'], fingerprint=snap['fingerprint'])
    return json_graph.node_link_data(graph, edges='links')


def handle(request):
    version = metadata.version('graphifyy')
    if version != VERSION:
        return dict(state='unsupported', code='runtime_version_mismatch', version=version)
    result = dict(state='ready', version=version)
    if request['action'] == 'doctor':
        return dict(result, python=sys.version.split()[0],
                    packages={d.metadata['Name']: d.version for d in metadata.distributions()})
    if request['action'] == 'build':
        return dict(result, graph=build(request['snapshot']))
    if request['action'] != 'query':
        raise ValueError('unknown_action')
    from graphify.cli import dispatch_command
    sys.argv = ['graphify', 'query', request['question'], '--graph', request['graph_path'], '--budget', '1000']
    output = StringIO()
    with redirect_stdout(output):
        dispatch_command('query')
    return dict(result, source_files=parse_query(output.getvalue()))


def main():
    try:
        request_path = Path(sys.argv[1]).resolve(strict=True)
        request = json.loads(request_path.read_text(encoding='utf-8'))
        os.chdir(request_path.parent)
        # Vendor diagnostics are not our JSON protocol and never reach public output.
        with redirect_stdout(StringIO()):
            result = handle(request)
    except metadata.PackageNotFoundError:
        result = dict(state='pending', code='package_missing')
    except (Exception, SystemExit):
        result = dict(state='failed', code='vendor_failed')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
