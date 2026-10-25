"""Optional proof that the youngcrow plugin installs and runs in the real Claude Code and Codex clients.

    python tests/smoke_plugin.py --claude /path/to/claude --codex /path/to/codex [--json]

It builds the wheel, runs `youngcrow init --client both` in a new project, adds this repository as a
local marketplace in both clients, installs `youngcrow@youngcrow`, runs the hook of each installed
copy, lets each client run the hook on a prompt that cites a URL, ends with `undo --confirm`, and
looks at what that leaves in each client. The clients get a throwaway HOME, CLAUDE_CONFIG_DIR and
CODEX_HOME under a new temporary folder, and only the variables they need, so they never see the real
user's home or credentials; only the wheel build gets the proxy variables, for hatchling. No model is
called: when a client runs the hook, its request goes to a loopback fixture that answers 400. Every
process started here is stopped before the end, also when a step fails. Needs `uv` and `uvx`.

The output is a receipt: client versions, each command with its exit code, and each check. `--json`
prints it as JSON. Exit code 0 when every check passed, 1 otherwise. Measured on Linux only; on Windows
pass the actual .exe files, not npm's .ps1/.cmd launchers. Not collected by `unittest discover` (no
`test` prefix).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import platform
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

REPO = Path(__file__).resolve().parents[1]
PLUGIN = 'youngcrow@youngcrow'
SKILLS = ('govern-capabilities', 'ingest-source', 'integrate-from-docs', 'personalizer', 'retrieve-memory')
AGENT = 'integration-specialist'
PROMPT = 'Read https://example.com/spec.pdf and tell me what it covers.'
QUIET_PROMPT = 'Say hello.'
GUIDANCE = 'Textual source reference detected'  # the text source_prompt adds for a prompt that cites a source
OS_NAMES = ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'PATHEXT', 'LANG', 'LC_ALL')
# Only the wheel build reaches a package index (for hatchling); the clients never get these.
BUILD_NAMES = ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
               'UV_NATIVE_TLS', 'UV_SYSTEM_CERTS', 'UV_INDEX_URL', 'UV_DEFAULT_INDEX', 'PIP_INDEX_URL')


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}


class Failed(Exception):
    """A check failed; the receipt says which."""


class Proof:
    def __init__(self, tmp: Path, claude: str, codex: str):
        self.tmp, self.claude, self.codex = tmp, claude, codex
        self.home = tmp / 'home'
        self.project = tmp / 'project'
        self.steps: list[dict] = []
        self.labels = {claude: 'claude', codex: 'codex', sys.executable: 'python'}
        uv = shutil.which('uv')
        self.uv, self.uvx = uv, shutil.which('uvx')
        self.labels.update({uv: 'uv', self.uvx: 'uvx'})
        node = shutil.which('node')
        dirs = [Path(sys.executable).parent, Path(claude).parent, Path(codex).parent]
        dirs += [Path(p).parent for p in (node, uv, shutil.which('git')) if p]
        path = os.pathsep.join(dict.fromkeys(str(d) for d in dirs))
        base = {k: v for k, v in os.environ.items() if k.upper() in OS_NAMES}
        self.env = {**base, 'PATH': path + os.pathsep + os.defpath, 'HOME': str(self.home),
                    'USERPROFILE': str(self.home), 'CLAUDE_CONFIG_DIR': str(self.home / '.claude'),
                    'CODEX_HOME': str(self.home / '.codex'), 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0'}
        if os.name == 'nt':
            self.env.update(APPDATA=str(self.home / 'AppData/Roaming'), LOCALAPPDATA=str(self.home / 'AppData/Local'))
        self.build_env = {**self.env, 'UV_CACHE_DIR': str(tmp / 'uv-cache'),
                          **{k: v for k, v in os.environ.items() if k.upper() in BUILD_NAMES}}

    # -- receipt -------------------------------------------------------------------------------
    def plain(self, value):
        """`value` with the temporary folder, the repository and the executables named, not spelled out."""
        if isinstance(value, list):
            return [self.plain(v) for v in value]
        text = str(value)
        if text in self.labels:
            return self.labels[text]
        return text.replace(str(self.tmp), '$TMP').replace(str(REPO), '$REPO')

    def step(self, number: str, title: str, brief: bool = True) -> dict:
        record = {'step': number, 'title': title, 'in_brief': brief, 'commands': [], 'checks': [], 'ok': None}
        self.steps.append(record)
        return record

    def check(self, what: str, ok: bool, detail=None):
        self.steps[-1]['checks'].append({'check': what, 'ok': bool(ok), **({'detail': detail} if detail is not None else {})})
        if not ok:
            raise Failed(what)

    def _record(self, argv, cwd, code, out, err, note=None):
        entry = {'argv': self.plain(list(argv)), 'cwd': self.plain(cwd), 'exit': code}
        lines = [line for line in out.strip().splitlines() if line.strip()]
        if lines:
            entry['stdout'] = self.plain(' | '.join(lines)[:300])
        if code != 0 and err.strip():
            entry['stderr'] = self.plain(' | '.join(err.strip().splitlines())[-300:])
        if note:
            entry['note'] = note
        self.steps[-1]['commands'].append(entry)

    # -- processes -----------------------------------------------------------------------------
    def popen(self, argv, cwd, env=None, **kwargs):
        return subprocess.Popen([str(a) for a in argv], cwd=cwd, env=env or self.env, start_new_session=(os.name != 'nt'),
                                **kwargs)

    @staticmethod
    def stop(process):
        """Stop `process` and, on POSIX, whatever is left in its process group, also after it exited by itself."""
        if os.name == 'nt':
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)  # the group is ours: start_new_session made the process its leader
            except ProcessLookupError:
                break  # nobody is left in the group
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                continue
            time.sleep(0.2)  # the leader is gone; give the rest of the group a moment before looking again
        process.poll()

    def run(self, argv, cwd=None, *, stdin: bytes | None = None, env=None, timeout=180, expect=0, note=None):
        cwd = cwd or self.project
        process = self.popen(argv, cwd, env, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = process.communicate(stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.stop(process)
            out, err = process.communicate()
            self._record(argv, cwd, 'timeout', out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace'))
            self.check(f'{self.plain(str(argv[0]))} ends within {timeout} s', False)
        finally:
            self.stop(process)
        out, err = out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace')
        self._record(argv, cwd, process.returncode, out, err, note)
        if expect is not None and process.returncode != expect:
            self.check(f'{self.plain(str(argv[0]))} exits with {expect}', False, process.returncode)
        return out

    def leftovers(self) -> list[str]:
        """Processes still alive whose environment names this proof's temporary folder (Linux /proc)."""
        found, marker = [], str(self.tmp).encode()
        for entry in Path('/proc').glob('[0-9]*') if os.name != 'nt' else ():
            try:
                if marker in (entry / 'environ').read_bytes() and int(entry.name) != os.getpid():
                    command = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
                    found.append(f'{entry.name} {self.plain(command[:160])}')
            except OSError:
                continue
        return found

    # -- loopback model fixture ----------------------------------------------------------------
    def capture(self, argv, extra_env, cwd=None, wait_for_exit=True, timeout=90, note=None) -> list[str]:
        """Run a client against a loopback server that answers 400; return the request bodies it sent."""
        bodies = queue.Queue()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _answer(self):
                size = int(self.headers.get('Content-Length') or 0)
                bodies.put(self.rfile.read(size).decode('utf-8', 'replace'))
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"loopback fixture"}}')

            do_POST = do_GET = _answer

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        argv = [a.replace('{fixture}', url) for a in argv]
        env = {**self.env, **{k: v.replace('{fixture}', url) for k, v in extra_env.items()}}
        cwd = cwd or self.project
        process = self.popen(argv, cwd, env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        seen = []
        try:
            if wait_for_exit:
                out, err = process.communicate(timeout=timeout)
            else:
                seen.append(bodies.get(timeout=timeout))  # the first request is enough
                self.stop(process)
                out, err = process.communicate()
            code = process.returncode
        except (subprocess.TimeoutExpired, queue.Empty):
            self.stop(process)
            out, err = process.communicate()
            code = 'timeout'
        finally:
            self.stop(process)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        while not bodies.empty():
            seen.append(bodies.get())
        self._record([str(a).replace(url, '$FIXTURE') for a in argv], cwd, code,
                     out.decode('utf-8', 'replace')[-300:], err.decode('utf-8', 'replace'), note)
        self.steps[-1]['commands'][-1]['requests_to_fixture'] = len(seen)
        return seen

    def app_server(self, requests: list[tuple[str, dict]]) -> list[dict]:
        """Codex's app-server over stdio: initialize, then each request in turn; results in order."""
        argv = [self.codex, 'app-server', '--stdio']
        process = self.popen(argv, self.project, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
        messages = queue.Queue()
        reader = threading.Thread(target=lambda: [messages.put(json.loads(line)) for line in process.stdout], daemon=True)
        reader.start()

        def send(number, method, params):
            process.stdin.write(json.dumps({'id': number, 'method': method, 'params': params}) + '\n')
            process.stdin.flush()
            deadline = time.monotonic() + 30
            while True:
                message = messages.get(timeout=max(0.01, deadline - time.monotonic()))
                if message.get('id') == number:
                    if 'error' in message:
                        self.check(f'app-server answers {method}', False, message['error'])
                    return message['result']

        results = []
        try:
            send(0, 'initialize', {'clientInfo': {'name': 'youngcrow-smoke-plugin', 'version': '1'}})
            process.stdin.write('{"method":"initialized"}\n')
            process.stdin.flush()
            results = [send(n, method, params) for n, (method, params) in enumerate(requests, start=1)]
        finally:
            self.stop(process)
            reader.join(timeout=5)
            process.stdin.close()
            process.stdout.close()
            self._record(argv, self.project, process.returncode, '', '',
                         f'requests {", ".join(m for m, _ in requests)}; stopped by the proof after the replies')
        return results

    # -- the proof -----------------------------------------------------------------------------
    def versions(self) -> dict:
        def version(argv):
            done = subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            return (done.stdout.strip() or done.stderr.strip()).splitlines()[-1]
        return {'claude': version([self.claude, '--version']), 'codex': version([self.codex, '--version'])}

    def git_state(self) -> str:
        done = subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain', '--ignored'], env=self.env,
                              capture_output=True, text=True, timeout=60)
        return done.stdout

    def prove(self):
        self.home.mkdir()
        (self.home / '.codex').mkdir()
        payload = json.dumps({'session_id': 'smoke-plugin', 'hook_event_name': 'UserPromptSubmit',
                              'cwd': str(self.project), 'prompt': PROMPT}).encode('utf-8')

        self.step('1', 'build the wheel and run init --client both in a new project')
        self.run([self.uv, 'build', '--wheel', '--python', sys.executable, '-o', self.tmp / 'dist'], cwd=REPO,
                 env=self.build_env, timeout=600)
        wheels = sorted((self.tmp / 'dist').glob('youngcrow-*.whl'))
        self.check('one wheel was built', len(wheels) == 1, self.plain([str(w) for w in wheels]))
        self.youngcrow = [self.uvx, '--python', sys.executable, '--from', wheels[0], 'youngcrow']
        report = json.loads(self.run([*self.youngcrow, 'init', '--root', self.project, '--client', 'both', '--json'],
                                     cwd=self.tmp, env=self.build_env))
        self.check('init wrote the Claude wiring and the Codex agent',
                   {'.claude/settings.json', '.codex/agents/integration-specialist.toml'} <= set(report['written']))
        self.check('init printed one next step per client', len(report['next_steps']) == 2, report['next_steps'])

        self.step('2', 'claude plugin validate')
        out = self.run([self.claude, 'plugin', 'validate', REPO])
        self.check('the validator passed', 'Validation passed' in out)

        self.step('3', 'Claude Code: add the local marketplace, install at project scope, list')
        self.run([self.claude, 'plugin', 'marketplace', 'add', REPO, '--json'])
        self.run([self.claude, 'plugin', 'install', PLUGIN, '--scope', 'project', '--json'])
        listed = json.loads(self.run([self.claude, 'plugin', 'list', '--json']))
        ours = [p for p in listed if p.get('id') == PLUGIN]
        self.check('claude plugin list shows the plugin enabled at project scope',
                   len(ours) == 1 and ours[0].get('enabled') is True and ours[0].get('scope') == 'project'
                   and Path(ours[0].get('projectPath', '')).resolve() == self.project.resolve(), self.plain(str(ours)))
        self.claude_copy = Path(ours[0]['installPath'])
        self.check('the copy Claude installed is the plugin folder, byte for byte',
                   tree(self.claude_copy) == tree(REPO / 'plugins/youngcrow'), self.plain(str(self.claude_copy)))
        out = self.run([self.claude, 'plugin', 'details', PLUGIN], note='beyond the brief: component inventory')
        self.check('claude plugin details counts five skills, the agent and both hooks',
                   'Skills (5)' in out and all(s in out for s in SKILLS) and 'Agents (1)' in out and AGENT in out
                   and 'SessionStart, UserPromptSubmit' in out)

        self.step('4', 'Codex: add the local marketplace, install, list')
        self.run([self.codex, 'plugin', 'marketplace', 'add', REPO, '--json'])
        added = json.loads(self.run([self.codex, 'plugin', 'add', PLUGIN, '--json']))
        out = self.run([self.codex, 'plugin', 'list'])
        self.check('codex plugin list shows the plugin installed and enabled',
                   any(PLUGIN in line and 'installed, enabled' in line for line in out.splitlines()))
        self.codex_copy = Path(added['installedPath'])
        self.check('the copy Codex installed is the plugin folder, byte for byte',
                   tree(self.codex_copy) == tree(REPO / 'plugins/youngcrow'), self.plain(str(self.codex_copy)))

        self.step('5', 'the hook of each installed copy gives what the project source_prompt gives')
        expected = self.run([sys.executable, '-B', self.project / '.youngcrow/scripts/source_prompt.py'], stdin=payload)
        self.check('source_prompt answers the prompt with source guidance', GUIDANCE in expected)
        for name, copy in (('Claude', self.claude_copy), ('Codex', self.codex_copy)):
            hook = copy / 'hooks' / 'youngcrow_hook.py'
            out = self.run([sys.executable, '-I', hook, 'prompt'], stdin=payload)
            self.check(f'{name} copy: prompt hook output equals source_prompt output', out == expected)
            out = self.run([sys.executable, '-I', hook, 'session-start'], stdin=b'{}')
            self.check(f'{name} copy: session-start is silent while the versions match', out == '')

        self.step('5+', 'Codex runs the plugin hook (loopback model fixture)', brief=False)
        self.codex_runs_the_hook()

        self.step('5+', 'Claude Code runs the plugin hook (loopback model fixture)', brief=False)
        self.claude_runs_the_hook()

        self.step('6', 'undo --confirm leaves the project empty')
        report = json.loads(self.run([*self.youngcrow, 'undo', '--confirm', '--root', self.project, '--json'],
                                     cwd=self.tmp, env=self.build_env))
        left = sorted(p.relative_to(self.project).as_posix() for p in self.project.rglob('*'))
        detail = {'left': left, 'kept_modified': report['kept_modified']}
        settings = self.project / '.claude/settings.json'
        if settings.is_file():
            detail['.claude/settings.json'] = settings.read_text(encoding='utf-8', errors='replace')
        self.check('the project folder is empty', left == [], detail)

        self.step('6+', 'what undo leaves in the clients', brief=False)
        listed = json.loads(self.run([self.claude, 'plugin', 'list', '--json']))
        ours = [p for p in listed if p.get('id') == PLUGIN]
        self.check('Claude Code no longer enables the plugin in this project',
                   len(ours) == 1 and ours[0].get('enabled') is False, self.plain(str(ours)))
        out = self.run([self.codex, 'plugin', 'list'])
        self.check('Codex keeps the plugin installed for the user (undo does not touch it)',
                   any(PLUGIN in line and 'installed, enabled' in line for line in out.splitlines()))
        self.run([self.codex, 'plugin', 'remove', PLUGIN])
        out = self.run([self.codex, 'plugin', 'list'])
        self.check('codex plugin remove takes it out',
                   any(PLUGIN in line and 'not installed' in line for line in out.splitlines()))

    def codex_exec(self, prompt: str) -> list[str]:
        fixture = ['-c', 'model="local-fixture"', '-c', 'model_provider="fixture"',
                   '-c', 'model_providers.fixture.name="Local fixture"',
                   '-c', 'model_providers.fixture.base_url="{fixture}/v1"',
                   '-c', 'model_providers.fixture.wire_api="responses"',
                   '-c', 'model_providers.fixture.requires_openai_auth=false']
        return self.capture([self.codex, 'exec', '--json', '--skip-git-repo-check', '--sandbox', 'read-only',
                             *fixture, prompt], {}, wait_for_exit=False,
                            note='stopped by the proof after the first request')

    def codex_runs_the_hook(self):
        config = self.home / '.codex' / 'config.toml'
        # Project trust lets Codex load the project's agent file; it does not trust hooks.
        with open(config, 'a', encoding='utf-8') as handle:
            handle.write('\n[projects.' + json.dumps(os.path.normcase(str(self.project))) + ']\ntrust_level = "trusted"\n')
        hooks, skills = self.app_server([('hooks/list', {'cwds': [str(self.project)]}),
                                         ('skills/list', {'cwds': [str(self.project)], 'forceReload': True})])
        found = [h for entry in hooks['data'] for h in entry['hooks'] if h.get('pluginId') == PLUGIN]
        self.check('Codex finds both plugin hooks, pointing at the installed copy, untrusted',
                   sorted(h['eventName'] for h in found) == ['sessionStart', 'userPromptSubmit']
                   and all(str(self.codex_copy / 'hooks' / 'youngcrow_hook.py') in h['command']
                           and h['trustStatus'] == 'untrusted' for h in found)
                   and not any(entry['errors'] for entry in hooks['data']),
                   self.plain([{k: h[k] for k in ('eventName', 'trustStatus', 'command')} for h in found]))
        names = {s['name'] for entry in skills['data'] for s in entry['skills']}
        self.check('Codex finds the five skills as youngcrow:<skill>', {f'youngcrow:{s}' for s in SKILLS} <= names)
        bodies = self.codex_exec(PROMPT)
        self.check('control: with the hooks untrusted, the request carries no source guidance',
                   bodies and not any(GUIDANCE in b for b in bodies))
        # What trusting them in /hooks records: the hash pair hooks/list reports for each hook.
        with open(config, 'a', encoding='utf-8') as handle:
            for hook in found:
                trusted, content = hook['currentHash'].split('/')
                handle.write(f'\n[hooks.state.{json.dumps(hook["key"])}]\ntrusted_hash = "{trusted}"\n'
                             f'trusted_content_hash = "{content}"\n')
        hooks, = self.app_server([('hooks/list', {'cwds': [str(self.project)]})])
        self.check('after trust, hooks/list reports both hooks trusted',
                   [h['trustStatus'] for e in hooks['data'] for h in e['hooks'] if h.get('pluginId') == PLUGIN]
                   == ['trusted', 'trusted'])
        bodies = self.codex_exec(PROMPT)
        body = next((b for b in bodies if GUIDANCE in b), '')
        self.check('the request Codex sends carries the hook source guidance', body != '')
        self.check('the same request names the five skills and the project agent',
                   all(f'youngcrow:{s}' in body for s in SKILLS) and AGENT in body)

    def claude_runs_the_hook(self):
        env = {'ANTHROPIC_BASE_URL': '{fixture}', 'ANTHROPIC_API_KEY': 'sk-ant-loopback-fixture-not-a-key'}
        argv = [self.claude, '-p', PROMPT, '--output-format', 'json', '--max-turns', '1']
        note = 'exit 1 is expected: the fixture answers 400'
        bodies = self.capture(argv, env, note=note)
        body = next((b for b in bodies if GUIDANCE in b), '')
        self.check('the request Claude Code sends carries the hook source guidance', body != '', len(bodies))
        self.check('the same request names the five skills and the agent as youngcrow:<name>',
                   all(f'youngcrow:{s}' in body for s in (*SKILLS, AGENT)))
        bodies = self.capture([self.claude, '-p', QUIET_PROMPT, '--output-format', 'json', '--max-turns', '1'], env,
                              note=note)
        self.check('control: a prompt that cites no source gets no source guidance',
                   bodies and not any(GUIDANCE in b for b in bodies), len(bodies))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--claude', required=True)
    parser.add_argument('--codex', required=True)
    parser.add_argument('--json', action='store_true', help='print the receipt as JSON')
    args = parser.parse_args(argv)
    if not (shutil.which('uv') and shutil.which('uvx')):
        parser.error('uv and uvx must be on PATH: the proof builds the wheel and runs it with them')
    tmp = Path(tempfile.mkdtemp(prefix='yc-plugin-proof-')).resolve()
    proof = Proof(tmp, str(Path(args.claude).resolve()), str(Path(args.codex).resolve()))
    __version__ = re.search(r"__version__ = '([^']+)'", (REPO / 'src/youngcrow/__init__.py').read_text()).group(1)
    receipt = {'receipt': 'youngcrow plugin proof', 'date': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'youngcrow': __version__, 'python': platform.python_version(), 'platform': platform.platform(),
               'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'paths': {'$TMP': 'a new temporary folder, removed at the end', '$REPO': 'this repository',
                         '$FIXTURE': 'the loopback model fixture'}}
    error, before = None, None
    try:
        before = proof.git_state()
        head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], env=proof.env, capture_output=True,
                              text=True, timeout=60).stdout.strip()
        receipt.update(head=head, clients=proof.versions())
        proof.prove()
    except Failed as failure:
        error = str(failure)
    except Exception as failure:  # an unexpected error is a failed proof too, with its reason
        error = f'{type(failure).__name__}: {failure}'
        if proof.steps:
            proof.steps[-1]['checks'].append({'check': 'no unexpected error', 'ok': False, 'detail': proof.plain(error)})
    finally:
        left = proof.leftovers()
        for line in left:  # ours by environment, so stopping them cannot touch anything else
            try:
                os.kill(int(line.split()[0]), signal.SIGKILL)
            except OSError:
                pass
        receipt['repository_unchanged'] = proof.git_state() == before
        receipt['steps'] = proof.steps
        for record in proof.steps:
            record['ok'] = all(c['ok'] for c in record['checks']) and bool(record['checks'])
        receipt['processes_left'] = left
        receipt['failed'] = error
        receipt['ok'] = error is None and not left and receipt['repository_unchanged']
        shutil.rmtree(tmp, ignore_errors=True)
    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    else:
        print(f"Claude Code {receipt.get('clients', {}).get('claude')}; Codex {receipt.get('clients', {}).get('codex')}")
        for record in receipt['steps']:
            for check in record['checks']:
                print(f"[{'ok' if check['ok'] else 'FAIL'}] {record['step']} {check['check']}")
        print('Proof passed.' if receipt['ok'] else f"Proof failed: {error or 'see processes_left / repository_unchanged'}")
    return 0 if receipt['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
