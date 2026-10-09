"""Bounded P06 Claude proof. Development-only runner; stdlib and existing helpers.

prepare: local metadata/authentication, no user prompt. run: ONE approved session.
Original Oct 3 receipts are never read as model context or modified.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import adoption_fs as fs
from documents import worker_environment
from integrations import check_path
from mission_clients import parse_events
import mission_process
import vault

BATCH = 'YC-TEST-20261010-A'
BASE = '.runtime/test-campaign-20261010/claude-p06'
SECONDS, TOOLS = 300, 24
SKILLS = ('retrieve-memory', 'karpathy', 'ponytail')
REQUIRED_EVIDENCE = {
    'vault/features/delivery-board/index.md', 'vault/decisions/static-site.md',
    'vault/features/delivery-board/runs/implementation.md',
    'vault/features/delivery-board/runs/native-memory.md', 'vault/operations/index.md',
}
REQUIRED_READS = {'vault/index.md', 'vault/project.json'} | {f'skills/{s}/SKILL.md' for s in SKILLS}
PROMPT = '''Recupere o piloto do quadro de entregas pelos índices do vault deste projeto.
Leia as skills retrieve-memory, karpathy e ponytail; siga os microíndices relevantes.
Encontre a feature, decisão vigente, execução mais recente, evidências, desenvolvimento,
produção comprovada e próxima ação. Confira UUIDs e hashes das notas que sustentam
a resposta. Não use conversa anterior, não ingira fontes, não altere arquivos nem
publique. Retorne somente JSON com project_id, feature_id, decision, development,
production, evidence (path, note_id, sha256), next_action, capabilities_used e warnings.
Conte apenas capacidades realmente usadas. Este consumidor não tem índice derivado:
use a navegação Markdown. Ferramentas: Read, Glob, Grep e Bash somente para
sha256sum -- CAMINHO_RELATIVO [CAMINHO_RELATIVO ...]. Agrupe hashes numa chamada.
Não leia fora deste projeto. Não use MCPs, rede, agentes ou comandos adicionais.
Limites: uma sessão, 300 segundos, 24 ferramentas. Não salve handoff: devolva no JSON.'''


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def reserve(path, value):
    # Exclusive and flushed before any model-bearing process is released.
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())


def read_prepared(base):
    receipt = json.loads((base / 'prepare-receipt.json').read_text(encoding='utf-8'))
    require(receipt.get('state') == 'prepared_no_model_prompt'
            and receipt.get('setup_sha256') == digest(base / 'setup.json'), 'prepared_package_changed')
    return json.loads((base / 'setup.json').read_text(encoding='utf-8'))


def tool_text(content):
    if isinstance(content, str):
        return content
    require(isinstance(content, list), 'invalid_tool_result')
    return '\n'.join(item['text'] for item in content if item.get('type') == 'text')


def snapshot(context):
    fs.checked_path(context)
    result = {}
    for current, directories, files in os.walk(context, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            fs.checked_path(path)
            if path.is_file():
                relative = path.relative_to(context).as_posix()
                check_path(context, relative)
                require(path.stat().st_size <= 1024 * 1024, 'context_file_too_large')
                result[relative] = digest(path)
    return result


def make_context(repo, context, skills_dir):
    require(not context.exists(), 'preserve_existing_context')
    public = repo / 'examples/delivery-board'
    require(not vault.check(public)['issues'], 'invalid_public_vault')
    sources = [(p, p.relative_to(public)) for p in (public / 'vault').rglob('*')
               if p.is_file() and 'local' not in p.relative_to(public).parts]
    for name in SKILLS:
        source = (repo / 'skills' if name == 'retrieve-memory' else skills_dir) / name / 'SKILL.md'
        fs.checked_path(source)
        require(source.is_file(), 'required_skill_missing:' + name)
        sources.extend((source, Path(base) / name / 'SKILL.md') for base in ('skills', '.claude/skills'))
    # Check all inputs before creating a destination; never copy a whole profile.
    for source, _ in sources:
        fs.checked_path(source)
        require(source.stat().st_nlink == 1, 'linked_source')
    context.mkdir(parents=True)
    for source, relative in sources:
        target = context / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (context / 'CLAUDE.md').write_text('# Controlled read-only memory proof\n\n' + PROMPT, encoding='utf-8')
    require(not vault.check(context)['issues'], 'invalid_context_vault')


class ToolGate:
    """Serial SDK callbacks decide BEFORE execution, not from emitted tool events."""
    def __init__(self, context, before):
        self.context, self.before = context.resolve(), before
        self.admitted, self.completed = {}, {}

    def relative(self, value, *, directory=False):
        require(isinstance(value, str) and value and '\x00' not in value, 'invalid_path')
        path = Path(value)
        require('..' not in path.parts, 'outside_context')
        path = path if path.is_absolute() else self.context / path
        fs.checked_path(path)
        require(path.resolve().is_relative_to(self.context), 'outside_context')
        relative = path.resolve().relative_to(self.context).as_posix()
        if directory:
            require(path.is_dir(), 'invalid_directory')
        else:
            require(relative in self.before, 'unreviewed_file')
            check_path(self.context, relative)
        return relative

    def admit(self, data):
        require(snapshot(self.context) == self.before, 'context_changed')
        key, name, args = data.get('tool_use_id'), data.get('tool_name'), data.get('tool_input')
        require(data.get('hook_event_name') == 'PreToolUse' and isinstance(key, str) and key, 'invalid_hook')
        require(key not in self.admitted, 'replayed_tool')
        require(len(self.admitted) < TOOLS, 'tool_budget')
        require(isinstance(args, dict), 'invalid_tool_input')
        paths = []
        if name == 'Read':
            require(set(args) <= {'file_path','offset','limit'}, 'unsupported_read')
            paths = [self.relative(args.get('file_path'))]
            lines = len((self.context / paths[0]).read_text(encoding='utf-8').splitlines())
            require(args.get('offset', 1) == 1 and args.get('limit', lines) >= lines, 'partial_read')
        elif name in ('Glob', 'Grep'):
            require(set(args) <= ({'pattern','path'} if name == 'Glob' else
                    {'pattern','path','glob','output_mode','-A','-B','-C','-n','-i','type','head_limit','offset','multiline'}), 'unsupported_search')
            target = args.get('path', '.')
            candidate = Path(target) if Path(target).is_absolute() else self.context / target
            self.relative(target, directory=candidate.is_dir())
            pattern = args.get('pattern' if name == 'Glob' else 'glob', '*')
            require(isinstance(pattern, str) and not pattern.startswith(('/', '\\'))
                    and '..' not in pattern and ':' not in pattern, 'outside_context')
        elif name == 'Bash':
            require(set(args) <= {'command','timeout','description','run_in_background'}
                    and not args.get('run_in_background', False), 'unsupported_command')
            command = args.get('command', '')
            require(isinstance(command, str) and re.fullmatch(r'sha256sum -- [A-Za-z0-9_./-]+(?: [A-Za-z0-9_./-]+)*', command), 'unsupported_command')
            paths = [self.relative(p) for p in command.split()[2:]]
        else:
            raise ValueError('unsupported_tool')
        entry = dict(tool_use_id=key, tool_name=name, tool_input=args, paths=paths)
        self.admitted[key] = entry
        return entry

    def complete(self, data):
        key = data.get('tool_use_id')
        require(data.get('hook_event_name') == 'PostToolUse' and key in self.admitted
                and key not in self.completed, 'unmatched_completion')
        entry = self.admitted[key]
        require(data.get('tool_name') == entry['tool_name'] and data.get('tool_input') == entry['tool_input'], 'changed_tool')
        self.completed[key] = entry
        return entry


def verify(context, before, events, supervision):
    require(supervision['reason'] == 'completed' and supervision['exit_code'] == 0
            and supervision['tree_reaped'], 'execution_not_successful')
    require(snapshot(context) == before, 'context_changed')
    terminal = [e for e in events if e.get('type') == 'result']
    require(len(terminal) == 1 and terminal[0].get('subtype') == 'success'
            and terminal[0].get('is_error') is False and not terminal[0].get('permission_denials'), 'missing_success_result')
    require(events[-1] is terminal[0], 'events_after_terminal')
    require(sum(e.get('type') == 'p06_prompt_sent' for e in events) == 1, 'invalid_prompt_count')
    sessions = {e['session_id'] for e in events if e.get('session_id')}
    require(len(sessions) == 1 and terminal[0].get('session_id') in sessions, 'invalid_session_count')
    require(not any(e.get('type') == 'p06_error' for e in events), 'controller_failed')
    admitted, completed, uses, results = {}, {}, {}, {}
    for event in events:
        kind = event.get('type')
        if kind in ('p06_admitted', 'p06_completed'):
            target = admitted if kind == 'p06_admitted' else completed
            key = event['tool_use_id']
            require(key not in target, 'duplicate_tool_event')
            target[key] = event
        elif kind in ('assistant','user'):
            content = event.get('message', {}).get('content', [])
            for item in content if isinstance(content, list) else []:
                if item.get('type') == 'tool_use':
                    key = item['id']
                    require(key not in uses, 'duplicate_tool_use')
                    uses[key] = item
                elif item.get('type') == 'tool_result':
                    key = item['tool_use_id']
                    require(key not in results and not item.get('is_error'), 'failed_tool')
                    results[key] = item
    require(0 < len(admitted) <= TOOLS and admitted.keys() == completed.keys() == uses.keys() == results.keys(), 'unreconciled_tools')
    reads, hashed = set(), set()
    for key, entry in admitted.items():
        require(uses[key]['name'] == entry['tool_name'] and uses[key]['input'] == entry['tool_input'], 'changed_tool')
        require(all(completed[key][k] == entry[k] for k in ('tool_name','tool_input','paths')), 'changed_completion')
        if entry['tool_name'] == 'Read':
            content = tool_text(results[key].get('content',''))
            relative = entry['paths'][0]
            text = (context / relative).read_text(encoding='utf-8')
            # UUID or skill name must actually be present in the successful output.
            if relative == 'vault/project.json':
                witness = json.loads(text)['project_id']
            elif relative.startswith('vault/'):
                witness = vault.metadata(text)[0]['id']
            else:
                witness = next((line for line in text.splitlines() if line.startswith('name:')), None)
                witness = witness or next((line for line in text.splitlines() if line.strip() and line != '---'), '')
            require(witness and witness in content, 'missing_read_content')
            reads.update(entry['paths'])
        if entry['tool_name'] == 'Bash':
            content = tool_text(results[key].get('content',''))
            checksums = re.findall(r'^([0-9a-f]{64}) [ *]([^\r\n]+)\r?$', content, re.M)
            require(len(checksums) == len(entry['paths']) and
                    {p:h for h,p in checksums} == {p:before[p] for p in entry['paths']}, 'missing_hash_output')
            hashed.update(entry['paths'])
    require(REQUIRED_READS <= reads, 'missing_memory_navigation')
    result = json.loads(terminal[0]['result'])
    require(isinstance(result, dict) and {'project_id','feature_id','decision','development','production','evidence','next_action','capabilities_used','warnings'} <= result.keys(), 'incomplete_handoff')
    for field in ('decision','development','production','next_action'):
        require(isinstance(result[field], (str,dict)) and bool(result[field]), 'empty_handoff')
    require(isinstance(result['capabilities_used'], (list,dict)) and bool(result['capabilities_used']), 'invalid_capabilities')
    project = json.loads((context / 'vault/project.json').read_text())['project_id']
    feature = vault.metadata((context / 'vault/features/delivery-board/index.md').read_text())[0]['id']
    require(result['project_id'] == project and result['feature_id'] == feature, 'wrong_identity')
    uuid.UUID(project); uuid.UUID(feature)
    require(isinstance(result['evidence'], list) and isinstance(result['warnings'], list), 'invalid_handoff')
    paths = set()
    for evidence in result['evidence']:
        relative = evidence['path']
        require(relative in before and relative in reads and relative in hashed
                and relative not in paths and relative.startswith('vault/') and relative.endswith('.md'), 'unread_evidence')
        require(evidence['sha256'] == before[relative], 'wrong_hash')
        note_id = vault.metadata((context / relative).read_text(encoding='utf-8'))[0]['id']
        require(evidence['note_id'] == note_id, 'wrong_note_id')
        uuid.UUID(note_id)
        paths.add(relative)
    require(REQUIRED_EVIDENCE <= paths, 'missing_current_evidence')
    # Integrity is mechanical; meaning still needs a reviewer reading the cited notes.
    models = sorted({e['model'] for e in events if e.get('type') == 'system' and isinstance(e.get('model'),str)})
    require(bool(models), 'model_unobserved')
    return dict(state='evidence_verified_pending_semantic_review', tool_calls=len(admitted),
                session_id=next(iter(sessions)), observed_models=models, handoff=result)


def check_credential_expiry(source):
    source = fs.checked_path(source)
    require(source.is_file(), 'subscription_credential_missing')
    try:
        expires = json.loads(source.read_text(encoding='utf-8'))['claudeAiOauth']['expiresAt']
    except (ValueError, KeyError, TypeError):
        raise ValueError('subscription_expiry_unknown') from None
    require(type(expires) is int, 'subscription_expiry_unknown')
    # Local metadata only, not proof of provider acceptance. Allow the 300-second
    # session plus 60 seconds for startup before relying on this credential.
    require(expires > (time.time() + SECONDS + 60) * 1000,
            'subscription_login_expired_or_expiring')


@contextmanager
def temporary_auth(source, profile):
    fs.checked_path(source)
    require(source.is_file(), 'subscription_credential_missing')
    fs.private_dir(profile)
    credential = profile / '.credentials.json'
    require(not credential.exists(), 'unreconciled_temporary_credential')
    original = digest(source)
    try:
        # Cleanup also covers partial copy and authentication failures.
        shutil.copyfile(source, credential)
        check_credential_expiry(credential)
        yield
    finally:
        credential.unlink(missing_ok=True)
        require(not credential.exists(), 'credential_cleanup_failed')
        require(digest(source) == original, 'original_auth_changed')


def emit(value):
    # ASCII transport survives Windows legacy stdout code pages under python -I.
    print(json.dumps(value, ensure_ascii=True), flush=True)


def controller(request):
    """Runs INSIDE mission_process's owned tree. Its blocking IO has an outer deadline."""
    context, profile = Path(request['context']), Path(request['profile'])
    require(snapshot(context) == request['before'], 'context_changed')
    env = worker_environment(profile / 'worker', offline=False)
    env.update(CLAUDE_CONFIG_DIR=str(profile), CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',
               PYTHONDONTWRITEBYTECODE='1')
    if os.name == 'nt':
        bash = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Git/bin/bash.exe'
        require(bash.is_file(), 'git_bash_missing')
        env['CLAUDE_CODE_GIT_BASH_PATH'] = str(bash)
    argv = request['client_argv']
    version = subprocess.run(argv + ['--version'], cwd=context, env=env, capture_output=True,
                             text=True, encoding='utf-8', timeout=15, check=True).stdout.strip()
    require(version == '2.1.220 (Claude Code)', 'unreviewed_claude_version')
    auth = subprocess.run(argv + ['auth','status'], cwd=context, env=env, capture_output=True,
                          text=True, encoding='utf-8', timeout=20, check=True)
    auth = json.loads(auth.stdout)
    require(auth.get('loggedIn') is True and auth.get('authMethod') == 'claude.ai'
            and auth.get('apiProvider') == 'firstParty', 'subscription_auth_failed')
    emit(dict(type='p06_auth', version=version, loggedIn=True, authMethod='claude.ai', apiProvider='firstParty'))
    save(profile / 'settings.json', dict(autoMemoryEnabled=False, attribution=dict(commit='',pr='')))
    save(profile / 'mcp.json', {'mcpServers':{}})
    args = argv + ['-p','--input-format','stream-json','--output-format','stream-json','--verbose',
                   '--no-session-persistence','--permission-mode','dontAsk','--setting-sources=',
                   '--settings',str(profile / 'settings.json'),'--strict-mcp-config','--mcp-config',str(profile / 'mcp.json'),
                   '--tools','Read,Glob,Grep,Bash','--allowedTools','Read,Glob,Grep,Bash',
                   '--effort','medium','--no-chrome']
    if request['model'] != 'default':
        args += ['--model', request['model']]
    gate = ToolGate(context, request['before'])
    child = subprocess.Popen(args, cwd=context, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def send(value):
        child.stdin.write(json.dumps(value).encode() + b'\n')
        child.stdin.flush()

    try:
        hooks = {name:[dict(matcher=None, hookCallbackIds=[callback], timeout=SECONDS + 60)]
                 for name, callback in (('PreToolUse','p06-pre'),('PostToolUse','p06-post'))}
        send(dict(type='control_request',request_id='init',request=dict(subtype='initialize',hooks=hooks)))
        initialized, sent, terminal = False, False, False
        while True:
            line = child.stdout.readline(1024 * 1024 + 1)
            if not line:
                break
            require(len(line) <= 1024 * 1024, 'event_too_large')
            event = json.loads(line)
            require(isinstance(event, dict) and not str(event.get('type','')).startswith('p06_'), 'invalid_client_event')
            emit(event)
            kind = event.get('type')
            if kind == 'control_response':
                response = event.get('response', {})
                require(not initialized and response.get('request_id') == 'init'
                        and response.get('subtype') == 'success', 'initialization_failed')
                names = {c['name'] for c in response.get('response', {}).get('commands', [])}
                initialized = True
                emit(dict(type='p06_initialized', skills=sorted(names & set(SKILLS))))
                if request['mode'] == 'prepare':
                    return 0
                emit(dict(type='p06_prompt_sent'))
                send(dict(type='user',message=dict(role='user',content=PROMPT),parent_tool_use_id=None,session_id='default'))
                sent = True
            elif kind == 'control_request':
                callback = event.get('request', {})
                require(sent and not terminal and callback.get('subtype') == 'hook_callback', 'unexpected_control_request')
                data = callback.get('input', {})
                require(callback.get('tool_use_id') in (None, data.get('tool_use_id')), 'changed_tool_identity')
                if callback.get('callback_id') == 'p06-pre':
                    try:
                        entry = gate.admit(data)
                    except ValueError as error:
                        emit(dict(type='p06_denied', reason=str(error), tool_use_id=data.get('tool_use_id')))
                        send(dict(type='control_response',response=dict(subtype='success',request_id=event['request_id'],response={
                            'continue':False, 'stopReason':str(error), 'hookSpecificOutput':{
                                'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':str(error)}})))
                        raise
                    # Flush the admission record before releasing the tool.
                    emit(dict(type='p06_admitted', **entry))
                    answer = {'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'allow'}}
                elif callback.get('callback_id') == 'p06-post':
                    emit(dict(type='p06_completed', **gate.complete(data)))
                    answer = {}
                else:
                    raise ValueError('unexpected_callback')
                send(dict(type='control_response', response=dict(subtype='success', request_id=event['request_id'], response=answer)))
            elif kind == 'result':
                require(sent and not terminal, 'unexpected_terminal')
                terminal = True
                child.stdin.close()
        require(terminal, 'missing_terminal')
        return child.wait()
    finally:
        # No grace period for further work. The outer job reaps remaining descendants.
        if child.poll() is None:
            child.kill()
        child.wait(timeout=3)
        child.stdin.close()
        child.stdout.close()


def supervised_worker(request, owner_path, seconds):
    plan = dict(argv=[sys.executable,'-I','-S',str(Path(__file__).resolve()),'--worker'],
                cwd=request['context'], stdin=json.dumps(request).encode(),
                timeout_seconds=seconds, output_limit_bytes=2 * 1024 * 1024,
                client='claude', connection='authenticated', credential_env=None)
    return mission_process.supervise(plan, on_started=lambda owner: reserve(owner_path, owner),
                                     stop_requested=lambda: False)


def package_hashes(repo):
    # The worker imports existing helpers. Bind their exact contents, not only Git HEAD.
    files = [Path(__file__).resolve(), repo / 'scripts/adoption_acl.ps1'] + sorted((repo / 'scripts').glob('*.py'))
    return {str(p.relative_to(repo)):digest(p) for p in files}


def native_executable(value):
    candidates = [Path(value)] if value else [Path(shutil.which('claude') or 'missing'),
        Path(os.environ.get('APPDATA','')) / 'npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe']
    executable = next((p.resolve() for p in candidates if p.suffix.lower() == '.exe' and p.is_file()), None)
    require(executable is not None, 'claude_exe_missing_use_--claude')
    return executable


def campaign(mode, executable=None, model='default', skills_dir=None):
    require(os.name == 'nt', 'native_proof_requires_operator_windows')
    base = fs.checked_path(ROOT / BASE)
    context = base / 'context'
    setup_path = base / 'setup.json'
    marker = base / 'started.json'
    source = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / '.credentials.json'
    if mode == 'prepare':
        require(not base.exists(), 'preserve_existing_package')
        check_credential_expiry(source)
        exe = native_executable(executable)
        base.parent.mkdir(parents=True, exist_ok=True)
        fs.private_dir(base)
        make_context(ROOT, context, Path(skills_dir) if skills_dir else Path.home() / '.codex/skills')
        revision = fs.git_read(ROOT, 'rev-parse', 'HEAD')
        require(revision.returncode == 0, 'git_revision_unavailable')
        setup = dict(batch_id=BATCH, operation_id=str(uuid.uuid4()), git_revision=revision.stdout.decode().strip(), before=snapshot(context),
                     executable=str(exe), executable_sha256=digest(exe), package=package_hashes(ROOT),
                     model=model, effort='medium', seconds=SECONDS, tool_calls=TOOLS,
                     approval_revision='48b16645727ebe9c5a2e3e83bbc32850d65ffe79',
                     planned_local='2026-10-10T18:30:00-03:00')
    else:
        setup = read_prepared(base)
        require(not marker.exists(), 'attempt_already_reserved_no_retry')
        check_credential_expiry(source)
        require(setup['batch_id'] == BATCH and setup['package'] == package_hashes(ROOT)
                and setup['before'] == snapshot(context), 'package_changed')
        exe = Path(setup['executable'])
        require(digest(exe) == setup['executable_sha256'], 'client_changed')
        require(executable is None and model == 'default' and skills_dir is None, 'prepare_options_not_allowed_on_run')
    request = dict(context=str(context), before=setup['before'], profile=str(base / ('profile-' + mode)),
                   client_argv=[str(exe)], mode=mode, model=setup['model'])
    receipt = dict(batch_id=BATCH, operation_id=setup['operation_id'], state='failed',
                   native_prompt_count=None if mode == 'run' else 0)
    # A losing concurrent invocation must not overwrite the owner's receipt.
    if mode == 'run':
        reserve(marker, setup)
    try:
        with temporary_auth(source, Path(request['profile'])):
            observed = supervised_worker(request, base / (mode + '-owner.json'), 60 if mode == 'prepare' else SECONDS)
            output = observed.pop('stdout')
            errors = observed.pop('stderr')
            # Preserve failures even if parsing or subsequent credential cleanup fails.
            (base / (mode + '-stderr.log')).write_bytes(errors)
            (base / (mode + '-events.jsonl')).write_bytes(output)
            receipt.update(supervision=observed)
            save(base / (mode + '-receipt.json'), receipt)
        receipt.update(temporary_credential_removed=True, original_auth_unchanged=True)
        events = parse_events(output)
        receipt['native_prompt_count'] = sum(e.get('type') == 'p06_prompt_sent' for e in events)
        if mode == 'prepare':
            require(observed['reason'] == 'completed' and observed['exit_code'] == 0 and observed['tree_reaped']
                    and receipt['native_prompt_count'] == 0 and any(e['type'] == 'p06_initialized' for e in events)
                    and snapshot(context) == setup['before'], 'preflight_failed')
            reserve(setup_path, setup)
            receipt['setup_sha256'] = digest(setup_path)
            receipt['state'] = 'prepared_no_model_prompt'
        else:
            receipt.update(verify(context, setup['before'], events, observed))
    except Exception as error:
        receipt['error'] = str(error) if isinstance(error, ValueError) else type(error).__name__
        raise
    finally:
        save(base / (mode + '-receipt.json'), receipt)
    return receipt


def main():
    if sys.argv[1:] == ['--worker']:
        try:
            return controller(json.load(sys.stdin))
        except Exception as error:
            emit(dict(type='p06_error', reason=str(error) if isinstance(error,ValueError) else type(error).__name__))
            return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','run'))
    parser.add_argument('--claude')
    parser.add_argument('--model', default='default')
    parser.add_argument('--skills-dir')
    args = parser.parse_args()
    try:
        result = campaign(args.mode, args.claude, args.model, args.skills_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'state':'blocked','reason':str(error) if isinstance(error,ValueError) else type(error).__name__}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
