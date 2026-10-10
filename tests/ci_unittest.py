"""Run unittest with failure identifiers visible in GitHub Actions annotations."""
import os
import re
import json
import unittest


def safe_identifier(identifier):
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*(?: \([A-Za-z_][A-Za-z0-9_.]*\))?', identifier):
        return identifier
    return 'test_identifier_unavailable'


def annotate_case(identifier, reports):
    """Publish selected fixture states, never arbitrary output or exception text."""
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    codes = {
        'completed', 'timeout', 'cancelled', 'output_limit', 'spawn_failed',
        'blocked', 'observed', 'refused', 'recovered', 'blocked_unattributed',
        'preflight_changed', 'reconciliation_required', 'phase_observed',
        'native_attribution_required', 'native_attribution_and_recovery_required',
        'invalid_manifest', 'transport_failed', 'transport_close_failed',
        'protocol_failed', 'dispatch_failed', 'deadline', 'execution_deadline',
        'persistence_failed', 'configuration_changed', 'workload_stop_unverified',
        'identity_changed', 'owner_still_present', 'stop_consumed',
        'unowned_active_candidate', 'recovery_deadline', 'execution_history_limit',
        'recovery_unverified', 'resources_observed', 'invalid_fixture_result',
        'guard_port_occupied', 'guard_exit_unverified',
        'Refused:guard_port_occupied', 'Refused:guard_exit_unverified',
        'ValueError:execution_deadline', 'TimeoutError:deadline',
        'TimeoutError', 'ConnectionRefusedError', 'ConnectionResetError',
        'ConnectionError', 'PermissionError', 'OSError', 'AssertionError',
        'ValueError', 'RuntimeError', 'FileNotFoundError',
        'fixture_setup', 'fixture_supervise', 'fixture_cleanup',
    }
    output = {}
    for stage in ('supervisor', 'transaction', 'A', 'B', 'A2', 'recovery', 'replay', 'egress', 'fixture'):
        if stage not in reports:
            continue
        result, fields = reports[stage], {}
        for key in ('state', 'reason', 'failure'):
            if key in result:
                value = result[key]
                fields[key] = value if value is None or (type(value) is str and value in codes) else 'other'
        for key in ('exit_code', 'journal_events', 'network_events', 'recovery_events'):
            if key in result and (result[key] is None or type(result[key]) is int):
                fields[key] = result[key]
        for key in ('journal_ms', 'network_ms'):
            values = result.get(key)
            if (type(values) is list and len(values) <= 60
                    and all(type(v) is int and 0 <= v <= 3600000 for v in values)):
                fields[key] = values
        if type(result.get('tree_reaped')) is bool:
            fields['tree_reaped'] = result['tree_reaped']
        elapsed = result.get('elapsed_seconds')
        if type(elapsed) in (int, float) and 0 <= elapsed <= 3600:
            fields['elapsed_seconds'] = elapsed
        for key in ('stdout', 'stderr'):
            if type(result.get(key)) is bytes:
                fields[key+'_bytes'] = len(result[key])
        if stage == 'egress':
            for key in ('accepted', 'eof', 'complete'):
                if type(result.get(key)) is bool:
                    fields[key] = result[key]
            count = result.get('bytes')
            if type(count) is int and 0 <= count <= 16384:
                fields['bytes'] = count
            if 'error' in result:
                error = result['error']
                fields['failure'] = error if type(error) is str and error in codes else 'other'
        output[stage] = fields
    print(f'::notice::{safe_identifier(identifier)} {json.dumps(output, separators=(",", ":"))}', flush=True)


class AnnotationRunner(unittest.TextTestRunner):
    def run(self, test):
        result = super().run(test)
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            failed = [case for case, _ in result.failures + result.errors]
            identifiers = set()
            for case in failed + result.unexpectedSuccesses:
                # Subtest IDs include parameter values; retain only the parent ID.
                if isinstance(case, unittest.case._SubTest):
                    case = case.test_case
                # Standard test IDs and class/module setup/teardown error holders.
                identifier = safe_identifier(case.id())
                if identifier not in identifiers:
                    print(f'::error::{identifier}', flush=True)
                    identifiers.add(identifier)
        return result


if __name__ == '__main__':
    unittest.main(module=None, testRunner=AnnotationRunner)
