"""Exercise controller code in real inherited containment, with a local launcher."""
import importlib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import mission_process

HELPER = Path(__file__).parent/'fixtures/isolated_controller.py'


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_controller'), 'controller missing')
        self.controller = importlib.import_module('mission_controller')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def manifest(self, phase='A', *, injection=False):
        extra = dict(injection_sha256=hashlib.sha256(b'disposable-test-injection').hexdigest()) if injection else {}
        return self.controller.phase_manifest(operation_id=str(uuid.uuid4()), nonce=uuid.uuid4().hex,
            deadline_ms=int(time.time()*1000)+5000, phase=phase, proxy_ipv4='172.17.0.1',
            ca_sha256='d'*64, placeholder='youngcrow-probe-'+uuid.uuid4().hex, **extra)

    def test_v4_binds_injection_receipt_without_accepting_native_proof(self):
        manifest=self.manifest(injection=True)
        result=self.run_controller(manifest)
        self.assertEqual(manifest['schema_version'],4)
        self.assertEqual(result['state'],'observed',result)
        self.assertEqual(result['fixture']['injected_value_sha256'],manifest['relay']['injection_sha256'])
        self.assertNotIn('echo_matches',result['fixture'])
        self.assertFalse(result['proof_accepted'])

    def test_v4_refuses_legacy_result_or_response_supplied_hash(self):
        for mode in ('legacy_echo','wrong_injection_hash'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                self.root=Path(temporary)
                result=self.run_controller(self.manifest(injection=True),mode)
                self.assertEqual(result['reason'],'fixture_result_invalid')

    def run_controller(self, manifest, mode='success'):
        plan = dict(argv=[sys.executable, '-I', '-B', str(HELPER.resolve()), '--controller', mode],
                    cwd=str(self.root), stdin=json.dumps(manifest).encode(), timeout_seconds=6,
                    output_limit_bytes=4096, client='metadata', connection='native')
        def owner(value):
            (self.root/'owner.json').write_text(json.dumps(value))
        result = mission_process.supervise(plan, on_started=owner, stop_requested=lambda: False)
        self.assertEqual(result['reason'], 'completed', result)
        self.assertEqual(result['exit_code'], 0, result)
        self.assertTrue(result['tree_reaped'], result)
        self.assertTrue(mission_process.owner_gone(result['owner']))
        self.assertNotIn(b'private-error-canary', result['stdout']+result['stderr'])
        return json.loads(result['stdout'])

    def test_open_pipe_waits_for_both_gates_and_decodes_fragmented_events(self):
        manifest = self.manifest()
        result = self.run_controller(manifest)
        self.assertEqual(result['state'], 'observed')
        self.assertEqual(result['phase'], 'A')
        self.assertEqual(result['model_calls'], 0)
        self.assertFalse(result['proof_accepted'])
        self.assertFalse(result['workload_reaped'])
        self.assertEqual(result['fixture']['nonce'], manifest['nonce'])
        self.assertEqual((self.root/'dispatches').read_bytes(), b'1\n')
        for kind in ('prepare_intent', 'prepared', 'run_intent', 'initialize_intent',
                     'initialize_gate', 'initialize_authorization', 'dispatch_intent',
                     'dispatch_gate', 'dispatch_authorization', 'observed'):
            self.assertTrue((self.root/(kind+'.json')).is_file(), kind)

    def test_persistence_failure_keeps_dispatch_closed_and_replay_consumed(self):
        manifest = self.manifest()
        first = self.run_controller(manifest, 'persist_failure')
        self.assertEqual(first['reason'], 'persistence_failed')
        self.assertFalse((self.root/'dispatches').exists())
        again = self.run_controller(manifest)
        self.assertEqual(again['reason'], 'persistence_failed')
        self.assertFalse((self.root/'dispatches').exists())

    def test_identity_and_network_namespace_changes_refuse_before_dispatch(self):
        for mode in ('prepare_identity', 'listening_identity', 'gate_identity', 'namespace_changed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary)
                result = self.run_controller(self.manifest(), mode)
                self.assertEqual(result['state'], 'refused')
                self.assertFalse((self.root/'dispatches').exists())

    def test_failed_dispatch_authorization_never_sends_the_command(self):
        result = self.run_controller(self.manifest(), 'dispatch_persist_failure')
        self.assertEqual(result['reason'], 'persistence_failed')
        self.assertTrue((self.root/'dispatch_gate.json').is_file())
        self.assertFalse((self.root/'dispatches').exists())

    def test_initialization_exit_zero_without_ready_never_opens_dispatch_gate(self):
        result = self.run_controller(self.manifest(), 'discovery_descendants')
        self.assertEqual(result['reason'], 'guardian_refused')
        self.assertFalse((self.root/'dispatch_intent.json').exists())
        self.assertFalse((self.root/'network-dispatch.json').exists())
        self.assertFalse((self.root/'dispatches').exists())

    def test_lost_observation_after_dispatch_does_not_allow_replay(self):
        manifest = self.manifest()
        first = self.run_controller(manifest, 'observation_persist_failure')
        self.assertEqual(first['state'], 'refused')
        self.assertEqual(first['reason'], 'persistence_failed')
        self.assertFalse(first['proof_accepted'])
        self.assertFalse((self.root/'observed.json').exists())
        again = self.run_controller(manifest)
        self.assertEqual(again['reason'], 'persistence_failed')
        self.assertEqual((self.root/'dispatches').read_bytes(), b'1\n')

    def test_bad_order_truncated_frames_and_extra_events_cannot_pass(self):
        for mode in ('early_ready', 'duplicate_started', 'truncated', 'oversized', 'extra_event', 'bad_echo'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary)
                result = self.run_controller(self.manifest(), mode)
                self.assertEqual(result['state'], 'refused', result)
                self.assertFalse(result['proof_accepted'])

    def test_phase_b_disconnect_remains_unattributed(self):
        result = self.run_controller(self.manifest('B'), 'unattributed_block')
        self.assertEqual(result['state'], 'blocked_unattributed')
        self.assertFalse(result['proof_accepted'])
        self.assertFalse(result['workload_reaped'])

    def test_phase_b_success_is_unexpected_allow(self):
        result = self.run_controller(self.manifest('B'))
        self.assertEqual(result['state'], 'unexpected_allow')
        self.assertFalse(result['proof_accepted'])

    def test_deadline_reaps_descendants_in_the_existing_supervisor(self):
        manifest = self.manifest()
        manifest['deadline_ms'] = int(time.time()*1000)+1800
        # Regenerate the fixed argv along with the changed deadline.
        manifest['dispatch_prefix'][-1] = str(manifest['deadline_ms'])
        result = self.run_controller(manifest, 'hang')
        self.assertEqual(result['reason'], 'deadline')
        self.assertFalse((self.root/'dispatches').exists())
        self.assertTrue((self.root/'helper.pid').exists())

    def test_manifest_rejects_arbitrary_commands_before_any_transport_effect(self):
        manifest = self.manifest()
        manifest['dispatch_prefix'] += ['--url', 'https://example.invalid']
        result = self.run_controller(manifest)
        self.assertEqual(result['reason'], 'invalid_manifest')
        self.assertFalse((self.root/'launch.json').exists())

    def test_partial_reader_startup_closes_child_and_sanitizes_error(self):
        process, first, second = Mock(), Mock(), Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('internal-launcher', .1), 0]
        first.is_alive.return_value = False
        second.start.side_effect = RuntimeError('private-error-canary')
        with patch.object(self.controller.subprocess, 'Popen', return_value=process), \
             patch.object(self.controller.threading, 'Thread', side_effect=[first, second]):
            with self.assertRaisesRegex(self.controller.Refused, '^transport_start_failed$'):
                self.controller.Channel(['internal-launcher'], cwd=self.root,
                                        deadline_ms=int(time.time()*1000)+5000)
        process.terminate.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        first.join.assert_called_once()
        second.join.assert_not_called()
        process.stdin.close.assert_called_once()
        process.stdout.close.assert_called_once()
        process.stderr.close.assert_called_once()


class ChannelShutdownTests(unittest.TestCase):
    def test_eof_allows_cleanup_and_stubborn_child_is_still_collected(self):
        for mode in ('cooperative', 'stubborn'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                result = mission_process.supervise(dict(argv=[sys.executable, '-I', '-B',
                    str(Path(__file__).parent/'fixtures/channel_shutdown.py'), mode],
                    cwd=temporary, stdin=b'', timeout_seconds=6, output_limit_bytes=4096,
                    client='metadata', connection='native'),
                    on_started=lambda _:None, stop_requested=lambda:False)
                self.assertEqual((result['reason'], result['exit_code']), ('completed', 0), result)
                self.assertTrue(result['tree_reaped'], result)
                self.assertTrue(mission_process.owner_gone(result['owner']))
                receipt = json.loads(result['stdout'])
                self.assertTrue(receipt['readers_collected'], receipt)
                self.assertEqual(receipt['cooperative_cleanup'], mode == 'cooperative', receipt)
                if mode == 'cooperative':
                    self.assertEqual(receipt['exit_code'], 0, receipt)
                else:
                    self.assertNotEqual(receipt['exit_code'], 0, receipt)

    def test_grace_shares_termination_budget_and_expired_deadline_skips_it(self):
        import mission_controller as controller
        for expired, late in ((False, False), (False, True), (True, False)):
            with self.subTest(expired=expired, late=late):
                channel = controller.Channel.__new__(controller.Channel)
                channel.stop, channel.process, channel.deadline = Mock(), Mock(), Mock()
                channel.threads = []
                channel.process.poll.return_value = None
                if expired:
                    channel.deadline.remaining.side_effect = controller.Refused('deadline')
                    channel.process.wait.side_effect = [subprocess.TimeoutExpired('fixture', .2), 0]
                else:
                    channel.deadline.remaining.return_value = .08
                    channel.process.wait.side_effect = [subprocess.TimeoutExpired('fixture', .08),
                        subprocess.TimeoutExpired('fixture', .12), 0]
                clock = [10, 10.08] if expired else [10, 10.18, 10.2] if late else [10, 10, 10.08]
                with patch.object(controller.time, 'monotonic', side_effect=clock):
                    channel.close()
                timeouts = [call.kwargs['timeout'] for call in channel.process.wait.call_args_list]
                self.assertEqual(len(timeouts), 2 if expired else 3)
                self.assertAlmostEqual(sum(timeouts[:-1]), .12 if expired else .02 if late else .2)
                self.assertEqual(timeouts[-1], .2)
                channel.process.terminate.assert_called_once()
                channel.process.kill.assert_called_once()


if __name__ == '__main__':
    unittest.main()
