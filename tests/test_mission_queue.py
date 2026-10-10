"""Real SQLite/CLI coordination; no provider, native worker or credentials."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch

from runtime_fixtures import RuntimeCase
import mission_runs
import mission_store as store
import missions


class QueueTests(RuntimeCase):
    def setUp(self):
        super().setUp()
        self.make_manifest()
        self.assertIsNotNone(importlib.util.find_spec('mission_queue'), 'missing persistent coordinator')
        self.queue = importlib.import_module('mission_queue')

    def apply(self, action, target=None, revision=1, operation=None):
        return self.queue.apply(self.root, action, target or self.mission['code'], revision,
                                operation or str(uuid.uuid4()), 'operator')

    def cli(self, *args):
        result = subprocess.run([sys.executable, '-B', str(Path(missions.__file__)),
                                 '--root', str(self.root), '--json', *args],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_cli_cycle_survives_new_processes_without_claiming_delivery(self):
        started = self.cli('queue', 'start', self.mission['code'], '--expected-revision', '1',
                           '--operation-id', str(uuid.uuid4()), '--actor-id', 'operator')
        session = started['session']
        self.assertEqual(session['state'], 'dev_pending')
        for revision, expected in ((1, 'qa_pending'), (2, 'fixture_completed')):
            advanced = self.cli('queue', 'step', session['id'], '--expected-revision', str(revision),
                                '--operation-id', str(uuid.uuid4()), '--actor-id', 'operator')
            self.assertEqual(advanced['session']['state'], expected)
        before = self.snapshot()
        status = self.cli('status', self.mission['code'])
        session = status['queue_sessions'][0]
        self.assertEqual(session['scope'], 'deterministic_rehearsal')
        self.assertEqual([r['role'] for r in session['results']], ['developer', 'qa'])
        self.assertEqual(len(session['events']), 3)
        self.assertEqual(session['next_action'], 'rehearsal_complete')
        self.assertIsNone(session['next_role'])
        self.assertEqual(status['snapshot']['development'], 'not_started')
        self.assertEqual(status['snapshot']['qa'], 'not_started')
        self.assertEqual(status['snapshot']['production'], 'not_verified')
        self.assertFalse(status['runtime_available'])
        self.assertFalse(status['runnable'])
        self.assertEqual(status['client_runs'], [])
        self.assertEqual(status['queue_preview']['scope'], 'initial_backlog')
        self.assertEqual(self.snapshot(), before)

    def test_replay_returns_original_receipt_and_conflicting_or_stale_requests_refuse(self):
        op = str(uuid.uuid4())
        first = self.apply('start', operation=op)
        session = first['session']['id']
        advance_op = str(uuid.uuid4())
        advanced = self.apply('step', session, operation=advance_op)
        self.assertEqual(self.apply('start', operation=op), first)
        self.assertEqual(self.apply('step', session, operation=advance_op), advanced)
        with self.assertRaisesRegex(ValueError, 'operation_conflict'):
            self.apply('cancel', session, operation=advance_op)
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.apply('step', session)
        with self.assertRaisesRegex(ValueError, 'queue_already_started'):
            self.apply('start')
        self.assertEqual(len(self.queue.sessions(self.root, self.mission['record_id'])[0]['events']), 2)

    def test_crash_before_commit_rolls_back_and_lost_ack_recovers_same_result(self):
        started = self.apply('start')['session']
        operation = str(uuid.uuid4())
        script_dir = str(Path(missions.__file__).parent)
        call = f"q.apply(Path({str(self.root)!r}), 'step', {started['id']!r}, 1, {operation!r}, 'operator')"
        prefix = f"import sys,os;sys.path.insert(0,{script_dir!r});from pathlib import Path;import mission_queue as q;"
        after_update = '''
from contextlib import contextmanager
original = q.store.transaction
@contextmanager
def interrupted(root):
    with original(root) as conn:
        def trace(sql):
            if sql.startswith('INSERT INTO queue_events'):
                os._exit(23)
        conn.set_trace_callback(trace)
        yield conn
q.store.transaction = interrupted
'''
        for interruption in ('q.fixture_result=lambda *args: os._exit(23);', after_update):
            crash = subprocess.run([sys.executable, '-B', '-c', prefix + interruption + call], timeout=30)
            self.assertEqual(crash.returncode, 23)
            # A writer may recover a pending journal; status never performs repair.
            with store.transaction(self.root):
                pass
            current = self.queue.sessions(self.root, self.mission['record_id'])[0]
            self.assertEqual((current['revision'], len(current['results']), len(current['events'])), (1, 0, 1))
        lost_ack = subprocess.run([sys.executable, '-B', '-c', prefix + call + ';os._exit(24)'], timeout=30)
        self.assertEqual(lost_ack.returncode, 24)
        repeated = self.apply('step', started['id'], operation=operation)
        self.assertEqual(repeated['session']['revision'], 2)
        current = self.queue.sessions(self.root, self.mission['record_id'])[0]
        self.assertEqual(len(current['events']), 2)
        self.assertEqual(len(current['results']), 1)

    def test_concurrent_processes_cannot_advance_same_revision_twice(self):
        session = self.apply('start')['session']
        processes = []
        try:
            for _ in range(2):
                processes.append(subprocess.Popen([sys.executable, '-B', str(Path(missions.__file__)),
                    '--root', str(self.root), '--json', 'queue', 'step', session['id'],
                    '--expected-revision', '1', '--operation-id', str(uuid.uuid4()), '--actor-id', 'operator'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            outputs = [p.communicate(timeout=30) for p in processes]
            self.assertEqual(sorted(p.returncode for p in processes), [0, 1], outputs)
            errors = [json.loads(out)['error'] for p, (out, _) in zip(processes, outputs) if p.returncode]
            self.assertEqual(errors, ['revision_conflict'])
            current = self.queue.sessions(self.root, self.mission['record_id'])[0]
            self.assertEqual((current['revision'], len(current['results'])), (2, 1))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.communicate()

    def test_revised_mission_blocks_step_but_allows_cancel_and_new_revision(self):
        session = self.apply('start')['session']
        saved = store.get_record(self.root, self.mission['record_id'])['snapshot']
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        missions.revise_mission(self.root, self.mission['code'], dict(request, title='Revised'),
                                1, str(uuid.uuid4()), dict(id='operator', role='pm'))
        status = missions.mission_status(self.root, self.mission['code'])
        self.assertEqual(status['queue_sessions'][0]['next_action'], 'cancel_stale_rehearsal')
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.apply('step', session['id'])
        self.assertEqual(self.apply('cancel', session['id'])['session']['state'], 'cancelled')
        next_session = self.apply('start', revision=2)['session']
        self.assertNotEqual(session['id'], next_session['id'])
        self.assertEqual(len(self.queue.sessions(self.root, self.mission['record_id'])), 2)

    def test_active_session_excludes_other_mission(self):
        self.apply('start')
        saved = store.get_record(self.root, self.mission['record_id'])['snapshot']
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        second = missions.prepare_mission(self.root, request, str(uuid.uuid4()), dict(id='operator', role='pm'))
        with self.assertRaisesRegex(ValueError, 'queue_busy'):
            self.apply('start', second['code'])

    def test_stale_source_blocks_advancement_and_status_explains_it(self):
        session = self.apply('start')['session']
        profile = self.root / 'vault/product/profile.md'
        profile.write_text(profile.read_text() + '\nChanged by human.\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply('step', session['id'])
        status = missions.mission_status(self.root, self.mission['code'])
        self.assertEqual(status['queue_sessions'][0]['next_action'], 'revise_inputs')
        self.assertEqual(self.snapshot(), before)

    def test_multiple_pbis_are_refused_without_migrating(self):
        saved = store.get_record(self.root, self.mission['record_id'])['snapshot']
        feature = saved['feature_ids'][0]
        path = self.write_item('pbi', feature)
        missions.import_item(self.root, path, 0, str(uuid.uuid4()), dict(id='operator', role='tech_lead'))
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        request['priority'] = [*saved['priority'], self.item_id(path)]
        missions.revise_mission(self.root, self.mission['code'], request, 1, str(uuid.uuid4()), dict(id='operator', role='pm'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'unsupported_queue_scope'):
            self.apply('start', revision=2)
        self.assertEqual(self.snapshot(), before)

    def test_schema_migration_preserves_unresolved_client_diagnostics(self):
        manifest = self.make_manifest()
        with store.transaction(self.root) as conn:
            mission_runs.migrate(conn)
        self.apply('start')
        # Use the existing durable diagnostic writer; queue migration must not hide it.
        _, config = mission_runs.mission_agent(self.root, manifest)
        run = mission_runs._record_check(self.root, manifest, config,
                                        dict(purpose='client_check', state='reserved', reason=None))
        self.assertEqual(mission_runs.list_runs(self.root, manifest['mission_id']), [run])
        status = missions.mission_status(self.root, self.mission['code'])
        self.assertEqual(status['blocking_runs'][0]['run_id'], run['id'])
        session = status['queue_sessions'][0]
        self.assertEqual(session['next_action'], 'inspect_client_run')
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply('step', session['id'])
        self.apply('cancel', session['id'])
        self.assertEqual(mission_runs.list_runs(self.root, manifest['mission_id']), [run])

    def test_migration_keeps_preexisting_pending_run_visible(self):
        manifest = self.make_manifest()
        _, config = mission_runs.mission_agent(self.root, manifest)
        run = mission_runs._record_check(self.root, manifest, config,
                                        dict(purpose='client_check', state='reserved', reason=None))
        with store.transaction(self.root) as conn:
            self.assertEqual(conn.execute('SELECT schema_version FROM metadata').fetchone()[0], 2)
            self.queue.migrate(conn)
        self.assertEqual(mission_runs.list_runs(self.root, manifest['mission_id']), [run])
        self.assertEqual(missions.mission_status(self.root, self.mission['code'])['blocking_runs'][0]['run_id'], run['id'])

    def test_qa_rejects_corrupted_fixture_result_without_advancing(self):
        session = self.apply('start')['session']
        session = self.apply('step', session['id'])['session']
        session['results'][0]['output_sha256'] = '0' * 64
        with store.transaction(self.root) as conn:
            conn.execute('UPDATE queue_sessions SET snapshot=? WHERE id=?', (json.dumps(session), session['id']))
        with self.assertRaisesRegex(ValueError, 'invalid_fixture_result'):
            self.apply('step', session['id'], revision=2)
        current = self.queue.sessions(self.root, self.mission['record_id'])[0]
        self.assertEqual((current['revision'], len(current['results']), len(current['events'])), (2, 1, 2))

    def test_old_status_does_not_migrate_and_old_runtime_helper_is_rejected(self):
        before = self.snapshot()
        self.assertEqual(missions.mission_status(self.root, self.mission['code'])['queue_sessions'], [])
        self.assertEqual(self.snapshot(), before)
        with patch.object(mission_runs, 'STORE_SCHEMA', None):
            with self.assertRaisesRegex(ValueError, 'incompatible_helper'):
                missions.mission_status(self.root, self.mission['code'])

    def test_completed_session_cannot_advance_or_restart_same_mission_revision(self):
        session = self.apply('start')['session']
        self.apply('step', session['id'])
        self.apply('step', session['id'], revision=2)
        with self.assertRaisesRegex(ValueError, 'invalid_transition'):
            self.apply('step', session['id'], revision=3)
        with self.assertRaisesRegex(ValueError, 'queue_already_started'):
            self.apply('start')
