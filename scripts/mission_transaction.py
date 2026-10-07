"""Private immutable synthetic plans and journals in the installation ledger.

Internal coordination only: this module does not authorize a native profile or
accept executable code, commands or cleanup flags from a client manifest.
"""
import copy
import hashlib
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

import adoption_fs as fs
import mission_controller as controller
import mission_execution as execution
import mission_runs as runs
import mission_sbx as sbx
import mission_store as store
import mission_process as processes

PHASES = ('A', 'B', 'A2')
EVENTS = ('prepare_intent', 'prepared', 'run_intent', 'initialize_intent', 'initialize_gate',
          'initialize_authorization', 'dispatch_intent', 'dispatch_gate', 'dispatch_authorization', 'observed')
PLAN_FIELDS = {'schema_version', 'manifest', 'run_id', 'project_id', 'project_sha256', 'candidate',
               'baseline', 'code_sha256', 'created_ms', 'deadline_ms', 'phases'}
SOURCES = ('mission_transaction.py', 'mission_controller.py', 'mission_execution.py',
           'mission_runs.py', 'mission_sbx.py', 'mission_process.py')


def sha(value):
    return hashlib.sha256(controller.encoded(value)).hexdigest()


def require(value, reason='invalid_execution_plan'):
    if not value:
        raise ValueError(reason)


def code_hashes():
    return {name: hashlib.sha256(fs.checked_path(Path(__file__).parent/name).read_bytes()).hexdigest()
            for name in SOURCES}


def build_plan(*, manifest, project_id, project_sha256, candidate, baseline, code_sha256,
               proxy_ipv4, ca_sha256):
    created = int(time.time()*1000)
    deadline = created + min(manifest['agent_seconds'], 120)*1000
    phases = [controller.phase_manifest(operation_id=str(uuid.uuid4()), nonce=uuid.uuid4().hex,
              deadline_ms=deadline, phase=phase, proxy_ipv4=proxy_ipv4, ca_sha256=ca_sha256,
              placeholder='youngcrow-probe-'+uuid.uuid4().hex) for phase in PHASES]
    plan = copy.deepcopy(dict(schema_version=2, manifest=manifest, run_id=str(uuid.uuid4()),
        project_id=project_id, project_sha256=project_sha256, candidate=candidate, baseline=baseline,
        code_sha256=code_sha256, created_ms=created, deadline_ms=deadline, phases=phases))
    validate_plan(plan)
    return plan


