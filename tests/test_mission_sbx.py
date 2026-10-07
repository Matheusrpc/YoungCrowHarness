"""Contracts for bounded Docker observations; no Docker or provider calls."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class SbxTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_sbx'), 'shared sbx adapter missing')
        self.module = importlib.import_module('mission_sbx')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.exe = self.root / 'sbx.exe'
        self.exe.write_bytes(b'fixture')

    def result(self, **changes):
        return dict(dict(reason='completed', exit_code=0, stdout=b'{"secrets":[]}', stderr=b'',
                         tree_reaped=True, started_at='2026-10-07T00:00:00+00:00',
                         ended_at='2026-10-07T00:00:01+00:00', elapsed_seconds=1), **changes)

    def query(self, result, args=('secret', 'ls', '--json')):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch('mission_process.supervise', return_value=result):
            response = driver.query('secret_inventory', args)
        return driver, response

    def test_error_is_classified_without_disclosing_stdout_or_stderr(self):
        result = self.result(exit_code=1, stdout=b'token-canary', stderr=b'Access is denied: token-canary')
        driver, response = self.query(result)
        self.assertFalse(response['ok'])
        self.assertEqual(response['reason'], 'permission_denied')
        record = driver.records[0]
        self.assertEqual(record['exit_code'], 1)
        self.assertNotIn('token-canary', json.dumps(record))
        self.assertEqual(driver.evidence[0]['stderr_b64'], 'QWNjZXNzIGlzIGRlbmllZDogdG9rZW4tY2FuYXJ5')

    def test_failure_classes_keep_partial_output_private(self):
        cases = [(self.result(stdout=b''), 'empty_output'),
                 (self.result(stdout=b'not JSON token-canary'), 'invalid_json'),
                 (self.result(stdout=b'[]'), 'contract_incompatible'),
                 (self.result(reason='timeout', stdout=b'token-canary'), 'timeout'),
                 (self.result(exit_code=1, stderr=b'unknown failure token-canary'), 'command_failed'),
                 (self.result(tree_reaped=False), 'unsupported_containment')]
        for result, expected in cases:
            with self.subTest(expected=expected):
                driver, response = self.query(result)
                self.assertEqual(response['reason'], expected)
                self.assertNotIn('token-canary', json.dumps(driver.records))

    def test_mutating_or_unknown_arguments_never_reach_process(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        for args in [('daemon', 'restart'), ('secret', 'set', 'token-canary'),
                     ('settings', 'get', 'token-canary', '--json')]:
            with self.subTest(args=args), patch('mission_process.supervise') as process:
                with self.assertRaisesRegex(ValueError, '^sbx_query_not_allowed$'):
                    driver.query('probe', args)
                process.assert_not_called()

    def test_executable_change_refuses_dispatch(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        self.exe.write_bytes(b'changed')
        with patch('mission_process.supervise') as process:
            response = driver.query('secret_inventory', ('secret', 'ls', '--json'))
        self.assertEqual(response['reason'], 'executable_changed')
        process.assert_not_called()

    def test_preflight_stops_before_settings_when_daemon_unavailable(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch('mission_process.supervise', return_value=self.result(stdout=b'{"status":"stopped"}')):
            report = driver.preflight()
        self.assertFalse(report['ready'])
        self.assertEqual(report['reason'], 'daemon_not_running')
        self.assertEqual([r['args'] for r in driver.records], [['daemon', 'status', '--json']])

    def test_unavailable_logon_session_is_not_an_empty_credential_inventory(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        failure = self.result(exit_code=1, stdout=b'', stderr=(
            b'error: list credential metadata: logon session does not exist or there is no '
            b'credential set associated with this logon session\nprivate-canary'))
        with patch('mission_process.supervise', side_effect=[
                self.result(stdout=b'{"status":"running"}'), failure]) as process:
            report = driver.preflight()
        self.assertEqual(report['reason'], 'credential_session_unavailable')
        self.assertEqual(report['failed_phase'], 'secret_inventory')
        self.assertFalse(report['ready'])
        self.assertFalse(report['effects_allowed'])
        self.assertIsNone(report['credential_inventory_empty'])
        self.assertEqual(process.call_count, 2)
        self.assertIn('Windows desktop session', report['guidance'])
        self.assertNotIn('private-canary', json.dumps(report))
        self.assertEqual(self.module._error(failure, ('ls', '--json')), 'command_failed')
        # A diagnostic hint must not override a timeout or incomplete containment.
        for result, expected in ((dict(failure, reason='timeout'), 'timeout'),
                                 (dict(failure, tree_reaped=False), 'unsupported_containment'),
                                 (dict(failure, exit_code=0), None),
                                 (self.result(exit_code=1, stderr=b'unknown logon failure'), 'command_failed')):
            self.assertEqual(self.module._error(result, ('secret', 'ls', '--json')), expected)

    def test_cli_exposes_preflight_on_existing_environment_command(self):
        import missions
        args = missions.parser().parse_args(['client', 'environment', '--executable', str(self.exe), '--preflight'])
        self.assertTrue(args.preflight)

    def test_candidate_cli_uses_shared_preflight_without_followup_inspection(self):
        import contextlib
        import io
        import missions
        result = dict(version='0.46.0', gaps=['runtime_profile_unverified'])
        report = dict(ready=False, effects_allowed=False, reason='active_consumer')
        with patch('mission_sandbox.inspect_environment', return_value=result), \
             patch('mission_sbx.inspect_preflight', return_value=report) as preflight, \
             patch('mission_sandbox.inspect_sandbox') as inspection, contextlib.redirect_stdout(io.StringIO()):
            code = missions.main(['--root', str(self.root), 'client', 'environment', '--sandbox', 'yc-fixture',
                                  '--executable', str(self.exe), '--preflight', '--json'])
        self.assertEqual(code, 1)
        self.assertEqual(preflight.call_args.kwargs, {'sandbox': 'yc-fixture'})
        inspection.assert_not_called()

    def test_existing_environment_queries_use_shared_failure_classification(self):
        import mission_sandbox
        observation = {}
        with patch('mission_process.supervise', return_value=self.result(exit_code=1, stderr=b'Access is denied')):
            with self.assertRaises(ValueError):
                mission_sandbox._exchange(self.exe, ['ls', '--json'], self.root, observation=observation)
        self.assertEqual(observation.get('reason'), 'permission_denied')
        self.assertEqual(observation.get('exit_code'), 1)

    def test_metadata_readiness_is_not_execution_or_authentication(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        def run(plan, **kwargs):
            args = plan['argv'][1:]
            if args[0] == 'daemon': data = {'status':'running'}
            elif args[0] == 'secret': data = {'secrets':[], 'custom_secrets':[], 'shadowed_services':[], 'env_only_count':0}
            elif args[0] == 'ls': data = {'sandboxes':[]}
            else: data = {'key':args[2], 'value':None, 'default':None, 'source':'default', 'type':'string'}
            return self.result(stdout=json.dumps(data).encode())
        with patch('mission_process.supervise', side_effect=run):
            report = driver.preflight()
        self.assertTrue(report['ready'])
        self.assertFalse(report['effects_allowed'])
        self.assertEqual(report.get('credential_inventory_empty'), True)

    def test_inspection_metadata_does_not_accept_option_as_sandbox_name(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch('mission_process.supervise') as process:
            with self.assertRaisesRegex(ValueError, 'sbx_query_not_allowed'):
                driver.query('inspect', ('inspect', '--cloud', '--json'))
        process.assert_not_called()

    def test_private_evidence_precedes_dispatch_and_preserves_failure(self):
        self.assertTrue(callable(getattr(self.module, 'inspect_preflight', None)), 'durable preflight missing')
        (self.root / '.gitignore').write_text('/.operacao-local/execution/\n')
        def run(plan, **kwargs):
            files = list((self.root / '.operacao-local/execution').glob('sbx-*.json'))
            self.assertEqual(len(files), 1)
            before = json.loads(files[0].read_text())
            self.assertEqual(before['commands'][-1]['reason'], 'pending')
            return self.result(exit_code=1, stderr=b'Access is denied: token-canary')
        with patch('mission_process.supervise', side_effect=run):
            report = self.module.inspect_preflight(self.root, self.exe, '0.46.0')
        saved = json.loads((self.root / report['evidence_path']).read_text())
        self.assertEqual(saved['commands'][0]['reason'], 'permission_denied')
        self.assertTrue(saved['evidence'][0]['stderr_b64'])
        self.assertNotIn('token-canary', json.dumps(report))

    def test_unprotected_storage_prevents_docker_queries(self):
        self.assertTrue(callable(getattr(self.module, 'inspect_preflight', None)), 'durable preflight missing')
        with patch('mission_process.supervise') as process:
            with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
                self.module.inspect_preflight(self.root, self.exe, '0.46.0')
        process.assert_not_called()

    def test_relative_executable_dispatch_uses_the_hashed_absolute_path(self):
        import os
        work = self.root / 'work'
        work.mkdir()
        original = Path.cwd()
        try:
            os.chdir(self.root)
            driver = self.module.Sbx(Path('sbx.exe'), work, version='0.46.0')
            def run(plan, **kwargs):
                self.assertEqual(plan['argv'][0], str(self.exe))
                return self.result()
            with patch('mission_process.supervise', side_effect=run):
                driver.query('secret_inventory', ('secret', 'ls', '--json'))
        finally:
            os.chdir(original)

    def test_selectively_unignored_evidence_is_refused_before_dispatch(self):
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True, capture_output=True)
        (self.root / '.gitignore').write_text('/.operacao-local/execution/*\n!/.operacao-local/execution/sbx-*.json\n')
        with patch('mission_process.supervise', return_value=self.result(exit_code=1)) as process:
            with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
                self.module.inspect_preflight(self.root, self.exe, '0.46.0')
        process.assert_not_called()

    def test_preserved_legacy_adapter_returns_structured_error(self):
        import contextlib
        import io
        import types
        import missions
        output = io.StringIO()
        with patch.dict(sys.modules, {'mission_sbx':types.ModuleType('mission_sbx')}), \
             patch('mission_process.supervise') as process, contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment',
                                  '--executable', str(self.exe), '--preflight', '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'incompatible_helper')
        process.assert_not_called()

    def test_old_supervisor_cannot_silently_discard_stderr(self):
        with patch('mission_process.SUPERVISOR_CAPTURE_VERSION', 0, create=True):
            with self.assertRaisesRegex(ValueError, '^incompatible_helper$'):
                self.module.Sbx(self.exe, self.root, version='0.46.0')

    def test_private_permission_failure_is_actionable_before_queries(self):
        (self.root / '.gitignore').write_text('/.operacao-local/execution/\n')
        with patch('adoption_fs.private_dir', side_effect=ValueError('unsupported_permissions')), \
             patch('mission_process.supervise') as process:
            with self.assertRaisesRegex(ValueError, '^execution_storage_unprotected$'):
                self.module.inspect_preflight(self.root, self.exe, '0.46.0')
        process.assert_not_called()

    def test_preflight_retains_failed_command_and_never_retries(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        def run(plan, **kwargs):
            args = plan['argv'][1:]
            self.assertEqual(plan['timeout_seconds'], 15)
            if args == ['daemon', 'status', '--json']:
                return self.result(stdout=b'{"status":"running"}')
            if args == ['secret', 'ls', '--json']:
                return self.result(exit_code=1, stderr=b'Access is denied: token-canary')
            self.fail('Unexpected query after failed secret inventory: ' + str(args))
        with patch('mission_process.supervise', side_effect=run):
            report = driver.preflight()
        self.assertEqual(report['reason'], 'permission_denied')
        self.assertEqual(report['failed_phase'], 'secret_inventory')
        self.assertEqual(len(driver.records), 2)
        self.assertNotIn('token-canary', json.dumps(report))

    def test_policy_queries_are_bounded_and_never_allow_mutations(self):
        for args, data in [
                (('policy', 'ls', '--json'), {'rules': []}),
                (('policy', 'ls', 'yc-fixture', '--json'), {'rules': []}),
                (('policy', 'log', 'yc-fixture', '--json', '--limit', '10'),
                 {'blocked_hosts': [], 'allowed_hosts': []})]:
            with self.subTest(args=args):
                driver, result = self.query(self.result(stdout=json.dumps(data).encode()), args)
                self.assertTrue(result['ok'])
                self.assertEqual(driver.records[0]['timeout_seconds'], 15)
                _, bad = self.query(self.result(stdout=b'{"rules":null}'), args)
                self.assertEqual(bad['reason'], 'contract_incompatible')
        for args in [('policy', 'ls', '--cloud', '--json'), ('policy', 'set', 'yc-fixture'),
                     ('policy', 'log', 'yc-fixture', '--json', '--limit', '100000')]:
            with patch('mission_process.supervise') as process:
                with self.assertRaisesRegex(ValueError, 'sbx_query_not_allowed'):
                    self.module.Sbx(self.exe, self.root, version='0.46.0').query('policy', args)
                process.assert_not_called()

    def test_empty_credential_inventory_includes_custom_and_environment_sources(self):
        for data, expected in [({'secrets': []}, None),
                ({'secrets': [], 'custom_secrets': ['private-canary'], 'shadowed_services': [], 'env_only_count': 0}, False),
                ({'secrets': [], 'custom_secrets': [], 'shadowed_services': [], 'env_only_count': 1}, False),
                ({'secrets': [], 'custom_secrets': [], 'shadowed_services': [], 'env_only_count': False}, None)]:
            self.assertIs(self.module.credential_inventory_empty(data), expected)

    def test_policy_metadata_requires_observed_fields_and_typed_log_timestamps(self):
        rule = dict(id='builtin', name='built-in', policy_id='', scope='global', applies_to='all',
                    resource_type='filesystem:read', decision='allow', resources=['/tmp'],
                    origin='builtin', layer='base', status='active', editable=False,
                    provenance={'created_via': 'builtin'}, actions=['read'])
        log = dict(count_since=1, host='fixture.invalid', last_seen='2026-10-07T01:00:00Z',
                   proxy_type='http', rule='fixture', since='2026-10-07T00:00:00Z', vm_name='yc-fixture',
                   reason='denied')
        for data, args, valid in [({'rules': [rule]}, ('policy', 'ls', '--json'), True),
                ({'rules': [dict(rule, extra='preserved')]}, ('policy', 'ls', '--json'), True),
                ({'rules': [{'arbitrary': 1}]}, ('policy', 'ls', '--json'), False),
                ({'rules': [dict(rule, editable=1)]}, ('policy', 'ls', '--json'), False),
                ({'blocked_hosts': [log], 'allowed_hosts': []}, ('policy', 'log', 'yc-fixture'), True),
                ({'blocked_hosts': [dict(log, count_since=True)], 'allowed_hosts': []}, ('policy', 'log', 'yc-fixture'), False),
                ({'blocked_hosts': [dict(log, since='not-a-date')], 'allowed_hosts': []}, ('policy', 'log', 'yc-fixture'), False)]:
            with self.subTest(data=data):
                self.assertEqual(self.module._contract(args, data), valid)


class CandidatePreflightTests(unittest.TestCase):
    result = SbxTests.result
    def test_recovery_attempt_deadline_prevents_late_stop(self):
        import mission_transaction as tx
        from test_mission_transaction import inputs
        driver, _ = self.candidate()
        args = inputs()
        args.update(baseline=driver.baseline, candidate=dict(id=self.vm_id, name=self.name,
                    outer_digest=self.inspection['image_digest'], inner_digest='sha256:'+'b'*64))
        plan = tx.build_plan(**args)
        self.inspection['state'] = self.listing['sandboxes'][0]['status'] = 'running'
        clock, queries = [0.0], []
        def exchange(command, **kwargs):
            queries.append(command['argv'][1])
            self.assertNotEqual(command['argv'][1], 'exec')
            result = self.exchange(command, **kwargs)
            if len(queries) == 3:
                clock[0] = 2.0
            return result
        with patch('time.monotonic', side_effect=lambda: clock[0]):
            backend = self.module.Recovery(driver, plan)
            backend.bind_deadline(1.0)
            with patch('mission_process.supervise', side_effect=exchange), self.assertRaisesRegex(ValueError, 'recovery_deadline'):
                backend.workload('A', stop=True)
        self.assertEqual(queries, ['ls', 'inspect', 'ls'])

    def test_native_recovery_never_executes_launcher_in_stopped_vm(self):
        import mission_transaction as tx
        from test_mission_transaction import inputs
        driver, report = self.candidate()
        self.assertTrue(callable(getattr(self.module, 'Recovery', None)), 'native recovery adapter missing')
        args = inputs()
        args.update(baseline=driver.baseline, candidate=dict(id=self.vm_id, name=self.name,
                    outer_digest=self.inspection['image_digest'], inner_digest='sha256:'+'b'*64))
        plan = tx.build_plan(**args)
        backend = self.module.Recovery(driver, plan)
        self.counts.clear()
        with patch('mission_process.supervise', side_effect=self.exchange), \
             patch.object(driver, 'daemon_identity', return_value=self.identity):
            self.assertEqual(backend.observe()['observations'], driver.baseline['observations'])
            with self.assertRaisesRegex(ValueError, 'candidate_not_running'):
                backend.workload('A', stop=True)
        self.assertFalse(any(args[0] in ('exec', 'stop') for args in self.counts))

    def test_native_recovery_uses_closed_launcher_arguments_for_owned_phase(self):
        import mission_transaction as tx
        from test_mission_transaction import inputs
        driver, _ = self.candidate()
        self.assertTrue(callable(getattr(self.module, 'Recovery', None)), 'native recovery adapter missing')
        args = inputs()
        args.update(baseline=driver.baseline, candidate=dict(id=self.vm_id, name=self.name,
                    outer_digest=self.inspection['image_digest'], inner_digest='sha256:'+'b'*64))
        plan = tx.build_plan(**args)
        backend = self.module.Recovery(driver, plan)
        self.inspection['state'] = self.listing['sandboxes'][0]['status'] = 'running'
        phase = plan['phases'][0]
        observed = dict(schema_version=1, operation_id=phase['operation_id'], nonce=phase['nonce'],
            manifest_sha256=tx.sha(phase), image=plan['candidate']['inner_digest'], container_id='a'*64,
            inspection_sha256='b'*64, state=dict(Status='exited', Running=False, Pid=0), workload_reaped=True)
        def exchange(command, **kwargs):
            if command['argv'][1] == 'exec':
                self.assertEqual(command['argv'][1:], ['exec', '-u', 'root', self.name,
                    '/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/launcher.py',
                    'stop', phase['operation_id'], phase['nonce']])
                self.assertEqual(command['stdin'], b'')
                return self.result(stdout=json.dumps(observed).encode())
            return self.exchange(command, **kwargs)
        with patch('mission_process.supervise', side_effect=exchange), \
             patch.object(driver, 'daemon_identity', return_value=self.identity):
            self.assertEqual(backend.workload('A', stop=True), observed)
        self.inspection['image_digest'] = 'sha256:'+'f'*64
        with patch('mission_process.supervise', side_effect=exchange), self.assertRaisesRegex(ValueError, 'candidate_identity_changed'):
            backend.workload('A', stop=True)
    def test_candidate_baseline_values_are_private_and_discarded_after_failed_refresh(self):
        driver, report = self.candidate()
        self.assertTrue(report['ready'])
        self.assertIsNotNone(getattr(driver, 'baseline', None), 'private restorable baseline missing')
        self.assertEqual(self.module._sha(driver.baseline), report['baseline_sha256'])
        self.assertEqual(driver.baseline['observations']['setting_proxy_sandbox']['source'], 'default')
        self.assertEqual(driver.baseline['daemon_identity'], self.identity)
        self.assertNotIn('baseline', report)
        with patch.object(driver, 'query', return_value=dict(ok=False, reason='fixture_failed')):
            driver.candidate_preflight(self.name)
        self.assertIsNone(driver.baseline)
    # Keep this fixture independent of a local Docker installation or any secret store.
    def setUp(self):
        SbxTests.setUp(self)
        self.name = 'yc-fixture'
        self.vm_id = '3a4a47a2-6dbd-4196-a7a8-a481f65bdd85'
        self.identity = {'pid': 10, 'created_at': '/Date(1791160560000)/'}
        self.inspection = dict(name=self.name, state='stopped', daemon_version='v0.46.0',
                               image_digest='sha256:' + 'a' * 64, cpus=2, memory='4096m',
                               runtime_mounts=[], sessions=0, mcp_gateway=True)
        self.listing = {'sandboxes': [dict(id=self.vm_id, name=self.name, status='stopped')]}
        self.change = None
        self.counts = {}

    def exchange(self, plan, **kwargs):
        args = tuple(plan['argv'][1:])
        self.counts[args] = self.counts.get(args, 0) + 1
        if args[0] == 'daemon': data = {'status': 'running', 'socket': 'fixture', 'logs': 'private-canary'}
        elif args[0] == 'secret': data = {'secrets': [], 'custom_secrets': [], 'shadowed_services': [], 'env_only_count': 0}
        elif args[0] == 'ls': data = self.listing
        elif args[0] == 'inspect': data = self.inspection
        elif args[:2] == ('policy', 'ls'): data = {'rules': []}
        elif args[:2] == ('policy', 'log'): data = {'blocked_hosts': [], 'allowed_hosts': []}
        else: data = {'key': args[2], 'value': '', 'default': '', 'source': 'default', 'type': 'string'}
        data = json.loads(json.dumps(data))
        if self.change:
            self.change(args, self.counts[args], data)
        return self.result(stdout=json.dumps(data).encode())

    def candidate(self, identities=None):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch('mission_process.supervise', side_effect=self.exchange), \
             patch.object(driver, 'daemon_identity', side_effect=identities or [self.identity, self.identity]), \
             patch.dict('os.environ', {}, clear=True):
            return driver, driver.preflight(sandbox=self.name)

    def test_stable_candidate_is_observed_but_does_not_authorize_effects(self):
        driver, report = self.candidate()
        self.assertTrue(report['ready'])
        self.assertFalse(report['effects_allowed'])
        self.assertEqual(report['scope'], 'candidate_metadata')
        self.assertEqual(report['candidate']['id'], self.vm_id)
        self.assertEqual(report['candidate']['memory_mib'], 4096)
        self.assertEqual(report['candidate']['image_digest'], self.inspection['image_digest'])
        self.assertRegex(report['baseline_sha256'], '^[a-f0-9]{64}$')
        self.assertNotIn('private-canary', json.dumps(report))
        self.assertTrue(any(row['args'][:2] == ['policy', 'log'] for row in driver.records))

    def test_daemon_replacement_and_policy_or_setting_drift_refuse(self):
        _, report = self.candidate([self.identity, dict(self.identity, created_at='/Date(1791160561000)/')])
        self.assertEqual(report['reason'], 'daemon_identity_changed')
        for target in [('settings', 'get', 'proxy.sandbox', '--json'), ('policy', 'ls', '--json')]:
            self.counts.clear()
            def change(args, count, data):
                if args == target and count == 2:
                    data['unexpected_field'] = 'private-canary'
            self.change = change
            _, report = self.candidate()
            self.assertEqual(report['reason'], 'configuration_changed')
            self.assertFalse(report['ready'])
            self.assertNotIn('private-canary', json.dumps(report))

    def test_active_duplicate_unknown_credentials_or_mounts_refuse_before_readiness(self):
        for mode, expected in [('active', 'active_consumer'), ('duplicate', 'inventory_identity_ambiguous'),
                               ('custom', 'credential_inventory_not_empty'), ('mount', 'host_mounts_present')]:
            with self.subTest(mode=mode):
                self.counts.clear()
                def change(args, count, data):
                    if mode == 'active' and args[0] == 'ls': data['sandboxes'][0]['status'] = 'running'
                    if mode == 'duplicate' and args[0] == 'ls': data['sandboxes'] *= 2
                    if mode == 'custom' and args[0] == 'secret': data['custom_secrets'] = ['private-canary']
                    if mode == 'mount' and args[0] == 'inspect': data['runtime_mounts'] = ['private-canary']
                self.change = change
                _, report = self.candidate()
                self.assertEqual(report['reason'], expected)
                self.assertFalse(report['ready'])
                self.assertNotIn('private-canary', json.dumps(report))

    def test_proxy_override_blocks_before_any_docker_command(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch.dict('os.environ', {'hTtPs_PrOxY': 'private-canary'}, clear=True), \
             patch('mission_process.supervise') as process:
            report = driver.preflight(sandbox=self.name)
        self.assertEqual(report['reason'], 'proxy_environment_present')
        process.assert_not_called()
        self.assertNotIn('private-canary', json.dumps(report))

    def test_inspection_uptime_changes_without_hiding_identity_drift(self):
        def uptime(args, count, data):
            if args[0] == 'inspect': data['daemon_uptime'] = str(count) + 'm0s'
        self.change = uptime
        _, report = self.candidate()
        self.assertTrue(report['ready'])
        for field, value in [('image_digest', 'sha256:' + 'b' * 64), ('unknown_field', 'private-canary')]:
            self.counts.clear()
            def change(args, count, data):
                uptime(args, count, data)
                if args[0] == 'inspect' and count == 2: data[field] = value
            self.change = change
            _, report = self.candidate()
            self.assertEqual(report['reason'], 'configuration_changed')

    @patch('mission_sbx.hash_executable', return_value='f' * 64)
    def test_daemon_identity_reads_only_fixed_metadata_and_refuses_ambiguity(self, _):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        row = dict(ProcessId=19, CreationDate='/Date(1791160560000)/', ExecutablePath=str(self.exe))
        with patch('mission_sbx.platform.system', return_value='Windows'), \
             patch('mission_process.supervise', return_value=self.result(stdout=json.dumps(row).encode())) as run:
            identity = driver.daemon_identity('daemon_identity_before')
        self.assertEqual(identity, dict(pid=19, created_at=row['CreationDate']))
        plan = run.call_args.args[0]
        self.assertTrue(plan['system_probe'])
        self.assertEqual(plan['timeout_seconds'], 15)
        self.assertNotIn('CommandLine', plan['argv'][-1])
        self.assertEqual(driver.records[-1]['command_kind'], 'host_metadata')
        for data, reason in [([row, row], 'daemon_identity_ambiguous'),
                             (dict(row, ExecutablePath=None), 'daemon_identity_unavailable'),
                             (dict(row, ExecutablePath=7), 'daemon_identity_unavailable'),
                             (dict(row, ProcessId=True), 'daemon_identity_contract_incompatible')]:
            with self.subTest(reason=reason), patch('mission_sbx.platform.system', return_value='Windows'), \
                 patch('mission_process.supervise', return_value=self.result(stdout=json.dumps(data).encode())):
                with self.assertRaisesRegex(ValueError, reason): driver.daemon_identity('identity')

    def test_missing_host_probe_keeps_phase_and_never_dispatches(self):
        driver = self.module.Sbx(self.exe, self.root, version='0.46.0')
        with patch('mission_sbx.platform.system', return_value='Windows'), \
             patch('mission_sbx.hash_executable', side_effect=FileNotFoundError('private-canary')), \
             patch('mission_process.supervise') as run:
            with self.assertRaisesRegex(ValueError, '^host_probe_unavailable$'):
                driver.daemon_identity('daemon_identity_before')
        run.assert_not_called()
        self.assertEqual(driver.records[-1]['phase'], 'daemon_identity_before')
        self.assertEqual(driver.records[-1]['reason'], 'host_probe_unavailable')
        self.assertNotIn('private-canary', json.dumps(driver.records))


if __name__ == '__main__':
    unittest.main()
