"""Optional real-client discovery checks. No paid model calls or MCP connections.

The full Codex agent check captures one request on a loopback-only model fixture.
Use --discovery-only with one or both clients and --report NEW_PATH for metadata only.

python tests/smoke_clients.py --codex /path/to/codex --claude /path/to/claude
On Windows pass the actual .exe files, not npm's .ps1/.cmd launchers.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from test_setup import ROOT, SetupTests, write


MISSION_SKILLS = {'yc-personalizer', 'yc-config', 'yc-missao', 'yc-status'}
DISCOVERY_SECONDS = 25


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read_messages(stream, messages):
    try:
        for line in stream:
            message = json.loads(line)
            if not isinstance(message, dict):
                break
            messages.put(message)
    except (ValueError, OSError):
        pass
    finally:
        messages.put(None)


def next_message(messages, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('discovery_timeout')
    try:
        message = messages.get(timeout=remaining)
    except queue.Empty:
        raise TimeoutError('discovery_timeout') from None
    if message is None:
        raise ValueError('invalid_or_closed_discovery_stream')
    return message


def check_codex(executable, project, env, discovery_only=False):
    process = subprocess.Popen([executable, 'app-server', '--stdio'], cwd=project, env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
    messages = queue.Queue()

    reader = threading.Thread(target=read_messages, args=(process.stdout, messages), daemon=True)
    reader.start()

    def request(number, method, params):
        process.stdin.write(json.dumps({'id': number, 'method': method, 'params': params}) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + DISCOVERY_SECONDS
        while True:
            response = next_message(messages, deadline)
            if response.get('id') == number:
                assert 'error' not in response, response
                return response['result']

    try:
        request(1, 'initialize', {'clientInfo': {'name': 'youngcrow-smoke', 'version': '1.0'}})
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        if discovery_only:
            skills = request(2, 'skills/list', {'cwds': [str(project)], 'forceReload': True})
            found = {s['name'] for entry in skills['data'] for s in entry['skills']}
            if not MISSION_SKILLS <= found or any(entry['errors'] for entry in skills['data']):
                raise ValueError('mission_skills_not_discovered')
            return {'skills': sorted(found)}
        config = request(4, 'config/read', {'cwd': str(project), 'includeLayers': True})
        servers = config['config'].get('mcp_servers', {})
        assert set(servers) == {'n8n', 'cloudflare-api'}, config
        assert all(not s['enabled'] for s in servers.values())
        print('Codex: project MCP configuration recognized; example servers disabled.')
        skills = request(2, 'skills/list', {'cwds': [str(project)], 'forceReload': True})
        found = {s['name'] for entry in skills['data'] for s in entry['skills']}
        assert {'humanizer', 'humanizer-ptbr', 'integrate-from-docs', 'personalizer', 'ingest-source', 'retrieve-memory', 'govern-capabilities',
                'yc-personalizer', 'yc-config', 'yc-missao', 'yc-status'} <= found, found
        assert not any(entry['errors'] for entry in skills['data']), skills
        print('Codex: humanizer, humanizer-ptbr, integrate-from-docs, personalizer, ingest-source, retrieve-memory and govern-capabilities discovered by the real skill loader.')
        hooks = request(3, 'hooks/list', {'cwds': [str(project)]})
        assert not any(entry['errors'] for entry in hooks['data']), hooks
        found_hooks = [h for entry in hooks['data'] for h in entry['hooks']]
        assert {h['eventName'] for h in found_hooks} == {'postToolUse', 'stop', 'userPromptSubmit'}, hooks
        print('Codex: project UserPromptSubmit, PostToolUse and Stop hooks discovered; execution still requires trust.')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdin.close()
        process.stdout.close()


def check_claude_discovery(executable, project, env, discovery_only=False):
    # SDK initialization loads local metadata without sending a user/model turn.
    process = subprocess.Popen(
        [executable, '--print', '--input-format', 'stream-json', '--output-format', 'stream-json',
         '--verbose', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}'],
        cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
    messages = queue.Queue()

    reader = threading.Thread(target=read_messages, args=(process.stdout, messages), daemon=True)
    reader.start()
    try:
        process.stdin.write(json.dumps({'type': 'control_request', 'request_id': 'init',
                                        'request': {'subtype': 'initialize'}}) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + DISCOVERY_SECONDS
        while True:
            message = next_message(messages, deadline)
            if message.get('type') == 'control_response':
                response = message['response']
                if not isinstance(response, dict):
                    raise ValueError('invalid_discovery_envelope')
                assert response.get('subtype') == 'success', response
                data = response['response']
                if discovery_only:
                    found = {c['name'] for c in data['commands']}
                    if response.get('request_id') != 'init' or not MISSION_SKILLS <= found:
                        raise ValueError('mission_skills_not_discovered')
                    return {'skills': sorted(found)}
                assert any(c['name'] == 'integrate-from-docs' for c in data['commands']), data.keys()
                assert any(c['name'] == 'personalizer' for c in data['commands']), data.keys()
                assert any(c['name'] == 'ingest-source' for c in data['commands']), data.keys()
                assert any(c['name'] == 'retrieve-memory' for c in data['commands']), data.keys()
                assert any(c['name'] == 'govern-capabilities' for c in data['commands']), data.keys()
                assert {'yc-personalizer', 'yc-config', 'yc-missao', 'yc-status'} <= {c['name'] for c in data['commands']}
                assert any(a['name'] == 'integration-specialist' for a in data['agents']), data.keys()
                print('Claude: govern-capabilities, retrieve-memory, ingest-source, personalizer, integrate-from-docs and integration-specialist discovered by SDK initialization; no model turn.')
                break
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdin.close()
        process.stdout.close()


def check_codex_agent(executable, project, env):
    """Capture one request to a loopback-only model fixture; no paid model call."""
    requests = queue.Queue()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.put(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
            self.send_response(400)
            self.end_headers()

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    process = subprocess.Popen(
        [executable, 'exec', '--json', '--skip-git-repo-check', '--sandbox', 'read-only',
         '-c', 'model="local-fixture"', '-c', 'model_provider="fixture"',
         '-c', 'model_providers.fixture.name="Local fixture"',
         '-c', f'model_providers.fixture.base_url="http://127.0.0.1:{server.server_port}/v1"',
         '-c', 'model_providers.fixture.wire_api="responses"',
         '-c', 'model_providers.fixture.requires_openai_auth=false',
         'List the custom agent names; do not execute tools.'],
        cwd=project, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        body = json.loads(requests.get(timeout=30))
        assert 'integration-specialist' in json.dumps(body.get('tools', [])), 'Specialist missing from native tool catalog'
        print('Codex: integration-specialist exposed in native agent tool catalog (loopback fixture, no paid model).')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex')
    parser.add_argument('--claude')
    parser.add_argument('--discovery-only', action='store_true',
                        help='Load mission skill metadata in the selected clients; never send a model turn')
    parser.add_argument('--report', type=Path, help='New JSON receipt; required with --discovery-only')
    args = parser.parse_args(argv)
    selected = {name: str(Path(value).resolve()) for name in ('codex', 'claude')
                if (value := getattr(args, name))}
    if args.discovery_only:
        if not selected or not args.report:
            parser.error('--discovery-only requires at least one client executable and --report')
        if any(not Path(value).is_file() for value in selected.values()):
            parser.error('Use existing native executable files')
    elif len(selected) != 2 or args.report:
        parser.error('Full smoke requires both --codex and --claude; --report is discovery-only')
    receipt = dict(state='running', scope='native_skill_discovery',
                   started_at=datetime.now(timezone.utc).isoformat(), user_prompts_sent=0,
                   application_verified=False, clients={name: {'state': 'not_run'} for name in ('codex', 'claude')},
                   platform=sys.platform, probe_sha256=digest(__file__))
    # Reserve a new receipt before setup or native processes; never replace old evidence.
    output = args.report.open('x', encoding='utf-8') if args.discovery_only else None
    if output:
        json.dump(receipt, output); output.flush()
    test = SetupTests()
    try:
        test.setUp()
        client = 'both' if len(selected) == 2 else next(iter(selected))
        result = test.run_setup('--client', client, '--no-plugins', timeout=180)
        assert result.returncode == 0, result.stderr
        test.git('init', '-q', str(test.target))
        env = test.child_env.copy()
        # Native clients must never discover the real user's home or credentials.
        env.update(HOME=str(test.home), USERPROFILE=str(test.home),
                   CODEX_HOME=str(test.home / '.codex'), CLAUDE_CONFIG_DIR=str(test.home / '.claude'),
                   CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
        if os.name == 'nt':
            env.update(APPDATA=str(test.home / 'AppData/Roaming'), LOCALAPPDATA=str(test.home / 'AppData/Local'))
        write(test.home / '.codex/config.toml',
              '[projects.' + json.dumps(os.path.normcase(str(test.target))) + ']\ntrust_level = "trusted"\n')
        if args.discovery_only:
            receipt['harness_revision'] = test.git('-C', str(ROOT), 'rev-parse', 'HEAD').stdout.strip()
            for client, executable in selected.items():
                evidence = receipt['clients'][client]
                evidence['state'] = 'running'
                try:
                    evidence['executable_sha256'] = digest(executable)
                    evidence['version'] = subprocess.run([executable, '--version'], cwd=test.target,
                        env=env, capture_output=True, text=True, encoding='utf-8', check=True,
                        timeout=15).stdout.strip()
                    entry = '.agents/skills' if client == 'codex' else '.claude/skills'
                    paths = [f'{base}/{name}/SKILL.md' for base in ('skills', entry) for name in sorted(MISSION_SKILLS)]
                    hashes = {p: digest(test.target / p) for p in paths}
                    probe = check_codex if client == 'codex' else check_claude_discovery
                    evidence.update(probe(executable, test.target, env, discovery_only=True))
                    if any(digest(test.target / p) != h for p,h in hashes.items()):
                        raise ValueError('installed_skills_changed')
                    evidence.update(state='passed', skill_sha256=hashes)
                except (ValueError, OSError, AssertionError, KeyError, TypeError, subprocess.SubprocessError) as error:
                    evidence.update(state='failed', error=type(error).__name__)
                    raise
            receipt['state'] = 'passed'
        else:
            check_codex(str(Path(args.codex).resolve()), test.target, env)
            result = subprocess.run([str(Path(args.claude).resolve()), 'mcp', 'get', 'n8n'], cwd=test.target,
                                    env=env, capture_output=True, encoding='utf-8', check=True, timeout=25)
            assert 'n8n.SEU-DOMINIO.example' in result.stdout, result.stdout
            assert 'Pending approval' in result.stdout, result.stdout
            print('Claude: project MCP recognized and awaiting approval; no connection attempted.')
            check_claude_discovery(str(Path(args.claude).resolve()), test.target, env)
            check_codex_agent(str(Path(args.codex).resolve()), test.target, env)
    except (ValueError, OSError, AssertionError, KeyError, TypeError, subprocess.SubprocessError) as error:
        if not args.discovery_only:
            raise
        receipt.update(state='failed', error=type(error).__name__)
    finally:
        cleaned = test.doCleanups()
        if output:
            if not cleaned:
                receipt.update(state='failed', error='temporary_fixture_cleanup_failed')
            receipt['temporary_fixture_removed'] = cleaned
            receipt['ended_at'] = datetime.now(timezone.utc).isoformat()
            output.seek(0); output.truncate()
            json.dump(receipt, output, indent=2)
            output.write('\n'); output.close()
            print(json.dumps(receipt))
    return int(args.discovery_only and receipt['state'] != 'passed')


if __name__ == '__main__':
    sys.exit(main())
