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
        self.assert_crash_recovery(started)

    def test_crash_during_qa_to_next_pbi_does_not_partially_release_dependency(self):
        a, b, c, d = self.multiple_pbis()
        session = self.apply('start', revision=2)['session']
        # Finish D and develop A: A's QA will unlock B ahead of C.
        for revision in (1, 2, 3):
            session = self.apply('step', session['id'], revision=revision)['session']
        self.assertEqual((session['pbi_id'], session['next_role']), (a, 'qa'))
        self.assert_crash_recovery(session)
        current = self.queue.sessions(self.root, self.mission['record_id'])[0]
        self.assertEqual((current['pbi_id'], current['next_role']), (b, 'developer'))

    def assert_crash_recovery(self, started):
        operation = str(uuid.uuid4())
        script_dir = str(Path(missions.__file__).parent)
        revision = started['revision']
        call = f"q.apply(Path({str(self.root)!r}), 'step', {started['id']!r}, {revision}, {operation!r}, 'operator')"
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
            self.assertEqual((current['revision'], len(current['results']), len(current['events'])),
                             (revision, len(started['results']), revision))
            self.assertEqual({k: v for k, v in current.items() if k != 'events'}, started)
        lost_ack = subprocess.run([sys.executable, '-B', '-c', prefix + call + ';os._exit(24)'], timeout=30)
        self.assertEqual(lost_ack.returncode, 24)
        repeated = self.apply('step', started['id'], revision=revision, operation=operation)
        self.assertEqual(repeated['session']['revision'], revision + 1)
        current = self.queue.sessions(self.root, self.mission['record_id'])[0]
        self.assertEqual(len(current['events']), revision + 1)
        self.assertEqual(len(current['results']), len(started['results']) + 1)

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

    def multiple_pbis(self):
        saved = store.get_record(self.root, self.mission['record_id'])['snapshot']
        feature = saved['feature_ids'][0]
        a = saved['priority'][0]
        paths = [self.write_item('pbi', feature) for _ in range(3)]
        b, c, d = [self.item_id(path) for path in paths]
        self.contract(paths[0], dependencies=[a])
        self.contract(paths[1], dependencies=[b])
        for path in paths:
            missions.import_item(self.root, path, 0, str(uuid.uuid4()), dict(id='operator', role='tech_lead'))
        request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
        request['priority'] = [c, d, b, a]
        missions.revise_mission(self.root, self.mission['code'], request, 1, str(uuid.uuid4()), dict(id='operator', role='pm'))
        return a, b, c, d

    def test_multiple_pbis_follow_priority_and_fixture_dependencies_across_cli_processes(self):
        a, b, c, d = self.multiple_pbis()
        session = self.apply('start', revision=2)['session']
        self.assertEqual([p['id'] for p in session['items']], [c, d, b, a])
        operation = None
        for pbi in (d, a, b, c):
            for role in ('developer', 'qa'):
                self.assertEqual((session['pbi_id'], session['next_role']), (pbi, role))
                operation = str(uuid.uuid4())
                args = ('queue', 'step', session['id'], '--expected-revision', str(session['revision']),
                        '--operation-id', operation, '--actor-id', 'operator')
                receipt = self.cli(*args)
                session = receipt['session']
                status = self.cli('status', self.mission['code'])
                self.assertFalse(status['runnable'])
                self.assertEqual(status['snapshot']['qa'], 'not_started')
                if role == 'developer':
                    self.assertEqual(session['next_role'], 'qa')
        self.assertEqual(self.cli(*args), receipt)
        self.assertEqual((session['state'], session['revision']), ('fixture_completed', 9))
        self.assertIsNone(session['pbi_id'])
        self.assertEqual(len({r['candidate_id'] for r in session['results']}), 8)
        self.assertTrue(all(p['state'] == 'fixture_completed' for p in session['items']))
        before = self.snapshot()
        status = self.cli('status', self.mission['code'])
        self.assertEqual(status['queue_preview']['first_candidate_id'], d)
        self.assertEqual(status['snapshot']['development'], 'not_started')
        self.assertEqual(status['snapshot']['production'], 'not_verified')
        self.assertEqual(status['client_runs'], [])
        self.assertEqual(len(status['queue_sessions'][0]['events']), 9)
        self.assertEqual(self.snapshot(), before)

    def test_dependency_waits_are_visible_and_cancel_keeps_completed_and_pending_items(self):
        a, b, c, d = self.multiple_pbis()
        start_op = str(uuid.uuid4())
        first = self.apply('start', revision=2, operation=start_op)
        session = first['session']
        status = missions.mission_status(self.root, self.mission['code'])
        waiting = {p['id']: p['waiting_on'] for p in status['queue_sessions'][0]['items']}
        self.assertEqual(waiting, {c: [b], d: [], b: [a], a: []})
        for revision in (1, 2):
            session = self.apply('step', session['id'], revision=revision)['session']
        self.assertEqual((session['pbi_id'], session['next_role']), (a, 'developer'))
        self.assertEqual(self.apply('start', revision=2, operation=start_op), first)
        cancelled = self.apply('cancel', session['id'], revision=3)['session']
        self.assertEqual(cancelled['state'], 'cancelled')
        self.assertEqual(len(cancelled['results']), 2)
        self.assertEqual([p['state'] for p in cancelled['items']],
                         ['pending', 'fixture_completed', 'pending', 'dev_pending'])
        with self.assertRaisesRegex(ValueError, 'invalid_transition'):
            self.apply('step', session['id'], revision=4)

    def test_missing_and_cyclic_dependencies_refuse_without_migrating(self):
        saved = store.get_record(self.root, self.mission['record_id'])['snapshot']
        pbi = next(r for r in saved['items'] if r['kind'] == 'pbi')
        path = pbi['snapshot']['note_path']
        for revision, dependency in ((1, str(uuid.uuid4())), (2, pbi['id'])):
            self.contract(path, dependencies=[dependency])
            missions.import_item(self.root, path, revision, str(uuid.uuid4()), dict(id='operator', role='tech_lead'))
            request = {key: saved[key] for key in ('title', 'feature_ids', 'priority', 'overrides', 'scope_reference')}
            missions.revise_mission(self.root, self.mission['code'], request, revision, str(uuid.uuid4()), dict(id='operator', role='pm'))
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
                self.apply('start', revision=revision + 1)
            self.assertEqual(self.snapshot(), before)

    def test_qa_rejects_valid_result_belonging_to_another_pbi(self):
        self.multiple_pbis()
        session = self.apply('start', revision=2)['session']
        for revision in (1, 2, 3):
            session = self.apply('step', session['id'], revision=revision)['session']
        session['results'][-1] = session['results'][0]
        with store.transaction(self.root) as conn:
            conn.execute('UPDATE queue_sessions SET snapshot=? WHERE id=?', (json.dumps(session), session['id']))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'invalid_fixture_result'):
            self.apply('step', session['id'], revision=4)
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
        with patch.object(self.queue, 'QUEUE_VERSION', 1):
            with self.assertRaisesRegex(ValueError, 'incompatible_helper'):
                missions.mission_status(self.root, self.mission['code'])

    def test_schema_three_session_keeps_exact_replay_and_resumes_after_upgrade(self):
        operation = str(uuid.uuid4())
        legacy = self.apply('start', operation=operation)
        session = legacy['session']
        session['schema_version'] = 1
        session.pop('items', None)
        session.pop('dependency_basis', None)
        session['candidate_id'] = str(uuid.uuid5(uuid.UUID(session['id']), 'developer'))
        with store.transaction(self.root) as conn:
            conn.execute('UPDATE metadata SET schema_version=3')
            conn.execute('UPDATE queue_sessions SET snapshot=? WHERE id=?', (json.dumps(session), session['id']))
            conn.execute('UPDATE queue_events SET receipt=? WHERE operation_id=?', (json.dumps(legacy), operation))
        before = self.snapshot()
        status = missions.mission_status(self.root, self.mission['code'])
        self.assertEqual(status['queue_sessions'][0]['schema_version'], 1)
        self.assertEqual(self.apply('start', operation=operation), legacy)
        self.assertEqual(self.snapshot(), before)
        for revision in (1, 2):
            current = self.apply('step', session['id'], revision=revision)['session']
        self.assertEqual(current['state'], 'fixture_completed')
        self.assertEqual([r['fixture_id'] for r in current['results']], ['queue-v1', 'queue-v1'])
        self.assertEqual(self.apply('start', operation=operation), legacy)
        with store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT schema_version FROM metadata').fetchone()[0], 4)

    def test_completed_session_cannot_advance_or_restart_same_mission_revision(self):
        session = self.apply('start')['session']
        self.apply('step', session['id'])
        self.apply('step', session['id'], revision=2)
        with self.assertRaisesRegex(ValueError, 'invalid_transition'):
            self.apply('step', session['id'], revision=3)
        with self.assertRaisesRegex(ValueError, 'queue_already_started'):
            self.apply('start')
