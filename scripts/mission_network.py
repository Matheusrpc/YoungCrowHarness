"""Private egress journal and restoration of the two sandbox proxy settings.

Native activation stays gated: custom-credential ownership is not documented.
Policy and credential inventories are immutable; this coordinator accepts only
trusted host adapters, never commands or restoration assertions from a client.
"""
import copy
import hashlib
import ipaddress
from pathlib import Path
import sys
import threading
import time

import mission_egress as egress
import mission_execution as execution
import mission_transaction as tx

KEYS = ('proxy.sandbox', 'no_proxy.sandbox')
require = tx.require


def python_hash():
    return hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()


def plan_config(value):
    require(type(value) is dict and set(value) == {'resolver', 'forbidden_ips'}, 'invalid_network_plan')
    return dict(copy.deepcopy(value), python_sha256=python_hash())


def setting(values, key):
    return values['observations']['setting_'+key.replace('.', '_')]


def validate_plan(plan):
    config = plan['network']
    require(type(config) is dict and set(config) == {'resolver', 'forbidden_ips', 'python_sha256'}
            and config['resolver'] == 'system' and execution.digest(config['python_sha256']), 'invalid_network_plan')
    ips = config['forbidden_ips']
    require(type(ips) is list and len(ips) <= 256 and all(type(ip) is str for ip in ips), 'invalid_network_plan')
    require(len(set(ips)) == len(ips) and all('%' not in ip and str(ipaddress.ip_address(ip)) == ip for ip in ips),
            'invalid_network_plan')
    baseline = plan['baseline']
    require(setting(baseline, 'proxy.sandbox')['value'] in ('', 'direct', 'system')
            and setting(baseline, 'no_proxy.sandbox')['value'] == ''
            and setting(baseline, 'no_proxy')['value'] == '', 'unsafe_proxy_baseline')


def guard_config(plan, phase, port):
    require(phase in ('A', 'A2'), 'invalid_network_phase')
    manifest = plan['phases'][tx.PHASES.index(phase)]
    return dict(schema_version=1, operation_id=manifest['operation_id'], phase=phase,
        nonce=manifest['nonce'], deadline_ms=plan['deadline_ms'], host=egress.HOST, port=443,
        listen_port=port, forbidden_ips=plan['network']['forbidden_ips'][:], max_connections=1)


def entry(record, kind, phase='A', key=None):
    return next((e['payload'] for e in record['network_events'] if e['kind'] == kind
                 and e['phase'] == phase and (key is None or e['payload'].get('key') == key)), None)


def target(record, key):
    ready = entry(record, 'guard_ready')
    require(ready is not None, 'guard_not_ready')
    value = f"socks5h://127.0.0.1:{ready['port']}" if key == 'proxy.sandbox' else ''
    original = setting(record['plan']['baseline'], key)
    return dict(original, value=value, source='default' if value == original['default'] else 'override')


def validate_events(record):
    events = record['network_events']
    require(type(events) is list and len(events) <= 40, 'invalid_network_journal')
    seen = dict(record, network_events=[])
    for item in events:
        require(type(item) is dict and set(item) == {'phase', 'kind', 'payload', 'at'}
                and type(item['at']) is str, 'invalid_network_journal')
        validate_event(seen, item['phase'], item['kind'], item['payload'])
        seen['network_events'].append(item)


