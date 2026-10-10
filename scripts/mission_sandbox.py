"""Read-only local prerequisites. An observed sbx version is not an executor proof."""
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import time
import uuid

from capabilities import canonical, parse_json
from mission_clients import _exchange as _client_exchange, hash_executable

ENVIRONMENT_OBSERVATION_VERSION = 1

# Updated only by a reviewed implementation after the complete native proof.
# A caller-supplied file or a field named "verified" cannot register a profile.
REVIEWED_PROFILES = ()
IDENTITY_FIELDS = {'sbx_version', 'executable_sha256', 'platform', 'vm_image_digest',
                   'client_image_digest', 'guardian_sha256', 'kit_sha256', 'client',
                   'client_version', 'client_sha256', 'protocol_version'}
REQUIRED_CONTROLS = dict(host_mounts=False, host_ports=False, host_sockets=False,
                         ssh=False, skills='off', mcp_client_access=False,
                         mcp_isolation_verified=True, clipboard=False,
                         remote_control=False, global_network_allow=False,
                         network_verified=True, auth_mode='oauth', api_precedence=False,
                         oauth_passthrough=False)

INVENTORY_PHASES = ('sandbox_inventory_before', 'sandbox_inspect', 'sandbox_inventory_after')


def _exchange(executable, args, root, *, observation=None, system_probe=False):
    if system_probe:
        return _client_exchange(executable, args, root, system_probe=True, observation=observation)
    from mission_sbx import Sbx
    driver = Sbx(executable, root, version=None)
    result = driver.query('runtime_query', args)
    if observation is not None:
        observation.update(driver.records[-1])
        if observation['reason'] == 'observed':
            observation['reason'] = 'completed'
    if not result['ok']:
        raise ValueError(result['reason'])
    return result['data'] if args == ['version'] else json.dumps(result['data'])


def _compatibility():
    import mission_clients, mission_process
    try:
        import mission_environment
        import mission_sbx
        import mission_execution
    except (ImportError, SyntaxError):
        raise ValueError('incompatible_helper') from None
    if (getattr(mission_process, 'SUPERVISOR_OBSERVATION_VERSION', None) != 1
            or getattr(mission_process, 'SUPERVISOR_CAPTURE_VERSION', None) != 1
            or getattr(mission_clients, 'DISCOVERY_OBSERVATION_VERSION', None) != 1
            or getattr(mission_environment, 'SELECTION_VERSION', None) != 1
            or not callable(getattr(mission_environment, 'StorageError', None))
            or not callable(getattr(mission_environment, 'storage_error', None))
            or getattr(mission_sbx, 'ADAPTER_VERSION', None) != 1
            or getattr(mission_execution, 'RESERVATION_VERSION', None) != 1
            or not callable(getattr(mission_execution, 'status', None))
            or not callable(getattr(mission_sbx, 'Sbx', None))
            or not callable(getattr(getattr(mission_sbx, 'Sbx', None), 'query', None))
            or not callable(getattr(mission_sbx, 'inspect_preflight', None))
            or not callable(getattr(mission_environment, 'read_selection', None))):
        raise ValueError('incompatible_helper')
    return mission_environment


def _unchecked(identity, reason='precondition_failed'):
    return dict(id=identity, started_at=None, ended_at=None, elapsed_seconds=None,
                timeout_seconds=None, output_limit_bytes=None, state='not_checked', reason=reason)


@contextmanager
def _phase(phases, identity, *, external=False):
    record = next((p for p in phases if p['id'] == identity), None)
    if record is None:
        record = _unchecked(identity)
        phases.append(record)
    start = time.monotonic()
    record.update(started_at=datetime.now(timezone.utc).isoformat(), state='observed', reason='completed',
                  timeout_seconds=30 if external else None, output_limit_bytes=8388608 if external else None)
    observation = {}
    try:
        yield observation
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        reason = observation.get('reason')
        if reason not in ('timeout', 'output_limit', 'spawn_failed', 'cancelled', 'unsupported_containment',
                          'permission_denied', 'credential_store_error', 'credential_session_unavailable',
                          'command_failed', 'empty_output',
                          'invalid_json', 'contract_incompatible', 'executable_changed', 'process_unavailable',
                          'client_discovery_failed'):
            reason = str(error) if str(error) in ('stale_observation', 'runtime_metadata_invalid',
                       'runtime_missing', 'runtime_invalid', 'unsupported_containment', 'unsupported_platform',
                       'whp_disabled', 'whp_unknown', 'kvm_unavailable') else 'observation_failed'
        state = ('timeout' if reason == 'timeout' else 'missing' if reason == 'runtime_missing' else
                 'unsupported' if reason in ('unsupported_containment', 'unsupported_platform') else 'failed')
        record.update(state=state, reason=reason)
        raise
    finally:
        record.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - start, 6))
        if external and observation:
            for key in ('started_at', 'ended_at', 'elapsed_seconds', 'timeout_seconds', 'output_limit_bytes'):
                record[key] = observation[key]


