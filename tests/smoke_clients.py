"""Optional real-client discovery checks. No model calls or MCP connections.

python tests/smoke_clients.py --codex /path/to/codex --claude /path/to/claude
On Windows pass the actual .exe files, not npm's .ps1/.cmd launchers.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

from test_setup import SetupTests, write


def check_codex(executable, project, env):
    process = subprocess.Popen([executable, 'app-server', '--stdio'], cwd=project, env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
    messages = queue.Queue()

    def read_messages():
        for line in process.stdout:
            messages.put(json.loads(line))

    reader = threading.Thread(target=read_messages, daemon=True)
    reader.start()

    def request(number, method, params):
        process.stdin.write(json.dumps({'id': number, 'method': method, 'params': params}) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + 20
        while True:
            response = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if response.get('id') == number:
                assert 'error' not in response, response
                return response['result']

    try:
        request(1, 'initialize', {'clientInfo': {'name': 'youngcrow-smoke', 'version': '1.0'}})
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        config = request(4, 'config/read', {'cwd': str(project), 'includeLayers': True})
        servers = config['config'].get('mcp_servers', {})
        assert set(servers) == {'n8n', 'cloudflare-api'}, config
        assert all(not s['enabled'] for s in servers.values())
        print('Codex: project MCP configuration recognized; example servers disabled.')
        skills = request(2, 'skills/list', {'cwds': [str(project)], 'forceReload': True})
        found = {s['name'] for entry in skills['data'] for s in entry['skills']}
        assert {'humanizer', 'humanizer-ptbr'} <= found, found
        assert not any(entry['errors'] for entry in skills['data']), skills
        print('Codex: humanizer and humanizer-ptbr discovered by the real skill loader.')
        hooks = request(3, 'hooks/list', {'cwds': [str(project)]})
        assert not any(entry['errors'] for entry in hooks['data']), hooks
        found_hooks = [h for entry in hooks['data'] for h in entry['hooks']]
        assert {h['eventName'] for h in found_hooks} == {'postToolUse', 'stop'}, hooks
        print('Codex: project PostToolUse and Stop hooks discovered; execution still requires trust.')
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', required=True)
    parser.add_argument('--claude', required=True)
    args = parser.parse_args()
    test = SetupTests()
    test.setUp()
    try:
        result = test.run_setup('--client', 'both', '--no-plugins')
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
        check_codex(str(Path(args.codex).resolve()), test.target, env)
        result = subprocess.run([str(Path(args.claude).resolve()), 'mcp', 'get', 'n8n'], cwd=test.target,
                                env=env, capture_output=True, encoding='utf-8', check=True, timeout=25)
        assert 'n8n.SEU-DOMINIO.example' in result.stdout, result.stdout
        assert 'Pending approval' in result.stdout, result.stdout
        print('Claude: project MCP recognized and awaiting approval; no connection attempted.')
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