def validate_plan(plan):
    require(type(plan) is dict and set(plan) == PLAN_FIELDS and type(plan['schema_version']) is int
            and plan['schema_version'] == 2)
    runs.manifest_valid(plan['manifest'])
    require(plan['manifest']['fixture_id'] == 'isolated-egress-v1')
    for key in ('run_id', 'project_id'):
        execution.identity(plan[key])
    require(execution.digest(plan['project_sha256']))
    require(type(plan['created_ms']) is int and type(plan['deadline_ms']) is int
            and 1000 < plan['deadline_ms']-plan['created_ms'] <= min(plan['manifest']['agent_seconds'], 120)*1000)
    candidate, baseline = plan['candidate'], plan['baseline']
    require(type(candidate) is dict and set(candidate) == {'id', 'name', 'outer_digest', 'inner_digest'})
    execution.identity(candidate['id'])
    require(sbx._name(candidate['name']) and all(type(candidate[k]) is str and
            re.fullmatch('sha256:[0-9a-f]{64}', candidate[k]) for k in ('outer_digest', 'inner_digest')))
    require(type(baseline) is dict and set(baseline) ==
            {'executable_sha256', 'version', 'daemon', 'daemon_identity', 'observations'}
            and execution.digest(baseline['executable_sha256']) and baseline['version'] == '0.46.0'
            and type(baseline['daemon']) is dict and baseline['daemon'].get('status') == 'running')
    ident = baseline['daemon_identity']
    require(type(ident) is dict and set(ident) == {'pid', 'created_at'} and type(ident['pid']) is int
            and ident['pid'] > 0 and type(ident['created_at']) is str and bool(ident['created_at']))
    observations = baseline['observations']
    queries = {'secret_inventory': ('secret', 'ls', '--json'), 'sandbox_inventory': ('ls', '--json'),
               'candidate_inspect': ('inspect', candidate['name'], '--json'),
               'policy_global': ('policy', 'ls', '--json'), 'policy_candidate': ('policy', 'ls', candidate['name'], '--json')}
    queries.update({'setting_'+k.replace('.', '_'): ('settings', 'get', k, '--json') for k in sbx.SETTINGS})
    require(type(observations) is dict and set(observations) == set(queries))
    require(all(sbx._contract(args, observations[key]) for key, args in queries.items()))
    require(sbx.credential_inventory_empty(observations['secret_inventory']) is True)
    inventory = observations['sandbox_inventory']['sandboxes']
    require(all(row.get('status') == 'stopped' for row in inventory))
    require(sum(row.get('id') == candidate['id'] and row.get('name') == candidate['name'] for row in inventory) == 1)
    inspected = observations['candidate_inspect']
    require(inspected.get('state') == 'stopped' and type(inspected.get('sessions')) is int and inspected['sessions'] == 0
            and inspected.get('image_digest') == candidate['outer_digest'] and inspected.get('cpus') == 2
            and inspected.get('memory') in ('4g', '4096m') and inspected.get('runtime_mounts') == [])
    require(type(plan['code_sha256']) is dict and set(plan['code_sha256']) == set(SOURCES)
            and all(execution.digest(v) for v in plan['code_sha256'].values()))
    phases = plan['phases']
    require(type(phases) is list and len(phases) == 3)
    for phase, manifest in zip(PHASES, phases):
        controller.validate_manifest(manifest)
        require(manifest['relay']['phase'] == phase and manifest['deadline_ms'] == plan['deadline_ms'])
    require(len({m['operation_id'] for m in phases} | {plan['manifest']['operation_id']}) == 4
            and len({m['nonce'] for m in phases}) == 3)
    require(len(controller.encoded(plan)) <= 32768, 'execution_record_limit')


def request(plan):
    manifest = plan['manifest']
    return dict(schema_version=1, operation_id=manifest['operation_id'], mission_id=manifest['mission_id'],
        project_id=plan['project_id'], project_sha256=plan['project_sha256'], manifest_sha256=sha(manifest),
        baseline_sha256=sha(plan['baseline']), executable_sha256=plan['baseline']['executable_sha256'],
        candidate_digest=plan['candidate']['outer_digest'], authorization_sha256=sha(manifest['authorization_ref']),
        deadline_ms=plan['deadline_ms'])


