"""Read-only sandbox preflight; external metadata is replaced, never certified."""
import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import missions


class SandboxEnvironmentTests(unittest.TestCase):
    def test_phase_timeout_keeps_independent_version_and_no_secrets(self):
        import mission_process
        before = self.snapshot()
        calls = []
        def supervised(plan, **kwargs):
            calls.append(plan['argv'])
            timeout = 'version' not in plan['argv']
            return dict(reason='timeout' if timeout else 'completed', exit_code=0, tree_reaped=True,
                        stdout=b'secret-canary' if timeout else b'sbx version: v0.46.0 abc123\n',
                        started_at='2026-10-05T00:00:00+00:00', ended_at='2026-10-05T00:00:30+00:00',
                        elapsed_seconds=30.01 if timeout else .01)
        with patch.object(self.sandbox.platform, 'system', return_value='Windows'), \
             patch.object(self.sandbox.platform, 'machine', return_value='AMD64'), \
             patch.object(self.sandbox.platform, 'win32_ver', return_value=('', '10.0.26200', '', '')), \
             patch.object(mission_process, 'supervise', side_effect=supervised):
            result = self.sandbox.inspect_environment(self.root, self.executable)
        by_id = {p['id']: p for p in result['phases']}
        self.assertEqual(by_id['virtualization']['state'], 'timeout')
        self.assertEqual(by_id['virtualization']['timeout_seconds'], 30)
        self.assertEqual(by_id['runtime_version']['state'], 'observed')
        self.assertEqual(len(calls), 2)
        for phase in result['phases']:
            self.assertEqual(set(phase), {'id', 'started_at', 'ended_at', 'elapsed_seconds',
                                        'timeout_seconds', 'output_limit_bytes', 'state', 'reason'})
        self.assertIn('runtime_profile_unverified', result['gaps'])
        self.assertEqual(result['profile_ids'], [])
        self.assertNotIn('secret-canary', json.dumps(result['phases']))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(result['selection']['origin'], 'default')
        self.assertEqual(by_id['sandbox_inspect']['reason'], 'not_requested')

    def test_phase_incompatible_helpers_and_selection_stop_before_queries(self):
        import mission_process, mission_clients
        for module, field in ((mission_process, 'SUPERVISOR_OBSERVATION_VERSION'),
                              (mission_clients, 'DISCOVERY_OBSERVATION_VERSION')):
            with patch.object(module, field, None, create=True), \
                 patch.object(mission_process, 'supervise', side_effect=AssertionError('must not query')):
                with self.assertRaisesRegex(ValueError, '^incompatible_helper$'):
                    self.sandbox.inspect_environment(self.root, self.executable)
        path = self.root / '.operacao-local/execution/selection.json'
        path.parent.mkdir(parents=True)
        path.write_text('secret-canary')
        with patch.object(mission_process, 'supervise', side_effect=AssertionError('must not query')):
            with self.assertRaises(ValueError):
                self.sandbox.inspect_environment(self.root, self.executable)

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_sandbox'),
                             'sandbox environment preflight is not implemented')
        self.sandbox = importlib.import_module('mission_sandbox')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.executable = self.root / 'sbx.exe'
        self.executable.write_bytes(b'synthetic installed executable')
        self.facts = dict(system='Windows', machine='AMD64', build='26200',
                          whp_state=1, distribution=None, kvm_access=None)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def inspect(self, *, facts=None, metadata=None):
        with patch.object(self.sandbox, '_host_facts', return_value=facts or self.facts), \
             patch.object(self.sandbox, '_exchange',
                          return_value=metadata or 'sbx version: v0.46.0 abc123\n'):
            return self.sandbox.inspect_environment(self.root, self.executable)

    def test_missing_runtime_is_readonly(self):
        before = self.snapshot()
        with patch.object(self.sandbox, '_host_facts', return_value=self.facts), \
             patch.object(self.sandbox, '_exchange', side_effect=AssertionError('must not execute')):
            result = self.sandbox.inspect_environment(self.root, self.root / 'missing.exe')
        self.assertIn('runtime_missing', result['gaps'])
        self.assertIsNone(result['version'])
        self.assertEqual(self.snapshot(), before)

    def test_observed_version_never_certifies_an_executor(self):
        before = self.snapshot()
        result = self.inspect()
        self.assertEqual(result['version'], '0.46.0')
        self.assertEqual(result['executable_sha256'],
                         hashlib.sha256(b'synthetic installed executable').hexdigest())
        self.assertIn('runtime_profile_unverified', result['gaps'])
        self.assertEqual(result['profile_ids'], [])
        self.assertEqual(self.snapshot(), before)

    def test_disabled_whp_and_unsupported_hosts_stay_blocked(self):
        for change, expected in [({'whp_state': 2}, 'whp_disabled'),
                                 ({'whp_state': None}, 'whp_unknown'),
                                 ({'build': '19045'}, 'unsupported_platform'),
                                 ({'machine': 'ARM64'}, 'unsupported_platform'),
                                 ({'system': 'Darwin'}, 'unsupported_platform'),
                                 ({'system': 'Linux', 'distribution': 'ubuntu:24.04',
                                   'kvm_access': False}, 'kvm_unavailable')]:
            with self.subTest(change=change):
                result = self.inspect(facts=dict(self.facts, **change))
                self.assertIn(expected, result['gaps'])
                self.assertIn('runtime_profile_unverified', result['gaps'])

    def test_replaced_executable_invalidates_observation(self):
        def exchanged(*args, **kwargs):
            self.executable.write_bytes(b'replaced executable')
            return 'sbx version: v0.46.0 abc123\n'
        with patch.object(self.sandbox, '_host_facts', return_value=self.facts), \
             patch.object(self.sandbox, '_exchange', side_effect=exchanged):
            result = self.sandbox.inspect_environment(self.root, self.executable)
        self.assertIn('stale_observation', result['gaps'])
        self.assertIsNone(result['version'])
        self.assertEqual(result['profile_ids'], [])

    def test_invalid_or_failed_metadata_is_sanitized(self):
        for metadata in ('secret-canary 0.46.0', 'sbx version: v0.46.0\nsbx version: v99.0.0',
                         'sbx version: v0.46.0\nsecret-canary'):
            result = self.inspect(metadata=metadata)
            self.assertIn('runtime_metadata_invalid', result['gaps'])
            self.assertNotIn('secret-canary', json.dumps(result))
        with patch.object(self.sandbox, '_host_facts', return_value=self.facts), \
             patch.object(self.sandbox, '_exchange', side_effect=ValueError('secret-canary')):
            result = self.sandbox.inspect_environment(self.root, self.executable)
        self.assertIn('runtime_metadata_failed', result['gaps'])
        self.assertNotIn('secret-canary', json.dumps(result))

    def test_cli_reports_missing_runtime_without_installing_or_writing(self):
        before = self.snapshot()
        output = io.StringIO()
        with patch.object(self.sandbox, '_host_facts', return_value=self.facts), \
             contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment',
                                  '--executable', str(self.root / 'missing.exe'), '--json'])
        self.assertEqual(code, 1)
        self.assertIn('runtime_missing', json.loads(output.getvalue())['gaps'])
        self.assertEqual(self.snapshot(), before)

    def test_preserved_incompatible_helper_reports_guidance(self):
        output = io.StringIO()
        with patch.object(self.sandbox, 'inspect_environment', None), \
             contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment',
                                  '--executable', str(self.executable), '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'incompatible_helper')

    def test_functional_legacy_helper_is_refused_before_queries(self):
        path = Path(__file__).parent / 'fixtures/legacy_mission_sandbox.py'
        spec = importlib.util.spec_from_file_location('legacy_sandbox', path)
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        legacy._host_facts = lambda root: self.facts
        legacy._exchange = lambda *args, **kwargs: 'sbx version: v0.46.0 abc123\n'
        self.assertNotIn('phases', legacy.inspect_environment(self.root, self.executable))
        before, output = self.snapshot(), io.StringIO()
        with patch.dict(sys.modules, {'mission_sandbox': legacy}), \
             patch.object(legacy, '_host_facts', wraps=legacy._host_facts) as queried, \
             contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment',
                                  '--executable', str(self.executable), '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'incompatible_helper')
        queried.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_windows_feature_query_accepts_only_known_integer_states(self):
        for metadata, expected in [('1', 1), ('2', 2), ('3', 3), ('4', 4),
                                   ('true', None), ('"1"', None), ('0', None),
                                   ('{"state":1,"state":2}', None), ('[1', None),
                                   ('1\nsecret-canary', None)]:
            with self.subTest(metadata=metadata), \
                 patch.object(self.sandbox.platform, 'system', return_value='Windows'), \
                 patch.object(self.sandbox.platform, 'win32_ver', return_value=('11', '10.0.26200', '', '')), \
                 patch.object(self.sandbox, '_exchange', return_value=metadata):
                result = self.sandbox._host_facts(self.root)
            self.assertEqual(result['whp_state'], expected)
            self.assertEqual(result['build'], '26200')
            self.assertNotIn('secret-canary', json.dumps(result))

    @unittest.skipUnless(os.name == 'nt', 'native Windows metadata and profile cache')
    def test_real_windows_metadata_does_not_write_profile(self):
        home = self.root / 'home'
        (home / 'AppData/Local').mkdir(parents=True)
        (home / 'AppData/Roaming').mkdir()
        before = self.snapshot()
        with patch.dict(os.environ, {'HOME': str(home), 'USERPROFILE': str(home),
                                     'LOCALAPPDATA': str(home / 'AppData/Local'),
                                     'APPDATA': str(home / 'AppData/Roaming')}):
            facts = self.sandbox._host_facts(self.root)
        self.assertEqual(facts['system'], 'Windows')
        self.assertEqual(self.snapshot(), before)


