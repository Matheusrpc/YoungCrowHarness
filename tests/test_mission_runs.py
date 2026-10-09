import importlib
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

from runtime_fixtures import RuntimeCase
from test_mission_clients import catalog
import mission_clients
import mission_store
import missions


class RunTests(RuntimeCase):
    def test_status_identifies_unresolved_runs_without_observing_or_changing_them(self):
        manifest = self.make_manifest()
        run = self.runs.reserve_check(self.root, manifest, self.observe())
        for event, action in ((None, 'inspect_client_run'),
                              (dict(kind='started', owner=dict(kind='linux-group', name='fixture', pid=123)), 'inspect_client_run'),
                              (dict(kind='uncertain'), 'review_reconciliation')):
            if event:
                run = self.runs.transition_run(self.root, run['id'], event, run['revision'], str(uuid.uuid4()))
            before = self.snapshot()
            with patch.object(self.runs.processes, 'owner_gone', side_effect=AssertionError('status probed owner')), \
                 patch.object(mission_clients, 'inspect_client', side_effect=AssertionError('status probed client')):
                status = missions.mission_status(self.root, manifest['mission_id'])
            self.assertEqual(status['next_action'], action)
            self.assertFalse(status['check_available'])
            self.assertTrue('queue_preview' in status, 'missing queue_preview')
            self.assertIsNone(status['queue_preview']['first_candidate_id'])
            self.assertEqual(status['blocking_runs'], [dict(run_id=run['id'], mission_id=run['mission_id'],
                operation_id=run['operation_id'], revision=run['revision'], state=run['state'], next_action=action)])
            self.assertEqual(status['client_runs'], [run])
            self.assertFalse(status['runnable'])
            self.assertEqual(self.snapshot(), before)
        self.runs.transition_run(self.root, run['id'], dict(kind='finished', state='interrupted', reason='cancelled'),
                                 run['revision'], str(uuid.uuid4()))
        before = self.snapshot()
        status = missions.mission_status(self.root, manifest['mission_id'])
        self.assertEqual(status['blocking_runs'], [])
        self.assertTrue(status['check_available'])
        self.assertEqual(status['queue_preview']['first_candidate_id'], status['snapshot']['priority'][0])
        self.assertEqual(status['next_action'], 'runtime_not_available')
        self.assertEqual(self.snapshot(), before)

    def test_status_reports_another_missions_blocking_run_through_cli(self):
        manifest = self.make_manifest()
        saved = mission_store.get_record(self.root, manifest['mission_id'])['snapshot']
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        second = missions.prepare_mission(self.root, dict(request, title='Second'), str(uuid.uuid4()),
                                          dict(id='fixture', role='pm'))
        run = self.runs.reserve_check(self.root, manifest, self.observe())
        before = self.snapshot()
        result = subprocess.run([sys.executable, '-B', str(Path(missions.__file__).resolve()),
                                 '--root', str(self.root), '--json', 'status', second['code']],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        status = json.loads(result.stdout)
        self.assertEqual(status['next_action'], 'inspect_client_run')
        self.assertFalse(status['check_available'])
        self.assertTrue('queue_preview' in status, 'missing queue_preview')
        self.assertIsNone(status['queue_preview']['first_candidate_id'])
        self.assertEqual(status['client_runs'], [])
        self.assertEqual(status['blocking_runs'][0]['mission_id'], manifest['mission_id'])
        self.assertEqual(status['blocking_runs'][0]['run_id'], run['id'])
        self.assertEqual(self.runs.list_runs(self.root, second['code']), [])
        self.assertEqual(self.snapshot(), before)

    def test_mission_projection_recovery_preserves_consumed_run_reservation(self):
        import mission_vault
        manifest = self.make_manifest()
        observation = self.observe()
        run = self.runs.reserve_check(self.root, manifest, observation)
        def rows():
            with mission_store.reader(self.root) as conn:
                return tuple(conn.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
                             for table in ('agent_runs', 'agent_run_events', 'agent_run_projections'))
        before = rows()
        saved = mission_store.get_record(self.root, manifest['mission_id'])['snapshot']
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        request['title'] = 'Second'
        real_write = mission_vault.atomic_write
        def interrupt(root, path, content):
            real_write(root, path, content)
            if path == self.mission['paths'][0]:
                raise OSError('after note write')
        actor = dict(id='fixture', role='pm')
        with patch.object(mission_vault, 'atomic_write', side_effect=interrupt):
            second = missions.revise_mission(self.root, manifest['mission_id'], request, 1, str(uuid.uuid4()), actor)
        self.assertEqual(second['projection_state'], 'pending')
        third = missions.revise_mission(self.root, manifest['mission_id'], dict(request, title='Third'),
                                        2, str(uuid.uuid4()), actor)
        self.assertEqual(third['projection_state'], 'current')
        self.assertEqual(missions.repair(self.root, manifest['mission_id'])['projection_state'], 'current')
        repeated = self.runs.reserve_check(self.root, manifest, observation)
        self.assertEqual(repeated, run)
        self.assertEqual(repeated['state'], 'reserved')
        self.assertEqual(repeated['reserved_seconds'], manifest['agent_seconds'])
        self.assertEqual(rows(), before)

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('mission_runs'), 'runs not implemented')
        self.runs = importlib.import_module('mission_runs')
        self.native = patch.object(mission_clients, 'discover', return_value=dict(version='0.146.0', models=catalog('codex'), controls=True, auth_kind='authenticated', profile_verified=True))
        self.native.start()
        self.addCleanup(self.native.stop)

    def observe(self):
        return mission_clients.inspect_client(self.root, 'codex', Path(sys.executable).resolve())

    def check(self, manifest, mode='success'):
        build = mission_clients.build_check
        with patch.object(mission_clients, 'build_check', side_effect=lambda *args: self.fixture_plan(build(*args), mode)):
            return self.runs.check_client(self.root, manifest, Path(sys.executable).resolve())

    def reconcile(self, run):
        path = 'vault/local/evidence-' + run['id'] + '.txt'
        proof = self.root / path
        proof.write_text('Fixture only: owned process terminated; synthetic external effect reviewed.')
        ref = dict(path=path, sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
        evidence = dict(authorization_ref='Authorized fixture review', termination=ref, external_effect=ref)
        return self.runs.reconcile_check(self.root, run['id'], evidence, run['revision'], str(uuid.uuid4()))

    def test_replay_never_starts_a_second_process(self):
        manifest = self.make_manifest()
        first = self.check(manifest)
        again = self.check(manifest)
        self.assertEqual(first['id'], again['id'])
        self.assertEqual(again['state'], 'succeeded', again)
        marker = self.root / 'vault/local/operations/checks' / manifest['operation_id'] / 'dispatches.txt'
        self.assertEqual(marker.read_text(), '1\n')
        self.assertIsNone(again['cost_usd'])
        self.assertEqual(again['config_digest'], missions.config_digest(missions.mission_status(self.root, 'M001')['snapshot']['config']))
        self.assertFalse(missions.mission_status(self.root, 'M001')['runnable'])
        import vault
        self.assertEqual(vault.check(self.root)['issues'], [])

    def test_reserved_replay_becomes_uncertain_and_blocks_new_uuid(self):
        manifest = self.make_manifest()
        reserved = self.runs.reserve_check(self.root, manifest, self.observe())
        replay = self.check(manifest)
        self.assertEqual(replay['id'], reserved['id'])
        self.assertEqual(replay['state'], 'uncertain')
        with self.assertRaisesRegex(ValueError, 'unresolved_run'):
            self.check(self.make_manifest())

    def test_schema_one_migration_rolls_back_atomically_and_status_is_readonly(self):
        manifest = self.make_manifest()
        before = self.snapshot()
        self.assertEqual(self.runs.list_runs(self.root, manifest['mission_id']), [])
        self.assertEqual(before, self.snapshot())
        with self.assertRaisesRegex(RuntimeError, 'abort'):
            with mission_store.transaction(self.root) as conn:
                self.runs.migrate(conn)
                raise RuntimeError('abort')
        with mission_store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT schema_version FROM metadata').fetchone()[0], 1)
            self.assertFalse(conn.execute("SELECT name FROM sqlite_master WHERE name='agent_runs'").fetchall())
        old = mission_store.list_records(self.root, None)
        self.check(manifest)
        self.assertEqual(mission_store.list_records(self.root, None), old)

    def test_same_operation_different_payload_and_stale_revision_refuse(self):
        manifest = self.make_manifest()
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.check(dict(manifest, mission_revision=2))
        self.check(manifest)
        with self.assertRaisesRegex(ValueError, 'operation_conflict'):
            self.check(dict(manifest, authorization_ref='changed'))

    def test_invalid_manifest_does_not_reserve(self):
        manifest = self.make_manifest()
        for patching in ({'max_runs': 2}, {'agent_seconds': 1000}, {'prompt': 'arbitrary'}, {'fixture_id': 'shell'}):
            with self.assertRaises(ValueError):
                self.check(dict(manifest, **patching))
        self.assertEqual(self.runs.list_runs(self.root, manifest['mission_id']), [])

    def test_reconcile_requires_evidence_and_preserves_consumption(self):
        manifest = self.make_manifest()
        run = self.runs.reserve_check(self.root, manifest, self.observe())
        run = self.check(manifest)
        with self.assertRaisesRegex(ValueError, 'insufficient_evidence'):
            self.runs.reconcile_check(self.root, run['id'], {}, run['revision'], str(uuid.uuid4()))
        self.assertEqual(self.runs.list_runs(self.root, manifest['mission_id'])[0]['reserved_seconds'], manifest['agent_seconds'])

    def test_live_run_replay_does_not_relabel_an_active_owner(self):
        manifest = self.make_manifest()
        run = self.runs.reserve_check(self.root, manifest, self.observe())
        event = dict(kind='started', owner=dict(kind='windows-job', name='Local\\YoungCrow-' + str(uuid.uuid4()), pid=123))
        operation = str(uuid.uuid4())
        first = self.runs.transition_run(self.root, run['id'], event, 1, operation)
        again = self.runs.transition_run(self.root, run['id'], event, 1, operation)
        self.assertEqual(first['revision'], again['revision'])
        with patch.object(self.runs.processes, 'owner_gone', return_value=False):
            self.assertEqual(self.check(manifest)['state'], 'running')

    def test_real_coordinator_crash_never_dispatches_twice(self):
        manifest = self.make_manifest()
        (self.root / 'vault/local/crash-manifest.json').write_text(json.dumps(manifest))
        helper = Path(__file__).parent / 'fixtures/mission_coordinator.py'
        result = subprocess.run([sys.executable, '-B', str(helper.resolve()), str(self.root)], timeout=90, capture_output=True)
        self.assertEqual(result.returncode, 9, result.stderr.decode(errors='replace'))
        saved = self.runs.list_runs(self.root, manifest['mission_id'])[0]
        deadline = time.monotonic() + 4
        while not self.runs.processes.owner_gone(saved['owner']) and time.monotonic() < deadline:
            time.sleep(.05)
        run = self.check(manifest)
        self.assertEqual(run['state'], 'uncertain')
        marker = self.root / 'vault/local/operations/checks' / manifest['operation_id'] / 'dispatches.txt'
        self.assertEqual(marker.read_text(), '1\n')
        self.assertEqual(run['attempts'], 1)
        proof = self.root / 'vault/local/operator-proof.md'
        proof.write_text('Fixture: owner termination and external nonce-only effect reviewed.')
        reference = dict(path='vault/local/operator-proof.md', sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
        evidence = dict(authorization_ref='Authorized fixture review', termination=reference, external_effect=reference)
        operation = str(uuid.uuid4())
        recovered = self.runs.reconcile_check(self.root, run['id'], evidence, run['revision'], operation)
        repeated = self.runs.reconcile_check(self.root, run['id'], evidence, run['revision'], operation)
        self.assertEqual(recovered['revision'], repeated['revision'])
        self.assertEqual(repeated['state'], 'interrupted')
        self.assertIsNone(repeated['cost_usd'])
        self.assertEqual(repeated['reserved_seconds'], manifest['agent_seconds'])

    def test_projection_failure_recovers_and_preserves_human_note(self):
        manifest = self.make_manifest()
        import mission_vault
        with patch.object(mission_vault, 'project_run', side_effect=OSError('disk unavailable')):
            run = self.check(manifest)
        self.assertEqual(run['projection_state'], 'pending')
        run = self.check(manifest)
        self.assertEqual(run['projection_state'], 'current')
        path = self.root / run['paths'][0]
        path.write_text(path.read_text() + '\nHuman annotation\n')
        run = self.check(manifest)
        self.assertEqual(run['projection_state'], 'conflict')
        self.assertIn('Human annotation', path.read_text())

    def test_crash_before_effect_keeps_reservation_and_requires_reconciliation(self):
        manifest = self.make_manifest()
        (self.root / 'vault/local/crash-manifest.json').write_text(json.dumps(manifest))
        helper = Path(__file__).parent / 'fixtures/mission_coordinator.py'
        result = subprocess.run([sys.executable, '-B', str(helper.resolve()), str(self.root), 'before-effect'],
                                timeout=90, capture_output=True)
        self.assertEqual(result.returncode, 9, result.stderr.decode(errors='replace'))
        run = self.check(manifest)
        self.assertEqual(run['state'], 'uncertain')
        self.assertFalse((self.root / 'vault/local/operations/checks' / manifest['operation_id']).exists())
        proof = self.root / 'vault/local/before-effect-proof.md'
        proof.write_text('Fixture coordinator exited before process release; no external marker.')
        reference = dict(path='vault/local/before-effect-proof.md', sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
        evidence = dict(authorization_ref='Authorized fixture review', termination=reference, external_effect=reference)
        recovered = self.runs.reconcile_check(self.root, run['id'], evidence, run['revision'], str(uuid.uuid4()))
        self.assertEqual(recovered['state'], 'interrupted')
        self.assertEqual(recovered['reserved_seconds'], manifest['agent_seconds'])

    def test_failed_run_still_consumes_the_configured_run_limit(self):
        original = self.configured
        def config():
            value = original()
            value['limits']['max_agent_runs'] = 1
            return value
        with patch.object(self, 'configured', side_effect=config):
            run = self.check(self.make_manifest(), 'malformed')
            self.assertEqual(run['state'], 'uncertain')
            self.assertEqual(self.reconcile(run)['state'], 'interrupted')
        with self.assertRaisesRegex(ValueError, 'limit_exceeded'):
            self.check(self.make_manifest())

    def test_failed_protocol_never_reports_success_or_secret(self):
        for mode in ('malformed', 'secret'):
            run = self.check(self.make_manifest(), mode)
            self.assertEqual(run['state'], 'uncertain')
            self.assertNotIn('fixture-secret-never-print', json.dumps(run))
            self.assertIsNone(run['cost_usd'])
            self.reconcile(run)

    def test_effect_without_conclusive_result_blocks_new_dispatch(self):
        for mode in ('after-effect', 'effect-crash', 'effect-truncated'):
            with self.subTest(mode=mode):
                manifest = self.make_manifest()
                manifest['agent_seconds'] = 30
                run = self.check(manifest, mode)
                self.assertEqual(run['state'], 'uncertain')
                self.assertEqual(self.check(manifest)['id'], run['id'])
                marker = self.root / 'vault/local/operations/checks' / manifest['operation_id'] / 'dispatches.txt'
                self.assertEqual(marker.read_text(), '1\n')
                with self.assertRaisesRegex(ValueError, '^unresolved_run$'):
                    self.check(self.make_manifest())
                self.reconcile(run)
