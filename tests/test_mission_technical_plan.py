"""A selected technical plan reaches only its PBI context; no model or worker."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch

from mission_fixtures import MissionCase, NOW
from integrations import note
import mission_queue
import mission_store as store
import missions

PM = dict(id='fixture-pm', role='pm')
TL = dict(id='fixture-tl', role='tech_lead')


class TechnicalPlanTests(MissionCase):
    def setUp(self):
        super().setUp()
        self.paths = self.tree(pbis=2)
        self.pbis = [self.item_id(p) for p in self.paths if '/pbis/' in p]
        self.index('vault/local/plans/index.md', '../index.md', 'Plans')
        self.store.append_link(self.root, 'vault/local/index.md', '[Plans](plans/index.md)')
        self.references = []
        for name in ('first', 'alternative', 'second'):
            path = f'vault/local/plans/{name}.md'
            content = note(self.project_id, path, 'decision', name, 'index.md',
                           f'# {name}\n\n[Index](index.md)\n\nSynthetic implementation approach.\n', NOW)
            (self.root / path).write_text(content, encoding='utf-8')
            self.store.append_link(self.root, 'vault/local/plans/index.md', f'[{name}]({name}.md)')
            self.references.append(dict(note_id=self.item_id(path), path=path,
                                       sha256=hashlib.sha256((self.root / path).read_bytes()).hexdigest()))
        for path, refs in zip(self.paths[2:], (self.references[:2], self.references[2:])):
            self.contract(path, references=[{k: v for k, v in ref.items() if k != 'sha256'} for ref in refs])
        for path in self.paths:
            missions.import_item(self.root, path, 0, str(uuid.uuid4()), TL if '/pbis/' in path else PM)
        missions.apply_config(self.root, self.configured(), None)
        self.request = dict(title='Technical plan fixture', feature_ids=[self.item_id(self.paths[1])],
                            priority=self.pbis, overrides={}, scope_reference='Approved fixture scope')
        self.mission = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()), PM)
        self.proposal = dict(schema_version=1, project_id=self.project_id, mission_id=self.mission['record_id'],
                             mission_revision=1, pbi_id=self.pbis[0], pbi_revision=1,
                             plan_reference=self.references[0], reason='Selected for the existing acceptance criteria')
        self.operation = str(uuid.uuid4())

    def apply(self, proposal=None, actor=None, operation=None, **options):
        self.assertTrue(callable(getattr(missions, 'set_technical_plan', None)), 'missing technical-plan command')
        return missions.set_technical_plan(self.root, proposal or self.proposal,
                                          operation or self.operation, actor or TL, **options)

    def command(self, *args):
        return [sys.executable, '-B', str(Path(missions.__file__)), '--root', str(self.root), '--json', *args]

    def cli(self, *args, code=0):
        result = subprocess.run(self.command(*args), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def arguments(self):
        path = 'vault/local/technical-plan.json'
        (self.root / path).write_text(json.dumps(self.proposal))
        return ('technical-plan', '--input', path, '--operation-id', self.operation,
                '--actor-id', TL['id'], '--actor-role', TL['role'])

    def test_cli_roundtrip_preserves_sources_and_isolates_each_pbi_plan(self):
        args = self.arguments()
        original = store.get_record(self.root, self.mission['record_id'])['snapshot']
        source_bytes = {p: (self.root / p).read_bytes() for p in original['inputs']}
        before = self.snapshot()
        preview = self.cli(*args, '--dry-run')
        self.assertEqual(preview['state'], 'preview')
        self.assertIsNone(preview['previous_technical_decision'])
        self.assertEqual(preview['technical_decision']['plan_reference'], self.references[0])
        self.assertEqual(self.snapshot(), before)
        receipt = self.cli(*args)
        self.assertEqual(receipt['revision'], 2)
        self.assertEqual(self.cli(*args), receipt)
        changed = store.get_record(self.root, self.mission['record_id'])['snapshot']
        decisions = changed.pop('technical_decisions')
        self.assertEqual(changed, original)
        context = self.cli('context', self.mission['code'], '--pbi', self.pbis[0], '--expected-revision', '2')
        self.assertEqual(context['technical_decision'], decisions[self.pbis[0]])
        self.assertEqual(context['context_sha256'], hashlib.sha256(missions.canonical(
            {k: v for k, v in context.items() if k != 'context_sha256'})).hexdigest())
        other = self.cli('context', self.mission['code'], '--pbi', self.pbis[1], '--expected-revision', '2')
        self.assertIsNone(other['technical_decision'])
        self.assertNotIn(self.references[0]['path'], [s['path'] for s in other['sources']])
        second = dict(self.proposal, pbi_id=self.pbis[1], mission_revision=2, plan_reference=self.references[2])
        self.apply(second, operation=str(uuid.uuid4()))
        plans = store.get_record(self.root, self.mission['record_id'])['snapshot']['technical_decisions']
        priority = {k: self.proposal[k] for k in ('schema_version', 'project_id', 'mission_id', 'reason')}
        missions.reprioritize_mission(self.root, dict(priority, mission_revision=3, priority=list(reversed(self.pbis))),
                                     str(uuid.uuid4()), PM)
        for pbi in self.pbis:
            self.assertEqual(missions.mission_context(self.root, self.mission['code'], pbi, 4)['technical_decision'], plans[pbi])
        missions.revise_mission(self.root, self.mission['code'], self.request, 4, str(uuid.uuid4()), PM)
        self.assertIsNone(missions.mission_context(self.root, self.mission['code'], self.pbis[0], 5)['technical_decision'])
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 5)
        self.assertEqual(source_bytes, {p: (self.root / p).read_bytes() for p in original['inputs']})

    def test_invalid_identity_revision_role_or_reference_never_writes(self):
        before = self.snapshot()
        profile = 'vault/product/profile.md'
        for change, error in (
                (dict(priority=self.pbis), 'invalid_proposal'),
                (dict(project_id=str(uuid.uuid4())), 'foreign_project'),
                (dict(pbi_id=str(uuid.uuid4())), 'unknown_pbi'),
                (dict(pbi_revision=2), 'revision_conflict'),
                (dict(pbi_revision=True), 'invalid_revision'),
                (dict(mission_revision=2), 'revision_conflict'),
                (dict(plan_reference=self.references[2]), 'invalid_plan_reference'),
                (dict(plan_reference=dict(note_id=self.item_id(profile), path=profile,
                      sha256=hashlib.sha256((self.root / profile).read_bytes()).hexdigest())), 'invalid_plan_reference'),
                (dict(plan_reference=dict(self.references[0], sha256='0' * 64)), 'invalid_plan_reference'),
                (dict(plan_reference=dict(self.references[0], extra='untrusted')), 'invalid_proposal'),
                (dict(reason=' '), 'invalid_proposal')):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, error):
                self.apply(dict(self.proposal, **change))
        with self.assertRaisesRegex(ValueError, 'invalid_actor'):
            self.apply(actor=PM)
        self.assertEqual(self.snapshot(), before)

    def test_replacing_plan_keeps_original_decision_in_history(self):
        first = self.apply()
        revised = dict(self.proposal, mission_revision=2, plan_reference=self.references[1], reason='Selected alternative')
        self.apply(revised, operation=str(uuid.uuid4()))
        self.assertEqual(self.apply()['event_id'], first['event_id'])
        context = missions.mission_context(self.root, self.mission['code'], self.pbis[0], 3)
        self.assertEqual(context['technical_decision']['plan_reference'], self.references[1])
        events = store.events(self.root, self.mission['record_id'])
        self.assertEqual(events[1]['record']['snapshot']['technical_decisions'][self.pbis[0]]['plan_reference'], self.references[0])
        self.assertEqual(len(events), 3)

    def test_reference_changed_while_freezing_mission_cannot_be_selected(self):
        original = missions.frozen_inputs
        def changed_source(root, items):
            path = root / self.references[0]['path']
            path.write_bytes(path.read_bytes() + b'\nChanged during preparation\n')
            return original(root, items)
        with patch.object(missions, 'frozen_inputs', side_effect=changed_source):
            mission = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()), PM)
        self.assertFalse(missions.mission_status(self.root, mission['code'])['check_available'])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply(dict(self.proposal, mission_id=mission['record_id']))
        self.assertEqual(self.snapshot(), before)

    def test_selected_reference_change_refuses_new_decision_but_replay_recovers(self):
        with patch.object(missions, 'project_receipt', side_effect=OSError('interrupted projection')):
            receipt = self.apply()
        self.assertEqual(receipt['projection_state'], 'pending')
        path = self.root / self.references[0]['path']
        path.write_bytes(path.read_bytes() + b'\nChanged source\n')
        before = self.snapshot()
        self.assertEqual(self.apply(dry_run=True)['state'], 'already_applied')
        self.assertEqual(self.snapshot(), before)
        repeated = self.apply()
        self.assertEqual((repeated['event_id'], repeated['projection_state']), (receipt['event_id'], 'current'))
        with self.assertRaisesRegex(ValueError, 'operation_conflict'):
            self.apply(dict(self.proposal, reason='Changed request'))
        with self.assertRaisesRegex(ValueError, 'mission_not_ready'):
            self.apply(dict(self.proposal, mission_revision=2), operation=str(uuid.uuid4()))
        with self.assertRaisesRegex(ValueError, 'stale_context'):
            missions.mission_context(self.root, self.mission['code'], self.pbis[0], 2)

    def test_active_queue_of_older_revision_blocks_plan_after_preview(self):
        self.apply(dry_run=True)
        mission_queue.apply(self.root, 'start', self.mission['code'], 1, str(uuid.uuid4()), PM['id'])
        missions.revise_mission(self.root, self.mission['code'], self.request, 1, str(uuid.uuid4()), PM)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'queue_busy'):
            self.apply(dict(self.proposal, mission_revision=2))
        self.assertEqual(self.snapshot(), before)

    def test_released_workspace_in_another_mission_locks_only_its_pbi(self):
        import mission_workspace
        (self.root / 'app.txt').write_text('base\n')
        ignore = self.root / '.gitignore'
        ignore.write_text(ignore.read_text() + '\n/.runtime/workspaces/\n')
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], env=self.env)
        git('add', '--', 'app.txt', '.gitignore')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base')
        base = git('rev-parse', 'HEAD').decode().strip()
        other = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()), PM)
        workspace = mission_workspace.prepare(self.root, mission=other['record_id'], pbi=self.pbis[0], base=base,
            expected_revision=1, operation_id=str(uuid.uuid4()), actor_id=PM['id'])
        mission_workspace.release(self.root, workspace['id'], expected_revision=1,
            operation_id=str(uuid.uuid4()), actor_id=PM['id'])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'technical_plan_locked'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.apply(dict(self.proposal, pbi_id=self.pbis[1], plan_reference=self.references[2]))['revision'], 2)

    def test_concurrent_pm_and_tech_lead_cannot_apply_same_revision(self):
        technical = self.arguments()
        priority = {k: self.proposal[k] for k in ('schema_version', 'project_id', 'mission_id', 'mission_revision', 'reason')}
        priority['priority'] = list(reversed(self.pbis))
        path = 'vault/local/priority.json'
        (self.root / path).write_text(json.dumps(priority))
        pm_args = ('reprioritize', '--input', path, '--operation-id', str(uuid.uuid4()), '--actor-id', PM['id'], '--actor-role', 'pm')
        processes = [subprocess.Popen(self.command(*args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for args in (technical, pm_args)]
        results = []
        for process in processes:
            out, err = process.communicate(timeout=30)
            results.append((process.returncode, json.loads(out)))
            self.assertEqual(err, '')
        self.assertEqual(sorted(code for code, _ in results), [0, 1])
        self.assertEqual([r['error'] for code, r in results if code], ['revision_conflict'])
        self.assertEqual(len(store.events(self.root, self.mission['record_id'])), 2)