class SandboxRuntimeTests(unittest.TestCase):
    def test_phase_inventory_timeout_leaves_dependents_unchecked(self):
        def timeout(executable, args, root, **kwargs):
            self.calls.append(args)
            kwargs['observation'].update(started_at='2026-10-05T00:00:00+00:00',
                ended_at='2026-10-05T00:00:30+00:00', elapsed_seconds=30.01,
                timeout_seconds=30, output_limit_bytes=8388608, reason='timeout')
            raise ValueError('client_discovery_timeout')
        with patch.object(self.sandbox, '_exchange', side_effect=timeout):
            result = self.sandbox.inspect_sandbox(self.root, self.executable, 'yc-fixture')
        self.assertEqual(self.calls, [['ls', '--json']])
        self.assertEqual([p['state'] for p in result['phases']], ['timeout', 'not_checked', 'not_checked'])
        self.assertIsNone(result['phases'][1]['started_at'])
        self.assertIsNone(result['runtime'])

    def setUp(self):
        import mission_sandbox
        self.sandbox = mission_sandbox
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.executable = self.root / 'sbx.exe'
        self.executable.write_bytes(b'synthetic executable')
        self.runtime = dict(id=str(uuid.uuid4()), name='yc-fixture', image_digest='sha256:' + 'a'*64,
                            executable_sha256=hashlib.sha256(self.executable.read_bytes()).hexdigest())
        self.listing = dict(sandboxes=[dict(id=self.runtime['id'], name='yc-fixture', status='stopped')])
        self.inspection = dict(name='yc-fixture', state='stopped', image_digest=self.runtime['image_digest'],
                               cpus=2, memory='4g', runtime_mounts=[], mcp_gateway=False,
                               sessions=0, daemon_version='v0.46.0',
                               secrets=[{'value':'secret-canary'}])
        self.calls = []

    def exchange(self, executable, args, root, **kwargs):
        self.calls.append(args)
        if args == ['ls', '--json']:
            return json.dumps(self.listing)
        if args == ['inspect', 'yc-fixture', '--json']:
            return json.dumps(self.inspection)
        raise AssertionError('Unexpected or mutating invocation: ' + repr(args))

    def observation(self):
        return dict(schema_version=1, runtime_id=self.runtime['id'], runtime_name='yc-fixture',
                    identity=dict(sbx_version='0.46.0', executable_sha256=self.runtime['executable_sha256'],
                                  platform='windows-amd64', vm_image_digest='sha256:'+'a'*64,
                                  client_image_digest='sha256:'+'b'*64, guardian_sha256='c'*64,
                                  kit_sha256='d'*64, client='codex', client_version='1.0.0',
                                  client_sha256='e'*64, protocol_version=1),
                    controls=dict(host_mounts=False, host_ports=False, host_sockets=False,
                                  ssh=False, skills='off', mcp_gateway=True, mcp_client_access=False,
                                  mcp_isolation_verified=True, mcp_probe_sha256='9'*64, clipboard=False,
                                  remote_control=False, global_network_allow=False,
                                  network_policy_sha256='f'*64, network_verified=True,
                                  auth_mode='oauth', api_precedence=False, oauth_passthrough=False))

    def test_unknown_or_widened_profile_never_authorizes(self):
        self.assertTrue(callable(getattr(self.sandbox, 'validate_runtime', None)))
        observation = self.observation()
        profile = dict(id='synthetic-only', identity=observation['identity'], controls=observation['controls'])
        self.assertIn('runtime_profile_unverified', self.sandbox.validate_runtime(observation, profile)['gaps'])
        with patch.object(self.sandbox, 'REVIEWED_PROFILES', (copy.deepcopy(profile),)):
            self.assertEqual(self.sandbox.validate_runtime(observation, profile)['gaps'], [])
            for key in ('host_mounts', 'host_ports', 'host_sockets', 'ssh', 'mcp_client_access', 'clipboard',
                        'remote_control', 'global_network_allow', 'api_precedence', 'oauth_passthrough'):
                changed = copy.deepcopy(observation)
                changed['controls'][key] = True
                with self.subTest(control=key):
                    self.assertIn('unsafe_' + key, self.sandbox.validate_runtime(changed, profile)['gaps'])
            for change in ({'runtime_id':None}, {'runtime_name':'--cloud'}, {'verified':True}):
                self.assertTrue(self.sandbox.validate_runtime(dict(observation, **change), profile)['gaps'])
            for group, key, value in [('controls','skills','readwrite'), ('controls','auth_mode','api'),
                                      ('controls','ssh',0), ('controls','network_verified',None),
                                      ('identity','guardian_sha256','0'*64), ('identity','protocol_version',True)]:
                changed = copy.deepcopy(observation)
                changed[group][key] = value
                self.assertTrue(self.sandbox.validate_runtime(changed, profile)['gaps'])

    def test_forged_profile_cannot_relax_mandatory_controls(self):
        self.assertTrue(callable(getattr(self.sandbox, 'validate_runtime', None)))
        observation = self.observation()
        observation['controls']['mcp_client_access'] = True
        profile = dict(id='synthetic-only', identity=observation['identity'], controls=observation['controls'])
        with patch.object(self.sandbox, 'REVIEWED_PROFILES', (profile,)):
            self.assertIn('unsafe_mcp_client_access', self.sandbox.validate_runtime(observation, profile)['gaps'])

    def test_observe_stop_never_starts_sandbox_or_certifies_reaping(self):
        self.assertTrue(callable(getattr(self.sandbox, 'observe_stop', None)))
        with patch.object(self.sandbox, '_exchange', side_effect=self.exchange):
            result = self.sandbox.observe_stop(self.executable, self.runtime)
        self.assertEqual(self.calls, [['ls','--json'], ['inspect','yc-fixture','--json'], ['ls','--json']])
        self.assertTrue(result['identity_matches'])
        self.assertTrue(result['sandbox_stopped'])
        self.assertFalse(result['workload_reaped'])
        self.assertIn('workload_stop_unverified', result['gaps'])
        self.assertNotIn('secret-canary', json.dumps(result))
        self.assertRegex(result['evidence_sha256'], '^[0-9a-f]{64}$')

    def test_observed_mib_memory_normalizes_to_same_resource_limit(self):
        for value, valid in [('4096m', True), ('4g', True), ('8192m', False), (4096, False)]:
            with self.subTest(memory=value), patch.object(self, 'inspection', dict(self.inspection, memory=value)), \
                 patch.object(self.sandbox, '_exchange', side_effect=self.exchange):
                result = self.sandbox.inspect_sandbox(self.root, self.executable, 'yc-fixture')
                self.assertEqual('runtime_resources_unverified' not in result['gaps'], valid)
                self.assertIn('runtime_profile_unverified', result['gaps'])

    def test_missing_replaced_duplicate_or_running_vm_remains_uncertain(self):
        self.assertTrue(callable(getattr(self.sandbox, 'observe_stop', None)))
        for mode in ('missing', 'replaced', 'duplicate', 'running', 'inspection_changed'):
            with self.subTest(mode=mode):
                listing = copy.deepcopy(self.listing)
                inspection = copy.deepcopy(self.inspection)
                if mode == 'missing': listing['sandboxes'] = []
                if mode == 'replaced': listing['sandboxes'][0]['id'] = str(uuid.uuid4())
                if mode == 'duplicate': listing['sandboxes'] *= 2
                if mode == 'running': inspection['state'] = 'running'
                if mode == 'inspection_changed': inspection['image_digest'] = 'sha256:' + 'b'*64
                with patch.object(self, 'listing', listing), patch.object(self, 'inspection', inspection), \
                     patch.object(self.sandbox, '_exchange', side_effect=self.exchange):
                    result = self.sandbox.observe_stop(self.executable, self.runtime)
                self.assertFalse(result['sandbox_stopped'])
                self.assertFalse(result['workload_reaped'])
                self.assertTrue(result['gaps'])

    def test_disappearance_between_queries_or_executable_change_is_not_stop(self):
        self.assertTrue(callable(getattr(self.sandbox, 'observe_stop', None)))
        count = 0
        def changed(executable, args, root, **kwargs):
            nonlocal count
            if args == ['ls','--json']:
                count += 1
                if count == 2:
                    return '{"sandboxes":[]}'
            return self.exchange(executable, args, root, **kwargs)
        with patch.object(self.sandbox, '_exchange', side_effect=changed):
            self.assertFalse(self.sandbox.observe_stop(self.executable, self.runtime)['sandbox_stopped'])
        def replaced(*args, **kwargs):
            self.executable.write_bytes(b'replaced')
            return self.exchange(*args, **kwargs)
        with patch.object(self.sandbox, '_exchange', side_effect=replaced):
            self.assertFalse(self.sandbox.observe_stop(self.executable, self.runtime)['sandbox_stopped'])

    def test_invalid_input_and_malformed_json_are_sanitized(self):
        self.assertTrue(callable(getattr(self.sandbox, 'observe_stop', None)))
        with patch.object(self.sandbox, '_exchange', side_effect=AssertionError('must not query')):
            for change in ({'id':None}, {'name':'--cloud'}, {'executable_sha256':'0'*64}):
                result = self.sandbox.observe_stop(self.executable, dict(self.runtime, **change))
                self.assertFalse(result['identity_matches'])
        for bad in ('{"sandboxes":[],"sandboxes":[]}', '{', '{"sandboxes":"secret-canary"}', 'NaN'):
            with patch.object(self.sandbox, '_exchange', return_value=bad):
                result = self.sandbox.observe_stop(self.executable, self.runtime)
            self.assertFalse(result['sandbox_stopped'])
            self.assertNotIn('secret-canary', json.dumps(result))

    def test_optional_environment_inspection_reports_mcp_without_executing_vm(self):
        self.assertTrue(callable(getattr(self.sandbox, 'inspect_sandbox', None)))
        self.inspection['mcp_gateway'] = True
        with patch.object(self.sandbox, '_exchange', side_effect=self.exchange):
            result = self.sandbox.inspect_sandbox(self.root, self.executable, 'yc-fixture')
        self.assertIn('mcp_isolation_unverified', result['gaps'])
        self.assertIn('runtime_profile_unverified', result['gaps'])
        self.assertEqual(result['runtime']['id'], self.runtime['id'])
        self.assertNotIn('secret-canary', json.dumps(result))
        self.assertFalse(any('exec' in call for call in self.calls))

    def test_cli_exposes_only_safe_runtime_metadata_and_preserves_old_helper(self):
        output = io.StringIO()
        environment = dict(schema_version=1, version='0.46.0', gaps=['runtime_profile_unverified'])
        self.inspection['mcp_gateway'] = True
        with patch.object(self.sandbox, 'inspect_environment', return_value=environment), \
             patch.object(self.sandbox, '_exchange', side_effect=self.exchange), contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment', '--executable',
                                  str(self.executable), '--sandbox', 'yc-fixture', '--json'])
        self.assertEqual(code, 1)
        self.assertIn('mcp_isolation_unverified', json.loads(output.getvalue())['gaps'])
        self.assertNotIn('secret-canary', output.getvalue())
        output = io.StringIO()
        with patch.object(self.sandbox, 'inspect_sandbox', None), contextlib.redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'environment', '--executable',
                                  str(self.executable), '--sandbox', 'yc-fixture', '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'incompatible_helper')


if __name__ == '__main__':
    unittest.main()
