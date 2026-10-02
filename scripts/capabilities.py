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
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
from document_store import safe_path

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


def render_result(result, as_json):
    # JSON escaping also makes terminal control characters inert in text mode.
    return json.dumps(result, ensure_ascii=True, indent=2 if as_json else None, sort_keys=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('list', 'describe'):
        sub = commands.add_parser(name)
        sub.add_argument('--json', action='store_true')
        if name == 'describe':
            sub.add_argument('id')
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(Path(args.root).resolve(strict=True))
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
