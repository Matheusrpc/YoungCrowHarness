"""Real planning revisions; no agent, provider or delivery acceptance."""
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch

from mission_fixtures import MissionCase
import mission_queue
import mission_store as store
import missions

ACTOR = dict(id='fixture-pm', role='pm')


class PriorityTests(MissionCase):
    def setUp(self):
        super().setUp()
        paths = self.tree(pbis=4)
        for path in paths:
            missions.import_item(self.root, path, 0, str(uuid.uuid4()),
                                 dict(id='fixture', role='tech_lead' if '/pbis/' in path else 'pm'))
        missions.apply_config(self.root, self.configured(), None)
        self.request = dict(title='Priority fixture',
            feature_ids=[self.item_id(p) for p in paths if '/features/' in p],
            priority=[self.item_id(p) for p in paths if '/pbis/' in p],
            overrides={}, scope_reference='Approved fixture scope')
        self.mission = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()), ACTOR)
        self.proposal = dict(schema_version=1, project_id=self.project_id,
            mission_id=self.mission['record_id'], mission_revision=1,
            priority=list(reversed(self.request['priority'])), reason='Deliver the selected priority first')
        self.operation = str(uuid.uuid4())

    def apply(self, proposal=None, actor=None, operation=None, **kwargs):
        self.assertTrue(callable(getattr(missions, 'reprioritize_mission', None)), 'missing restricted priority command')
        return missions.reprioritize_mission(self.root, proposal or self.proposal,
            operation or self.operation, actor or ACTOR, **kwargs)

    def command(self, *args):
        return [sys.executable, '-B', str(Path(missions.__file__)), '--root', str(self.root), '--json', *args]

    def cli(self, *args, code=0):
        result = subprocess.run(self.command(*args), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def arguments(self, operation=None):
        path = 'vault/local/priority-proposal.json'
        (self.root / path).write_text(json.dumps(self.proposal))
        return ('reprioritize', '--input', path, '--operation-id', operation or self.operation,
                '--actor-id', ACTOR['id'], '--actor-role', 'pm')

    def test_cli_preview_then_apply_changes_only_priority_and_decision(self):
        args = self.arguments()
        original = store.get_record(self.root, self.mission['record_id'])['snapshot']
        before = self.snapshot()
        preview = self.cli(*args, '--dry-run')
        self.assertEqual(preview['state'], 'preview')
        self.assertEqual(preview['previous_priority'], original['priority'])
        self.assertEqual(preview['priority'], self.proposal['priority'])
        self.assertEqual(preview['protected_pbi_ids'], [])
        self.assertFalse(preview['runnable'])
        self.assertEqual(self.snapshot(), before)
        receipt = self.cli(*args)
        self.assertEqual((receipt['record_id'], receipt['revision']), (self.mission['record_id'], 2))
        self.assertEqual(self.cli(*args), receipt)
        result = self.cli('status', self.mission['code'])
        changed = result['snapshot']
        decision = changed.pop('last_planning_decision')
        self.assertEqual(decision, dict(action='reprioritize', reason=self.proposal['reason']))
        self.assertEqual(changed.pop('priority'), self.proposal['priority'])
        original.pop('priority')
        self.assertEqual(changed, original)
        self.assertEqual([p['id'] for p in result['queue_preview']['items']], self.proposal['priority'])
        self.assertEqual(len(result['events']), 2)

    def test_invalid_proposals_and_actor_are_refused_without_writes(self):
        before = self.snapshot()
        cases = [(dict(scope_reference='Changed scope'), 'invalid_proposal'),
                 (dict(schema_version=True), 'invalid_proposal'),
                 (dict(project_id=str(uuid.uuid4())), 'foreign_project'),
                 (dict(mission_id=str(uuid.uuid4())), 'unknown_mission'),
                 (dict(mission_revision=2), 'revision_conflict'),
                 (dict(mission_revision=True), 'invalid_revision'),
                 (dict(priority=self.proposal['priority'][:-1]), 'invalid_priority'),
                 (dict(priority=self.proposal['priority'] + [str(uuid.uuid4())]), 'invalid_priority'),
                 (dict(priority=[self.proposal['priority'][0]] * 4), 'invalid_priority'),
                 (dict(reason=''), 'invalid_proposal')]
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, error):
                self.apply(dict(self.proposal, **update))
        with self.assertRaisesRegex(ValueError, 'invalid_actor'):
            self.apply(actor=dict(ACTOR, role='tech_lead'))
        self.assertEqual(self.snapshot(), before)

    def test_replay_survives_stale_source_and_changed_request_conflicts(self):
        receipt = self.apply()
        path = self.root / 'vault/product/profile.md'
        path.write_bytes(path.read_bytes() + b'\nChanged after the decision\n')
        before = self.snapshot()
        self.assertEqual(self.apply(), receipt)
        for proposal, actor in ((dict(self.proposal, reason='Different reason'), ACTOR),
                                (self.proposal, dict(ACTOR, id='another-pm'))):
            with self.assertRaisesRegex(ValueError, 'operation_conflict'):
                self.apply(proposal, actor)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 2)

    def test_stale_sources_and_projection_conflict_block_new_decision(self):
        profile = self.root / 'vault/product/profile.md'
        original = profile.read_bytes()
        profile.write_bytes(original + b'\nChanged\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        profile.write_bytes(original)
        note = self.root / self.mission['paths'][0]
        note.write_bytes(note.read_bytes() + b'\nHuman projection change\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_active_old_queue_is_preserved_and_blocks_priority(self):
        session = mission_queue.apply(self.root, 'start', self.mission['code'], 1, str(uuid.uuid4()), ACTOR['id'])['session']
        missions.revise_mission(self.root, self.mission['code'], self.request, 1, str(uuid.uuid4()), ACTOR)
        self.proposal['mission_revision'] = 2
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'queue_busy'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        mission_queue.apply(self.root, 'cancel', session['id'], 1, str(uuid.uuid4()), ACTOR['id'])
        self.assertEqual(self.apply()['revision'], 3)

    def test_pending_projection_preview_never_repairs_but_replay_does(self):
        with patch.object(missions, 'project_receipt', side_effect=OSError('lost projection')):
            first = self.apply()
        self.assertEqual(first['projection_state'], 'pending')
        before = self.snapshot()
        preview = self.apply(dry_run=True)
        self.assertEqual(preview['state'], 'already_applied')
        self.assertEqual(preview['receipt']['event_id'], first['event_id'])
        self.assertEqual(self.snapshot(), before)
        repeated = self.apply()
        self.assertEqual((repeated['event_id'], repeated['revision'], repeated['projection_state']),
                         (first['event_id'], 2, 'current'))
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 2)

    def test_interrupted_commit_rolls_back_then_same_operation_can_complete(self):
        before = self.snapshot()
        original = store.commit_record
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('interrupted before transaction commit')
        with patch.object(store, 'commit_record', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.apply()['revision'], 2)
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 2)

    def test_preview_is_not_reservation_and_apply_rechecks_queue(self):
        self.apply(dry_run=True)
        mission_queue.apply(self.root, 'start', self.mission['code'], 1, str(uuid.uuid4()), ACTOR['id'])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'queue_busy'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_two_concurrent_proposals_accept_only_one_revision(self):
        args1 = self.arguments()
        args2 = self.arguments(str(uuid.uuid4()))
        processes = [subprocess.Popen(self.command(*args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for args in (args1, args2)]
        results = []
        for process in processes:
            out, err = process.communicate(timeout=30)
            results.append((process.returncode, json.loads(out)))
            self.assertEqual(err, '')
        self.assertEqual(sorted(code for code, _ in results), [0, 1])
        self.assertEqual([r['error'] for code, r in results if code], ['revision_conflict'])
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 2)

    def test_workspace_history_pins_pbi_even_after_release_in_other_mission(self):
        import mission_workspace
        (self.root / 'app.txt').write_text('base\n')
        ignore = self.root / '.gitignore'
        ignore.write_text(ignore.read_text() + '\n/.runtime/workspaces/\n')
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], env=self.env)
        git('add', '--', 'app.txt', '.gitignore')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base')
        base = git('rev-parse', 'HEAD').decode().strip()
        other = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()), ACTOR)
        pbi = self.request['priority'][1]
        workspace = mission_workspace.prepare(self.root, mission=other['record_id'], pbi=pbi, base=base,
            expected_revision=1, operation_id=str(uuid.uuid4()), actor_id=ACTOR['id'])
        mission_workspace.release(self.root, workspace['id'], expected_revision=1,
            operation_id=str(uuid.uuid4()), actor_id=ACTOR['id'])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'priority_locked'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        a, b, c, d = self.request['priority']
        self.proposal['priority'] = [c, b, a, d]
        self.assertEqual(self.apply(dry_run=True)['protected_pbi_ids'], [b])
        self.apply()
        self.assertEqual(mission_workspace.status(self.root, workspace['id'])['mission_revision'], 1)