def validate_event(record, phase, kind, payload):
    require(type(payload) is dict and phase in ('A', 'B', 'A2', 'recovery'), 'invalid_network_event')
    key = payload.get('key')
    require(entry(record, kind, phase, key) is None, 'effect_consumed')
    plan = record['plan']
    if kind.startswith('guard_'):
        require(phase in ('A', 'A2'), 'invalid_network_phase')
        previous = [e['kind'] for e in record['network_events'] if e['phase'] == phase and e['kind'].startswith('guard_')]
        allowed = {None: ('guard_intent',), 'guard_intent': ('guard_started',),
            'guard_started': ('guard_ready', 'guard_refused'), 'guard_ready': ('guard_request', 'guard_refused'),
            'guard_request': ('guard_destination', 'guard_refused'),
            'guard_destination': ('guard_finished', 'guard_refused'),
            'guard_finished': ('guard_closed',), 'guard_refused': ('guard_closed',),
            'guard_closed': ('guard_reaped',)}
        require(kind in allowed.get(previous[-1] if previous else None, ()), 'invalid_guard_order')
        port = 0 if phase == 'A' else (entry(record, 'guard_ready') or {}).get('port')
        config = guard_config(plan, phase, port)
        if kind == 'guard_intent':
            require(payload == dict(config=config), 'guard_identity_changed')
            require(phase == 'A' or entry(record, 'barrier', 'B') is not None, 'invalid_guard_order')
            return
        if kind == 'guard_started':
            require(set(payload) == {'pid'} and type(payload['pid']) is int and payload['pid'] > 1,
                    'guard_identity_changed')
            return
        pid = entry(record, 'guard_started', phase)['pid']
        if kind == 'guard_reaped':
            ready = entry(record, 'guard_ready', phase)
            require(ready is not None and set(payload) == {'pid', 'port', 'exit_code'}
                    and payload['pid'] == pid and payload['port'] == ready['port']
                    and type(payload['exit_code']) is int and payload['exit_code'] in (0, 125), 'guard_exit_unverified')
            require(payload['exit_code'] == (125 if entry(record, 'guard_refused', phase) else 0), 'guard_exit_unverified')
            return
        identity = {k:config[k] for k in ('operation_id', 'phase', 'nonce')}
        require(all(payload.get(k) == v for k,v in identity.items())
                and type(payload.get('at_ms')) is int, 'guard_identity_changed')
        fields = {k:v for k,v in payload.items() if k not in (*identity, 'at_ms')}
        if kind == 'guard_ready':
            require(set(fields) == {'pid', 'port', 'deadline_ms'} and fields['pid'] == pid
                    and type(fields['port']) is int and 1 <= fields['port'] <= 65535
                    and port in (0, fields['port']) and fields['deadline_ms'] == plan['deadline_ms'], 'guard_identity_changed')
        elif kind == 'guard_request':
            require(fields == dict(host=egress.HOST, port=443), 'origin_forbidden')
        elif kind == 'guard_destination':
            require(set(fields) == {'host', 'port', 'resolved', 'selected_ip', 'peer', 'peer_port', 'family', 'decision'}
                    and type(fields['resolved']) is list, 'destination_forbidden')
            resolved = egress.validate_destination(fields['host'], fields['port'], tuple(fields['resolved']),
                                                  config['forbidden_ips'])
            require(fields['selected_ip'] in resolved and fields['selected_ip'] == fields['peer']
                    and ipaddress.ip_address(fields['peer']).version == 4 and fields['peer_port'] == 443
                    and fields['family'] == 'IPv4' and fields['decision'] == 'connected', 'destination_forbidden')
        elif kind == 'guard_finished':
            require(set(fields) == {'transferred_bytes', 'client_to_upstream_bytes', 'upstream_to_client_bytes'}
                    and all(type(v) is int and 0 <= v <= egress.MAX_BYTES for v in fields.values())
                    and fields['transferred_bytes'] == fields['client_to_upstream_bytes']+fields['upstream_to_client_bytes'],
                    'invalid_guard_counts')
        elif kind == 'guard_refused':
            require(set(fields) == {'reason'} and fields['reason'] in egress.REFUSALS |
                    {'OSError', 'TimeoutError', 'ConnectionError', 'ConnectionResetError', 'BrokenPipeError', 'ValueError'},
                    'invalid_guard_refusal')
        else:
            require(not fields, 'invalid_guard_event')
        return
    if kind == 'barrier':
        ready, reaped = entry(record, 'guard_ready'), entry(record, 'guard_reaped')
        require(phase == 'B' and reaped and reaped['exit_code'] == 0
                and payload == dict(port=ready['port'], available=True), 'guard_exit_unverified')
        return
    restore = phase == 'recovery'
    prefix = 'restore_' if restore else ''
    require(restore or phase == 'A', 'invalid_network_phase')
    if kind in (prefix+'setting_intent', prefix+'setting_observed'):
        require(key in KEYS, 'invalid_network_setting')
        original = setting(plan['baseline'], key)
        applied = target(record, key)
        if restore:
            require(entry(record, 'setting_intent', key=key) is not None, 'unowned_setting')
        if kind.endswith('setting_intent'):
            require(payload == dict(key=key, before=applied if restore else original,
                                    after=original if restore else applied) and original != applied,
                    'invalid_network_setting')
        else:
            require(entry(record, prefix+'setting_intent', phase, key) is not None
                    and payload == dict(key=key, value=original if restore else applied), 'invalid_network_setting')
        return
    if kind == prefix+'restart_intent':
        require(set(payload) == {'before'} and type(payload['before']) is dict
                and set(payload['before']) == {'pid', 'created_at'}
                and type(payload['before']['pid']) is int and payload['before']['pid'] > 0
                and type(payload['before']['created_at']) is str and payload['before']['created_at'], 'invalid_restart')
        require(entry(record, 'setting_intent', key='proxy.sandbox') is not None, 'invalid_restart')
    elif kind == prefix+'restarted':
        intent = entry(record, prefix+'restart_intent', phase)
        require(intent is not None and set(payload) == {'before', 'after'} and payload['before'] == intent['before']
                and type(payload['after']) is dict and set(payload['after']) == {'pid', 'created_at'}
                and type(payload['after']['pid']) is int and payload['after']['pid'] > 0
                and type(payload['after']['created_at']) is str and payload['after']['created_at']
                and payload['after'] != payload['before'], 'restart_unverified')
    else:
        raise ValueError('invalid_network_event')


