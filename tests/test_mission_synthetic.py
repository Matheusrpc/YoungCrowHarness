"""Synthetic admission uses real mission storage and never dispatches a process."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import uuid

from runtime_fixtures import RuntimeCase
import mission_clients
import mission_execution
import mission_process
import mission_runs as runs
import mission_sandbox
import mission_sbx
import mission_store
import missions


class SyntheticAdmissionTests(RuntimeCase):
    def manifest(self):
        return dict(self.make_manifest(), fixture_id='isolated-egress-v1')

    def check(self, manifest):
        # Poison external boundaries: any regression must fail before a process/effect.
        with ExitStack() as stack:
            for owner, name in ((mission_clients, 'inspect_client'), (mission_clients, 'build_check'),
                                (mission_process, 'supervise'), (mission_sbx.Sbx, 'query'),
                                (mission_execution.Registry, 'reserve')):
                stack.enter_context(patch.object(owner, name, side_effect=AssertionError(name)))
            try:
                return runs.check_client(self.root, manifest, Path(sys.executable).resolve())
            except ValueError as error:
                self.fail(f'synthetic admission refused: {error}')

    def test_synthetic_receipt_is_terminal_and_contains_no_client_observation(self):
        manifest = self.manifest()
        run = self.check(manifest)
        self.assertEqual(run['purpose'], 'isolated_egress_check')
        self.assertEqual((run['state'], run['reason']), ('failed', 'controller_pending'))
        self.assertEqual(run['model_calls'], 0)
        self.assertFalse(run['effects_allowed'])
        self.assertEqual(run['manifest'], manifest)
        self.assertIsNone(run['owner'])
        self.assertIsNone(run['started_at'])
        self.assertIsNotNone(run['ended_at'])
        self.assertLessEqual(run['created_at'], run['ended_at'])
        self.assertLessEqual(run['ended_at'], run['updated_at'])
        for key in ('client', 'connection', 'requested_model', 'resolved_model', 'observed_model',
                    'requested_effort', 'observed_effort', 'version', 'policy_digest',
                    'executable_sha256', 'baseline_sha256'):
            self.assertNotIn(key, run)
        self.assertEqual(mission_clients.NATIVE_PROFILES, set())
        self.assertEqual(mission_sandbox.REVIEWED_PROFILES, ())
        self.assertEqual(run['projection_state'], 'current')
        self.assertIn('"model_calls": 0', (self.root / run['paths'][0]).read_text())
        with mission_store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT state FROM agent_runs').fetchone()[0], 'failed')

    def test_replay_preserves_receipt_and_consumes_limits_once(self):
        manifest = self.manifest()
        first, again = self.check(manifest), self.check(manifest)
        self.assertEqual(first, again)
        self.assertEqual(len(runs.list_runs(self.root, manifest['mission_id'])), 1)
        with mission_store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM agent_run_events').fetchone()[0], 1)

    def test_same_uuid_changed_fixture_or_authorization_conflicts(self):
        manifest = self.manifest()
        self.check(manifest)
        for changed in ({'fixture_id': 'echo-v1'}, {'authorization_ref': 'changed'}):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'operation_conflict'):
                runs.check_client(self.root, dict(manifest, **changed), Path(sys.executable).resolve())

    def test_strict_synthetic_manifest_rejects_budget_free_commands_and_wrong_limits(self):
        manifest = self.manifest()
        for changed in ({'api_budget_usd': '1'}, {'prompt': 'arbitrary'}, {'url': 'https://example.invalid'},
                        {'argv': ['sh']}, {'max_runs': 3}, {'authorization_ref': ' '},
                        {'fixture_id': ['isolated-egress-v1']}, {'role': 'unknown'},
                        {'agent_seconds': 100000}, {'mission_revision': 2}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                runs.check_client(self.root, dict(manifest, **changed), Path(sys.executable).resolve())
        self.assertEqual(runs.list_runs(self.root, manifest['mission_id']), [])

    def test_stale_inputs_refuse_admission(self):
        manifest = self.manifest()
        paths = list((self.root/'vault/local').glob('**/pbis/*/index.md'))
        self.assertTrue(paths)
        paths[0].write_text(paths[0].read_text() + '\nOperator edit\n')
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            runs.check_client(self.root, manifest, Path(sys.executable).resolve())
        self.assertEqual(runs.list_runs(self.root, manifest['mission_id']), [])

    def test_blocked_admission_obeys_cumulative_run_and_time_limits(self):
        manifest = self.manifest()
        _, config = runs.mission_agent(self.root, manifest)
        limit = min(config['limits']['max_agent_runs'],
                    config['limits']['mission_active_seconds'] // manifest['agent_seconds'])
        for _ in range(limit):
            self.check(dict(manifest, operation_id=str(uuid.uuid4())))
        with self.assertRaisesRegex(ValueError, 'limit_exceeded'):
            runs.check_client(self.root, dict(manifest, operation_id=str(uuid.uuid4())), Path(sys.executable).resolve())
        self.assertEqual(len(runs.list_runs(self.root, manifest['mission_id'])), limit)

    def test_existing_unresolved_run_blocks_new_synthetic_admission(self):
        manifest = self.manifest()
        first = self.check(manifest)
        # Simulate an interrupted durable reservation; do not invent a passing client profile.
        with mission_store.transaction(self.root) as conn:
            stored = runs.find_run(conn, first['id'])
            stored.update(state='uncertain', ended_at=None)
            conn.execute('UPDATE agent_runs SET state=?,snapshot=? WHERE id=?',
                         ('uncertain', json.dumps(stored), first['id']))
        with self.assertRaisesRegex(ValueError, 'unresolved_run'):
            runs.check_client(self.root, dict(manifest, operation_id=str(uuid.uuid4())), Path(sys.executable).resolve())

    def test_two_coordinators_record_one_consumed_operation(self):
        manifest = self.manifest()
        barrier = threading.Barrier(2)
        agent = runs.mission_agent
        def together(*args):
            value = agent(*args)
            barrier.wait(timeout=10)
            return value
        with patch.object(runs, 'mission_agent', side_effect=together), ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(runs.check_client, self.root, manifest, Path(sys.executable).resolve()) for _ in range(2)]
            try:
                results = [future.result(timeout=15) for future in futures]
            except ValueError as error:
                self.fail(f'synthetic admission refused: {error}')
        self.assertEqual(results[0]['id'], results[1]['id'])
        self.assertEqual(len(runs.list_runs(self.root, manifest['mission_id'])), 1)
        with mission_store.reader(self.root) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM agent_run_events').fetchone()[0], 1)

    def test_direct_model_reservation_refuses_synthetic_manifest(self):
        manifest = self.manifest()
        with patch.object(mission_clients, 'build_check', side_effect=AssertionError('model plan used')):
            with self.assertRaisesRegex(ValueError, 'invalid_manifest'):
                runs.reserve_check(self.root, manifest, {})

    def test_cli_preserves_explicit_block_in_json_and_runs(self):
        manifest = self.manifest()
        path = self.root/'vault/local/synthetic.json'
        path.write_text(json.dumps(manifest))
        output = io.StringIO()
        with redirect_stdout(output):
            code = missions.main(['--root', str(self.root), 'client', 'check', '--manifest',
                                  'vault/local/synthetic.json', '--executable', str(Path(sys.executable).resolve()), '--json'])
        self.assertEqual(code, 1, output.getvalue())
        result = json.loads(output.getvalue())
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['model_calls'], 0)
        self.assertEqual(runs.list_runs(self.root, manifest['mission_id'])[0]['id'], result['id'])
