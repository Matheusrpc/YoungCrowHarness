"""Offline project capability inventory. Reading never installs or executes a capability."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
import tomllib
from urllib.parse import urlsplit
import uuid

sys.dont_write_bytecode = True
from document_store import safe_path, atomic_write, project_lock, git

Capability = dict
Observation = dict
Audit = dict
CLIENTS = ('claude', 'codex')
FILE_LIMIT = 1024 * 1024
SET_LIMIT = 16 * FILE_LIMIT
FIELDS = {'id', 'kind', 'purpose', 'clients', 'scope', 'required', 'origin',
          'declared_version', 'files', 'permissions', 'native', 'expected'}
PERMISSIONS = {'read', 'write', 'network', 'data', 'environments', 'credential_env'}
NATIVE = {'server', 'transport', 'url', 'command', 'args', 'credential_env',
          'enabled', 'allow_tools', 'deny_tools'}
LEGACY = ('skills_de_projeto', 'skills_de_usuario', 'plugins')


def require(condition, code='invalid_catalog'):
    if not condition:
        raise ValueError(code)


def text(value, limit=2000):
    return isinstance(value, str) and len(value) <= limit and not any(ord(c) < 32 for c in value)


def identifier(value):
    return text(value, 63) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', value) and not re.fullmatch(
        r'con|prn|aux|nul|com[0-9]|lpt[0-9]', value)


def relative_path(value):
    require(text(value) and value and '\\' not in value and ':' not in value, 'unsafe_path')
    require(not PurePosixPath(value).is_absolute() and not PureWindowsPath(value).drive, 'unsafe_path')
    for part in value.split('/'):
        require(part not in ('', '.', '..') and not part.endswith((' ', '.'))
                and not re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?', part), 'unsafe_path')
    return value


def signature(info):
    # Windows Python versions disagree on ctime semantics between stat and fstat.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)


def read_inputs(root, files):
    require(isinstance(files, list), 'invalid_paths')
    records, size, seen = {}, 0, set()
    for relative in files:
        relative_path(relative)
        key = relative.casefold() if os.name == 'nt' else relative
        require(key not in seen, 'duplicate_path')
        seen.add(key)
        path = safe_path(root, relative)
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'unsafe_path')
        require(before.st_size <= FILE_LIMIT, 'file_limit')
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(path, flags), 'rb') as source:
            opened = os.fstat(source.fileno())
            require(signature(before) == signature(opened), 'input_changed')
            data = source.read(FILE_LIMIT + 1)
            after = os.fstat(source.fileno())
        safe_path(root, relative)
        require(signature(before) == signature(after) == signature(path.lstat()), 'input_changed')
        require(len(data) <= FILE_LIMIT, 'file_limit')
        size += len(data)
        require(size <= SET_LIMIT, 'set_limit')
        try:
            data.decode('utf-8-sig')
        except UnicodeError:
            raise ValueError('text_required') from None
        require(b'\x00' not in data, 'text_required')
        records[relative] = data
    return records


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def contract_digest(capability):
    return hashlib.sha256(canonical({k: v for k, v in capability.items() if k != 'expected'})).hexdigest()


def records_digest(records):
    digest = hashlib.sha256()
    for relative, data in sorted(records.items()):
        name = relative.encode('utf-8')
        digest.update(len(name).to_bytes(8, 'big'))
        digest.update(name)
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


def content_digest(root, files):
    return records_digest(read_inputs(root, files))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def parse_json(data):
    try:
        return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique_object,
                          parse_constant=lambda _: require(False, 'invalid_json'))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError('invalid_json') from None


def strings(value, limit=200):
    return (isinstance(value, list) and len(value) <= limit
            and all(text(v) for v in value) and len(value) == len(set(value)))


def safe_locator(value):
    require(text(value), 'invalid_locator')
    if '://' in value:
        try:
            url = urlsplit(value)
            require(url.scheme in ('http', 'https') and url.hostname and not url.username
                    and not url.password and not url.query and not url.fragment, 'sensitive_locator')
        except ValueError:
            raise ValueError('sensitive_locator') from None


def legacy_identity(raw, reference):
    require(isinstance(reference, str) and reference.count('/') == 1)
    section, name = reference.split('/')
    require(section in LEGACY and isinstance(raw.get(section), dict) and name in raw[section])
    item = raw[section][name]
    require(isinstance(item, dict))
    if section == 'skills_de_projeto' or item.get('versionado_aqui'):
        return dict(kind='repository', locator=item['versionado_aqui'], revision=None), item.get('versao')
    if section == 'plugins':
        return dict(kind='marketplace', locator=item.get('origem', ''),
                    revision=item.get('revisao_do_marketplace')), item.get('versao_ativa')
    upstream = item.get('upstream')
    if isinstance(upstream, dict):
        return dict(kind='git', locator=upstream.get('repo', ''), revision=upstream.get('commit')), upstream.get('versao')
    return dict(kind='repository', locator='manual-inventory', revision=None), None


def legacy_catalog(raw):
    result = []
    for section in LEGACY:
        entries = raw.get(section, {})
        require(isinstance(entries, dict))
        for name in entries:
            identity, version = legacy_identity(raw, section + '/' + name)
            prefix = {'plugins': 'plugin-', 'skills_de_usuario': 'user-', 'skills_de_projeto': ''}[section]
            result.append(dict(id=prefix + name, kind='skill',
                               purpose=dict(when='Legacy inventory', inputs='Unspecified',
                                            outputs='Unspecified', limits='Identity not verified'),
                               clients=list(CLIENTS), scope='inventory',
                               required={c: False for c in CLIENTS}, origin=identity, declared_version=version,
                               files=dict(common=[], claude=[], codex=[]),
                               permissions={p: [] for p in PERMISSIONS}, native={},
                               expected=dict(contract_sha256=None, files_sha256={c: None for c in CLIENTS})))
    return result


def validate_capability(cap):
    require(isinstance(cap, dict) and set(cap) == FIELDS)
    require(identifier(cap['id']) and cap['kind'] in ('skill', 'agent', 'mcp', 'runtime'))
    require(cap['scope'] in ('project', 'inventory'))
    require(strings(cap['clients'], 2) and cap['clients'] and set(cap['clients']) <= set(CLIENTS))
    require(isinstance(cap['required'], dict) and set(cap['required']) == set(cap['clients'])
            and all(type(v) is bool for v in cap['required'].values()))
    require(isinstance(cap['purpose'], dict) and set(cap['purpose']) == {'when', 'inputs', 'outputs', 'limits'}
            and all(text(v) for v in cap['purpose'].values()))
    origin = cap['origin']
    require(isinstance(origin, dict) and set(origin) == {'kind', 'locator', 'revision'})
    require(origin['kind'] in ('repository', 'git', 'marketplace', 'remote', 'package'))
    safe_locator(origin['locator'])
    require(origin['revision'] is None or text(origin['revision']))
    require(cap['declared_version'] is None or text(cap['declared_version']))
    files = cap['files']
    require(isinstance(files, dict) and set(files) == {'common', *CLIENTS})
    require(all(strings(v, 100) for v in files.values()))
    paths = [p for values in files.values() for p in values]
    require(len(paths) <= 100 and len(paths) == len(set(paths)), 'file_count')
    if os.name == 'nt':
        require(len(paths) == len({p.casefold() for p in paths}), 'duplicate_path')
    for path in paths:
        relative_path(path)
        require(path != 'skills-lock.json', 'recursive_identity')
    permissions = cap['permissions']
    require(isinstance(permissions, dict) and set(permissions) == PERMISSIONS
            and all(strings(v) for v in permissions.values()))
    require(all(re.fullmatch(r'[A-Z_][A-Z0-9_]*', v) for v in permissions['credential_env']))
    for destination in permissions['network']:
        safe_locator(destination)
    require(isinstance(cap['native'], dict) and set(cap['native']) <= set(cap['clients']))
    for native in cap['native'].values():
        require(isinstance(native, dict) and set(native) <= NATIVE and identifier(native.get('server')))
        require(native.get('transport') in ('http', 'stdio'))
        require(native.get('enabled') is None or type(native['enabled']) is bool)
        for name in ('args', 'credential_env', 'allow_tools', 'deny_tools'):
            require(strings(native.get(name, [])))
        require(all(re.fullmatch(r'[A-Z_][A-Z0-9_]*', v) for v in native.get('credential_env', [])))
        if native['transport'] == 'http':
            safe_locator(native.get('url'))
            require(native['url'].startswith(('http://', 'https://')))
        else:
            require(text(native.get('command')) and native['command'])
    expected = cap['expected']
    require(isinstance(expected, dict) and set(expected) == {'contract_sha256', 'files_sha256'})
    require(isinstance(expected['files_sha256'], dict) and set(expected['files_sha256']) == set(cap['clients']))
    require(all(v is None or (isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v))
                for v in [expected['contract_sha256'], *expected['files_sha256'].values()]))
    return cap


def catalog_from_bytes(data):
    raw = parse_json(data)
    require(isinstance(raw, dict) and type(raw.get('version')) is int and raw['version'] in (2, 3))
    if raw['version'] == 2:
        catalog = legacy_catalog(raw)
    else:
        require(set(raw) <= {'version', 'capabilities', 'clientes', 'nota', 'note_en', *LEGACY})
        catalog = copy.deepcopy(raw.get('capabilities'))
        require(isinstance(catalog, list))
        for cap in catalog:
            require(isinstance(cap, dict))
            if 'legacy_ref' in cap:
                require('origin' not in cap and 'declared_version' not in cap)
                cap['origin'], cap['declared_version'] = legacy_identity(raw, cap.pop('legacy_ref'))
    require(len(catalog) <= 200, 'capability_limit')
    for cap in catalog:
        validate_capability(cap)
    require(len(catalog) == len({c['id'] for c in catalog}), 'duplicate_id')
    return catalog


def load_catalog(root):
    return catalog_from_bytes(read_inputs(root, ['skills-lock.json'])['skills-lock.json'])


CONFIG_FILES = {'claude': ('.mcp.json', '.claude/settings.json'),
                'codex': ('.codex/config.toml', '.codex/hooks.json')}
COVERAGE = ['project_files_only', 'global_config_unobserved', 'plugins_unobserved',
            'managed_policy_unobserved', 'sandbox_unobserved', 'credentials_unobserved',
            'runtime_unobserved', 'client_version_unobserved']


def value_digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def existing_inputs(root, paths):
    present = []
    for relative in sorted(set(paths)):
        relative_path(relative)
        if safe_path(root, relative).exists():
            present.append(relative)
    return present


def native_projection(native):
    """Only hashes, booleans and fixed enums leave native configuration parsers."""
    return {key: (value if key in ('enabled', 'transport') else value_digest(value))
            for key, value in native.items() if key != 'server'}


def inspect_client(root, client, *, records=None):
    require(client in CLIENTS, 'invalid_client')
    paths = CONFIG_FILES[client]
    if records is None:
        records = read_inputs(root, existing_inputs(root, paths))
    result = dict(files={p: hashlib.sha256(records[p]).hexdigest() if p in records else None for p in paths},
                  servers={}, permissions={}, codes=[], coverage=list(COVERAGE))
    codes = set()
    docs = {}
    for relative in paths:
        if relative not in records:
            continue
        try:
            data = records[relative]
            parsed = tomllib.loads(data.decode('utf-8-sig')) if relative.endswith('.toml') else parse_json(data)
            require(isinstance(parsed, dict))
            docs[relative] = parsed
        except (ValueError, TypeError, UnicodeError, RecursionError):
            codes.add('config_read_failed')
    main = docs.get(paths[0], {})
    settings = docs.get(paths[1], {})
    known_main = {'mcpServers'} if client == 'claude' else {'mcp_servers', 'skills', 'agents', 'features', 'hooks'}
    known_settings = {'permissions', 'hooks', 'attribution', 'enabledMcpjsonServers',
                      'disabledMcpjsonServers', 'enableAllProjectMcpServers'} if client == 'claude' else {'hooks'}
    if set(main) - known_main or set(settings) - known_settings:
        codes.add('unsupported_fields')
    if settings.get('hooks') or main.get('hooks'):
        codes.add('hooks_present')
    permissions = settings.get('permissions', {})
    if not isinstance(permissions, dict):
        codes.add('config_read_failed')
        permissions = {}
    if set(permissions) - {'allow', 'deny', 'ask'}:
        codes.add('unsupported_fields')
    for action in ('allow', 'deny', 'ask'):
        rules = permissions.get(action, [])
        if not strings(rules):
            codes.add('config_read_failed')
            rules = []
        result['permissions'][action] = [value_digest(rule) for rule in sorted(rules)]
    # Keep only fingerprints; retain per-server scope so unrelated rules do not create drift.
    result['mcp_permissions'] = {}
    servers = main.get('mcpServers' if client == 'claude' else 'mcp_servers', {})
    if not isinstance(servers, dict):
        codes.add('config_read_failed')
        servers = {}
    require(len(servers) <= 200, 'capability_limit')
    for name, entry in servers.items():
        server_codes = set()
        if not isinstance(entry, dict) or not identifier(name):
            codes.add('config_read_failed')
            continue
        if client == 'claude':
            scoped = dict(allow=[], deny=[], ask=[], unknown=False)
            prefix = f'mcp__{name}__'
            for action in ('allow', 'deny', 'ask'):
                for rule in permissions.get(action, []) if strings(permissions.get(action, [])) else []:
                    if rule.startswith(prefix):
                        tool = rule[len(prefix):]
                        if re.fullmatch(r'[A-Za-z0-9_.-]+', tool):
                            scoped[action].append(value_digest(rule))
                        else:
                            scoped['unknown'] = True
                    elif rule.startswith('mcp') and (rule == f'mcp__{name}' or '*' in rule):
                        scoped['unknown'] = True
            result['mcp_permissions'][value_digest(name)] = scoped
        known = ({'type', 'url', 'command', 'args', 'env', 'headers'} if client == 'claude' else
                 {'url', 'command', 'args', 'env', 'env_vars', 'enabled', 'required', 'enabled_tools',
                  'disabled_tools', 'bearer_token_env_var', 'http_headers', 'env_http_headers',
                  'startup_timeout_sec', 'tool_timeout_sec'})
        if set(entry) - known:
            server_codes.add('unsupported_fields')
        transport = entry.get('type', 'http' if 'url' in entry else 'stdio')
        if transport not in ('http', 'stdio'):
            server_codes.add('unsupported_transport')
            transport = 'unsupported'
        projected = dict(transport=transport)
        if client == 'codex':
            enabled = entry.get('enabled', True)
            if type(enabled) is not bool:
                server_codes.add('config_read_failed')
                enabled = None
            projected['enabled'] = enabled
        else:
            # Loading project config is not proof of native approval or effective activation.
            projected['enabled'] = None
            codes.add('native_approval_unobserved')
        for field in ('url', 'command'):
            if field in entry:
                if not text(entry[field]):
                    server_codes.add('config_read_failed')
                else:
                    projected[field] = entry[field]
        if 'url' in entry:
            try:
                safe_locator(entry['url'])
            except ValueError:
                server_codes.add('sensitive_config')
        args = entry.get('args', [])
        if not isinstance(args, list) or not all(text(v) for v in args):
            server_codes.add('config_read_failed')
            args = []
        projected['args'] = args
        if args:
            server_codes.add('arguments_require_review')
            if any(re.search(r'(?i)token|secret|password|credential|api.?key|bearer', v) for v in args):
                server_codes.add('sensitive_config')
        if entry.get('env') or entry.get('headers') or entry.get('http_headers'):
            server_codes.add('sensitive_config')
        credentials = entry.get('env_vars', [])
        if not strings(credentials):
            credentials = []
            server_codes.add('config_read_failed')
        credentials = list(credentials)
        if 'bearer_token_env_var' in entry:
            credentials.append(entry['bearer_token_env_var'])
        env_headers = entry.get('env_http_headers', {})
        if isinstance(env_headers, dict):
            credentials.extend(env_headers.values())
        else:
            server_codes.add('config_read_failed')
        if not all(isinstance(v, str) and re.fullmatch(r'[A-Z_][A-Z0-9_]*', v) for v in credentials):
            server_codes.add('config_read_failed')
            credentials = []
        projected['credential_env'] = sorted(set(credentials))
        for native_key, actual_key in [('allow_tools', 'enabled_tools'), ('deny_tools', 'disabled_tools')]:
            if client == 'codex' and actual_key in entry:
                if strings(entry[actual_key]):
                    projected[native_key] = sorted(entry[actual_key])
                else:
                    server_codes.add('config_read_failed')
        result['servers'][value_digest(name)] = dict(values=native_projection(projected), codes=sorted(server_codes))
        codes.update(server_codes)
    result['codes'] = sorted(codes)
    return result


def config_observation(cap, client, observed):
    native = cap['native'].get(client)
    if not native:
        return None, []
    server = observed['servers'].get(value_digest(native['server']))
    if server is None:
        return 'missing', ['server_missing']
    codes = server['codes']
    if 'config_read_failed' in codes:
        return 'failed', codes
    if 'unsupported_fields' in codes or 'unsupported_transport' in codes:
        return 'unsupported', codes
    wanted = native_projection({k: sorted(v) if k in ('allow_tools', 'deny_tools', 'credential_env') else v
                                for k, v in native.items()})
    if client == 'claude':
        # Native allow/deny patterns differ from Codex filters; exact MCP rules only.
        rules = observed['mcp_permissions'][value_digest(native['server'])]
        if rules['unknown']:
            return 'unverified', ['permission_patterns_unverified']
        for key, action in [('allow_tools', 'allow'), ('deny_tools', 'deny')]:
            wanted.pop(key, None)
            expected = [value_digest(f"mcp__{native['server']}__{tool}") for tool in native.get(key, [])]
            if set(expected) != set(rules[action]):
                return 'changed', ['permission_difference']
        if rules['ask'] or set(rules['allow']) & set(rules['deny']):
            return 'changed', ['permission_difference']
        if native.get('enabled') is not None:
            return 'unverified', ['native_approval_unobserved']
    if any(server['values'].get(k) != v for k, v in wanted.items()):
        return 'changed', ['config_difference']
    if 'sensitive_config' in codes or 'arguments_require_review' in codes:
        return 'unverified', codes
    return 'matched', codes


def audit(root, client):
    try:
        require(client in (*CLIENTS, 'both'), 'invalid_client')
        selected = CLIENTS if client == 'both' else (client,)
        first = read_inputs(root, ['skills-lock.json'])['skills-lock.json']
        catalog = catalog_from_bytes(first)
        paths = {'skills-lock.json'}
        for c in selected:
            paths.update(CONFIG_FILES[c])
            for cap in catalog:
                if c in cap['clients']:
                    paths.update(cap['files']['common'] + cap['files'][c])
        records = read_inputs(root, existing_inputs(root, paths))
        require(records.get('skills-lock.json') == first, 'input_changed')
        configs = {c: inspect_client(root, c, records=records) for c in selected}
        hashes = {p: hashlib.sha256(records[p]).hexdigest() if p in records else None for p in sorted(paths)}
        observations = []
        for cap in catalog:
            for c in selected:
                if c not in cap['clients']:
                    continue
                files = cap['files']['common'] + cap['files'][c]
                codes = []
                expected = cap['expected']
                if any(p not in records for p in files):
                    content = 'missing'
                    codes.append('file_missing')
                elif expected['contract_sha256'] and expected['contract_sha256'] != contract_digest(cap):
                    content = 'changed'
                    codes.append('contract_difference')
                elif files and expected['files_sha256'][c] and records_digest({p: records[p] for p in files}) != expected['files_sha256'][c]:
                    content = 'changed'
                    codes.append('content_difference')
                elif (not expected['contract_sha256'] or not expected['files_sha256'][c]
                      or cap['scope'] == 'inventory' or cap['kind'] in ('mcp', 'runtime')):
                    content = 'unverified'
                    codes.append('implementation_unobserved')
                else:
                    content = 'matched'
                for p in files:
                    data = records.get(p, b'')
                    if re.search(rb'(?m)^allowed-tools\s*:', data):
                        codes.append('skill_grants')
                    if re.search(rb'!`|(?m:^hooks\s*:)', data):
                        codes.append('dynamic_instructions')
                config_state, config_codes = config_observation(cap, c, configs[c])
                states = [content, config_state]
                state = next(s for s in ('failed', 'unsupported', 'missing', 'changed', 'unverified', 'matched') if s in states)
                observations.append(dict(id=cap['id'], client=c, required=cap['required'][c], state=state,
                    content_state=content, config_state=config_state, codes=sorted(set(codes + config_codes)),
                    input_hashes={p: hashes[p] for p in sorted({'skills-lock.json', *files, *CONFIG_FILES[c]})},
                    observed_version=None, runtime_proof=None))
        coverage = dict(limits=list(COVERAGE), files=hashes,
                        clients={c: dict(codes=configs[c]['codes'], server_count=len(configs[c]['servers'])) for c in selected})
        if not any(o['required'] for o in observations):
            coverage['limits'].append('no_required_capabilities')
        for c in selected:
            declared = {value_digest(cap['native'][c]['server']) for cap in catalog if c in cap['native']}
            if set(configs[c]['servers']) - declared:
                coverage['clients'][c]['codes'].append('uncatalogued_servers')
        unsafe = any('config_read_failed' in cfg['codes'] for cfg in configs.values())
        pending = any(o['required'] and o['state'] != 'matched' for o in observations)
        return dict(schema=1, client=client, observations=observations, coverage=coverage,
                    exit_code=2 if unsafe else (1 if pending else 0))
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return dict(schema=1, client=client, observations=[], coverage=dict(limits=list(COVERAGE)),
                    codes=['invalid_or_unreadable_input'], exit_code=2)


def render_result(result, as_json):
    # JSON escaping also makes terminal control characters inert in text mode.
    return json.dumps(result, ensure_ascii=True, indent=2 if as_json else None, sort_keys=True)


REVIEW_BASE = '.operacao-local/capabilities'


def verify_review_storage(root, destination=None):
    private = (REVIEW_BASE, '.operacao-local/docling', 'vault/local')
    for path in private:
        safe_path(root, path + '/.probe')
    identity = parse_json(read_inputs(root, ['vault/project.json'])['vault/project.json'])
    project = str(uuid.UUID(identity['project_id']))
    rules = read_inputs(root, ['.gitignore'])['.gitignore'].splitlines()
    detected = git(root, 'rev-parse', '--show-toplevel')
    if detected.returncode:
        require(b'not a git repository' in detected.stderr.lower(), 'storage_not_ready')
        require(all(('/' + p + '/').encode() in rules for p in private), 'storage_not_ready')
        require(not any(line.startswith(b'!') for line in rules), 'ignore_negation_requires_git')
    else:
        tracked = git(root, 'ls-files', '-z', '--', *private)
        require(tracked.returncode == 0 and not tracked.stdout, 'private_storage_tracked')
        probes = [p + '/.probe' for p in private]
        probes += [REVIEW_BASE + '/reviews/.probe.json', '.operacao-local/docling/lock.json']
        if destination:
            probes.append(destination)
        for probe in probes:
            safe_path(root, probe)
            require(git(root, 'check-ignore', '--quiet', '--', probe).returncode == 0, 'storage_not_ready')
    return project


def review_payload(root, capability_id, client):
    require(identifier(capability_id) and client in (*CLIENTS, 'both'), 'invalid_review')
    project = verify_review_storage(root)
    result = audit(root, client)
    require(result['exit_code'] != 2, 'invalid_review_inputs')
    observations = [o for o in result['observations'] if o['id'] == capability_id]
    require(bool(observations), 'unknown_capability')
    # Use the same manifest revision that the auditor read, not a later catalog silently.
    data = read_inputs(root, ['skills-lock.json', 'vault/project.json'])
    manifest_hash = hashlib.sha256(data['skills-lock.json']).hexdigest()
    require(all(o['input_hashes']['skills-lock.json'] == manifest_hash for o in observations), 'input_changed')
    cap = next(c for c in catalog_from_bytes(data['skills-lock.json']) if c['id'] == capability_id)
    hashes = {p: digest for o in observations for p, digest in o['input_hashes'].items()}
    hashes['vault/project.json'] = hashlib.sha256(data['vault/project.json']).hexdigest()
    proposals = {}
    for o in observations:
        c = o['client']
        native = cap['native'].get(c, {})
        proposals[c] = dict(file=CONFIG_FILES[c][0], capability_id=capability_id,
                            manifest_reference='skills-lock.json', fields=sorted(native),
                            expected=native_projection(native), action='manual_review_required')
    return dict(schema=1, project_id=project, capability_id=capability_id, client=client,
                input_hashes=dict(sorted(hashes.items())), observations=observations,
                coverage=result['coverage']['clients'], proposals=proposals,
                authorization='not_asserted')


def inputs_current(root, hashes):
    require(isinstance(hashes, dict) and len(hashes) <= 205, 'invalid_review')
    records = read_inputs(root, existing_inputs(root, list(hashes)))
    return all((hashlib.sha256(records[p]).hexdigest() if p in records else None) == digest
               for p, digest in hashes.items())


def prepare_review(root, capability_id, client):
    verify_review_storage(root)
    with project_lock(root):
        payload = review_payload(root, capability_id, client)
        data = canonical(payload)
        require(len(data) <= FILE_LIMIT, 'file_limit')
        digest = hashlib.sha256(data).hexdigest()
        relative = f'{REVIEW_BASE}/reviews/{digest}.json'
        verify_review_storage(root, relative)
        require(inputs_current(root, payload['input_hashes']), 'input_changed')
        path = safe_path(root, relative)
        if path.exists():
            require(read_inputs(root, [relative])[relative] == data, 'review_tampered')
        else:
            atomic_write(root, relative, data,
                         before_write=lambda temporary: verify_review_storage(root, temporary))
        return dict(digest=digest, path=relative, state='prepared', authorization='not_asserted')


def check_review(root, digest):
    result = dict(digest=digest if isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) else None,
                  state='failed', codes=[], authorization='not_asserted')
    try:
        require(result['digest'] is not None, 'invalid_review')
        relative = f'{REVIEW_BASE}/reviews/{digest}.json'
        project = verify_review_storage(root, relative)
        data = read_inputs(root, [relative])[relative]
        require(hashlib.sha256(data).hexdigest() == digest, 'review_tampered')
        payload = parse_json(data)
        require(payload['schema'] == 1 and payload['project_id'] == project, 'wrong_project')
        result['state'] = 'current' if inputs_current(root, payload['input_hashes']) else 'changed'
        if result['state'] == 'changed':
            result['codes'] = ['input_changed']
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        result['codes'] = ['invalid_review_or_storage']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('list', 'describe', 'audit', 'review'):
        sub = commands.add_parser(name)
        sub.add_argument('--json', action='store_true')
        if name == 'describe':
            sub.add_argument('id')
        if name in ('audit', 'review'):
            sub.add_argument('--client', choices=(*CLIENTS, 'both'), default='both')
        if name == 'review':
            group = sub.add_mutually_exclusive_group(required=True)
            group.add_argument('--id')
            group.add_argument('--check')
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve(strict=True)
        if args.command == 'audit':
            result = audit(root, args.client)
            print(render_result(result, args.json))
            return result['exit_code']
        if args.command == 'review':
            result = check_review(root, args.check) if args.check else prepare_review(root, args.id, args.client)
            print(render_result(result, args.json))
            return {'prepared': 0, 'current': 0, 'changed': 1, 'failed': 2}[result['state']]
        catalog = load_catalog(root)
        if args.command == 'list':
            result = [{k: cap[k] for k in ('id', 'kind', 'purpose', 'clients')} for cap in catalog]
        else:
            result = next((cap for cap in catalog if cap['id'] == args.id), None)
            require(result is not None, 'unknown_capability')
        print(render_result(result, args.json))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print(json.dumps({'state': 'failed', 'codes': ['invalid_or_unreadable_input']}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