def append(registry, record, phase, kind, payload):
    require(record['state'] != 'recovered' and record['schema_version'] in (3, 4), 'effect_consumed')
    if phase != 'recovery':
        require(not record['recovery'] and time.time()*1000 < record['plan']['deadline_ms'], 'execution_deadline')
    validate_event(record, phase, kind, payload)
    record['network_events'].append(dict(phase=phase, kind=kind, payload=copy.deepcopy(payload), at=execution.stamp()))
    record['state'] = 'consumed'
    registry.save(record)


def event(registry, operation_id, phase, kind, payload):
    with registry.locked():
        append(registry, tx.load(registry, operation_id), phase, kind, payload)


def matches(record, observed, *, recovering=False):
    """Normalize only exact values covered by our immutable setting intents."""
    value = copy.deepcopy(observed)
    for key in KEYS:
        intent = entry(record, 'setting_intent', key=key)
        if intent:
            actual = setting(value, key)
            allowed = (intent['before'], intent['after']) if recovering else (intent['after'],)
            require(actual in allowed, 'configuration_changed')
            value['observations']['setting_'+key.replace('.', '_')] = copy.deepcopy(intent['before'])
    restarted = entry(record, 'restarted')
    plan = record['plan']
    if restarted and not recovering:
        plan = dict(plan, baseline=dict(plan['baseline'], daemon_identity=restarted['after']))
    tx.configuration_matches(plan, value, active=value['observations']['candidate_inspect']['state'] == 'running',
                             recovering=recovering)


def verify(record, observed):
    require(entry(record, 'restarted') is not None, 'network_not_activated')
    matches(record, observed)


def activate(registry, operation_id, backend):
    with registry.locked():
        record = tx.load(registry, operation_id)
        deadline = tx.controller.Deadline(record['plan']['deadline_ms'])
        backend.bind_deadline(time.monotonic()+deadline.remaining())
        require(entry(record, 'guard_ready') is not None, 'guard_not_ready')
        require(not any(e['kind'] == 'setting_intent' for e in record['network_events']), 'effect_consumed')
        tx.configuration_matches(record['plan'], backend.observe())
        for key in KEYS:
            original, applied = setting(record['plan']['baseline'], key), target(record, key)
            if original == applied:
                continue
            append(registry, record, 'A', 'setting_intent', dict(key=key, before=original, after=applied))
            deadline.remaining()
            backend.setting(key, applied)
            deadline.remaining()
            matches(record, backend.observe())
            append(registry, record, 'A', 'setting_observed', dict(key=key, value=applied))
        before = backend.observe()
        matches(record, before)
        require(before['observations']['candidate_inspect']['state'] == 'stopped', 'configuration_changed')
        append(registry, record, 'A', 'restart_intent', dict(before=before['daemon_identity']))
        deadline.remaining()
        backend.restart()
        deadline.remaining()
        after = backend.observe()
        matches(record, after, recovering=True)
        append(registry, record, 'A', 'restarted', dict(before=before['daemon_identity'], after=after['daemon_identity']))
        verify(record, after)


def ports_absent(record):
    ports = sorted({e['payload']['port'] for e in record['network_events'] if e['kind'] == 'guard_ready'})
    require(all(egress.port_available(port) for port in ports), 'guard_port_occupied')
    return ports


