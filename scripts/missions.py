"""Prepare product missions locally. No model dispatch, test runner or deployment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
import capabilities
from capabilities import canonical, parse_json, read_inputs, text
from document_store import safe_path, atomic_write
from mission_config import CONFIG_PATH, ROLES, OPTIONAL_ROLES, normalize_config, load_config, effective_config, config_digest, config_gaps
from mission_backlog import identity, project_id, read_item, validate_graph, require
import mission_store as store
from mission_vault import project_receipt


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def load_input(root, path):
    return parse_json(read_inputs(root, [path])[path])


def config_report(config):
    return dict(schema_version=1, config=config, digest=config_digest(config), gaps=config_gaps(config),
                compatibility={role: 'not_verified' for role in config['agents']}, runtime_available=False)


def config_current(root):
    return load_config(root) if safe_path(root, CONFIG_PATH).exists() else None


def apply_config(root, raw, expected_digest):
    config = normalize_config(raw)
    require(expected_digest is None or (isinstance(expected_digest, str) and len(expected_digest) == 64), 'invalid_digest')
    current = config_current(root)
    require((config_digest(current) if current else None) == expected_digest, 'config_conflict')
    with store.transaction(root):
        current = config_current(root)
        require((config_digest(current) if current else None) == expected_digest, 'config_conflict')
        atomic_write(root, CONFIG_PATH, json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    return config_report(config)


def project_result(root, receipt):
    try:
        result = project_receipt(root, receipt, store.get_record(root, receipt['record_id']))
        return dict(receipt, projection_state=result['state'], paths=result['paths'])
    except (ValueError, OSError):
        return dict(receipt, projection_state='pending', paths=[])


def commit(root, record, revision, operation, actor):
    with store.transaction(root) as conn:
        receipt = store.commit_record(conn, record=record, expected_revision=revision,
                                      operation_id=operation, actor=actor, now=utc_now())
    return project_result(root, receipt)


def operation(root, request, revision, operation_id, actor):
    digest = store.request_hash(dict(request, operation_id=operation_id), actor, revision)
    receipt = store.replay(root, operation_id, digest)
    return project_result(root, receipt) if receipt else None


def import_item(root, note_path, expected_revision, operation_id, actor):
    item = read_item(root, note_path)
    store.actor_valid(actor)
    require(actor['role'] == ('tech_lead' if item['kind'] == 'pbi' else 'pm'), 'invalid_actor')
    request = dict(action='import', item=item)
    repeated = operation(root, request, expected_revision, operation_id, actor)
    if repeated:
        return repeated
    old = store.get_record(root, item['id'])
    require((old['revision'] if old else 0) == expected_revision, 'revision_conflict')
    if old:
        previous_path = old['snapshot']['note_path']
        require(previous_path == note_path or not safe_path(root, previous_path).exists(), 'identity_conflict')
    for record in store.list_records(root, item['kind']):
        require(record['id'] == item['id'] or record['snapshot']['note_path'] != note_path, 'identity_conflict')
    snapshot = dict(item, state='draft' if item['gaps'] else 'refined')
    return commit(root, dict(id=item['id'], kind=item['kind'], snapshot=snapshot, _request=request),
                  expected_revision, operation_id, actor)


def validate_request(request):
    require(isinstance(request, dict) and set(request) == {'title', 'feature_ids', 'priority', 'overrides', 'scope_reference'}, 'invalid_request')
    require(text(request['title'], 500) and request['title'].strip(), 'invalid_request')
    require(text(request['scope_reference'], 8000), 'invalid_request')
    for key in ('feature_ids', 'priority'):
        value = request[key]
        require(isinstance(value, list) and len(value) <= 5000, 'invalid_request')
        for entry in value:
            identity(entry)
        require(len(value) == len(set(value)), 'invalid_request')
    require(request['feature_ids'], 'invalid_request')
    effective_config(normalize_config(dict(schema_version=1, agents={role: {} for role in ROLES + OPTIONAL_ROLES})), request['overrides'])


def capability_snapshot(root, config):
    selected = [(role, agent['client'], cap) for role, agent in config['agents'].items() for cap in agent['capabilities']]
    if not selected:
        return [], []
    try:
        catalog = {cap['id']: cap for cap in capabilities.load_catalog(root)}
    except (ValueError, OSError):
        catalog = {}
    reports, observations, gaps = {}, [], []
    for role, client, cap_id in selected:
        cap = catalog.get(cap_id)
        if cap is None:
            gaps.append(f'capability:{cap_id}:unknown')
            observations.append(dict(id=cap_id, role=role, state='unknown', runtime_proof=None))
            continue
        if client not in ('claude', 'codex'):
            gaps.append(f'capability:{cap_id}:client_pending')
            continue
        if client not in reports:
            reports[client] = capabilities.audit(root, client)
        report = reports[client]
        observation = next((o for o in report.get('observations', []) if o['id'] == cap_id and o['client'] == client), None)
        state = observation['state'] if observation else 'unverified'
        observations.append(dict(id=cap_id, role=role, client=client, contract_sha256=capabilities.contract_digest(cap),
                                 observation=observation, coverage=report.get('coverage'), state=state))
        if state != 'matched':
            gaps.append(f'capability:{cap_id}:{state}')
    return observations, gaps


def frozen_inputs(root, items):
    paths = {'vault/product/profile.md'}
    for record in items:
        item = record['snapshot']
        paths.add(item['note_path'])
        paths.update(ref['path'] for ref in item['references'])
    data = read_inputs(root, sorted(paths))
    return {p: hashlib.sha256(value).hexdigest() for p, value in data.items()}


def build_mission(root, request, defaults):
    records = {r['id']: r for r in store.list_records(root, None) if r['kind'] != 'mission'}
    for feature in request['feature_ids']:
        require(feature in records and records[feature]['kind'] == 'feature', 'unknown_feature')
    selected = set(request['feature_ids'])
    pbis = [r['id'] for r in records.values() if r['kind'] == 'pbi' and
            (r['snapshot']['contract'] or {}).get('parent_id') in selected]
    require(set(request['priority']) == set(pbis), 'invalid_priority')
    selected.update(pbis)
    for feature in request['feature_ids']:
        parent = (records[feature]['snapshot']['contract'] or {}).get('parent_id')
        if parent in records:
            selected.add(parent)
    items = [records[key] for key in sorted(selected)]
    gaps = []
    for record in items:
        saved = record['snapshot']
        current = read_item(root, saved['note_path'])
        require(current['id'] == record['id'], 'identity_conflict')
        if any(current[k] != saved[k] for k in current):
            gaps.append('stale_item:' + record['id'])
        gaps.extend(f"{record['code']}:{gap}" for gap in current['gaps'])
    gaps.extend(f"{entry['code']}:{entry['item_id']}" for entry in validate_graph([r['snapshot'] for r in items]))
    for feature in request['feature_ids']:
        if not any((records[p]['snapshot']['contract'] or {}).get('parent_id') == feature for p in pbis):
            gaps.append('feature_without_pbis:' + feature)
    if not request['scope_reference'].strip():
        gaps.append('scope_reference')
    config = effective_config(defaults, request['overrides'])
    gaps.extend(config_gaps(config))
    observations, cap_gaps = capability_snapshot(root, config)
    gaps.extend(cap_gaps)
    return dict(title=request['title'], feature_ids=request['feature_ids'], pbi_ids=pbis, priority=request['priority'],
                scope_reference=request['scope_reference'], overrides=request['overrides'], config=config,
                config_digest=config_digest(config), inputs=frozen_inputs(root, items), items=items,
                capabilities=observations, gaps=sorted(set(gaps)), state='draft' if gaps else 'prepared',
                runtime_available=False, runnable=False, development='not_started', qa='not_started', production='not_verified')


def prepare_mission(root, request, operation_id, actor):
    validate_request(request)
    store.actor_valid(actor)
    require(actor['role'] == 'pm', 'invalid_actor')
    intent = dict(action='prepare', request=request)
    repeated = operation(root, intent, 0, operation_id, actor)
    if repeated:
        return repeated
    defaults = config_current(root) or normalize_config(dict(schema_version=1, agents={role: {} for role in ROLES}))
    snapshot = build_mission(root, request, defaults)
    return commit(root, dict(id=str(uuid.uuid4()), kind='mission', snapshot=snapshot, _request=intent), 0, operation_id, actor)


def revise_mission(root, mission_id, request, expected_revision, operation_id, actor):
    validate_request(request)
    store.actor_valid(actor)
    require(actor['role'] == 'pm', 'invalid_actor')
    existing = store.get_record(root, mission_id)
    require(existing is not None and existing['kind'] == 'mission', 'unknown_mission')
    intent = dict(action='revise', target=existing['id'], request=request)
    repeated = operation(root, intent, expected_revision, operation_id, actor)
    if repeated:
        return repeated
    require(existing['revision'] == expected_revision, 'revision_conflict')
    # Revisions inherit the frozen configuration. Only explicit overrides can change it.
    snapshot = build_mission(root, request, existing['snapshot']['config'])
    return commit(root, dict(id=existing['id'], kind='mission', snapshot=snapshot, _request=intent), expected_revision, operation_id, actor)


def mission_status(root, mission_id):
    existing = store.get_record(root, mission_id)
    if existing is None:
        return dict(schema_version=1, state='not_initialized' if not (root / store.DB_PATH).exists() else 'not_found',
                    runtime_available=False, runnable=False)
    require(existing['kind'] == 'mission', 'unknown_mission')
    snapshot = existing['snapshot']
    stale = []
    for path, expected in snapshot['inputs'].items():
        try:
            if hashlib.sha256(read_inputs(root, [path])[path]).hexdigest() != expected:
                stale.append(path)
        except (OSError, ValueError):
            stale.append(path)
    current_records = {r['id']: r for r in store.list_records(root, None)}
    for record in snapshot['items']:
        current = current_records.get(record['id'])
        if current is None or current['revision'] != record['revision']:
            stale.append('revision:' + record['id'])
    history = store.events(root, existing['id'])
    state = 'conflict' if any(e['projection_state'] == 'conflict' for e in history) else 'pending' if any(e['projection_state'] != 'current' for e in history) else 'current'
    with store.reader(root) as conn:
        projections = conn.execute('SELECT p.path,p.sha256 FROM projections p JOIN events e ON e.seq=p.sequence WHERE e.record_id=?', (existing['id'],)).fetchall()
    for path, expected in projections:
        try:
            if hashlib.sha256(read_inputs(root, [path])[path]).hexdigest() != expected:
                state = 'conflict'
        except FileNotFoundError:
            if state != 'conflict':
                state = 'pending'
        except (OSError, ValueError):
            state = 'conflict'
    return dict(schema_version=1, id=existing['id'], code=existing['code'], revision=existing['revision'],
                state=snapshot['state'], snapshot=snapshot, gaps=snapshot['gaps'], stale_inputs=sorted(stale),
                events=[{k: v for k, v in e.items() if k not in ('record', 'request_hash')} for e in history],
                projection_state=state, compatibility={role: 'not_verified' for role in snapshot['config']['agents']},
                runtime_available=False, runnable=False, next_action='revise_inputs' if stale else 'complete_gaps' if snapshot['gaps'] else 'runtime_not_available')


def repair(root, identifier):
    record = store.get_record(root, identifier)
    require(record is not None, 'unknown_record')
    results = []
    for event in store.events(root, record['id']):
        with store.reader(root) as conn:
            receipt = store.receipt(conn, event)
        results.append(project_result(root, receipt))
    state = 'conflict' if any(r['projection_state'] == 'conflict' for r in results) else 'pending' if any(r['projection_state'] != 'current' for r in results) else 'current'
    return dict(schema_version=1, record_id=record['id'], projection_state=state, receipts=results)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('invalid_arguments')


def parser():
    p = Parser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--json', action='store_true')
    subs = p.add_subparsers(dest='command', required=True)
    config = subs.add_parser('config').add_subparsers(dest='action', required=True)
    config.add_parser('show')
    for name in ('validate', 'apply'):
        sub = config.add_parser(name)
        sub.add_argument('--input', required=True)
        if name == 'apply':
            sub.add_argument('--expected-digest', required=True)
    backlog = subs.add_parser('backlog').add_subparsers(dest='action', required=True).add_parser('import')
    backlog.add_argument('--note', required=True)
    backlog.add_argument('--expected-revision', type=int, required=True)
    prepare = subs.add_parser('prepare')
    revise = subs.add_parser('revise')
    revise.add_argument('identifier')
    revise.add_argument('--expected-revision', type=int, required=True)
    for sub in (prepare, revise):
        sub.add_argument('--input', required=True)
    for sub in (prepare, revise, backlog):
        sub.add_argument('--operation-id', required=True)
        sub.add_argument('--actor-id', required=True)
        sub.add_argument('--actor-role', choices=('pm', 'tech_lead'), required=True)
    for name in ('status', 'repair'):
        subs.add_parser(name).add_argument('identifier')
    return p


CONFLICTS = {'operation_conflict', 'revision_conflict', 'config_conflict', 'identity_conflict', 'store_busy', 'invalid_store'}
SAFE_ERRORS = CONFLICTS | {'invalid_config', 'invalid_request', 'invalid_arguments', 'invalid_digest', 'invalid_actor',
                         'invalid_revision', 'invalid_identity', 'invalid_priority', 'unknown_mission', 'unknown_feature',
                         'unknown_record', 'foreign_project', 'invalid_contract', 'incompatible_helper'}


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        root = args.root.resolve(strict=True)
        if args.command == 'config':
            if args.action == 'show':
                config = config_current(root)
                result = config_report(config) if config else dict(schema_version=1, state='not_configured')
            else:
                raw = load_input(root, args.input)
                result = config_report(normalize_config(raw)) if args.action == 'validate' else apply_config(root, raw, None if args.expected_digest == 'absent' else args.expected_digest)
        elif args.command in ('prepare', 'revise', 'backlog'):
            actor = dict(id=args.actor_id, role=args.actor_role)
            if args.command == 'backlog':
                result = import_item(root, args.note, args.expected_revision, args.operation_id, actor)
            elif args.command == 'prepare':
                result = prepare_mission(root, load_input(root, args.input), args.operation_id, actor)
            else:
                result = revise_mission(root, args.identifier, load_input(root, args.input), args.expected_revision, args.operation_id, actor)
        else:
            result = mission_status(root, args.identifier) if args.command == 'status' else repair(root, args.identifier)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if result.get('projection_state') in ('pending', 'conflict') else 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        code = str(error) if str(error) in SAFE_ERRORS else 'invalid_input'
        print(json.dumps(dict(schema_version=1, error=code, guidance='Review local inputs and the mission usage guide. No provider was called.')))
        return 1 if code in CONFLICTS else 2


if __name__ == '__main__':
    raise SystemExit(main())