def _name(value):
    return isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}', value)


def _uuid(value):
    try:
        return type(value) is str and str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _digest(value, prefix=''):
    return type(value) is str and re.fullmatch(re.escape(prefix) + '[0-9a-f]{64}', value)


def validate_runtime(observation: dict, profile: dict) -> dict:
    """Compare normalized facts against code-reviewed profiles and mandatory limits."""
    gaps = []
    if (type(observation) is not dict or set(observation) !=
            {'schema_version', 'runtime_id', 'runtime_name', 'identity', 'controls'}):
        return dict(gaps=['invalid_runtime_observation'], identity_digest=None)
    identity, controls = observation['identity'], observation['controls']
    if (type(observation['schema_version']) is not int or observation['schema_version'] != 1
            or not _uuid(observation['runtime_id']) or not _name(observation['runtime_name'])):
        gaps.append('invalid_runtime_identity')
    if type(identity) is not dict or set(identity) != IDENTITY_FIELDS:
        gaps.append('invalid_runtime_identity')
    else:
        for key, value in identity.items():
            if key.endswith('_sha256'):
                valid = _digest(value)
            elif key.endswith('_image_digest'):
                valid = _digest(value, 'sha256:')
            elif key == 'protocol_version':
                valid = type(value) is int and value == 1
            elif key == 'client':
                valid = value in ('claude', 'codex')
            else:
                valid = type(value) is str and bool(re.fullmatch(r'[a-zA-Z0-9_.+-]{1,128}', value))
            if not valid:
                gaps.append('invalid_' + key)
    if type(controls) is not dict or set(controls) != set(REQUIRED_CONTROLS) | {
            'network_policy_sha256', 'mcp_gateway', 'mcp_probe_sha256'}:
        gaps.append('invalid_runtime_controls')
    if type(controls) is dict:
        for key, expected in REQUIRED_CONTROLS.items():
            value = controls.get(key)
            if type(value) is not type(expected) or value != expected:
                gaps.append(('unobserved_' if value is None else 'unsafe_') + key)
        if not _digest(controls.get('network_policy_sha256')):
            gaps.append('unobserved_network_policy')
        if type(controls.get('mcp_gateway')) is not bool:
            gaps.append('unobserved_mcp_gateway')
        if not _digest(controls.get('mcp_probe_sha256')):
            gaps.append('mcp_isolation_unverified')
    try:
        registered = (type(profile) is dict and set(profile) == {'id', 'identity', 'controls'}
                      and any(canonical(profile) == canonical(p) for p in REVIEWED_PROFILES))
        if not registered:
            gaps.append('runtime_profile_unverified')
        elif canonical({'identity': identity, 'controls': controls}) != canonical(
                {k:profile[k] for k in ('identity', 'controls')}):
            gaps.append('runtime_profile_mismatch')
        digest = hashlib.sha256(canonical(observation)).hexdigest()
    except (ValueError, TypeError, RecursionError):
        gaps.append('invalid_runtime_observation')
        digest = None
    return dict(gaps=sorted(set(gaps)), identity_digest=digest)


