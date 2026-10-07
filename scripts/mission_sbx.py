"""Bounded sbx metadata and owned recovery. No credential writes or model calls."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import time
import uuid

from capabilities import parse_json
from mission_clients import hash_executable
import mission_process

ADAPTER_VERSION = 1
CANDIDATE_PREFLIGHT_VERSION = 1
SETTINGS = ('proxy.sandbox', 'no_proxy.sandbox', 'proxy', 'no_proxy',
            'proxy.daemon', 'no_proxy.daemon', 'proxy.integratedAuth')
QUERIES = {('version',), ('daemon', 'status', '--json'), ('secret', 'ls', '--json'), ('ls', '--json')}
QUERIES.update(('settings', 'get', key, '--json') for key in SETTINGS)
QUERIES.add(('policy', 'ls', '--json'))
PROXY_ENV = {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
             'DOCKER_SANDBOXES_PROXY', 'DOCKER_SANDBOXES_NO_PROXY'}


def credential_inventory_empty(data):
    """Missing sources are unknown, never an empty credential store."""
    lists = ('secrets', 'custom_secrets', 'shadowed_services')
    if (any(type(data.get(key)) is not list for key in lists)
            or type(data.get('env_only_count')) is not int or data['env_only_count'] < 0):
        return None
    return not any(data[key] for key in lists) and data['env_only_count'] == 0


def _name(value):
    return type(value) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}', value)


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _policy_rule(row):
    strings = ('id', 'name', 'policy_id', 'scope', 'applies_to', 'resource_type',
               'decision', 'origin', 'layer', 'status')
    return (type(row) is dict and all(type(row.get(k)) is str for k in strings)
            and all(type(row.get(k)) is list and all(type(v) is str for v in row[k])
                    for k in ('resources', 'actions')) and type(row.get('editable')) is bool
            and type(row.get('provenance')) is dict
            and type(row['provenance'].get('created_via')) is str
            and ('sandbox_id' not in row or type(row['sandbox_id']) is str))


def _policy_log(row, blocked):
    if (type(row) is not dict or type(row.get('count_since')) is not int or row['count_since'] < 0
            or any(type(row.get(k)) is not str for k in ('host', 'proxy_type', 'rule', 'vm_name'))
            or (blocked and type(row.get('reason')) is not str)):
        return False
    try:
        return all(type(row.get(k)) is str and datetime.fromisoformat(row[k]).utcoffset() is not None
                   for k in ('since', 'last_seen'))
    except ValueError:
        return False


def _stable(label, value):
    # sbx reports uptime in inspect even when the selected VM is stopped.
    # All other fields, including unknown ones, must still match exactly.
    return {k: v for k, v in value.items() if k != 'daemon_uptime'} if label == 'candidate_inspect' else value


def context():
    # Hints describe this process, not the operator's identity or a security certification.
    return dict(platform=platform.system(), pid=os.getpid(),
                remote_session_hint=any(os.environ.get(k) for k in ('SSH_CONNECTION', 'SSH_CLIENT', 'SSH_TTY')),
                environment_policy='mission_process_allowlist')


def _error(result, args=()):
    if not result['tree_reaped']:
        return 'unsupported_containment'
    if result['reason'] != 'completed':
        return result['reason'] if result['reason'] in ('timeout', 'output_limit', 'spawn_failed', 'cancelled') else 'process_failed'
    if result['exit_code'] != 0:
        error = result.get('stderr', b'').lower()
        if args == ('secret', 'ls', '--json') and error.splitlines()[:1] == [
                b'error: list credential metadata: logon session does not exist or there is no '
                b'credential set associated with this logon session']:
            return 'credential_session_unavailable'
        if any(s in error for s in (b'access is denied', b'permission denied', b'acesso negado')):
            return 'permission_denied'
        if any(s in error for s in (b'credential manager', b'credread', b'keyring', b'keychain')):
            return 'credential_store_error'
        return 'command_failed'
    return None


def _contract(args, data):
    if type(data) is not dict:
        return False
    if args[0] == 'daemon':
        return data.get('status') in ('running', 'stopped')
    if args[0] == 'ls':
        return type(data.get('sandboxes')) is list and all(type(r) is dict for r in data['sandboxes'])
    if args[0] == 'secret':
        return type(data.get('secrets')) is list
    if args[0] == 'inspect':
        return data.get('name') == args[1]
    if args[:2] == ('policy', 'ls'):
        return type(data.get('rules')) is list and all(_policy_rule(row) for row in data['rules'])
    if args[:2] == ('policy', 'log'):
        return all(type(data.get(key)) is list and all(_policy_log(row, key == 'blocked_hosts') for row in data[key])
                   for key in ('blocked_hosts', 'allowed_hosts'))
    return (data.get('key') == args[2] and data.get('source') in ('default', 'override')
            and 'value' in data and 'default' in data and data.get('type') in ('string', 'bool', 'boolean'))


class Sbx:
    def __init__(self, executable, root, *, version, evidence_path=None):
        if getattr(mission_process, 'SUPERVISOR_CAPTURE_VERSION', None) != 1:
            raise ValueError('incompatible_helper')
        self.executable, self.root = Path(executable).absolute(), Path(root).resolve(strict=True)
        self.digest = hash_executable(self.executable)
        self.version, self.records, self.evidence = version, [], []
        self.baseline = None  # Trusted coordinator only; never included in the public report.
        self.timeout_seconds = 15
        self.context = context()
        self.evidence_path = evidence_path

    def private_destination(self, path, *, temporary=False, parent_identity=None):
        import adoption_fs as fs
        from mission_environment import _private, _git_boundary, storage_error, StorageError
        phase = 'temporary_evidence' if temporary else 'evidence_destination'
        checking_git = True
        try:
            fs.checked_path(path)
            if _git_boundary(self.root):
                code = fs.git_read(self.root, 'check-ignore', '--quiet', '--', path.relative_to(self.root).as_posix()).returncode
                if code:
                    raise StorageError(phase, 'git_exclusion_missing' if code == 1 else 'git_query_failed')
            elif any(line.lstrip().startswith('!') for line in (self.root / '.gitignore').read_text().splitlines()):
                # Without a repository, Git cannot evaluate precedence. Refuse ambiguous negations.
                raise StorageError(phase, 'git_exclusion_missing')
            checking_git = False
            if temporary and os.name == 'nt':
                before = path.lstat()
                identity = fs.identity(path)
                if (self.evidence_path is None or path.parent != self.evidence_path.parent
                        or not re.fullmatch(r'\.yc-[A-Za-z0-9_-]+\.tmp', path.name)
                        or parent_identity is None or fs.identity(path.parent) != parent_identity
                        or identity is None or not stat.S_ISREG(before.st_mode) or before.st_size):
                    raise StorageError(phase, 'unsupported_entry')
                # Only atomic_write's new empty file, never the directory or an existing receipt.
                fs.protect_for_storage(path)
                fs.checked_path(path)
                if (fs.identity(path) != identity or path.lstat().st_size
                        or fs.identity(path.parent) != parent_identity):
                    raise StorageError(phase, 'unsupported_entry')
                _private(path.parent)
            else:
                _private(path if path.exists() else path.parent)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if checking_git and isinstance(error, subprocess.TimeoutExpired):
                raise StorageError(phase, 'git_query_timeout') from None
            raise storage_error(error, phase) from None

    def persist(self):
        if self.evidence_path is not None:
            import adoption_fs as fs
            from document_store import atomic_write
            self.private_destination(self.evidence_path)
            parent_identity = fs.identity(self.evidence_path.parent)
            atomic_write(self.root, self.evidence_path.relative_to(self.root), json.dumps(dict(
                schema_version=1, commands=self.records, evidence=self.evidence)),
                before_write=lambda name: self.private_destination(self.root / name, temporary=True,
                                                                   parent_identity=parent_identity))

    def query(self, phase, args):
        result = self._query(phase, args)
        self.persist()
        return result

    def _query(self, phase, args):
        args = tuple(args)
        inspection = (len(args) == 3 and args[0] == 'inspect' and args[2] == '--json'
                      and _name(args[1]))
        policy = (len(args) in (4, 6) and args[:2] in (('policy', 'ls'), ('policy', 'log'))
                  and _name(args[2]) and args[3:] == (('--json',) if args[1] == 'ls'
                                                                     else ('--json', '--limit', '10')))
        if (args not in QUERIES and not inspection and not policy) or not phase.replace('_', '').isalnum():
            raise ValueError('sbx_query_not_allowed')
        return self._observe(phase, args, self.executable, lambda data: _contract(args, data))

    def _observe(self, phase, args, executable, contract, *, system_probe=False):
        try:
            probe_digest = hash_executable(executable)
        except (OSError, ValueError):
            probe_digest = None
        start = datetime.now(timezone.utc).isoformat()
        record = dict(phase=phase, args=list(args), executable_sha256=self.digest,
                      version=self.version, context=self.context, timeout_seconds=self.timeout_seconds,
                      output_limit_bytes=65536, started_at=start, ended_at=start,
                      elapsed_seconds=0, exit_code=None, reason='pending')
        if system_probe:
            record.update(command_kind='host_metadata', probe_executable_sha256=probe_digest)
        if probe_digest is None:
            record['reason'] = 'host_probe_unavailable' if system_probe else 'executable_changed'
        self.records.append(record)
        self.persist()
        if probe_digest is None:
            return dict(ok=False, reason=record['reason'])
        try:
            if hash_executable(self.executable) != self.digest:
                record['reason'] = 'executable_changed'
                return dict(ok=False, reason=record['reason'])
            result = mission_process.supervise(dict(argv=[str(executable), *args], cwd=str(self.root),
                stdin=b'', timeout_seconds=self.timeout_seconds, output_limit_bytes=65536, connection='authenticated',
                client='metadata', credential_env=None, system_probe=system_probe),
                on_started=lambda _: None, stop_requested=lambda: False)
        except (OSError, ValueError):
            record['reason'] = 'process_unavailable'
            return dict(ok=False, reason=record['reason'])
        for key in ('started_at', 'ended_at', 'elapsed_seconds', 'exit_code'):
            record[key] = result[key]
        raw = {}
        for key in ('stdout', 'stderr'):
            value = result.get(key, b'')
            record[key + '_bytes'] = len(value)
            record[key + '_sha256'] = hashlib.sha256(value).hexdigest()
            raw[key + '_b64'] = base64.b64encode(value).decode('ascii')
        self.evidence.append(dict(phase=phase, **raw))
        reason, data = _error(result, args), None
        if reason is None:
            if not result['stdout'].strip():
                reason = 'empty_output'
            else:
                try:
                    data = result['stdout'].decode('utf-8') if args == ('version',) else parse_json(result['stdout'])
                    if args != ('version',) and not contract(data):
                        reason = 'contract_incompatible'
                except (ValueError, UnicodeError, RecursionError):
                    reason = 'invalid_json'
        try:
            if hash_executable(self.executable) != self.digest or hash_executable(executable) != probe_digest:
                reason = 'executable_changed'
        except (OSError, ValueError):
            reason = 'executable_changed'
        record['reason'] = reason or 'observed'
        # Raw values are for the trusted caller only; public reports use records.
        return dict(ok=reason is None, reason=record['reason'], data=data if reason is None else None)

    def daemon_identity(self, phase):
        """Observe PID plus creation, not command lines or a restart-prone status string."""
        if platform.system() != 'Windows':
            raise ValueError('daemon_identity_unsupported')
        executable = Path(os.environ.get('SYSTEMROOT', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        args = ('-NoProfile', '-NonInteractive', '-Command',
                "Get-CimInstance Win32_Process -Filter \"Name='sbx.exe'\" "
                '| Select-Object ProcessId,CreationDate,ExecutablePath | ConvertTo-Json -Compress')
        result = self._observe(phase, args, executable,
                               lambda data: type(data) in (dict, list), system_probe=True)
        self.persist()
        if not result['ok']:
            raise ValueError(result['reason'])
        rows = result['data'] if type(result['data']) is list else [result['data']]
        # An inaccessible path cannot be dismissed as an unrelated process.
        if any(type(row) is not dict or type(row.get('ExecutablePath')) is not str
               or not row['ExecutablePath'] for row in rows):
            raise ValueError('daemon_identity_unavailable')
        matches = [row for row in rows if os.path.normcase(row['ExecutablePath']) == os.path.normcase(str(self.executable))]
        if len(matches) != 1:
            raise ValueError('daemon_identity_ambiguous')
        row = matches[0]
        if (type(row.get('ProcessId')) is not int or row['ProcessId'] <= 0
                or type(row.get('CreationDate')) is not str
                or not re.fullmatch(r'/Date\([0-9]+\)/', row['CreationDate'])):
            raise ValueError('daemon_identity_contract_incompatible')
        return dict(pid=row['ProcessId'], created_at=row['CreationDate'])

    def preflight(self, *, sandbox=None):
        if sandbox is not None:
            return self.candidate_preflight(sandbox)
        report = dict(schema_version=1, ready=False, effects_allowed=False, model_calls=0,
                      reason='contract_incompatible', failed_phase=None, commands=self.records,
                      credential_inventory_empty=None)
        if self.version != '0.46.0':
            return report
        queries = [('daemon_before', ('daemon', 'status', '--json')),
                   ('secret_inventory', ('secret', 'ls', '--json')),
                   ('sandbox_inventory', ('ls', '--json'))]
        queries += [('setting_' + key.replace('.', '_'), ('settings', 'get', key, '--json')) for key in SETTINGS]
        queries += [('daemon_after', ('daemon', 'status', '--json'))]
        daemon = None
        for phase, args in queries:
            result = self.query(phase, args)
            reason = result['reason']
            if result['ok'] and args[0] == 'secret':
                report['credential_inventory_empty'] = credential_inventory_empty(result['data'])
            if result['ok'] and args[0] == 'daemon':
                if result['data']['status'] != 'running':
                    reason = 'daemon_not_running'
                elif daemon is not None and result['data'] != daemon:
                    reason = 'configuration_changed'
                else:
                    daemon = result['data']
            if reason != 'observed':
                report.update(reason=reason, failed_phase=phase)
                if reason == 'credential_session_unavailable':
                    report['guidance'] = (
                        'The Windows credential set is unavailable in this logon session. '
                        'Run this preflight from your signed-in Windows desktop session '
                        'before any Docker changes. This does not mean the credential inventory is empty.')
                return report
        report.update(ready=True, reason='metadata_observed')
        return report

    def candidate_preflight(self, name):
        """Repeated read-only baseline. Readiness never authorizes a native proof."""
        self.baseline = None
        report = dict(schema_version=1, scope='candidate_metadata', ready=False,
                      effects_allowed=False, model_calls=0, commands=self.records,
                      credential_inventory_empty=None, failed_phase=None,
                      pending=['exclusive_use_reservation', 'daemon_log_capture',
                               'inner_candidate_identity', 'integrated_isolation_proof',
                               'authenticated_clients'])
        phase = 'preconditions'
        def read(label, args):
            nonlocal phase
            phase = label
            result = self.query(label, args)
            if not result['ok']:
                raise ValueError(result['reason'])
            return result['data']
        def require(condition, reason):
            if not condition:
                raise ValueError(reason)
        def inventory(value):
            rows = value['sandboxes']
            ids, names = [], []
            for row in rows:
                ident = row.get('id')
                require(type(ident) is str and re.fullmatch(
                    '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', ident)
                    and _name(row.get('name')), 'inventory_contract_incompatible')
                ids.append(ident)
                names.append(row['name'])
            require(len(set(ids)) == len(ids) and len(set(names)) == len(names), 'inventory_identity_ambiguous')
            require(all(row.get('status') == 'stopped' for row in rows), 'active_consumer')
            require(names.count(name) == 1, 'candidate_missing')
            return next(row['id'] for row in rows if row['name'] == name)
        try:
            require(self.version == '0.46.0', 'contract_incompatible')
            require(_name(name), 'invalid_runtime_identity')
            require(not any(k.upper() in PROXY_ENV and v for k, v in os.environ.items()), 'proxy_environment_present')
            daemon = read('daemon_before', ('daemon', 'status', '--json'))
            require(daemon['status'] == 'running', 'daemon_not_running')
            phase = 'daemon_identity_before'
            identity = self.daemon_identity(phase)
            queries = [('secret_inventory', ('secret', 'ls', '--json')),
                       ('sandbox_inventory', ('ls', '--json'))]
            queries += [('setting_' + key.replace('.', '_'), ('settings', 'get', key, '--json')) for key in SETTINGS]
            queries += [('policy_global', ('policy', 'ls', '--json')),
                        ('policy_candidate', ('policy', 'ls', name, '--json')),
                        ('candidate_inspect', ('inspect', name, '--json'))]
            baseline = {}
            for label, args in queries:
                value = read(label, args)
                baseline[label] = value
                if label == 'secret_inventory':
                    empty = credential_inventory_empty(value)
                    report['credential_inventory_empty'] = empty
                    require(empty is not None, 'credential_inventory_incomplete')
                    require(empty, 'credential_inventory_not_empty')
                elif label == 'sandbox_inventory':
                    candidate_id = inventory(value)
            data = baseline['candidate_inspect']
            require(data.get('state') == 'stopped' and type(data.get('sessions')) is int
                    and data['sessions'] == 0, 'candidate_not_idle')
            require(data.get('daemon_version') == 'v0.46.0'
                    and type(data.get('image_digest')) is str
                    and re.fullmatch('sha256:[0-9a-f]{64}', data['image_digest']), 'candidate_identity_unverified')
            require(type(data.get('cpus')) is int and data['cpus'] == 2
                    and data.get('memory') in ('4g', '4096m'), 'runtime_resources_unverified')
            require(type(data.get('runtime_mounts')) is list and not data['runtime_mounts'], 'host_mounts_present')
            require(type(data.get('mcp_gateway')) is bool, 'mcp_gateway_unobserved')
            require('daemon_uptime' not in data or type(data['daemon_uptime']) is str, 'contract_incompatible')
            read('policy_log', ('policy', 'log', name, '--json', '--limit', '10'))
            for label, args in queries:
                observed = read(label + '_after', args)
                if label == 'candidate_inspect':
                    require('daemon_uptime' not in observed or type(observed['daemon_uptime']) is str,
                            'contract_incompatible')
                require(_stable(label, observed) == _stable(label, baseline[label]), 'configuration_changed')
            require(read('daemon_after', ('daemon', 'status', '--json')) == daemon, 'configuration_changed')
            phase = 'daemon_identity_after'
            require(self.daemon_identity(phase) == identity, 'daemon_identity_changed')
            self.baseline = dict(executable_sha256=self.digest, version=self.version,
                                 daemon=daemon, daemon_identity=identity,
                                 observations={k: _stable(k, v) for k, v in baseline.items()})
            report.update(ready=True, reason='candidate_metadata_observed',
                          baseline_sha256=_sha(self.baseline),
                          candidate=dict(id=candidate_id, name=name, image_digest=data['image_digest'],
                                         cpus=2, memory_mib=4096, mcp_gateway=data['mcp_gateway']))
        except ValueError as error:
            report.update(reason=str(error), failed_phase=phase)
            guidance = {
                'proxy_environment_present': 'Use a session without proxy environment overrides; preserve the current session configuration.',
                'active_consumer': 'Finish the active sandbox work before reserving Docker exclusively for the proof.',
                'credential_inventory_not_empty': 'Use an installation reserved for the synthetic proof; preserve existing credentials.',
                'credential_inventory_incomplete': 'Inspect the private secret-inventory response; absence of metadata is not an empty store.',
                'credential_session_unavailable': 'Run this diagnostic in your signed-in Windows desktop session with Credential Manager access.',
                'configuration_changed': 'Compare the before/after entries in the private receipt and preserve the external changes.',
                'daemon_identity_changed': 'The Docker process changed during observation. Inspect its lifecycle before requesting another proof.',
                'daemon_identity_ambiguous': 'Inspect the Docker process inventory; a single daemon instance could not be identified.',
                'daemon_identity_unsupported': 'Daemon identity is currently verified only on Windows; the dedicated runner needs native validation.',
                'host_probe_unavailable': 'Check the Windows PowerShell executable used for the host-metadata phase.',
                'candidate_missing': 'Select the existing diagnostic sandbox by name; this command will not create one.',
            }
            report['guidance'] = guidance.get(str(error),
                'Inspect the failed phase in the private receipt before making changes. This diagnostic does not authorize effects.')
        return report


class Recovery:
    """Closed host recovery commands, used outside the original process group/job.

    Never pass this adapter into a contained controller: metadata queries use the
    existing supervisor. It does not configure egress, credentials or policies.
    """
    def __init__(self, driver, plan, *, timeout_seconds=60):
        import mission_transaction as tx
        tx.validate_plan(plan)
        tx.require(0 < timeout_seconds <= 60, 'invalid_recovery_deadline')
        self.driver, self.plan = driver, plan
        self.until = time.monotonic()+timeout_seconds
        tx.require(driver.digest == plan['baseline']['executable_sha256']
                   and driver.version == plan['baseline']['version'], 'executable_changed')

    def bind_deadline(self, until):
        self.until = min(self.until, until)
        self.remaining()

    def setting(self, key, target):
        raise ValueError('native_egress_contract_unverified')

    def restart(self):
        raise ValueError('native_egress_contract_unverified')

    def remaining(self):
        value = min(15, self.until-time.monotonic())
        if value <= 0:
            raise ValueError('recovery_deadline')
        self.driver.timeout_seconds = value
        return value

    def query(self, label, args):
        self.remaining()
        result = self.driver.query(label, args)
        self.remaining()
        if not result['ok']:
            raise ValueError(result['reason'])
        return result['data']

    def candidate(self):
        candidate = self.plan['candidate']
        first = self.query('recovery_inventory_before', ('ls', '--json'))
        inspected = self.query('recovery_candidate', ('inspect', candidate['name'], '--json'))
        after = self.query('recovery_inventory_after', ('ls', '--json'))
        matches = [row for row in first['sandboxes'] if row.get('name') == candidate['name']]
        if (first != after or len(matches) != 1 or matches[0].get('id') != candidate['id']
                or inspected.get('image_digest') != candidate['outer_digest']
                or inspected.get('state') not in ('running', 'stopped')
                or matches[0].get('status') != inspected['state']):
            raise ValueError('candidate_identity_changed')
        return first, inspected

    def observe(self):
        first, inspected = self.candidate()
        observations = dict(sandbox_inventory=first, candidate_inspect=_stable('candidate_inspect', inspected))
        for key in SETTINGS:
            observations['setting_'+key.replace('.', '_')] = self.query('recovery_setting', ('settings', 'get', key, '--json'))
        observations['secret_inventory'] = self.query('recovery_secrets', ('secret', 'ls', '--json'))
        observations['policy_global'] = self.query('recovery_policy', ('policy', 'ls', '--json'))
        observations['policy_candidate'] = self.query('recovery_candidate_policy', ('policy', 'ls', self.plan['candidate']['name'], '--json'))
        daemon = self.query('recovery_daemon', ('daemon', 'status', '--json'))
        self.remaining()
        identity = self.driver.daemon_identity('recovery_daemon_identity')
        final, last = self.candidate()
        if final != first or _stable('candidate_inspect', last) != observations['candidate_inspect']:
            raise ValueError('configuration_changed')
        return dict(executable_sha256=self.driver.digest, version=self.driver.version, daemon=daemon,
                    daemon_identity=identity, observations=observations)

    def workload(self, phase, stop=False):
        import mission_transaction as tx
        _, candidate = self.candidate()
        if candidate['state'] != 'running':
            raise ValueError('candidate_not_running')
        manifest = self.plan['phases'][tx.PHASES.index(phase)]
        args = ('exec', '-u', 'root', self.plan['candidate']['name'], '/usr/bin/python3.14',
                '-I', '-B', '/opt/youngcrow/launcher.py', 'stop' if stop else 'observe',
                manifest['operation_id'], manifest['nonce'])
        self.remaining()
        result = self.driver._observe('recovery_workload', args, self.driver.executable, lambda data: type(data) is dict)
        self.remaining()
        if not result['ok']:
            raise ValueError(result['reason'])
        tx.workload_valid(self.plan, phase, result['data'])
        return result['data']

    def stop_vm(self):
        _, candidate = self.candidate()
        if candidate['state'] != 'running':
            raise ValueError('candidate_not_running')
        if hash_executable(self.driver.executable) != self.driver.digest:
            raise ValueError('executable_changed')
        result = mission_process.supervise(dict(argv=[str(self.driver.executable), 'stop', self.plan['candidate']['name']],
            cwd=str(self.driver.root), stdin=b'', timeout_seconds=self.remaining(), output_limit_bytes=65536,
            connection='authenticated', client='metadata', credential_env=None),
            on_started=lambda _: None, stop_requested=lambda: False)
        self.remaining()
        if not result['tree_reaped'] or result['reason'] != 'completed' or result['exit_code'] != 0:
            raise ValueError('sandbox_stop_unverified')


def inspect_preflight(root, executable, version, *, sandbox=None):
    """Explicit diagnostic: private local evidence, no Docker mutation command."""
    import adoption_fs as fs
    from mission_environment import AREA, _storage, _private, storage_error
    root = Path(root).resolve(strict=True)
    _storage(root)
    try:
        for relative in ('.operacao-local', AREA):
            directory = fs.checked_path(root / relative)
            if not directory.exists():
                if relative == AREA:
                    fs.private_dir(directory)
                else:
                    directory.mkdir(mode=0o777 if os.name == 'nt' else 0o700)
        _private(root / AREA)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise storage_error(error, 'storage_creation') from None
    path = root / AREA / ('sbx-' + uuid.uuid4().hex + '.json')
    driver = Sbx(executable, root, version=version, evidence_path=path)
    report = driver.preflight(sandbox=sandbox)
    driver.persist()
    report['evidence_path'] = path.relative_to(root).as_posix()
    return report
