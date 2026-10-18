"""Exact subscription-client profiles. Configuration is not execution qualification."""
import json
import os
from pathlib import Path
import re
import sys
import tomllib

import adoption_fs as fs
from mission_clients import hash_executable, parse_events, safe_name
from mission_worker import exec_argv, require, sha, workspace

VERSIONS = {'codex': '0.159.2', 'claude': '2.1.296'}
BINARIES = {'codex': '1748767b230ebfc3d4ab7e4e254920d0c0ad9691fd8c11f190e7d44511a4a92e',
            'claude': '24972e3bc859fab2b46ed4c1e51f7d6130f06d3bd550811a114640de3370d0de'}
# Populate only after full native routing and account-policy qualification. User JSON is not proof.
QUALIFIED = frozenset()
DISABLED = ('hooks', 'plugins', 'apps', 'multi_agent', 'multi_agent_v2', 'browser_use',
            'browser_use_external', 'browser_use_full_cdp_access', 'computer_use', 'in_app_browser',
            'image_generation', 'remote_plugin', 'executor_capability_discovery', 'skill_search',
            'skill_mcp_dependency_install', 'shell_snapshot', 'code_mode', 'code_mode_host',
            'workspace_dependencies', 'goals', 'tool_suggest')
CLOUD_ENV = {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
             'NODE_EXTRA_CA_CERTS', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'CODEX_PROXY_CERT',
             'CODEX_EXEC_SERVER_PROXY_PRIVATE_IPS_VIA_UPSTREAM'}


def verify_binary(client, executable):
    require(sys.platform == 'linux' and client in VERSIONS, 'unsupported_tool_client')
    require(Path(executable).is_absolute(), 'invalid_executable')
    digest = hash_executable(executable)
    require(digest == BINARIES[client], 'unsupported_tool_client')
    return dict(version=VERSIONS[client], sha256=digest)


def managed_gaps(client):
    if client == 'codex':
        candidates = [Path('/etc/codex') / name for name in ('requirements.toml', 'managed_config.toml')]
        defaults = Path('/etc/codex/config.toml')
        if defaults.exists():
            try:
                config = tomllib.loads(defaults.read_text())
            except (ValueError, OSError):
                return ['managed_policy_unreadable']
            # Official0.159.2 treats this as lower-precedence defaults; plugins=false
            # prevents loading this catalog. Other defaults still require qualification.
            if not set(config) <= {'marketplaces', 'plugins'}:
                return ['managed_policy_conflict']
    else:
        root = Path('/etc/claude-code')
        candidates = [root/'managed-settings.json', root/'managed-mcp.json', *root.glob('managed-settings.d/*.json')]
    return ['managed_policy_conflict'] if any(p.exists() for p in candidates) else []


def toml(value):
    scalars, tables = [], []
    for key, item in value.items():
        if isinstance(item, dict):
            tables.append((key, item))
        else:
            scalars.append(f'{key} = {json.dumps(item)}\n')
    for key, item in tables:
        scalars.append(f'\n[{key}]\n')
        scalars.extend(f'{name} = {json.dumps(v)}\n' for name, v in item.items())
    return ''.join(scalars).encode()