def _read_sandbox(root, executable, name, expected=None, phases=None):
    """Only ls/inspect/ls. Neither query starts a stopped VM; output is allowlisted."""
    if not _name(name):
        raise ValueError('invalid_runtime_identity')
    before = hash_executable(executable)
    if expected and (not _uuid(expected.get('id')) or expected.get('executable_sha256') != before
                     or not _digest(expected.get('image_digest'), 'sha256:')):
        raise ValueError('invalid_runtime_identity')
    phases = [] if phases is None else phases
    def listed(identity):
        with _phase(phases, identity, external=True) as observation:
            return listed_value(observation)
    def listed_value(observation):
        data = parse_json(_exchange(executable, ['ls', '--json'], root, observation=observation).encode())
        if type(data) is not dict or type(data.get('sandboxes')) is not list:
            raise ValueError('invalid_runtime_metadata')
        rows = data['sandboxes']
        if not all(type(row) is dict for row in rows):
            raise ValueError('invalid_runtime_metadata')
        matches = [row for row in rows if row.get('name') == name]
        if len(matches) != 1 or not _uuid(matches[0].get('id')):
            raise ValueError('runtime_identity_unconfirmed')
        row = matches[0]
        if expected and row['id'] != expected['id']:
            raise ValueError('runtime_identity_unconfirmed')
        return {key:row.get(key) for key in ('id', 'name', 'status')}
    first = listed('sandbox_inventory_before')
    with _phase(phases, 'sandbox_inspect', external=True) as observation:
        data = parse_json(_exchange(executable, ['inspect', name, '--json'], root, observation=observation).encode())
        if (type(data) is not dict or data.get('name') != name or data.get('daemon_version') != 'v0.46.0'
                or not _digest(data.get('image_digest'), 'sha256:')
                or data.get('state') != first['status'] or first['status'] not in ('running', 'stopped')
                or (expected and data['image_digest'] != expected['image_digest'])):
            raise ValueError('runtime_metadata_unconfirmed')
    last = listed('sandbox_inventory_after')
    if first != last or before != hash_executable(executable):
        raise ValueError('runtime_observation_changed')
    # Preserve unknown as null. Never copy proxy URLs, secrets, mounts or arbitrary metadata.
    return dict(id=first['id'], name=name, state=data['state'], image_digest=data['image_digest'],
                executable_sha256=before,
                cpus=data.get('cpus') if type(data.get('cpus')) is int else None,
                memory='4g' if data.get('memory') in ('4g', '4096m') else None,
                mcp_gateway=data.get('mcp_gateway') if type(data.get('mcp_gateway')) is bool else None,
                host_mounts=bool(data['runtime_mounts']) if type(data.get('runtime_mounts')) is list else None,
                sessions=data.get('sessions') if type(data.get('sessions')) is int else None)


def inspect_sandbox(root: Path, executable: Path, name: str) -> dict:
    """Inspect an existing VM without accepting a caller-supplied certification."""
    _compatibility()
    phases = [_unchecked(p) for p in INVENTORY_PHASES]
    result = dict(runtime=None, gaps=['runtime_profile_unverified'], phases=phases)
    try:
        runtime = _read_sandbox(root, executable, name, phases=phases)
        result['runtime'] = runtime
        for key, field in (('host_mounts', 'host_mounts'),):
            if runtime[field] is not False:
                result['gaps'].append(('unobserved_' if runtime[field] is None else 'unsafe_') + key)
        if runtime['cpus'] != 2 or runtime['memory'] != '4g':
            result['gaps'].append('runtime_resources_unverified')
        result['gaps'].extend(['network_policy_unverified', 'sharing_controls_unverified',
                               'authentication_unverified', 'inner_runtime_unverified',
                               'mcp_isolation_unverified'])
        if runtime['mcp_gateway'] is None:
            result['gaps'].append('unobserved_mcp_gateway')
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        result['gaps'].append('runtime_observation_failed')
    return result


def observe_stop(executable: Path, runtime: dict) -> dict:
    result = dict(identity_matches=False, sandbox_stopped=False, workload_reaped=False,
                  evidence_sha256=None, gaps=['workload_stop_unverified'])
    try:
        if type(runtime) is not dict or set(runtime) != {'id', 'name', 'image_digest', 'executable_sha256'}:
            raise ValueError('invalid_runtime_identity')
        observed = _read_sandbox(Path.cwd(), executable, runtime['name'], runtime)
        result['identity_matches'] = True
        result['sandbox_stopped'] = observed['state'] == 'stopped' and observed['sessions'] == 0
        result['evidence_sha256'] = hashlib.sha256(canonical(observed)).hexdigest()
        if not result['sandbox_stopped']:
            result['gaps'].append('sandbox_stop_unverified')
        # A stopped VM alone cannot certify the nested process or future restart behavior.
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        result['gaps'].append('runtime_observation_failed')
    return result