def validate_record(record):
    require(set(record) == {'schema_version', 'request', 'plan', 'plan_sha256', 'state', 'revision',
                           'created_at', 'updated_at', 'journal', 'recovery', 'owner'}, 'execution_reservation_invalid')
    require(type(record['schema_version']) is int and record['schema_version'] == 2
            and record['state'] in ('reserved', 'consumed', 'recovered')
            and type(record['revision']) is int and record['revision'] > 0
            and all(type(record[k]) is str for k in ('created_at', 'updated_at')),
            'execution_reservation_invalid')
    validate_plan(record['plan'])
    require(record['plan_sha256'] == sha(record['plan']) and record['request'] == request(record['plan']),
            'execution_reservation_invalid')
    journal = record['journal']
    require(type(journal) is list and len(journal) <= 30 and type(record['recovery']) is list,
            'execution_reservation_invalid')
    for index, event in enumerate(journal):
        phase = PHASES[index//len(EVENTS)]
        require(type(event) is dict and set(event) == {'phase', 'kind', 'payload', 'at'}
                and event['phase'] == phase and event['kind'] == EVENTS[index % len(EVENTS)]
                and type(event['at']) is str, 'execution_reservation_invalid')
        validate_event(record['plan'], phase, event['kind'], event['payload'])
    require(record['state'] != 'reserved' or not journal, 'execution_reservation_invalid')
    if record['owner'] is not None:
        validate_owner(record['owner'])
    recovery = record['recovery']
    require(len(recovery) <= 128, 'execution_history_limit')
    for entry in recovery:
        require(type(entry) is dict and set(entry) == {'kind', 'payload', 'at'}
                and entry['kind'] in ('started', 'stop_intent', 'workload', 'stop_vm_intent', 'closed')
                and type(entry['payload']) is dict and type(entry['at']) is str, 'execution_reservation_invalid')
    if record['state'] == 'recovered':
        require(recovery and recovery[-1]['kind'] == 'closed', 'execution_reservation_invalid')
        validate_closure(record, recovery[-1]['payload'])
    require(len(controller.encoded(record)) <= execution.MAX_RECORD, 'execution_record_limit')


def reserve(registry, plan):
    validate_plan(plan)
    plan = copy.deepcopy(plan)
    with registry.locked():
        rows = registry.records()
        old = next((r for r in rows if r['request']['operation_id'] == plan['manifest']['operation_id']), None)
        if old:
            require(old.get('schema_version') == 2 and old['plan'] == plan, 'operation_conflict')
            return dict(new=False, record=old)
        require(not any(r['state'] not in ('abandoned', 'recovered') for r in rows), 'execution_reserved')
        require(0 < plan['deadline_ms']-time.time()*1000 <= 120000, 'execution_deadline')
        record = dict(schema_version=2, request=request(plan), plan=plan, plan_sha256=sha(plan), state='reserved',
                      revision=0, created_at=execution.stamp(), updated_at=execution.stamp(), journal=[], recovery=[], owner=None)
        registry.save(record)
        return dict(new=True, record=record)


def load(registry, operation_id):
    execution.identity(operation_id)
    record = next((r for r in registry.records() if r['request']['operation_id'] == operation_id), None)
    require(record is not None and record.get('schema_version') == 2, 'integrated_reservation_missing')
    return record


def validate_event(plan, phase, kind, payload):
    require(phase in PHASES and kind in EVENTS and type(payload) is dict, 'invalid_phase_event')
    manifest = plan['phases'][PHASES.index(phase)]
    identity = dict(operation_id=manifest['operation_id'], nonce=manifest['nonce'], manifest_sha256=sha(manifest))
    require(all(payload.get(k) == v for k, v in identity.items()), 'identity_changed')
    if kind == 'prepare_intent':
        require(set(payload) == {*identity, 'image', 'manifest'} and payload['manifest'] == manifest
                and payload['image'] == plan['candidate']['inner_digest'], 'identity_changed')


def phase_event(registry, operation_id, phase, kind, payload):
    with registry.locked():
        record = load(registry, operation_id)
        require(record['state'] != 'recovered', 'effect_consumed')
        validate_event(record['plan'], phase, kind, payload)
        events = record['journal']
        require(not any(e['phase'] == phase and e['kind'] == kind for e in events), 'effect_consumed')
        require(len(events) < 30 and phase == PHASES[len(events)//len(EVENTS)]
                and kind == EVENTS[len(events) % len(EVENTS)], 'invalid_phase_order')
        require(record['request']['deadline_ms'] > time.time()*1000, 'execution_deadline')
        require(not record['recovery'], 'recovery_started')
        events.append(dict(phase=phase, kind=kind, payload=copy.deepcopy(payload), at=execution.stamp()))
        record['state'] = 'consumed'
        registry.save(record)
        return record


def admit(root, registry, plan):
    """Two durable stores, no effects. A gap between writes is never a new dispatch."""
    validate_plan(plan)
    require(store.project_id(root) == plan['project_id']
            and sha(str(Path(root).resolve(strict=True))) == plan['project_sha256'], 'project_changed')
    old = runs.existing(root, plan['manifest'])
    if old:
        if 'execution_plan_sha256' in old:
            require(old['execution_plan_sha256'] == sha(plan), 'operation_conflict')
        return dict(new=False, run=old)
    _, config = runs.mission_agent(root, plan['manifest'])
    new, run = runs._record_check(root, plan['manifest'], config,
        dict(purpose='isolated_egress_check', state='reserved', reason=None, model_calls=0,
             effects_allowed=False, execution_plan_sha256=sha(plan)), run_id=plan['run_id'], with_new=True)
    require(run.get('execution_plan_sha256') == sha(plan), 'operation_conflict')
    if not new:
        return dict(new=False, run=run)
    reserved = reserve(registry, plan)
    require(reserved['new'], 'effect_consumed')
    return dict(new=True, run=run)


def bound_run(root, record):
    plan = record['plan']
    require(store.project_id(root) == plan['project_id']
            and sha(str(Path(root).resolve(strict=True))) == plan['project_sha256'], 'project_changed')
    run = runs.existing(root, plan['manifest'])
    require(run is not None and run['id'] == plan['run_id']
            and run.get('execution_plan_sha256') == record['plan_sha256'], 'mission_binding_changed')
    return run


def validate_owner(owner):
    require(type(owner) is dict and set(owner) == {'kind', 'name', 'pid'}
            and owner['kind'] in ('linux-group', 'windows-job') and type(owner['name']) is str
            and type(owner['pid']) is int and owner['pid'] > 1, 'invalid_owner')
    execution.identity(owner['name'].removeprefix('Local\\YoungCrow-'))


def claim(root, registry, operation_id, owner):
    """Called by the existing supervisor before releasing its child bootstrap."""
    validate_owner(owner)
    with registry.locked():
        record = load(registry, operation_id)
        require(record['state'] == 'reserved' and record['owner'] is None and not record['recovery'], 'effect_consumed')
        require(record['plan']['deadline_ms'] > time.time()*1000, 'execution_deadline')
        run = bound_run(root, record)
        require(run['state'] == 'reserved', 'effect_consumed')
        runs.mission_agent(root, record['plan']['manifest'])
        run = runs.transition_run(root, run['id'], dict(kind='started', owner=owner), run['revision'], str(uuid.uuid4()))
        record['owner'] = copy.deepcopy(owner)
        registry.save(record)
        return run


def workload_valid(plan, phase, observed):
    manifest = plan['phases'][PHASES.index(phase)]
    require(type(observed) is dict and set(observed) == {'schema_version', 'operation_id', 'nonce',
            'manifest_sha256', 'container_id', 'image', 'state', 'inspection_sha256', 'workload_reaped'},
            'workload_stop_unverified')
    require(type(observed['schema_version']) is int and observed['schema_version'] == 1
            and observed['operation_id'] == manifest['operation_id'] and observed['nonce'] == manifest['nonce']
            and observed['manifest_sha256'] == sha(manifest) and observed['image'] == plan['candidate']['inner_digest']
            and execution.digest(observed['container_id']) and execution.digest(observed['inspection_sha256']),
            'identity_changed')
    state = observed['state']
    require(type(state) is dict and set(state) == {'Status', 'Running', 'Pid'}
            and state['Status'] in ('created', 'running', 'exited', 'dead')
            and type(state['Running']) is bool and type(state['Pid']) is int
            and state['Running'] == (state['Status'] == 'running')
            and (state['Pid'] > 0 if state['Running'] else state['Pid'] == 0)
            and observed['workload_reaped'] is (not state['Running']), 'workload_stop_unverified')
    return not state['Running']


def workload_matches(record, phase, observed):
    terminal = workload_valid(record['plan'], phase, observed)
    identities = []
    for event in record['journal']:
        if event['phase'] == phase:
            if event['kind'] == 'prepared':
                identities.append(event['payload']['observation']['container_id'])
            elif event['kind'] == 'run_intent':
                identities.append(event['payload']['container_id'])
    identities.extend(entry['payload']['observation']['container_id'] for entry in record['recovery']
        if entry['kind'] in ('stop_intent', 'workload') and entry['payload'].get('phase') == phase)
    require(all(cid == observed['container_id'] for cid in identities), 'identity_changed')
    return terminal


def configuration_matches(plan, observed, *, active=False, recovering=False):
    baseline = plan['baseline']
    require(type(observed) is dict and set(observed) == set(baseline)
            and all(observed[k] == baseline[k] for k in ('executable_sha256', 'version', 'daemon')),
            'configuration_changed')
    ident = observed['daemon_identity']
    require(type(ident) is dict and set(ident) == {'pid', 'created_at'} and type(ident['pid']) is int
            and ident['pid'] > 0 and type(ident['created_at']) is str and bool(ident['created_at'])
            and (recovering or ident == baseline['daemon_identity']), 'configuration_changed')
    values = copy.deepcopy(observed['observations'])
    require(type(values) is dict and set(values) == set(baseline['observations']), 'configuration_changed')
    inspected = values['candidate_inspect']
    require(type(inspected) is dict and inspected.get('state') in ('running', 'stopped'), 'configuration_changed')
    if active:
        require(inspected['state'] == 'running', 'configuration_changed')
        inspected['state'] = 'stopped'
        for row in values['sandbox_inventory']['sandboxes']:
            if row.get('id') == plan['candidate']['id']:
                require(row.get('status') == 'running', 'configuration_changed')
                row['status'] = 'stopped'
    require(values == baseline['observations'], 'configuration_changed')


def validate_closure(record, payload):
    require(set(payload) == {'observation', 'observation_sha256', 'owner', 'owner_absent', 'daemon_identity_before'}
            and payload['observation_sha256'] == sha(payload['observation'])
            and payload['daemon_identity_before'] == payload['observation']['daemon_identity']
            and payload['owner'] == record['owner'] and payload['owner_absent'] is True,
            'recovery_unverified')
    configuration_matches(record['plan'], payload['observation'], recovering=True)
    for phase in {event['phase'] for event in record['journal']}:
        receipts = [entry['payload']['observation'] for entry in record['recovery']
                    if entry['kind'] == 'workload' and entry['payload'].get('phase') == phase]
        require(receipts and workload_matches(record, phase, receipts[-1]), 'workload_stop_unverified')


def recover(registry, operation_id, backend, *, timeout_seconds=60):
    """Trusted host observer, never caller-supplied cleanup evidence or commands.

    The backend issues closed metadata/stop operations and returns native values.
    Global settings/credential mutations belong to the subsequent egress increment;
    any such drift here is preserved and keeps the installation reserved.
    """
    require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 60, 'invalid_recovery_deadline')
    until = time.monotonic()+timeout_seconds
    def remaining():
        require(time.monotonic() < until, 'recovery_deadline')
    with registry.locked():
        record = load(registry, operation_id)
        def result(state, reason):
            return dict(state=state, reason=reason, operation_id=operation_id, model_calls=0,
                        proof_accepted=False, effects_allowed=False)
        if record['state'] == 'recovered':
            return result('recovered', 'resources_observed')
        def save(kind, **payload):
            remaining()
            # One receipt per phase is sufficient; failed read-only retries cannot
            # consume the bounded history needed to close this reservation.
            if kind in ('started', 'workload') and any(e['kind'] == kind
                    and e['payload'].get('phase') == payload.get('phase') for e in record['recovery']):
                return
            record['recovery'].append(dict(kind=kind, payload=payload, at=execution.stamp()))
            registry.save(record)
            remaining()
        try:
            remaining()
            require(record['owner'] is None or processes.owner_gone(record['owner']), 'owner_still_present')
            require(callable(getattr(backend, 'bind_deadline', None)), 'recovery_unverified')
            backend.bind_deadline(until)
            save('started', timeout_seconds=timeout_seconds)
            observed = backend.observe()
            remaining()
            active = observed['observations']['candidate_inspect']['state'] == 'running'
            configuration_matches(record['plan'], observed, active=active, recovering=True)
            daemon_identity_before = copy.deepcopy(observed['daemon_identity'])
            phases = [phase for phase in PHASES if any(e['phase'] == phase for e in record['journal'])]
            for phase in phases:
                if active:
                    workload = backend.workload(phase)
                    remaining()
                    if not workload_matches(record, phase, workload):
                        require(not any(e['kind'] == 'stop_intent' and e['payload'].get('phase') == phase
                                        for e in record['recovery']), 'stop_consumed')
                        save('stop_intent', phase=phase, observation=workload)
                        workload = backend.workload(phase, stop=True)
                    require(workload_matches(record, phase, workload), 'workload_stop_unverified')
                    save('workload', phase=phase, observation=workload)
                else:
                    previous = [e['payload']['observation'] for e in record['recovery']
                                if e['kind'] == 'workload' and e['payload'].get('phase') == phase]
                    require(previous and workload_matches(record, phase, previous[-1]), 'workload_stop_unverified')
            if active:
                require(phases, 'unowned_active_candidate')
                require(not any(e['kind'] == 'stop_vm_intent' for e in record['recovery']), 'stop_consumed')
                save('stop_vm_intent', candidate=record['plan']['candidate'])
                backend.stop_vm()
                remaining()
            observed = backend.observe()
            remaining()
            configuration_matches(record['plan'], observed, recovering=True)
            require(record['owner'] is None or processes.owner_gone(record['owner']), 'owner_still_present')
            payload = dict(observation=observed, observation_sha256=sha(observed), owner=record['owner'],
                           owner_absent=True, daemon_identity_before=daemon_identity_before)
            validate_closure(record, payload)
            record['state'] = 'recovered'
            save('closed', **payload)
            return result('recovered', 'resources_observed')
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError, controller.Refused) as error:
            known = {'configuration_changed', 'workload_stop_unverified', 'identity_changed', 'owner_still_present',
                     'stop_consumed', 'unowned_active_candidate', 'recovery_deadline', 'execution_history_limit'}
            return result('blocked', str(error) if str(error) in known else 'recovery_unverified')


