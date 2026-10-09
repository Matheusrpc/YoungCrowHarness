import copy
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
import uuid
from contextlib import closing, redirect_stdout
from unittest.mock import patch

from mission_fixtures import MissionCase
from mission_config import load_config, effective_config, config_digest

ACTOR = dict(id='fixture-pm', role='pm')
TL = dict(id='fixture-tl', role='tech_lead')
DB = 'vault/local/operations/state.sqlite3'


class ProjectionCrash(BaseException):
    """Stop the entire repair loop, as losing the coordinator would."""


class MissionTests(MissionCase):
    def interrupt_note_write(self, *, path=None, hard=False):
        import mission_vault
        real_write = mission_vault.atomic_write
        written = []
        def write(root, relative, content):
            real_write(root, relative, content)
            parts = Path(relative).parts
            target = relative == path if path else parts[:3] == ('vault', 'local', 'missions') and len(parts) == 5
            if target and not written:
                written.append(relative)
                raise ProjectionCrash() if hard else OSError('interrupted after note write')
        return patch.object(mission_vault, 'atomic_write', side_effect=write), written

    def test_unconfirmed_projection_recovers_after_new_revision_and_replay(self):
        request, actor = self.prepared_fixture()
        interrupted, written = self.interrupt_note_write()
        with interrupted:
            first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(first['projection_state'], 'pending')
        self.assertEqual(len(written), 1)
        newer = self.m.revise_mission(self.root, first['record_id'], dict(request, title='Revision two'),
                                     1, str(uuid.uuid4()), actor)
        self.assertEqual(newer['projection_state'], 'current')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        replay = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(replay['event_id'], first['event_id'])
        self.assertEqual(replay['projection_state'], 'current')
        status = self.m.mission_status(self.root, first['record_id'])
        self.assertEqual((status['revision'], len(status['events']), status['projection_state']), (2, 2, 'current'))
        self.assertIn('Revision: 2.', (self.root/written[0]).read_text())
        self.assertIn('Revision two', (self.root/written[0]).read_text())

    def test_unconfirmed_newer_projection_recovers_with_regressing_clock(self):
        request, actor = self.prepared_fixture()
        first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        interrupted, _ = self.interrupt_note_write()
        with interrupted, patch('missions.utc_now', return_value='2026-10-03T12:00:00+00:00'):
            second = self.m.revise_mission(self.root, first['record_id'], dict(request, title='Second'),
                                          1, str(uuid.uuid4()), actor)
        self.assertEqual(second['projection_state'], 'pending')
        with patch('missions.utc_now', return_value='2026-10-03T11:00:00+00:00'):
            third = self.m.revise_mission(self.root, first['record_id'], dict(request, title='Third'),
                                         2, str(uuid.uuid4()), actor)
        self.assertEqual(third['projection_state'], 'current')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        self.assertIn('Third', (self.root/first['paths'][0]).read_text())
        self.assertEqual(len(self.db.events(self.root, first['record_id'])), 3)

    def test_legacy_conflict_after_interrupted_write_can_be_repaired(self):
        request, actor = self.prepared_fixture()
        interrupted, _ = self.interrupt_note_write()
        with interrupted:
            first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        # Reproduce the durable state left by the former false-conflict path.
        with patch('missions.project_receipt', return_value=dict(state='conflict', paths=[])):
            self.m.revise_mission(self.root, first['record_id'], dict(request, title='Second'),
                                  1, str(uuid.uuid4()), actor)
        with self.db.transaction(self.root) as conn:
            conn.execute("UPDATE events SET projection_state='conflict' WHERE record_id=?", (first['record_id'],))
        self.assertEqual(self.m.mission_status(self.root, first['record_id'])['projection_state'], 'conflict')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        status = self.m.mission_status(self.root, first['record_id'])
        self.assertEqual((status['revision'], len(status['events']), status['projection_state']), (2, 2, 'current'))

    def test_crash_during_repair_recovers_without_new_event(self):
        request, actor = self.prepared_fixture()
        first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        with patch('missions.project_receipt', side_effect=OSError('before note write')):
            self.m.revise_mission(self.root, first['record_id'], dict(request, title='Second'),
                                  1, str(uuid.uuid4()), actor)
        interrupted, written = self.interrupt_note_write(hard=True)
        with interrupted, self.assertRaises(ProjectionCrash):
            self.m.repair(self.root, first['record_id'])
        self.assertEqual(len(written), 1)
        # A later revision must also recover a write interrupted inside repair.
        newer = self.m.revise_mission(self.root, first['record_id'], dict(request, title='Third'),
                                     2, str(uuid.uuid4()), actor)
        self.assertEqual(newer['projection_state'], 'current')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        before = self.snapshot()
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(self.db.events(self.root, first['record_id'])), 3)

    def test_human_change_after_interrupted_projection_remains_conflict(self):
        request, actor = self.prepared_fixture()
        interrupted, written = self.interrupt_note_write()
        with interrupted:
            first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        path = self.root/written[0]
        human = path.read_bytes()+b'\nHuman addition after interruption.\n'
        path.write_bytes(human)
        newer = self.m.revise_mission(self.root, first['record_id'], dict(request, title='Second'),
                                     1, str(uuid.uuid4()), actor)
        self.assertEqual(newer['projection_state'], 'conflict')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'conflict')
        self.assertEqual(path.read_bytes(), human)

    def test_human_restore_of_confirmed_old_projection_is_not_adopted(self):
        request, actor = self.prepared_fixture()
        first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        path = self.root/first['paths'][0]
        historical = path.read_bytes()
        self.m.revise_mission(self.root, first['record_id'], dict(request, title='Second'),
                              1, str(uuid.uuid4()), actor)
        path.write_bytes(historical)
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'conflict')
        self.assertEqual(path.read_bytes(), historical)

    def test_unconfirmed_import_projection_recovers_without_changing_source(self):
        path = self.write_item('epic')
        note = f'vault/local/operations/items/{self.item_id(path)}/index.md'
        interrupted, written = self.interrupt_note_write(path=note)
        with interrupted:
            first = self.m.import_item(self.root, path, 0, self.op_id, ACTOR)
        self.assertEqual(first['projection_state'], 'pending')
        self.assertEqual(written, [note])
        self.contract(path, objective='Revised objective')
        source = (self.root/path).read_bytes()
        second = self.m.import_item(self.root, path, 1, str(uuid.uuid4()), ACTOR)
        self.assertEqual(second['projection_state'], 'current')
        self.assertEqual(self.m.repair(self.root, first['record_id'])['projection_state'], 'current')
        self.assertEqual((self.root/path).read_bytes(), source)
        self.assertEqual(len(self.db.events(self.root, first['record_id'])), 2)

    def test_client_runs_is_readonly_on_fresh_project(self):
        before = self.snapshot()
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), '--json', 'client', 'runs', '--mission', 'M001'])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['runs'], [])
        self.assertEqual(before, self.snapshot())

    def test_client_check_requires_manifest_and_sanitizes_errors(self):
        import mission_runs
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), 'client', 'check', '--executable', sys.executable])
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['error'], 'invalid_arguments')
        manifest = self.root / 'vault/local/probe.json'
        manifest.write_text('{}')
        output = io.StringIO()
        with patch.object(mission_runs, 'check_client', side_effect=ValueError('fixture-secret-never-print')):
            with redirect_stdout(output):
                code = self.m.main(['--root', str(self.root), 'client', 'check', '--executable', sys.executable,
                                    '--manifest', 'vault/local/probe.json'])
        self.assertNotEqual(code, 0)
        self.assertNotIn('fixture-secret-never-print', output.getvalue())
        self.assertNotIn('No provider was called', output.getvalue())

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('missions'), 'mission backend not implemented')
        self.m = importlib.import_module('missions')
        self.db = importlib.import_module('mission_store')
        self.op_id = str(uuid.uuid4())

    def prepared_fixture(self, features=1, pbis=2):
        paths = self.tree(features, pbis)
        for path in paths:
            self.m.import_item(self.root, path, 0, str(uuid.uuid4()), TL if '/pbis/' in path else ACTOR)
        self.m.apply_config(self.root, self.configured(), None)
        self.paths = paths
        return dict(title='Fixture mission', feature_ids=[self.item_id(p) for p in paths if '/features/' in p],
                    priority=[self.item_id(p) for p in paths if '/pbis/' in p], overrides={}, scope_reference='Approved fixture scope'), ACTOR

    def test_repeat_returns_same_mission_and_single_event(self):
        request, actor = self.prepared_fixture()
        first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        second = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(first['record_id'], second['record_id'])
        self.assertEqual(first['sequence'], second['sequence'])
        self.assertEqual(len(self.db.list_records(self.root, 'mission')), 1)
        self.assertEqual(self.m.mission_status(self.root, first['code'])['state'], 'prepared')
        import vault
        self.assertEqual(vault.check(self.root)['issues'], [])

    def test_configuration_change_does_not_rewrite_mission(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        first = self.db.get_record(self.root, receipt['record_id'])
        current = load_config(self.root)
        self.m.apply_config(self.root, effective_config(current, {'agents': {'pm': {'model': 'fixture-b'}}}), config_digest(current))
        self.assertEqual(self.db.get_record(self.root, receipt['record_id']), first)
        status = self.m.mission_status(self.root, first['id'])
        self.assertFalse(status['runnable'])
        self.assertFalse(status['stale_inputs'])
        self.assertEqual(self.m.prepare_mission(self.root, request, self.op_id, actor)['sequence'], receipt['sequence'])

    def test_revision_and_operation_conflicts_are_read_only(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'operation_conflict'):
            self.m.prepare_mission(self.root, dict(request, title='Changed'), self.op_id, actor)
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.m.revise_mission(self.root, receipt['code'], request, 0, str(uuid.uuid4()), actor)
        with self.assertRaisesRegex(ValueError, 'config_conflict'):
            self.m.apply_config(self.root, self.configured(), None)
        self.assertEqual(self.snapshot(), before)

    def test_list_is_empty_without_initializing_storage(self):
        (self.root / 'vault/project.json').unlink()
        before = self.snapshot()
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), '--json', 'list'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), dict(
            schema_version=1, missions=[], runtime_available=False, runnable=False))
        self.assertEqual(self.snapshot(), before)

    def test_list_returns_only_current_mission_summaries(self):
        request, actor = self.prepared_fixture()
        first = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.m.revise_mission(self.root, first['code'], dict(request, title='Revised mission'),
                              1, str(uuid.uuid4()), actor)
        second = self.m.prepare_mission(self.root, dict(request, scope_reference=''), str(uuid.uuid4()), actor)
        before = self.snapshot()
        with patch('missions.mission_status', side_effect=AssertionError('Inventory must not inspect each mission')):
            result = self.m.list_missions(self.root)
        self.assertEqual(result['missions'], [
            dict(id=first['record_id'], code=first['code'], title='Revised mission', revision=2, state='prepared'),
            dict(id=second['record_id'], code=second['code'], title=request['title'], revision=1, state='draft')])
        self.assertFalse(result['runtime_available'])
        self.assertFalse(result['runnable'])
        self.assertEqual(self.snapshot(), before)

    def test_list_finds_mission_after_projection_failure_without_repair(self):
        request, actor = self.prepared_fixture()
        with patch('missions.project_receipt', side_effect=OSError('interrupted projection')):
            receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(receipt['projection_state'], 'pending')
        self.assertNotIn(receipt['record_id'], (self.root / 'vault/local/missions/index.md').read_text())
        before = self.snapshot()
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), '--json', 'list'])
        self.assertEqual(code, 0)
        found = json.loads(output.getvalue())['missions'][0]
        self.assertEqual(found['id'], receipt['record_id'])
        self.assertEqual(self.m.mission_status(self.root, found['code'])['projection_state'], 'pending')
        self.assertEqual(self.snapshot(), before)

    def test_list_refuses_corrupt_or_foreign_storage_without_writes(self):
        request, actor = self.prepared_fixture()
        self.m.prepare_mission(self.root, request, self.op_id, actor)
        project_path = self.root / 'vault/project.json'
        project = json.loads(project_path.read_text())
        project['project_id'] = str(uuid.uuid4())
        project_path.write_text(json.dumps(project))
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt):
                if corrupt:
                    (self.root / DB).write_bytes(b'corrupt')
                before = self.snapshot()
                output = io.StringIO()
                with redirect_stdout(output):
                    code = self.m.main(['--root', str(self.root), '--json', 'list'])
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(output.getvalue())['error'], 'invalid_store')
                self.assertEqual(self.snapshot(), before)

    def test_queue_preview_uses_priority_and_explains_initial_dependencies_without_writes(self):
        request, actor = self.prepared_fixture(features=2, pbis=2)
        a, b, c, d = request['priority']
        for item_id, dependencies in ((b, [a]), (c, [b])):
            path = next(p for p in self.paths if self.item_id(p) == item_id)
            self.contract(path, dependencies=dependencies)
            self.m.import_item(self.root, path, 1, str(uuid.uuid4()), TL)
        request['priority'] = [c, d, b, a]
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        before = self.snapshot()
        output = io.StringIO()
        with patch('mission_clients.inspect_client', side_effect=AssertionError('preview inspected client')), \
             patch('mission_runs.check_client', side_effect=AssertionError('preview dispatched client')), \
             redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), '--json', 'status', receipt['code']])
        self.assertEqual(code, 0, output.getvalue())
        status = json.loads(output.getvalue())
        self.assertTrue('queue_preview' in status, 'missing queue_preview')
        preview = status['queue_preview']
        self.assertEqual(preview['scope'], 'initial_backlog')
        self.assertEqual([p['id'] for p in preview['items']], [c, d, b, a])
        self.assertEqual([p['dependencies'] for p in preview['items']], [[b], [], [a], []])
        self.assertEqual(preview['first_candidate_id'], d)
        for item in preview['items']:
            saved = self.db.get_record(self.root, item['id'])
            self.assertEqual((item['code'], item['title'], item['revision']),
                             (saved['code'], saved['snapshot']['title'], saved['revision']))
        self.assertEqual(status['next_action'], 'runtime_not_available')
        self.assertFalse(status['runnable'])
        self.assertFalse(status['runtime_available'])
        self.assertEqual(self.snapshot(), before)
        self.m.revise_mission(self.root, receipt['code'], dict(request, priority=[c, a, b, d]),
                              1, str(uuid.uuid4()), actor)
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['queue_preview']['first_candidate_id'], a)

    def test_queue_preview_withholds_candidate_for_stale_inputs_projections_and_gaps(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        projection = self.root / receipt['paths'][0]
        source = self.root / self.paths[-1]
        for target, replacement, action in (
                (source, source.read_bytes() + b'\nHuman source update\n', 'revise_inputs'),
                (projection, None, 'repair_projection'),
                (projection, b'Human projection change\n', 'review_projection_conflict')):
            with self.subTest(action=action):
                original = target.read_bytes()
                try:
                    if replacement is None:
                        target.unlink()
                    else:
                        target.write_bytes(replacement)
                    before = self.snapshot()
                    status = self.m.mission_status(self.root, receipt['code'])
                    self.assertTrue('queue_preview' in status, 'missing queue_preview')
                    self.assertIsNone(status['queue_preview']['first_candidate_id'])
                    self.assertEqual(status['next_action'], action)
                    self.assertEqual(self.snapshot(), before)
                finally:
                    target.write_bytes(original)
        self.m.revise_mission(self.root, receipt['code'], dict(request, scope_reference=''),
                              1, str(uuid.uuid4()), actor)
        status = self.m.mission_status(self.root, receipt['code'])
        self.assertTrue('queue_preview' in status, 'missing queue_preview')
        self.assertIsNone(status['queue_preview']['first_candidate_id'])
        self.assertEqual(status['next_action'], 'complete_gaps')

    def test_queue_preview_withholds_candidate_for_missing_or_cyclic_dependencies(self):
        request, actor = self.prepared_fixture(pbis=3)
        a, b, c = request['priority']
        paths = {self.item_id(p): p for p in self.paths if '/pbis/' in p}
        for revision, dependencies, gap in ((1, [str(uuid.uuid4())], 'invalid_dependency'),
                                             (2, [b], 'dependency_cycle')):
            with self.subTest(gap=gap):
                self.contract(paths[a], dependencies=dependencies)
                self.m.import_item(self.root, paths[a], revision, str(uuid.uuid4()), TL)
                if gap == 'dependency_cycle':
                    self.contract(paths[b], dependencies=[a])
                    self.m.import_item(self.root, paths[b], 1, str(uuid.uuid4()), TL)
                receipt = self.m.prepare_mission(self.root, request, str(uuid.uuid4()), actor)
                before = self.snapshot()
                status = self.m.mission_status(self.root, receipt['code'])
                self.assertTrue('queue_preview' in status, 'missing queue_preview')
                self.assertIsNone(status['queue_preview']['first_candidate_id'])
                self.assertTrue(any(g.startswith(gap + ':') for g in status['gaps']))
                self.assertEqual(status['next_action'], 'complete_gaps')
                self.assertFalse(status['runnable'])
                self.assertEqual(self.snapshot(), before)

    def test_status_does_not_initialize_or_repair(self):
        project = self.root / 'vault/project.json'
        saved_project = project.read_bytes()
        project.unlink()
        before = self.snapshot()
        self.assertEqual(self.m.mission_status(self.root, 'M001')['state'], 'not_initialized')
        self.assertEqual(self.snapshot(), before)
        project.write_bytes(saved_project)
        path = self.root / DB
        path.parent.mkdir(parents=True)
        path.write_bytes(b'corrupt')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'invalid_store'):
            self.m.mission_status(self.root, 'M001')
        self.assertEqual(self.snapshot(), before)

    def test_status_prioritizes_projection_repair_over_stale_inputs(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        path = self.root / receipt['paths'][0]
        original = path.read_bytes()
        with (self.root / self.paths[-1]).open('a') as source:
            source.write('\nUpdated human source.\n')
        for content, action in ((None, 'repair_projection'), (b'Human edits to preserve\n', 'review_projection_conflict')):
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            before = self.snapshot()
            status = self.m.mission_status(self.root, receipt['code'])
            self.assertEqual(status['next_action'], action)
            self.assertFalse(status['check_available'])
            self.assertTrue(status['stale_inputs'])
            self.assertEqual(self.snapshot(), before)
        path.write_bytes(original)
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['next_action'], 'revise_inputs')

    def test_status_uses_at_most_nine_git_processes_per_call_without_writes(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        before = self.snapshot()
        results = []
        for identifier in (receipt['code'], receipt['record_id']):
            with patch.object(self.store, 'git', wraps=self.store.git) as git:
                results.append(self.m.mission_status(self.root, identifier))
            self.assertLessEqual(git.call_count, 9)
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.snapshot(), before)

    def test_status_revalidates_private_storage_after_input_and_projection_reads(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        ignore = self.root / '.gitignore'
        original = ignore.read_bytes()
        for reader in ('read_inputs', 'projection_hash'):
            with self.subTest(reader=reader):
                read = getattr(self.m, reader)
                changed = []
                def change_ignore(*args, **kwargs):
                    value = read(*args, **kwargs)
                    if not changed:
                        changed.append(True)
                        ignore.write_bytes(original + b'\n!/vault/local/\n')
                    return value
                try:
                    with patch.object(self.m, reader, side_effect=change_ignore):
                        with self.assertRaisesRegex(ValueError, 'Private storage is not ignored'):
                            self.m.mission_status(self.root, receipt['code'])
                    self.assertTrue(changed)
                finally:
                    ignore.write_bytes(original)

    def test_status_rechecks_newly_tracked_private_file_between_calls(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['state'], 'prepared')
        private = self.root / 'vault/local/private.md'
        private.write_bytes(b'private fixture')
        self.git('add', '-f', '--', 'vault/local/private.md')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Private storage is already tracked'):
            self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(self.snapshot(), before)

    def test_status_detects_item_revision_changed_during_input_read(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        item_id = self.item_id(self.paths[-1])
        read = self.m.read_inputs
        changed = []
        def revise_item(*args, **kwargs):
            value = read(*args, **kwargs)
            if not changed:
                changed.append(True)
                with closing(sqlite3.connect(self.root / DB)) as conn:
                    conn.execute('UPDATE records SET revision=revision+1 WHERE id=?', (item_id,))
                    conn.commit()
            return value
        with patch.object(self.m, 'read_inputs', side_effect=revise_item):
            status = self.m.mission_status(self.root, receipt['code'])
        self.assertIn('revision:' + item_id, status['stale_inputs'])

    def test_status_reopens_database_replaced_during_input_read(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        replacement = self.root / (DB + '.replacement')
        shutil.copyfile(self.root / DB, replacement)
        with closing(sqlite3.connect(replacement)) as conn:
            for table in ('records', 'events', 'projections'):
                conn.execute('DELETE FROM ' + table)
            conn.commit()
        read = self.m.read_inputs
        def replace_database(*args, **kwargs):
            value = read(*args, **kwargs)
            if replacement.exists():
                os.replace(replacement, self.root / DB)
            return value
        with patch.object(self.m, 'read_inputs', side_effect=replace_database):
            status = self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(status['stale_inputs'], sorted('revision:' + self.item_id(p) for p in self.paths))

    def test_status_refuses_database_removed_during_input_read(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        read = self.m.read_inputs
        def remove_database(*args, **kwargs):
            value = read(*args, **kwargs)
            (self.root / DB).unlink(missing_ok=True)
            return value
        with patch.object(self.m, 'read_inputs', side_effect=remove_database):
            with self.assertRaisesRegex(ValueError, 'invalid_store'):
                self.m.mission_status(self.root, receipt['code'])
        self.assertFalse((self.root / DB).exists())

    def test_projection_failure_recovers_without_duplicate(self):
        request, actor = self.prepared_fixture()
        with patch('missions.project_receipt', side_effect=OSError('fixture')):
            receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(receipt['projection_state'], 'pending')
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['projection_state'], 'pending')
        recovered = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertEqual(recovered['sequence'], receipt['sequence'])
        self.assertEqual(recovered['projection_state'], 'current')
        self.assertEqual(len(self.db.list_records(self.root, 'mission')), 1)

    def test_recovery_after_first_database_transaction_rolls_back(self):
        with patch('missions.atomic_write', side_effect=OSError('synthetic interrupted first config')):
            with self.assertRaises(OSError):
                self.m.apply_config(self.root, self.configured(), None)
        self.assertFalse((self.root / 'youngcrow/agents.json').exists())
        before = self.snapshot()
        self.assertEqual(self.m.mission_status(self.root, 'M001')['state'], 'not_initialized')
        self.assertEqual(self.snapshot(), before)
        result = self.m.apply_config(self.root, self.configured(), None)
        self.assertEqual(result['gaps'], [])
        self.assertEqual(self.db.list_records(self.root, None), [])

    def test_recovery_after_real_hot_journal_preserves_committed_state(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        original = self.db.get_record(self.root, receipt['record_id'])
        script = '''import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1], isolation_level=None)
db.execute('PRAGMA journal_mode=DELETE')
db.execute('PRAGMA cache_size=1')
db.execute('PRAGMA synchronous=FULL')
db.execute('BEGIN IMMEDIATE')
db.execute('UPDATE records SET snapshot=? WHERE id=?', ('x' * (2 * 1024 * 1024), sys.argv[2]))
os._exit(73)
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(self.root / DB), receipt['record_id']], timeout=20)
        self.assertEqual(child.returncode, 73)
        journal = self.root / (DB + '-journal')
        self.assertTrue(journal.is_file())
        self.assertNotEqual(journal.read_bytes()[:8], b'\x00' * 8)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'invalid_store'):
            self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(self.snapshot(), before)
        # Explicit repair recovers SQLite; status remains strictly read-only.
        self.assertEqual(self.m.repair(self.root, receipt['code'])['projection_state'], 'current')
        self.assertEqual(self.db.get_record(self.root, receipt['record_id']), original)
        self.assertEqual(self.m.repair(self.root, receipt['code'])['projection_state'], 'current')
        self.assertEqual(len(self.m.mission_status(self.root, receipt['code'])['events']), 1)

    def test_recovery_of_large_projection_preserves_human_edits(self):
        paths = self.tree(features=1, pbis=2)
        # Individually bounded sources aggregate to an operational note larger than 1 MiB.
        for i, path in enumerate(paths[-2:]):
            self.contract(path, acceptance=[f'{i}:{n}:' + 'x' * 7000 for n in range(90)])
            self.assertLess((self.root / path).stat().st_size, 1024 * 1024)
        for path in paths:
            self.m.import_item(self.root, path, 0, str(uuid.uuid4()), TL if '/pbis/' in path else ACTOR)
        self.m.apply_config(self.root, self.configured(), None)
        request = dict(title='Large valid mission', feature_ids=[self.item_id(paths[1])],
                       priority=[self.item_id(p) for p in paths[-2:]], overrides={}, scope_reference='Fixture')
        receipt = self.m.prepare_mission(self.root, request, self.op_id, ACTOR)
        self.assertEqual(receipt['projection_state'], 'current')
        path = self.root / receipt['paths'][0]
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['projection_state'], 'current')
        self.assertEqual(self.m.prepare_mission(self.root, request, self.op_id, ACTOR)['event_id'], receipt['event_id'])
        self.assertEqual(self.m.repair(self.root, receipt['code'])['projection_state'], 'current')
        request['title'] = 'Refined large mission'
        self.m.revise_mission(self.root, receipt['code'], request, 1, str(uuid.uuid4()), ACTOR)
        human = path.read_bytes() + b'\nPreserve human addition.\n'
        path.write_bytes(human)
        self.assertEqual(self.m.repair(self.root, receipt['code'])['projection_state'], 'conflict')
        self.assertEqual(path.read_bytes(), human)

    def test_private_and_linked_storage_is_rejected(self):
        path = self.write_item('epic')
        self.git('add', '-f', '--', path)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.m.import_item(self.root, path, 0, self.op_id, ACTOR)
        self.assertEqual(self.snapshot(), before)
        self.git('rm', '--cached', '--', path)
        self.m.apply_config(self.root, self.configured(), None)
        for relative in (DB + '-journal', DB):
            source = self.root / 'shared-file'
            source.write_bytes(b'fixture')
            target = self.root / relative
            if target.exists():
                target.unlink()
            os.link(source, target)
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.m.import_item(self.root, path, 0, self.op_id, ACTOR)
            self.assertEqual(self.snapshot(), before)
            target.unlink(); source.unlink()

    def test_snapshot_staleness_and_source_identity(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        saved = self.db.get_record(self.root, receipt['record_id'])
        profile = self.root / 'vault/product/profile.md'
        profile.write_text(profile.read_text(encoding='utf-8') + '\nChanged.\n', encoding='utf-8')
        self.assertTrue(self.m.mission_status(self.root, receipt['code'])['stale_inputs'])
        self.assertEqual(self.db.get_record(self.root, receipt['record_id']), saved)
        self.contract(self.paths[-1], project_id=str(uuid.uuid4()))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.m.import_item(self.root, self.paths[-1], 1, str(uuid.uuid4()), TL)
        self.assertEqual(self.snapshot(), before)

    def test_revisions_keep_all_refinement_events(self):
        request, actor = self.prepared_fixture()
        with patch('missions.utc_now', return_value='2026-10-03T12:00:00+00:00'):
            receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        with patch('missions.utc_now', return_value='2026-10-03T11:00:00+00:00'):
            newer = self.m.revise_mission(self.root, receipt['code'], dict(request, title='Refined'), 1, str(uuid.uuid4()), actor)
        self.assertGreater(newer['sequence'], receipt['sequence'])
        status = self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(len(status['events']), 2)
        self.assertEqual(status['events'][0]['created_at'], '2026-10-03T12:00:00+00:00')
        self.assertEqual(status['events'][1]['created_at'], '2026-10-03T11:00:00+00:00')

    def test_multiple_drafts_are_not_active_missions(self):
        request, actor = self.prepared_fixture(features=2)
        for _ in range(2):
            receipt = self.m.prepare_mission(self.root, request, str(uuid.uuid4()), actor)
            status = self.m.mission_status(self.root, receipt['code'])
            self.assertEqual(len(status['snapshot']['pbi_ids']), 4)
            self.assertFalse(status['runtime_available'])
            self.assertFalse(status['runnable'])
        self.assertEqual(len(self.db.list_records(self.root, 'mission')), 2)

    def test_no_advanced_transition_or_shell_execution(self):
        before = self.snapshot()
        for extra in ('status', 'completed', 'counters', 'deploy'):
            with self.assertRaises(ValueError):
                self.m.prepare_mission(self.root, {extra: 'secret-fixture'}, self.op_id, ACTOR)
        self.assertEqual(self.snapshot(), before)
        request, actor = self.prepared_fixture()
        self.contract(self.paths[-1], validation=['$(touch never-execute); rm -rf /'])
        self.m.import_item(self.root, self.paths[-1], 1, str(uuid.uuid4()), TL)
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        self.assertFalse((self.root / 'never-execute').exists())
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['state'], 'prepared')

    def test_human_projection_edit_is_preserved(self):
        request, actor = self.prepared_fixture()
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        path = self.root / receipt['paths'][0]
        path.write_text(path.read_text(encoding='utf-8') + '\nHuman addition.\n', encoding='utf-8')
        content = path.read_bytes()
        self.assertEqual(self.m.mission_status(self.root, receipt['code'])['projection_state'], 'conflict')
        result = self.m.repair(self.root, receipt['code'])
        self.assertEqual(result['projection_state'], 'conflict')
        self.assertEqual(path.read_bytes(), content)

    def test_capability_selection_does_not_activate_tools(self):
        from test_capabilities import CapabilityCase
        import capabilities
        fixture = CapabilityCase()
        fixture.root = self.root
        catalog = fixture.seed()
        cap = catalog[0]
        cap['expected']['contract_sha256'] = capabilities.contract_digest(cap)
        for client in cap['clients']:
            cap['expected']['files_sha256'][client] = capabilities.content_digest(self.root, cap['files']['common'] + cap['files'][client])
        fixture.save(catalog)
        request, actor = self.prepared_fixture()
        request['overrides'] = {'agents': {'pm': {'capabilities': ['sample', 'not-installed']}}}
        before = {p: v for p, v in self.snapshot().items() if p.startswith(('.claude/', '.codex/', '.mcp'))}
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        status = self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(status['state'], 'draft')
        self.assertIn('capability:not-installed:unknown', status['gaps'])
        known = next(c for c in status['snapshot']['capabilities'] if c['id'] == 'sample')
        self.assertEqual(known['state'], 'matched')
        self.assertEqual(known['contract_sha256'], cap['expected']['contract_sha256'])
        self.assertTrue(known['coverage'])
        self.assertEqual(before, {p: v for p, v in self.snapshot().items() if p.startswith(('.claude/', '.codex/', '.mcp'))})

    def test_cli_errors_are_sanitized(self):
        source = self.root / 'invalid.json'
        source.write_text('{"api_key":"secret-fixture"}', encoding='utf-8')
        output = io.StringIO()
        before = self.snapshot()
        with redirect_stdout(output):
            code = self.m.main(['--root', str(self.root), '--json', 'config', 'validate', '--input', 'invalid.json'])
        self.assertEqual(code, 2)
        self.assertNotIn('secret-fixture', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['schema_version'], 1)
        self.assertEqual(self.snapshot(), before)

    def test_request_accepts_optional_role_override_syntax(self):
        request = dict(title='Integration', feature_ids=[str(uuid.uuid4())], priority=[],
                       scope_reference='Approved', overrides={'agents': {'integration_specialist': {'model': 'fixture-b'}}})
        self.m.validate_request(request)

    def test_unknown_schema_and_foreign_store_are_read_only(self):
        self.m.apply_config(self.root, self.configured(), None)
        for column, value in [('schema_version', 2), ('project_id', str(uuid.uuid4()))]:
            with closing(sqlite3.connect(self.root / DB)) as conn:
                conn.execute('UPDATE metadata SET schema_version=1, project_id=?', (self.project_id,))
                conn.execute(f'UPDATE metadata SET {column}=?', (value,))
                conn.commit()
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, 'invalid_store'):
                self.m.apply_config(self.root, self.configured(), config_digest(load_config(self.root)))
            self.assertEqual(self.snapshot(), before)

    def test_import_rename_preserves_identity_and_rejects_live_collision(self):
        path = self.write_item('epic')
        first = self.m.import_item(self.root, path, 0, self.op_id, ACTOR)
        newer = path.replace('/index.md', '/renamed.md')
        (self.root / newer).write_bytes((self.root / path).read_bytes())
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'identity_conflict'):
            self.m.import_item(self.root, newer, 1, str(uuid.uuid4()), ACTOR)
        self.assertEqual(self.snapshot(), before)
        (self.root / path).unlink()
        second = self.m.import_item(self.root, newer, 1, str(uuid.uuid4()), ACTOR)
        self.assertEqual(first['record_id'], second['record_id'])
        self.assertEqual(first['code'], second['code'])
        self.assertEqual(second['revision'], 2)

    def test_negated_ignore_is_rejected_without_repair(self):
        path = self.write_item('epic')
        ignore = self.root / '.gitignore'
        ignore.write_text(ignore.read_text(encoding='utf-8') + '\n!/vault/local/\n', encoding='utf-8')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.m.import_item(self.root, path, 0, self.op_id, ACTOR)
        self.assertEqual(self.snapshot(), before)

    def test_first_import_with_wrong_revision_does_not_initialize_store(self):
        path = self.write_item('epic')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.m.import_item(self.root, path, 1, self.op_id, ACTOR)
        self.assertEqual(self.snapshot(), before)

    def test_incompatible_helper_fails_before_any_write(self):
        source = Path(__file__).resolve().parents[1] / 'scripts'
        target = self.root / 'scripts'
        target.mkdir()
        for name in ('missions', 'mission_config', 'mission_backlog', 'mission_store', 'mission_vault',
                     'capabilities', 'document_store', 'integrations', 'vault'):
            shutil.copyfile(source / (name + '.py'), target / (name + '.py'))
        (target / 'capabilities.py').write_text('# preserved legacy helper\n', encoding='utf-8')
        before = self.snapshot()
        result = subprocess.run([sys.executable, '-B', str(target / 'missions.py'), '--root', str(self.root), '--json', 'status', 'M001'],
                                capture_output=True, text=True, timeout=20)
        self.assertIn('"error": "incompatible_helper"', result.stdout, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.snapshot(), before)

    def test_incomplete_criteria_and_external_dependency_stay_draft(self):
        request, actor = self.prepared_fixture()
        self.contract(self.paths[-1], dor=[], dependencies=[str(uuid.uuid4())])
        self.m.import_item(self.root, self.paths[-1], 1, str(uuid.uuid4()), TL)
        receipt = self.m.prepare_mission(self.root, request, self.op_id, actor)
        status = self.m.mission_status(self.root, receipt['code'])
        self.assertEqual(status['state'], 'draft')
        self.assertTrue(any('invalid_dependency' in gap for gap in status['gaps']))
        self.assertTrue(any(':dor' in gap for gap in status['gaps']))

    def test_incompatible_client_helper_is_rejected_before_any_write(self):
        before = self.snapshot()
        with patch.dict(sys.modules, {'mission_clients': object()}):
            with self.assertRaisesRegex(ValueError, '^incompatible_helper$'):
                self.m.runtime_helpers()
        self.assertEqual(self.snapshot(), before)

    def test_native_probe_requires_explicit_manifest(self):
        before = self.snapshot()
        smoke = Path(__file__).parent / 'smoke_mission_runtime.py'
        for arguments in (['--executable', sys.executable], ['--native-manifest', 'vault/local/absent.json']):
            result = subprocess.run([sys.executable, '-B', str(smoke), '--root', str(self.root), *arguments],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('mission_runtime_smoke_failed', result.stdout)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
