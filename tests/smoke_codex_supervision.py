"""Official Codex transport startup under supervision; no tool/model execution proof."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mission_process as processes
import mission_tool_clients as clients
import mission_worker as worker

def run(executable, docker, image):
    binary = clients.verify_binary('codex', executable)
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(3)
            length = int(self.headers.get('Content-Length', '0'))
            assert 0 < length <= worker.DATA_LIMIT and not requests
            body = json.loads(self.rfile.read(length))
            requests.append(body)
            item = dict(type='message', role='assistant', id='m1',
                        content=[dict(type='output_text', text='Local startup fixture done.')])
            events = [dict(type='response.created', response={'id': '1'}),
                      dict(type='response.output_item.done', item=item),
                      dict(type='response.completed', response=dict(id='1', usage=dict(
                          input_tokens=0, input_tokens_details=None, output_tokens=0, output_tokens_details=None, total_tokens=0)))]
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for event in events:
                self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())

    events, handle = [], None
    operation = str(uuid.uuid4())
    mirror = Path('/tmp') / ('youngcrow-' + operation)
    with tempfile.TemporaryDirectory(prefix='yc-codex-agent-') as directory, HTTPServer(('127.0.0.1', 0), Handler) as server:
        root = Path(directory)
        source = root / 'source'
        source.mkdir()
        (source / 'clamp.py').write_bytes(b'def clamp(value, low, high):\n    return max(low, value)\n')
        packed = worker.pack(source, ['clamp.py'], root / 'input.tar')
        def persist(kind, payload):
            events.append(dict(kind=kind, payload=payload))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            plan = dict(contract='isolated-tools', schema_version=1, operation_id=operation,
                        deadline_ms=int(time.time() * 1000) + 60000, image_digest=image,
                        package_sha256=packed['sha256'], engine=worker.engine(docker))
            handle = worker.start(plan, root / 'input.tar', docker, persist)
            # Bundled gpt-5.5 metadata exposes direct tools and freeform patches.
            # Responses are fixed local data; no request reaches this model.
            profile = clients.build_profile('codex', executable, handle, root / 'control', dict(model='gpt-5.5', effort='low'))
            argv = profile['argv'][:-1]
            for override in ('model_provider="fixture"', 'model_providers.fixture.name="local deterministic fixture"',
                             'model_providers.fixture.base_url=' + json.dumps(f'http://127.0.0.1:{server.server_port}/v1'),
                             'model_providers.fixture.wire_api="responses"', 'model_providers.fixture.requires_openai_auth=false',
                             'model_providers.fixture.request_max_retries=0', 'model_providers.fixture.stream_max_retries=0'):
                argv += ['-c', override]
            result = processes.supervise(dict(argv=argv + ['-'], cwd=profile['cwd'], stdin=b'Follow the fixture instructions.\n',
                timeout_seconds=35, output_limit_bytes=worker.DATA_LIMIT, connection='authenticated',
                execution_contract='isolated-tools', environment_overrides=profile['environment_overrides']),
                on_started=lambda owner: persist('client_started', owner), stop_requested=lambda: False)
            assert result['reason'] == 'completed' and result['exit_code'] == 0 and result['tree_reaped'], result
            catalog = {item.get('name') for item in requests[0].get('tools', [])} if requests else set()
            assert {'exec_command', 'apply_patch'} <= catalog, sorted(str(name) for name in catalog)
            assert len(requests) == 1, len(requests)
            assert processes.owner_gone(result['owner'])
            result = dict(kind='native-codex-supervision-no-model', **binary, image_digest=image,
                          owner_kind=result['owner']['kind'], tools_exposed=sorted(catalog), tools_executed=[],
                          fixture_requests=len(requests), tree_reaped=True, model_calls=0, qualified=False)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            try:
                if handle is None:
                    handle = next((e['payload'] for e in reversed(events) if e['kind'] in ('ready', 'start_intent', 'created')), None)
                if handle:
                    worker.stop(handle, persist)
                    worker.remove(handle, persist)
            finally:
                if mirror.exists():
                    shutil.rmtree(mirror)
    result['worker_removed'] = True
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--docker', type=Path, required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.executable, args.docker, args.image)
    with args.report.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))
