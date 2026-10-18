"""Official Codex with deterministic local responses; no provider or subscription proof."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shlex
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

ORIGINAL = b'def clamp(value, low, high):\n    return max(low, value)\n'
FIXED = b'def clamp(value, low, high):\n    return min(high, max(low, value))\n'


def run(executable, docker, image):
    binary = clients.verify_binary('codex', executable)
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(3)
            length = int(self.headers.get('Content-Length', '0'))
            assert 0 < length <= worker.DATA_LIMIT and len(requests) < 3
            body = json.loads(self.rfile.read(length))
            requests.append(body)
            number = len(requests)
            if number == 1:
                code = ("import os; from pathlib import Path; assert os.getuid() == 1000; "
                        "assert Path.cwd() == Path(" + repr(str(mirror / 'cwd')) + "); "
                        "assert Path.cwd().resolve() == Path.cwd(); "
                        "assert not Path(" + repr(str(source)) + ").exists(); "
                        "Path('clamp.py').write_bytes(" + repr(FIXED) + "); print('worker-cwd-ok')")
                item = dict(type='function_call', call_id='c1', name='exec_command',
                            arguments=json.dumps(dict(cmd='python3 -c ' + shlex.quote(code), login=False, max_output_tokens=500)))
            elif number == 2:
                item = dict(type='custom_tool_call', call_id='c2', name='apply_patch',
                            input='*** Begin Patch\n*** Add File: probe.txt\n+native patch\n*** End Patch')
            else:
                item = dict(type='message', role='assistant', id='m1',
                            content=[dict(type='output_text', text='Local fixture done.')])
            events = [dict(type='response.created', response={'id': str(number)}),
                      dict(type='response.output_item.done', item=item),
                      dict(type='response.completed', response=dict(id=str(number), usage=dict(
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
        (source / 'clamp.py').write_bytes(ORIGINAL)
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
            # This metadata exposes direct tools; all responses come from the local fixture.
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
            catalog = {item.get('name') for item in requests[0]['tools']} if requests else set()
            assert {'exec_command', 'apply_patch'} <= catalog, sorted(str(name) for name in catalog)
            assert len(requests) == 3, len(requests)
            outputs = [item for request in requests[1:] for item in request['input'] if item.get('call_id') == 'c1' and item['type'] == 'function_call_output']
            assert any('worker-cwd-ok' in item['output'] and 'Process exited with code 0' in item['output'] for item in outputs), outputs
            artifact = worker.collect(handle, root / 'result', persist)
            assert (root / 'result/clamp.py').read_bytes() == FIXED
            assert (root / 'result/probe.txt').read_bytes() == b'native patch\n'
            assert (source / 'clamp.py').read_bytes() == ORIGINAL
            assert list((mirror / 'cwd').iterdir()) == [], 'Tool wrote into the host mirror'
            assert processes.owner_gone(result['owner'])
            result = dict(kind='native-codex-local-responses-no-model', **binary, image_digest=image,
                        tools_checked=['exec_command', 'apply_patch'], fixture_requests=len(requests),
                        tree_reaped=True, original_preserved=True, host_mirror_empty=True,
                        sandbox_mode=profile['configuration']['sandbox_mode'],
                        artifact=artifact, model_calls=0, qualified=False)
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