def build_profile(client, executable, handle, control, selection):
    binary = verify_binary(client, executable)
    require(not managed_gaps(client), 'managed_policy_conflict')
    require(set(selection) == {'model', 'effort'} and all(type(v) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', v)
            for v in selection.values()), 'invalid_model_selection')
    control = fs.checked_path(Path(control).absolute())
    fs.outside_git(control)
    if not control.exists(): fs.private_dir(control)
    require(control.stat().st_mode & 0o077 == 0, 'worker_control_not_private')
    home = control/'account'
    cwd = Path(workspace(handle['operation_id']))
    mirror = fs.checked_path(cwd.parent)
    if not mirror.exists(): fs.private_dir(mirror)
    require(mirror.stat().st_mode & 0o077 == 0, 'worker_control_not_private')
    for path in (home, cwd):
        fs.checked_path(path)
        if not path.exists(): fs.private_dir(path)
        require(path.is_dir() and path.stat().st_mode & 0o077 == 0, 'worker_control_not_private')
    # Only configuration previously written by this helper may be replaced. Never read/copy auth.
    marker = control/'profile-files.json'
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    environment_config, builtin_tools = None, []
    command = exec_argv(handle, ['/usr/local/bin/codex', 'exec-server', '--listen', 'stdio'])
    if client == 'codex':
        configuration = dict(forced_login_method='chatgpt', model=selection['model'],
                             model_reasoning_effort=selection['effort'], sandbox_mode='workspace-write', web_search='disabled', notify=[],
                             features={**dict.fromkeys(DISABLED, False), 'skip_host_skill_discovery': True},
                             agents={'enabled': False}, skills={'include_instructions': False},
                             **{'skills.bundled': {'enabled': False}, 'cloud.skills': {'enabled': False},
                                'orchestrator.mcp': {'enabled': False}, 'mcp_servers': {}})
        environment_config = dict(default=handle['container_id'], include_local=False,
                                  environments=[dict(id=handle['container_id'], program=command[0], args=command[1:],
                                                     cwd=str(cwd), initialize_timeout_sec=10.0)])
        entry = environment_config['environments'][0]
        transport = toml({k:v for k,v in environment_config.items() if k!='environments'}) + b'\n[[environments]]\n' + toml(entry)
        contents = {home/'config.toml': toml(configuration), home/'environments.toml': transport}
        argv = [str(executable), 'exec', '--strict-config', '--ephemeral', '--skip-git-repo-check', '--json', '-']
        overrides = dict(CODEX_HOME=str(home))
    else:
        configuration = dict(disableAllHooks=True, forceLoginMethod='claudeai', enabledPlugins={},
                             enableAllProjectMcpServers=False)
        command = exec_argv(handle, ['/usr/local/bin/python3', '-I', '-B', '/opt/youngcrow/mcp.py'])
        mcp = dict(mcpServers=dict(youngcrow=dict(type='stdio', command=command[0], args=command[1:], alwaysLoad=True)))
        settings, transport = control/'settings.json', control/'mcp.json'
        contents = {settings: fs.canonical(configuration), transport: fs.canonical(mcp)}
        argv = [str(executable), '-p', '--restricted', '--tools', '', '--strict-mcp-config',
                '--mcp-config', str(transport), '--allowedTools', 'mcp__youngcrow__run',
                '--permission-mode', 'dontAsk', '--permission-prompts', 'none', '--disable-slash-commands',
                '--no-chrome', '--no-session-persistence', '--settings', str(settings),
                '--model', selection['model'], '--effort', selection['effort'], '--output-format', 'stream-json', '--verbose']
        overrides = dict(CLAUDE_CONFIG_DIR=str(home), DISABLE_UPDATES='1', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
    for path in contents:
        fs.checked_path(path)
        if path.exists():
            require(previous.get(str(path)) == sha(path.read_bytes()), 'worker_profile_changed')
    files = []
    for path, data in contents.items():
        # Parent is private/trusted and shared execution reservation serializes profile writes.
        with path.open('wb') as stream:
            stream.write(data)
        path.chmod(0o600)
        files.append(dict(path=str(path), sha256=sha(data)))
    marker.write_bytes(fs.canonical({row['path']:row['sha256'] for row in files}))
    marker.chmod(0o600)
    public = dict(client=client, version=binary['version'], executable_sha256=binary['sha256'],
                  image_digest=handle['image_digest'], configuration=configuration,
                  environment_config=environment_config, builtin_tools=builtin_tools,
                  argv=argv, cwd=str(cwd), config_files=files, environment_overrides=overrides)
    public['profile_sha256'] = sha(fs.canonical(public))
    return public


def verify_profile(profile):
    require(sha(fs.canonical({k:v for k,v in profile.items() if k!='profile_sha256'})) == profile['profile_sha256'],
            'worker_profile_changed')
    for row in profile['config_files']:
        path = fs.checked_path(Path(row['path']))
        require(path.is_file() and path.stat().st_size <= 16384 and sha(path.read_bytes()) == row['sha256'],
                'worker_profile_changed')
    require(not managed_gaps(profile['client']), 'managed_policy_conflict')


def validate_qualification(profile, evidence):
    verify_profile(profile)
    key = (profile['client'], profile['version'], profile['executable_sha256'], profile['image_digest'])
    require(key in QUALIFIED and type(evidence) is dict and evidence.get('profile_sha256') == profile['profile_sha256'],
            'tool_profile_unqualified')


def observe_result(client,data):
    """Read native events; configured selections are never substituted for observations.

    These pinned headless protocols do not report applied effort. Codex also omits
    model. A successful process therefore cannot yet satisfy the coding contract.
    """
    events=parse_events(data)
    models,tools=set(),set()
    terminal=None
    require(client in VERSIONS,'client_protocol_error')
    for event in events:
        kind=event['type']
        if client=='codex':
            if kind in ('item.started','item.updated','item.completed'):
                item=event.get('item');require(type(item) is dict,'client_protocol_error')
                name=item.get('type')
                require(name in ('agent_message','reasoning','command_execution','file_change'),'unexpected_tool')
                if name in ('command_execution','file_change'):tools.add(name)
            elif kind=='turn.completed':
                require(terminal is None,'client_protocol_error');terminal=event
            else:require(kind in ('thread.started','turn.started'),'client_protocol_error')
        elif kind=='system':
            require(event.get('subtype')=='init' and type(event.get('tools')) is list
                    and all(type(t) is str for t in event['tools'])
                    and set(event['tools'])=={'mcp__youngcrow__run'},'unexpected_tool')
            require(safe_name(event.get('model')),'client_protocol_error')
            models.add(event['model'])
        elif kind in ('assistant','user'):
            message=event.get('message');require(type(message) is dict,'client_protocol_error')
            if kind=='assistant':
                require(safe_name(message.get('model')),'client_protocol_error')
                models.add(message['model'])
            content=message.get('content');require(type(content) is list,'client_protocol_error')
            for block in content:
                require(type(block) is dict,'client_protocol_error')
                name=block.get('type')
                if name=='tool_use':
                    require(kind=='assistant' and block.get('name')=='mcp__youngcrow__run','unexpected_tool')
                    tools.add(block['name'])
                else:require(name in (('text','thinking') if kind=='assistant' else ('tool_result',)),
                             'client_protocol_error')
        elif kind=='result':
            require(terminal is None and event.get('subtype')=='success' and event.get('is_error') is False
                    and not event.get('permission_denials'),'client_protocol_error')
            terminal=event
        else:raise ValueError('client_protocol_error')
    require(terminal is not None and terminal is events[-1],'client_protocol_error')
    require(len(models)<=1,'worker_selection_mismatch')
    return dict(observed_model=next(iter(models),None),observed_effort=None,tools_observed=sorted(tools))


def client_environment(plan):
    allowed = {'PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', *CLOUD_ENV}
    env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    overrides = plan['environment_overrides']
    require(set(overrides) <= {'CODEX_HOME','CLAUDE_CONFIG_DIR','DISABLE_UPDATES','CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'},
            'invalid_tool_environment')
    env.update(overrides)
    return env