def restore(registry, record, backend, remaining, daemon_identity):
    """Called with the ledger locked, after owner absence and workload/VM stop."""
    def observe():
        remaining()
        observed = backend.observe()
        remaining()
        require(observed['daemon_identity'] == daemon_identity, 'configuration_changed')
        return observed
    for key in KEYS:
        intent = entry(record, 'setting_intent', key=key)
        if not intent:
            continue
        remaining()
        observed = observe()
        matches(record, observed, recovering=True)
        require(observed['observations']['candidate_inspect']['state'] == 'stopped', 'configuration_changed')
        if setting(observed, key) == intent['after']:
            require(entry(record, 'restore_setting_intent', 'recovery', key) is None, 'effect_consumed')
            append(registry, record, 'recovery', 'restore_setting_intent',
                   dict(key=key, before=intent['after'], after=intent['before']))
            remaining()
            backend.setting(key, intent['before'])
            observed = observe()
        remaining()
        matches(record, observed, recovering=True)
        require(setting(observed, key) == intent['before'], 'configuration_changed')
        if entry(record, 'restore_setting_intent', 'recovery', key) and not entry(record, 'restore_setting_observed', 'recovery', key):
            append(registry, record, 'recovery', 'restore_setting_observed', dict(key=key, value=intent['before']))
    if not entry(record, 'setting_intent', key='proxy.sandbox'):
        return daemon_identity
    remaining()
    before = observe()
    tx.configuration_matches(record['plan'], before, recovering=True)
    intent = entry(record, 'restore_restart_intent', 'recovery')
    if intent is None:
        append(registry, record, 'recovery', 'restore_restart_intent', dict(before=before['daemon_identity']))
        remaining()
        backend.restart()
        intent = entry(record, 'restore_restart_intent', 'recovery')
    after = backend.observe()
    remaining()
    tx.configuration_matches(record['plan'], after, recovering=True)
    if not entry(record, 'restore_restarted', 'recovery'):
        append(registry, record, 'recovery', 'restore_restarted', dict(before=intent['before'], after=after['daemon_identity']))
    require(after['daemon_identity'] == entry(record, 'restore_restarted', 'recovery')['after'], 'configuration_changed')
    return copy.deepcopy(after['daemon_identity'])


class Network:
    """A/A2 own one helper at a time; B observes the same port without a helper."""
    def __init__(self, registry, operation_id, backend, *, cwd):
        self.registry, self.operation_id, self.backend, self.cwd = registry, operation_id, backend, cwd
        self.guard = None
        self.writer = threading.Lock()

    def record(self):
        return tx.load(self.registry, self.operation_id)

    def start_guard(self, config, persist):
        return egress.Guard(config, persist, cwd=self.cwd)

    def guard_event(self, phase, kind, payload):
        with self.writer:
            event(self.registry, self.operation_id, phase, kind, payload)

    def phase_event(self, phase, kind, payload):
        # The pipe drainer and phase controller share one durable writer. The
        # installation lock itself remains nonblocking across other processes.
        with self.writer:
            tx.phase_event(self.registry, self.operation_id, phase, kind, payload)

    def before_phase(self, phase):
        record = self.record()
        require(python_hash() == record['plan']['network']['python_sha256'], 'code_changed')
        if phase == 'B':
            ports_absent(record)
            event(self.registry, self.operation_id, 'B', 'barrier', dict(port=entry(record, 'guard_ready')['port'], available=True))
        else:
            port = 0 if phase == 'A' else entry(record, 'guard_ready')['port']
            if port:
                require(egress.port_available(port), 'guard_port_occupied')
            self.guard = self.start_guard(guard_config(record['plan'], phase, port),
                lambda kind,payload:self.guard_event(phase, kind, payload))
            if phase == 'A':
                activate(self.registry, self.operation_id, self.backend)
        self.verify(phase)

    def verify(self, phase):
        verify(self.record(), self.backend.observe())
        if phase == 'B':
            ports_absent(self.record())
        else:
            require(self.guard is not None and self.guard.error is None
                    and self.guard.channel.process.poll() is None, 'guard_not_ready')

    def after_phase(self, phase):
        if phase == 'B':
            ports_absent(self.record())
        else:
            require(self.guard.finish()['exit_code'] == 0, 'guard_exit_unverified')
            self.guard = None

    def close(self):
        if self.guard is not None:
            self.guard.close()
