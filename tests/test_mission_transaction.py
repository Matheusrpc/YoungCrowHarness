"""Private durable plans and controller journal; no native sandbox effects."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import mission_execution as execution
import mission_sbx
from runtime_fixtures import RuntimeCase
import mission_backlog
import mission_runs
import mission_store
from fixtures.transaction_storage import registry_storage


def inputs():
    import mission_transaction as tx
    mid, op, pid, vm = (str(uuid.uuid4()) for _ in range(4))
    manifest = dict(schema_version=1, mission_id=mid, mission_revision=1, role='pm',
                    operation_id=op, authorization_ref='Local contract test', agent_seconds=30,
                    max_runs=1, api_budget_usd=None, fixture_id='isolated-egress-v1')
    candidate = dict(id=vm, name='yc-fixture', outer_digest='sha256:'+'a'*64,
                     inner_digest='sha256:'+'b'*64)
    observations = dict(secret_inventory=dict(secrets=[], custom_secrets=[], shadowed_services=[], env_only_count=0),
        sandbox_inventory=dict(sandboxes=[dict(id=vm, name='yc-fixture', status='stopped')]),
        candidate_inspect=dict(name='yc-fixture', state='stopped', sessions=0, cpus=2, memory='4g',
            image_digest=candidate['outer_digest'], daemon_version='v0.46.0', runtime_mounts=[], mcp_gateway=True),
        policy_global=dict(rules=[]), policy_candidate=dict(rules=[]))
    for key in mission_sbx.SETTINGS:
        observations['setting_'+key.replace('.', '_')] = dict(key=key, value='', default='', source='default', type='string')
    baseline = dict(executable_sha256='c'*64, version='0.46.0', daemon=dict(status='running'),
                    daemon_identity=dict(pid=10, created_at='/Date(1791160560000)/'), observations=observations)
    return dict(manifest=manifest, project_id=pid, project_sha256='d'*64,
                candidate=candidate, baseline=baseline, code_sha256=tx.code_hashes(),
                proxy_ipv4='172.17.0.1', ca_sha256='f'*64)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_transaction'), 'durable plan coordinator missing')
        import mission_transaction as tx
        self.tx = tx
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)/'registry'
        self.enterContext(registry_storage(self.base))
        self.registry = execution.Registry(self.base)
        self.args = inputs()
        self.plan = tx.build_plan(**self.args)

    def test_plan_roundtrip_keeps_values_and_distinct_phase_identities_after_expiry(self):
        first = self.tx.reserve(self.registry, self.plan)
        self.assertTrue(first['new'])
        original = copy.deepcopy(self.plan)
        self.plan['baseline']['observations']['setting_proxy_sandbox']['value'] = 'changed'
        with patch.object(time, 'time', return_value=time.time()+1000):
            record = execution.Registry(self.base).records()[0]
            self.assertEqual(record['plan'], original)
            self.assertFalse(self.tx.reserve(self.registry, original)['new'])
        self.assertEqual(len({p['operation_id'] for p in original['phases']}), 3)
        self.assertEqual(len({p['nonce'] for p in original['phases']}), 3)
        self.assertEqual({p['deadline_ms'] for p in original['phases']}, {original['deadline_ms']})
        self.assertLessEqual(original['deadline_ms']-original['created_ms'], 30000)
        self.assertEqual({p.name for p in self.base.iterdir()}, {'registry.json','reclaim.lock'})

    def test_legacy_consumed_and_other_projects_remain_exclusive(self):
        self.tx.reserve(self.registry, self.plan)
        other = self.tx.build_plan(**inputs())
        with self.assertRaisesRegex(ValueError, 'execution_reserved'):
            self.tx.reserve(self.registry, other)
        legacy = self.tx.request(self.plan)
        with tempfile.TemporaryDirectory() as temporary:
            registry = execution.Registry(Path(temporary)/'old')
            registry.reserve(legacy)
            registry.intent(legacy['operation_id'], 'A', dict(before_sha256='1'*64, after_sha256='2'*64))
            before = (registry.base/'registry.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'operation_conflict'):
                self.tx.reserve(registry, self.plan)
            self.assertEqual((registry.base/'registry.json').read_bytes(), before)

    def test_phase_intent_is_durable_and_repeat_or_out_of_order_cannot_authorize_effect(self):
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        payload = dict(operation_id=phase['operation_id'], nonce=phase['nonce'],
                       manifest_sha256=self.tx.sha(phase), image=self.plan['candidate']['inner_digest'], manifest=phase)
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent', payload)
        reopened = execution.Registry(self.base).records()[0]
        self.assertEqual(reopened['state'], 'consumed')
        self.assertEqual(reopened['journal'][0]['payload'], payload)
        with self.assertRaisesRegex(ValueError, 'effect_consumed'):
            self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent', payload)
        with self.assertRaisesRegex(ValueError, 'invalid_phase_order'):
            self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'dispatch_intent', payload)
        with self.assertRaisesRegex(ValueError, 'invalid_phase_order'):
            phase2 = self.plan['phases'][2]
            self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A2', 'prepare_intent',
                dict(payload, operation_id=phase2['operation_id'], nonce=phase2['nonce'],
                     manifest_sha256=self.tx.sha(phase2), manifest=phase2))

    def test_invalid_plan_and_failed_persistence_do_not_consume_effect(self):
        for change in ('baseline', 'phase', 'revision', 'deadline'):
            plan = copy.deepcopy(self.plan)
            if change == 'baseline': plan['baseline']['observations']['secret_inventory']['secrets'] = ['secret']
            elif change == 'phase': plan['phases'][1]['nonce'] = plan['phases'][0]['nonce']
            elif change == 'revision': plan['manifest']['mission_revision'] = False
            else: plan['deadline_ms'] += 120000
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.tx.reserve(self.registry, plan)
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        payload = dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                       image=self.plan['candidate']['inner_digest'], manifest=phase)
        with patch('document_store.atomic_write', side_effect=OSError('disk')), self.assertRaises(OSError):
            self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent', payload)
        self.assertEqual(self.registry.records()[0]['journal'], [])

    def test_recovery_uses_saved_baseline_without_checkout_and_repeated_recovery_is_read_only(self):
        self.assertTrue(callable(getattr(self.tx, 'recover', None)), 'verified recovery missing')
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'recovered')
        self.assertEqual(execution.Registry(self.base).status()['state'], 'available')
        before = (self.base/'registry.json').read_bytes()
        again = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result, again)
        self.assertEqual((self.base/'registry.json').read_bytes(), before)
        self.assertEqual(backend.effects, [])
        self.assertFalse(self.tx.reserve(self.registry, self.plan)['new'])

    def test_recovery_requires_full_observations_and_preserves_external_changes(self):
        self.assertTrue(callable(getattr(self.tx, 'recover', None)), 'verified recovery missing')
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        backend.current['observations']['setting_proxy_sandbox']['value'] = 'external-proxy'
        self.assertEqual(self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)['state'], 'blocked')
        self.assertEqual(backend.effects, [])
        self.assertEqual(self.registry.status()['state'], 'reserved')
        backend.current = {'verified': True}
        self.assertEqual(self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)['state'], 'blocked')

    def test_stopped_vm_without_inner_receipt_never_invokes_launcher_or_closes(self):
        self.assertTrue(callable(getattr(self.tx, 'recover', None)), 'verified recovery missing')
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                 image=self.plan['candidate']['inner_digest'], manifest=phase))
        backend = RecoveryFixture(self.plan)
        result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(backend.effects, [])
        self.assertEqual(self.registry.status()['state'], 'consumed')

    def test_live_inner_workload_is_stopped_then_vm_and_verified_before_release(self):
        self.assertTrue(callable(getattr(self.tx, 'recover', None)), 'verified recovery missing')
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                 image=self.plan['candidate']['inner_digest'], manifest=phase))
        backend = RecoveryFixture(self.plan, active=True)
        with patch.object(time, 'time', return_value=time.time()+1000):
            result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'recovered')
        self.assertEqual(backend.effects, ['stop:A', 'stop_vm'])
        self.assertEqual(self.registry.records()[0]['request']['deadline_ms'], self.plan['deadline_ms'])

    def test_lost_stop_vm_response_is_observed_without_repeating_effect(self):
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                 image=self.plan['candidate']['inner_digest'], manifest=phase))
        backend = RecoveryFixture(self.plan, active=True)
        stop = backend.stop_vm
        def lost():
            stop()
            raise OSError('lost response')
        backend.stop_vm = lost
        first = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(first['state'], 'blocked')
        second = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(second['state'], 'recovered')
        self.assertEqual(backend.effects, ['stop:A', 'stop_vm'])

    def test_failed_intent_write_prevents_stop(self):
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                 image=self.plan['candidate']['inner_digest'], manifest=phase))
        backend = RecoveryFixture(self.plan, active=True)
        save = self.registry.save
        def fail(record):
            if record['recovery'][-1]['kind'] == 'stop_intent':
                raise OSError('disk')
            return save(record)
        with patch.object(self.registry, 'save', side_effect=fail):
            result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(backend.effects, [])
        self.assertEqual(self.registry.status()['state'], 'consumed')

    def test_recovery_compares_current_configuration_after_daemon_restart(self):
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        backend.current['daemon_identity'] = dict(pid=11, created_at='/Date(1791160590000)/')
        with self.assertRaisesRegex(ValueError, 'configuration_changed'):
            self.tx.configuration_matches(self.plan, backend.current)
        self.assertEqual(self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)['state'], 'recovered')
        self.assertEqual(self.registry.records()[0]['plan']['baseline']['daemon_identity']['pid'], 10)

    def test_recovery_refuses_container_changed_since_prepared_receipt(self):
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        identity = dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase))
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(identity, image=self.plan['candidate']['inner_digest'], manifest=phase))
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepared',
            dict(identity, observation=dict(identity, schema_version=1, container_id='c'*64,
                                           image=self.plan['candidate']['inner_digest'])))
        backend = RecoveryFixture(self.plan, active=True)
        result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(backend.effects, [])

    def test_recovery_refuses_container_changed_during_stop(self):
        self.tx.reserve(self.registry, self.plan)
        phase = self.plan['phases'][0]
        self.tx.phase_event(self.registry, self.plan['manifest']['operation_id'], 'A', 'prepare_intent',
            dict(operation_id=phase['operation_id'], nonce=phase['nonce'], manifest_sha256=self.tx.sha(phase),
                 image=self.plan['candidate']['inner_digest'], manifest=phase))
        backend = RecoveryFixture(self.plan, active=True)
        workload = backend.workload
        def changed(phase, stop=False):
            result = workload(phase, stop)
            if stop:
                result['container_id'] = 'c'*64
            return result
        backend.workload = changed
        result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(backend.effects, ['stop:A'])

    def test_recovery_binds_backend_to_attempt_deadline(self):
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        with patch.object(time, 'monotonic', return_value=10), patch.object(backend, 'bind_deadline') as bind:
            self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend, timeout_seconds=1)
        bind.assert_called_once_with(11)

    def test_daemon_identity_must_stay_stable_during_recovery(self):
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        before = backend.observe()
        backend.current['daemon_identity']['pid'] += 1
        with patch.object(backend, 'observe', side_effect=[before, backend.observe()]):
            result = self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)
        self.assertEqual(result['state'], 'blocked')

    def test_repeated_failed_observation_does_not_exhaust_recovery_history(self):
        self.tx.reserve(self.registry, self.plan)
        backend = RecoveryFixture(self.plan)
        original = backend.current['observations']['setting_proxy_sandbox']['value']
        backend.current['observations']['setting_proxy_sandbox']['value'] = 'external'
        for _ in range(130):
            self.assertEqual(self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)['state'], 'blocked')
        backend.current['observations']['setting_proxy_sandbox']['value'] = original
        self.assertEqual(self.tx.recover(self.registry, self.plan['manifest']['operation_id'], backend)['state'], 'recovered')


class RecoveryFixture:
    """Native boundary simulator; raw observations, never a cleanup approval flag."""
    def __init__(self, plan, active=False):
        self.plan = copy.deepcopy(plan)
        self.current = copy.deepcopy(plan['baseline'])
        self.effects = []
        self.active = active
        self.workload_running = active
        self._state()

    def _state(self):
        status = 'running' if self.active else 'stopped'
        self.current['observations']['candidate_inspect']['state'] = status
        self.current['observations']['sandbox_inventory']['sandboxes'][0]['status'] = status

    def observe(self):
        return copy.deepcopy(self.current)

    def bind_deadline(self, until):
        self.until = until

    def workload(self, phase, stop=False):
        assert self.active, 'must not exec stopped VM'
        manifest = self.plan['phases'][('A', 'B', 'A2').index(phase)]
        if stop:
            self.effects.append('stop:'+phase)
            self.workload_running = False
        import mission_transaction as tx
        return dict(schema_version=1, operation_id=manifest['operation_id'], nonce=manifest['nonce'],
                    container_id='a'*64, image=self.plan['candidate']['inner_digest'],
                    manifest_sha256=tx.sha(manifest), inspection_sha256='b'*64,
                    state=dict(Status='running' if self.workload_running else 'exited',
                               Running=self.workload_running, Pid=42 if self.workload_running else 0),
                    workload_reaped=not self.workload_running)

    def stop_vm(self):
        assert not self.workload_running
        self.effects.append('stop_vm')
        self.active = False
        self._state()


class MissionBindingTests(RuntimeCase):
    def make_plan(self):
        import mission_transaction as tx
        args = inputs()
        args['manifest'] = dict(self.make_manifest(), fixture_id='isolated-egress-v1')
        args['project_id'] = mission_backlog.project_id(self.root)
        args['project_sha256'] = tx.sha(str(self.root.resolve()))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.registry = execution.Registry(Path(temporary.name)/'execution')
        self.enterContext(registry_storage(self.registry.base))
        return tx, tx.build_plan(**args)

    def test_mission_and_global_plan_bind_before_claim_and_replay_never_grants_dispatch(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'admit', None)), 'mission plan binding missing')
        first = tx.admit(self.root, self.registry, plan)
        self.assertTrue(first['new'])
        self.assertEqual(first['run']['id'], plan['run_id'])
        self.assertEqual(first['run']['execution_plan_sha256'], tx.sha(plan))
        self.assertEqual(self.registry.records()[0]['plan']['run_id'], first['run']['id'])
        repeated = tx.admit(self.root, self.registry, plan)
        self.assertFalse(repeated['new'])
        self.assertEqual(first['run'], repeated['run'])
        self.assertEqual(len(mission_runs.list_runs(self.root, plan['manifest']['mission_id'])), 1)
        owner = dict(kind='linux-group', name=str(uuid.uuid4()), pid=123)
        tx.claim(self.root, self.registry, plan['manifest']['operation_id'], owner)
        with self.assertRaisesRegex(ValueError, 'effect_consumed'):
            tx.claim(self.root, self.registry, plan['manifest']['operation_id'], owner)

    def test_failed_second_store_write_cannot_be_resumed_as_new_admission(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'admit', None)), 'mission plan binding missing')
        with patch.object(tx, 'reserve', side_effect=OSError('disk')), self.assertRaises(OSError):
            tx.admit(self.root, self.registry, plan)
        again = tx.admit(self.root, self.registry, plan)
        self.assertFalse(again['new'])
        self.assertFalse(self.registry.base.exists())

    def test_old_controller_pending_receipt_stays_terminal_and_does_not_reserve_globally(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'admit', None)), 'mission plan binding missing')
        old = mission_runs.check_client(self.root, plan['manifest'], Path(sys.executable))
        again = tx.admit(self.root, self.registry, plan)
        self.assertFalse(again['new'])
        self.assertEqual(again['run']['id'], old['id'])
        self.assertEqual(again['run']['reason'], 'controller_pending')
        self.assertFalse(self.registry.base.exists())

    def test_legacy_reconciliation_cannot_close_integrated_run(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'admit', None)), 'mission plan binding missing')
        first = tx.admit(self.root, self.registry, plan)
        evidence = dict(authorization_ref='fixture', termination={}, external_effect={})
        with self.assertRaisesRegex(ValueError, 'integrated_recovery_required'):
            mission_runs.reconcile_check(self.root, first['run']['id'], evidence, first['run']['revision'], str(uuid.uuid4()))

    def test_verified_global_recovery_closes_mission_receipt_once_without_refunding_limits(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'reconcile', None)), 'mission recovery binding missing')
        first = tx.admit(self.root, self.registry, plan)
        backend = RecoveryFixture(plan)
        result = tx.reconcile(self.root, self.registry, plan['manifest']['operation_id'], backend)
        self.assertEqual(result['run']['state'], 'interrupted')
        self.assertEqual(result['run']['reason'], 'execution_recovered')
        self.assertEqual(result['run']['reserved_seconds'], first['run']['reserved_seconds'])
        self.assertEqual(result['run']['attempts'], 1)
        again = tx.reconcile(self.root, self.registry, plan['manifest']['operation_id'], backend)
        self.assertEqual(result, again)
        with mission_store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM agent_run_events').fetchone()[0], 2)

    def test_real_controller_and_durable_journal_run_three_phases_once_under_supervision(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'run_reserved', None)), 'integrated controller missing')
        tx.admit(self.root, self.registry, plan)
        import mission_process
        command = dict(argv=[sys.executable, '-I', '-B', str(Path(__file__).parent/'fixtures/transaction_controller.py')],
            cwd=str(self.root), stdin=json.dumps(dict(root=str(self.root), registry=str(self.registry.base),
                    operation_id=plan['manifest']['operation_id'])).encode(), timeout_seconds=15,
            output_limit_bytes=16384, client='metadata', connection='native')
        result = mission_process.supervise(command, on_started=lambda owner:
            tx.claim(self.root, self.registry, plan['manifest']['operation_id'], owner), stop_requested=lambda:False)
        self.assertEqual((result['reason'], result['exit_code']), ('completed', 0), result)
        self.assertTrue(result['tree_reaped'])
        decoded = json.loads(result['stdout'])
        self.assertEqual([p['state'] for p in decoded['phases']], ['observed', 'blocked_unattributed', 'observed'])
        self.assertFalse(decoded['proof_accepted'])
        self.assertEqual(len(self.registry.records()[0]['journal']), 30)
        for phase in ('A', 'B', 'A2'):
            self.assertEqual((self.root/'.runtime'/('transaction-'+phase)/'dispatches').read_bytes(), b'1\n')
        again = mission_process.supervise(command, on_started=lambda owner:None, stop_requested=lambda:False)
        self.assertEqual(again['exit_code'], 0, again)
        self.assertEqual(json.loads(again['stdout'])['reason'], 'reconciliation_required')
        self.assertEqual(len(self.registry.records()[0]['journal']), 30)

    def test_identity_drift_before_dispatch_prevents_fixture_request(self):
        tx, plan = self.make_plan()
        self.assertTrue(callable(getattr(tx, 'run_reserved', None)), 'integrated controller missing')
        tx.admit(self.root, self.registry, plan)
        import mission_process
        command = dict(argv=[sys.executable, '-I', '-B', str(Path(__file__).parent/'fixtures/transaction_controller.py')],
            cwd=str(self.root), stdin=json.dumps(dict(root=str(self.root), registry=str(self.registry.base),
                operation_id=plan['manifest']['operation_id'], mode='drift')).encode(), timeout_seconds=10,
            output_limit_bytes=16384, client='metadata', connection='native')
        result = mission_process.supervise(command, on_started=lambda owner:
            tx.claim(self.root, self.registry, plan['manifest']['operation_id'], owner), stop_requested=lambda:False)
        self.assertEqual(result['exit_code'], 0, result)
        self.assertFalse((self.root/'.runtime/transaction-A/dispatches').exists())
        self.assertEqual(json.loads(result['stdout'])['phases'][0]['reason'], 'persistence_failed')


if __name__ == '__main__':
    unittest.main()