def _host_facts(root: Path, phases=None) -> dict:
    phases = [] if phases is None else phases
    with _phase(phases, 'host_metadata'):
        facts = dict(system=platform.system(), machine=platform.machine(),
                     build=None, whp_state=None, distribution=None, kvm_access=None)
        if facts['system'] == 'Windows':
            facts['build'] = str(platform.win32_ver()[1]).rsplit('.', 1)[-1]
        elif facts['system'] == 'Linux':
            try:
                release = platform.freedesktop_os_release()
                facts['distribution'] = release.get('ID', '') + ':' + release.get('VERSION_ID', '')
            except OSError:
                pass
    try:
        with _phase(phases, 'virtualization', external=facts['system'] == 'Windows') as observation:
            if facts['system'] == 'Windows':
                powershell = Path(os.environ.get('SYSTEMROOT', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
                output = _exchange(powershell, ['-NoProfile', '-NonInteractive', '-Command',
                    "Get-CimInstance Win32_OptionalFeature -Filter \"Name='HypervisorPlatform'\" "
                    '| Select-Object -ExpandProperty InstallState | ConvertTo-Json -Compress'], root,
                    system_probe=True, observation=observation)
                value = parse_json(output.encode())
                if type(value) is int and value in (1, 2, 3, 4):
                    facts['whp_state'] = value
                if facts['whp_state'] != 1:
                    raise ValueError('whp_disabled' if facts['whp_state'] in (2, 3) else 'whp_unknown')
            elif facts['system'] == 'Linux':
                facts['kvm_access'] = False
                try:
                    info = Path('/dev/kvm').lstat()
                    facts['kvm_access'] = stat.S_ISCHR(info.st_mode) and os.access('/dev/kvm', os.R_OK | os.W_OK)
                except OSError:
                    pass
                if not facts['kvm_access']:
                    raise ValueError('kvm_unavailable')
            else:
                raise ValueError('unsupported_platform')
    except (ValueError, OSError, UnicodeError):
        pass  # Unknown prerequisites never enable a feature.
    return facts


def inspect_environment(root: Path, executable: Path) -> dict:
    selection = _compatibility().read_selection(root)
    import mission_execution
    reservation = mission_execution.status()
    root, executable = Path(root).resolve(strict=True), Path(executable).absolute()
    phases = []
    facts = _host_facts(root, phases)
    gaps = []
    if reservation['state'] != 'available':
        gaps.append('execution_reserved' if reservation['state'] in ('reserved','consumed') else 'execution_reservation_unknown')
    if str(facts['machine']).lower() not in ('amd64', 'x86_64'):
        gaps.append('unsupported_platform')
    if facts['system'] == 'Windows':
        build = facts['build']
        if not isinstance(build, str) or not build.isdecimal() or int(build) < 22000:
            gaps.append('unsupported_platform')
        if facts['whp_state'] != 1:
            gaps.append('whp_disabled' if facts['whp_state'] in (2, 3) else 'whp_unknown')
    elif facts['system'] == 'Linux':
        if facts['distribution'] != 'ubuntu:24.04':
            gaps.append('unsupported_platform')
        if facts['kvm_access'] is not True:
            gaps.append('kvm_unavailable')
    else:
        gaps.append('unsupported_platform')

    digest, version = None, None
    try:
        with _phase(phases, 'runtime_identity'):
            if not executable.exists():
                raise ValueError('runtime_missing')
            try:
                digest = hash_executable(executable)
                if os.name == 'nt' and executable.suffix.lower() != '.exe':
                    raise ValueError('invalid_executable')
            except (OSError, ValueError):
                digest = None
                raise ValueError('runtime_invalid') from None
    except (OSError, ValueError) as error:
        gaps.append('runtime_missing' if str(error) == 'runtime_missing' else 'runtime_invalid')
    if digest:
        try:
            with _phase(phases, 'runtime_version', external=True) as observation:
                output = _exchange(executable, ['version'], root, observation=observation)
                match = re.fullmatch(r'sbx version: v?(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?) [0-9a-f]{6,64}',
                                     output.strip()) if isinstance(output, str) and len(output) <= 256 else None
                if hash_executable(executable) != digest:
                    raise ValueError('stale_observation')
                if not match:
                    raise ValueError('runtime_metadata_invalid')
                version = match[1]
        except (OSError, ValueError, UnicodeError) as error:
            gaps.append(str(error) if str(error) in ('stale_observation', 'runtime_metadata_invalid') else 'runtime_metadata_failed')
    else:
        phases.append(_unchecked('runtime_version'))
    phases.extend(_unchecked(p, 'not_requested') for p in INVENTORY_PHASES)
    gaps.append('runtime_profile_unverified')
    return dict(schema_version=1, kind='sbx', executable=str(executable),
                executable_sha256=digest, version=version, selection=selection, phases=phases,
                execution_reservation=reservation,
                platform={k: facts[k] for k in ('system', 'machine', 'build', 'distribution')},
                prerequisites={k: facts[k] for k in ('whp_state', 'kvm_access')},
                gaps=sorted(set(gaps)), profile_ids=[],
                checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
