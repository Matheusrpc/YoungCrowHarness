"""Opt-in native capability probe, with disposable data and no model turn.

--client codex|claude --executable ABS_PATH --root NEW_DISPOSABLE_PATH
The stdio server is a synthetic witness, never a provider integration.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from document_store import process_alive


def assess_native(evidence):
    if not evidence['completed']:
        return 'pending'
    return 'passed' if (
        evidence['allowed_calls'] == 1 and evidence['allowed_result']
        and evidence['denied_calls'] == 0 and evidence['denial_observed']
        and evidence['revoked_calls'] == 0 and evidence['revocation_observed']
        and evidence['restored_calls'] == 1 and evidence['vault_unchanged']
    ) else 'failed'


def serve(root, log):
    root, log = root.resolve(strict=True), log.resolve()
    if log.parent != root or log.exists():
        raise ValueError('Fixture log must be a new file directly inside the disposable root')
    pending = log.with_suffix('.pid.pending')
    with pending.open('x', encoding='ascii') as pidfile:
        pidfile.write(str(os.getpid()))
    try:
        # Publish complete bytes without replacing another server's ownership marker.
        os.link(pending, log.with_suffix('.pid'))
    finally:
        pending.unlink()
    # The fixture owns this process and can close itself even if a native parent leaves stdin open.
    def await_stop():
        while not log.with_suffix('.stop').exists():
            time.sleep(.05)
        os._exit(0)
    threading.Thread(target=await_stop, daemon=True).start()
    for line in sys.stdin:
        if len(line.encode('utf-8')) > 1024 * 1024:
            return 2
        message = json.loads(line)
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return 2
        if 'id' not in message:
            continue
        method, params = message.get('method'), message.get('params', {})
        result, error = None, None
        if method == 'initialize':
            result = dict(protocolVersion=params['protocolVersion'], capabilities={'tools': {}},
                          serverInfo={'name': 'youngcrow-synthetic', 'version': '1'})
        elif method == 'tools/list':
            result = {'tools': [dict(name=name, description='Synthetic counter only',
                                   inputSchema={'type': 'object', 'properties': {},
                                                'additionalProperties': False})
                                for name in ('yc_read', 'yc_write')]}
        elif method == 'tools/call':
            if params.get('name') not in ('yc_read', 'yc_write') or params.get('arguments', {}) != {}:
                error = {'code': -32602, 'message': 'Unknown tool or invalid arguments'}
            else:
                with log.open('a', encoding='utf-8') as output:
                    output.write(json.dumps({'tool': params['name'], 'id': message['id']}) + '\n')
                result = {'content': [{'type': 'text', 'text': 'synthetic-ok'}], 'isError': False}
        elif method == 'ping':
            result = {}
        else:
            error = {'code': -32601, 'message': 'Unknown method'}
        print(json.dumps({'jsonrpc': '2.0', 'id': message['id'],
                          **({'error': error} if error else {'result': result})}), flush=True)
    return 0


class NativeRPC:
    def __init__(self, executable, project, env):
        self.process = subprocess.Popen([str(executable), 'app-server', '--stdio'],
                                        cwd=project, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding='utf-8')
        self.messages, self.number = queue.Queue(), 0
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def read(self):
        for line in self.process.stdout:
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                self.messages.put({'transport_error': True})
        self.messages.put({'transport_error': True})

    def request(self, method, params):
        self.number += 1
        self.process.stdin.write(json.dumps({'id': self.number, 'method': method, 'params': params}) + '\n')
        self.process.stdin.flush()
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            message = self.messages.get(timeout=max(.01, deadline - time.monotonic()))
            if message.get('transport_error'):
                raise RuntimeError('native_transport_closed')
            if message.get('id') == self.number:
                return message
        raise TimeoutError('native_timeout')

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        self.process.stdout.close()
        return self.process.poll() is not None


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding='utf-8')


def count(log, tool):
    return sum(json.loads(line)['tool'] == tool for line in log.read_text().splitlines()) if log.exists() else 0


def stop_fixture(log):
    log.with_suffix('.stop').touch()
    pidfile = log.with_suffix('.pid')
    publishing = log.with_suffix('.pid.pending').exists()
    if not pidfile.exists():
        return int(publishing)  # An unfinished ownership record cannot confirm cleanup.
    pid = int(pidfile.read_text())
    deadline = time.monotonic() + 5
    while process_alive(pid) and time.monotonic() < deadline:
        time.sleep(.05)
    return int(process_alive(pid))


class NativeCleanupError(RuntimeError):
    def __init__(self, alive):
        super().__init__('native_process_cleanup_incomplete')
        self.processes_alive = alive


def denied(response):
    # A transport failure or authentication error is not an enforcement proof.
    error = response.get('error', {})
    message = str(error.get('message', '')).lower()
    return any(term in message for term in ('unknown tool', 'tool not found', 'not allowed',
                                            'disabled', 'unknown mcp server', 'not available'))


def synthetic_result(response):
    result = response.get('result', {})
    return not result.get('isError') and any(c.get('text') == 'synthetic-ok'
                                           for c in result.get('content', []))


def codex_phase(executable, project, root, env, phase, enabled):
    log = root / (phase + '.jsonl')
    config = ('[mcp_servers.yc]\ncommand = ' + json.dumps(sys.executable) + '\nargs = '
              + json.dumps(['-B', str(Path(__file__).resolve()), '--serve-mcp', '--root', str(root),
                            '--log', str(log)]) + '\nenabled = ' + str(enabled).lower()
              + '\nenabled_tools = ["yc_read"]\ndisabled_tools = ["yc_write"]\n')
    write(project / '.codex/config.toml', config)
    rpc = NativeRPC(executable, project, env)
    responses = {}
    try:
        initialized = rpc.request('initialize', {'clientInfo': {'name': 'youngcrow-capability-proof', 'version': '1'}})
        if 'error' in initialized:
            raise RuntimeError('native_initialize_failed')
        rpc.process.stdin.write('{"method":"initialized"}\n')
        rpc.process.stdin.flush()
        started = rpc.request('thread/start', {'cwd': str(project), 'ephemeral': True,
                                             'sandbox': 'read-only', 'approvalPolicy': 'on-request'})
        if 'error' in started:
            raise RuntimeError('native_thread_unavailable')
        thread = started['result']['thread']['id']
        for tool in (('yc_read', 'yc_write') if phase == 'enabled' else ('yc_read',)):
            responses[tool] = rpc.request('mcpServer/tool/call',
                                         {'threadId': thread, 'server': 'yc', 'tool': tool, 'arguments': {}})
        # Synthetic replies contain no user data. Keep diagnostic protocol output local.
        write(root / (phase + '-responses.json'), json.dumps(responses, indent=2))
    finally:
        try:
            rpc.close()
        finally:
            alive = stop_fixture(log) + int(rpc.process.poll() is None)
            if alive:
                raise NativeCleanupError(alive)
    return responses, log, True


def probe(client, executable, root):
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError('Select an absolute native executable path')
    if not root.is_absolute() or root.exists():
        raise ValueError('Use a new absolute disposable directory')
    root.mkdir(parents=True)
    home, project = root / 'home', root / 'project'
    home.mkdir()
    project.mkdir()
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT'}}
    env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / '.codex'),
               CLAUDE_CONFIG_DIR=str(home / '.claude'), APPDATA=str(home / 'AppData/Roaming'),
               LOCALAPPDATA=str(home / 'AppData/Local'), TMP=str(root), TEMP=str(root),
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
    version = subprocess.run([str(executable), '--version'], cwd=project, env=env,
                             capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    evidence = dict(client=client, version=version, started_at=datetime.now(timezone.utc).isoformat(),
                    completed=False, allowed_calls=0, denied_calls=0, allowed_result=False,
                    denial_observed=False, revoked_calls=0, revocation_observed=False,
                    restored_calls=0, vault_unchanged=True, reason='native_dispatch_unavailable',
                    native_processes_alive=0, model_turns=0)
    # The installed Claude SDK exposes metadata; no authenticated model dispatch is assumed.
    if client == 'claude':
        return evidence
    write(home / '.codex/config.toml', '[projects.' + json.dumps(os.path.normcase(str(project)))
          + ']\ntrust_level = "trusted"\n')
    vault = project / 'vault/previous-run.md'
    write(vault, 'Synthetic historical evidence. No authority.\n')
    before = hashlib.sha256(vault.read_bytes()).hexdigest()
    try:
        for phase, enabled in (('enabled', True), ('revoked', False), ('restored', True)):
            responses, log, stopped = codex_phase(executable, project, root, env, phase, enabled)
            evidence['native_processes_alive'] += int(not stopped)
            response = responses['yc_read']
            if phase == 'enabled':
                evidence.update(allowed_calls=count(log, 'yc_read'), allowed_result=synthetic_result(response),
                                denied_calls=count(log, 'yc_write'), denial_observed=denied(responses['yc_write']))
                if not evidence['allowed_result']:
                    return evidence
            elif phase == 'revoked':
                evidence.update(revoked_calls=count(log, 'yc_read'), revocation_observed=denied(response))
            else:
                evidence['restored_calls'] = count(log, 'yc_read') if synthetic_result(response) else 0
        evidence.update(completed=True, reason='native_dispatch_observed')
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError, queue.Empty, subprocess.TimeoutExpired) as error:
        evidence['reason'] = 'native_probe_incomplete:' + type(error).__name__
        evidence['native_processes_alive'] = getattr(error, 'processes_alive', 0)
    finally:
        evidence['vault_unchanged'] = before == hashlib.sha256(vault.read_bytes()).hexdigest()
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve-mcp', action='store_true')
    parser.add_argument('--client', choices=('codex', 'claude'))
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    if args.serve_mcp:
        if not args.log:
            parser.error('--log required')
        return serve(args.root, args.log)
    if not args.client or not args.executable:
        parser.error('--client and --executable required')
    evidence = probe(args.client, args.executable, args.root)
    evidence['status'] = assess_native(evidence)
    write(args.root / 'evidence.json', json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
    return {'passed': 0, 'failed': 1, 'pending': 2}[evidence['status']]


if __name__ == '__main__':
    sys.exit(main())
