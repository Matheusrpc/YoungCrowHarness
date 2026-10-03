"""Read selected Markdown contracts as data; never run validation strings."""
import hashlib
from pathlib import Path
import re
import uuid

from capabilities import parse_json, read_inputs, relative_path, text
from vault import metadata, links, local_path

START = '<!-- youngcrow:contract:start -->'
END = '<!-- youngcrow:contract:end -->'
KINDS = ('epic', 'feature', 'pbi')
CONTRACT_FIELDS = {'schema_version', 'project_id', 'parent_id', 'owner', 'objective',
                   'acceptance', 'dor', 'dod', 'validation', 'dependencies', 'references'}


def require(condition, code='invalid_contract'):
    if not condition:
        raise ValueError(code)


def identity(value):
    require(isinstance(value, str), 'invalid_identity')
    try:
        require(str(uuid.UUID(value)) == value, 'invalid_identity')
    except (ValueError, AttributeError):
        raise ValueError('invalid_identity') from None
    return value


def project_id(root):
    raw = parse_json(read_inputs(root, ['vault/project.json'])['vault/project.json'])
    require(isinstance(raw, dict), 'invalid_project')
    return identity(raw.get('project_id'))


def private(path):
    value = path.casefold()
    return any(value == p or value.startswith(p + '/') for p in
               ('vault/local', '.operacao-local', '.runtime', '.superpowers'))


def read_item(root: Path, note_path: str) -> dict:
    try:
        return _read_item(root, note_path)
    except (OSError, UnicodeError, KeyError, TypeError):
        raise ValueError('invalid_backlog_source') from None


def _read_item(root, note_path):
    relative_path(note_path)
    require(note_path.startswith('vault/') and note_path.endswith('.md'), 'invalid_note_path')
    data = read_inputs(root, [note_path])[note_path]
    content = data.decode('utf-8-sig')
    try:
        fields, body = metadata(content)
    except ValueError:
        raise ValueError('invalid_note_metadata') from None
    item_id = identity(fields['id'])
    kind = fields['type']
    require(kind in KINDS, 'invalid_item_kind')
    index = local_path(note_path, fields['index'])
    require(index is not None, 'invalid_index')
    read_inputs(root, [index])
    for target, _ in links(body):
        path = local_path(note_path, target)
        require(path is None or private(note_path) or not private(path), 'public_private_reference')
    contract = None
    references = []
    if START in body or END in body:
        require(body.count(START) == body.count(END) == 1)
        section = body.split(START)[1].split(END)
        require(len(section) == 2)
        match = re.fullmatch(r'\s*```json\s*\n(.*?)\n```\s*', section[0], re.S)
        require(match is not None)
        contract = parse_json(match[1].encode())
        require(isinstance(contract, dict) and set(contract) == CONTRACT_FIELDS)
        require(type(contract['schema_version']) is int and contract['schema_version'] == 1)
        require(identity(contract['project_id']) == project_id(root), 'foreign_project')
        if contract['parent_id'] is not None:
            identity(contract['parent_id'])
        require(contract['owner'] == ('tech_lead' if kind == 'pbi' else 'pm'), 'invalid_owner')
        require(text(contract['objective'], 8000))
        for key in ('acceptance', 'dor', 'dod', 'validation', 'dependencies'):
            values = contract[key]
            require(isinstance(values, list) and len(values) <= 1000)
            require(all(text(v, 8000) and v.strip() for v in values))
            require(len(values) == len(set(values)))
        for dependency in contract['dependencies']:
            identity(dependency)
        require(kind == 'pbi' or not contract['dependencies'], 'invalid_dependency')
        refs = contract['references']
        require(isinstance(refs, list) and len(refs) <= 200)
        seen = set()
        for ref in refs:
            require(isinstance(ref, dict) and set(ref) == {'note_id', 'path'})
            identity(ref['note_id'])
            relative_path(ref['path'])
            require(ref['path'].startswith('vault/') and ref['path'].endswith('.md'), 'invalid_reference')
            require(ref['note_id'] not in seen, 'duplicate_reference')
            seen.add(ref['note_id'])
            require(private(note_path) or not private(ref['path']), 'public_private_reference')
        sources = read_inputs(root, [r['path'] for r in refs])
        for ref in refs:
            source = sources[ref['path']]
            source_fields, _ = metadata(source.decode('utf-8-sig'))
            require(identity(source_fields['id']) == ref['note_id'], 'reference_identity_mismatch')
            references.append(dict(ref, sha256=hashlib.sha256(source).hexdigest()))
    item = dict(id=item_id, kind=kind, title=fields['title'], note_path=note_path,
                note_sha256=hashlib.sha256(data).hexdigest(), contract=contract, references=references)
    item['gaps'] = item_gaps(item)
    return item


def item_gaps(item: dict) -> list[str]:
    contract = item['contract']
    if contract is None:
        return ['missing_contract']
    keys = ['objective', 'acceptance', 'dor', 'dod']
    if item['kind'] != 'epic':
        keys.append('parent_id')
    if item['kind'] == 'pbi':
        keys.extend(['validation', 'references'])
    return [key for key in keys if not contract[key] or
            (isinstance(contract[key], str) and not contract[key].strip())]


def validate_graph(items: list[dict]) -> list[dict]:
    by_id, diagnostics, edges = {}, set(), {}
    for item in items:
        if item['id'] in by_id:
            diagnostics.add(('duplicate_id', item['id']))
        by_id[item['id']] = item
    for key, item in by_id.items():
        contract = item['contract']
        if contract is None:
            continue
        parent = by_id.get(contract['parent_id'])
        kind = item['kind']
        if (kind == 'epic' and contract['parent_id'] is not None) or (kind != 'epic' and
                (parent is None or parent['kind'] != {'feature': 'epic', 'pbi': 'feature'}[kind])):
            diagnostics.add(('invalid_parent', key))
        edges[key] = contract['dependencies']
        for dep in contract['dependencies']:
            if dep not in by_id or by_id[dep]['kind'] != 'pbi':
                diagnostics.add(('invalid_dependency', key))
    # A separate path set avoids recursion depth limits on large backlogs.
    done = set()
    for start in edges:
        stack, active = [(start, False)], set()
        while stack:
            key, leaving = stack.pop()
            if leaving:
                active.discard(key)
                done.add(key)
            elif key in active:
                diagnostics.add(('dependency_cycle', key))
            elif key not in done:
                active.add(key)
                stack.append((key, True))
                stack.extend((dep, False) for dep in edges.get(key, []))
    return [dict(code=code, item_id=key) for code, key in sorted(diagnostics)]