def run_reserved(root, registry, operation_id, launcher_factory, observe_identity):
    """Run inside the existing supervisor; dependencies are trusted closed adapters.

    No public native entry point is enabled until egress and recovery of its global
    configuration are integrated. Tests use local processes through this same path.
    """
    result = dict(state='blocked', reason='reconciliation_required', phases=[], model_calls=0,
                  proof_accepted=False, effects_allowed=False)
    record = load(registry, operation_id)
    if record['journal'] or record['recovery'] or record['state'] != 'reserved':
        return result
    try:
        owner = record['owner']
        require(owner is not None and os.getppid() == owner['pid'], 'containment_required')
        if owner['kind'] == 'linux-group':
            require(os.getpgrp() == owner['pid'], 'containment_required')
        plan = record['plan']
        run = bound_run(root, record)
        require(run['state'] == 'running' and run['owner'] == owner, 'mission_binding_changed')
        for phase, manifest in zip(PHASES, plan['phases']):
            def persist(kind, payload):
                if kind in ('prepare_intent', 'dispatch_authorization'):
                    current = load(registry, operation_id)
                    linked = bound_run(root, current)
                    require(linked['state'] == 'running' and linked['owner'] == owner, 'mission_binding_changed')
                    runs.mission_agent(root, plan['manifest'])
                    require(code_hashes() == plan['code_sha256'], 'code_changed')
                    configuration_matches(plan, observe_identity(), active=True)
                phase_event(registry, operation_id, phase, kind, payload)
            observed = controller.run_phase(launcher_factory(phase), manifest,
                                             plan['candidate']['inner_digest'], persist)
            result['phases'].append(observed)
            if observed['state'] != ('blocked_unattributed' if phase == 'B' else 'observed'):
                return result
        result.update(state='observed', reason='native_attribution_and_recovery_required')
    except (ValueError, OSError, TypeError, KeyError):
        result['reason'] = 'preflight_changed'
    return result


def reconcile(root, registry, operation_id, backend):
    """Project closure follows the global receipt, including after a lost reply."""
    record = load(registry, operation_id)
    bound_run(root, record)
    result = recover(registry, operation_id, backend)
    if result['state'] != 'recovered':
        return result
    record = load(registry, operation_id)
    with store.transaction(root) as conn:
        run = runs.find_run(conn, record['plan']['run_id'])
        require(run.get('execution_plan_sha256') == record['plan_sha256'], 'mission_binding_changed')
        if run['state'] in runs.UNRESOLVED:
            revision = run['revision']
            evidence = dict(operation_id=operation_id, plan_sha256=record['plan_sha256'],
                            closure_sha256=sha(record['recovery'][-1]))
            run.update(state='interrupted', reason='execution_recovered', ended_at=runs.now(), evidence=evidence)
            runs.save_event(conn, run, dict(kind='execution_recovered', evidence=evidence), revision,
                            str(uuid.uuid5(uuid.UUID(operation_id), 'execution_recovered')))
        else:
            require(run['reason'] == 'execution_recovered', 'mission_binding_changed')
    return dict(result, run=runs.project(root, run))
