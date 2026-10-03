"""Local provider fixture: only a synthetic image, no account or real model."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import struct
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mission_clients
import mission_process

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--executable', required=True, type=Path)
parser.add_argument('--strict-config', action='store_true')
args = parser.parse_args()
if not args.executable.is_absolute():
    parser.error('--executable must be an absolute native binary path')
exe = args.executable
binary_sha256 = mission_clients.hash_executable(exe)
bodies = []
image_path = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        bodies.append(body)
        if len(bodies) > 1:
            self.send_response(400)
            self.end_headers()
            return
        item = dict(type='function_call', name='view_image', call_id='fixture-call',
                    id='fixture-item', arguments=json.dumps({'path': str(image_path)}))
        events = [dict(type='response.created', response={'id': 'fixture-response'}),
                  dict(type='response.output_item.done', output_index=0, item=item),
                  dict(type='response.completed', response={'id': 'fixture-response',
                       'status': 'completed', 'output': [item],
                       'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}})]
        data = ''.join('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n'
                       for event in events).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = HTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with tempfile.TemporaryDirectory(prefix="yc-image-boundary-") as folder:
        root = Path(folder).resolve()
        (root / '.codex').mkdir()
        image_path = root / 'sentinel.png'
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
        image_path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
                               + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b''))
        work = root / 'empty'
        work.mkdir()
        argv = [str(exe), 'exec', '--json', '--ephemeral', '--ignore-user-config',
                '--sandbox', 'read-only', '--skip-git-repo-check', '--color', 'never', '--model', 'fixture',
                '-c', 'approval_policy="never"', '-c', 'web_search="disabled"', '-c', 'mcp_servers={}',
                '-c', 'tools.view_image=false', '-c', 'project_root_markers=[]',
                '-c', 'project_doc_max_bytes=0', '-c', 'model_provider="fixture"',
                '-c', 'model_providers.fixture.name="Fixture"',
                '-c', f'model_providers.fixture.base_url="http://127.0.0.1:{server.server_port}/v1"',
                '-c', 'model_providers.fixture.wire_api="responses"',
                '-c', 'model_providers.fixture.requires_openai_auth=false',
                '-c', 'model_providers.fixture.request_max_retries=0',
                '-c', 'model_providers.fixture.stream_max_retries=0']
        for feature in mission_clients.CODEX_DISABLED:
            argv += ['--disable', feature]
        if args.strict_config:
            argv += ['--strict-config']
        argv += ['-']
        with patch.dict(os.environ, {'HOME': str(root), 'USERPROFILE': str(root), 'CODEX_HOME': str(root / '.codex')}):
            result = mission_process.supervise(dict(argv=argv, cwd=str(work), stdin=b'Return OK, no tools.',
                         timeout_seconds=30, output_limit_bytes=1000000, client='codex',
                         connection='authenticated', credential_env=None, merge_stderr=True),
                         on_started=lambda _: None, stop_requested=lambda: False)
        image_sent = any('data:image/' in json.dumps(b.get('input')) for b in bodies[1:])
        # A refused image alone is insufficient to certify the whole native profile.
        print(json.dumps(dict(profile='failed' if image_sent else 'not_proven',
             executable_sha256=binary_sha256, strict_config=args.strict_config, model_calls=0,
             reason=result['reason'], exit_code=result['exit_code'],
             tree_reaped=result['tree_reaped'], requests=len(bodies),
             tools=[t.get('name', t.get('type')) for t in bodies[0].get('tools', [])] if bodies else None,
             image_sent=image_sent,
             unknown_view_image_setting=b'tools.view_image' in result['stdout']
                 and (b'unknown configuration field' in result['stdout'] or b'is ignored' in result['stdout']))))
finally:
    server.shutdown()
    server.server_close()
    thread.join()

raise SystemExit(1 if image_sent else 2)
