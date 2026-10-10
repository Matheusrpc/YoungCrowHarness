"""Bounded context from real mission notes; no client or model invocation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch
from contextlib import contextmanager

from mission_fixtures import MissionCase
import missions
import mission_store as store
from capabilities import canonical


class ContextTests(MissionCase):
    def setUp(self):
        super().setUp()
        self.paths = self.tree(features=2, pbis=2)
        self.epic, self.feature, self.pbi, self.sibling = self.paths[:4]
        self.pbi_id = self.item_id(self.pbi)
        # A dependency is identified, but its own context is not pulled in.
        self.contract(self.pbi, dependencies=[self.item_id(self.sibling)])
        for path in self.paths:
            missions.import_item(self.root, path, 0, str(uuid.uuid4()),
                                 dict(id='fixture', role='tech_lead' if '/pbis/' in path else 'pm'))
        missions.apply_config(self.root, self.configured(), None)
        self.request = dict(title='Context fixture',
            feature_ids=[self.item_id(p) for p in self.paths if '/features/' in p],
            priority=[self.item_id(p) for p in self.paths if '/pbis/' in p],
            overrides={}, scope_reference='Selected fixture scope')
        self.mission = missions.prepare_mission(self.root, self.request, str(uuid.uuid4()),
                                               dict(id='fixture', role='pm'))

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-B', str(Path(missions.__file__)),
            '--root', str(self.root), '--json', *args], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def context(self, **options):
        return missions.mission_context(self.root, self.mission['code'],
            options.pop('pbi', self.pbi_id), options.pop('revision', 1), **options)

    def test_cli_selects_ancestry_and_explicit_sources_without_writes(self):
        before = self.snapshot()
        args = ('context', self.mission['code'], '--pbi', self.item_id(self.pbi), '--expected-revision', '1')
        result = self.cli(*args)
        self.assertEqual(self.cli(*args), result)
        self.assertEqual(result['project_id'], self.project_id)
        self.assertEqual(result['mission']['revision'], 1)
        self.assertEqual([r['id'] for r in result['items']],
                         [self.item_id(p) for p in (self.epic, self.feature, self.pbi)])
        self.assertEqual([r['id'] for r in result['dependencies']], [self.item_id(self.sibling)])
        self.assertNotIn('contract', result['dependencies'][0])
        self.assertEqual({s['path'] for s in result['sources']},
                         {self.epic, self.feature, self.pbi, 'vault/product/profile.md'})
        for source in result['sources']:
            raw = (self.root / source['path']).read_bytes()
            self.assertEqual(source['content'].encode('utf-8'), raw)
            self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(source['note_id'], self.item_id(source['path']))
        digest = result.pop('context_sha256')
        self.assertEqual(digest, hashlib.sha256(canonical(result)).hexdigest())
        self.assertFalse(result['runtime_available'])
        self.assertFalse(result['runnable'])
        self.assertEqual(result['source_trust'], 'untrusted_data')
        self.assertEqual(self.snapshot(), before)

    def test_rejects_old_revision_and_pbi_outside_mission(self):
        self.assertTrue(callable(getattr(missions, 'mission_context', None)), 'missing context query')
        before = self.snapshot()
        for options, error in ((dict(revision=2), 'revision_conflict'),
                               (dict(pbi=str(uuid.uuid4())), 'unknown_pbi'),
                               (dict(pbi=self.item_id(self.feature)), 'unknown_pbi'),
                               (dict(revision=True), 'invalid_revision')):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, error):
                self.context(**options)
        self.assertEqual(self.snapshot(), before)

    def test_changed_or_missing_source_refuses_instead_of_partial_context(self):
        self.assertTrue(callable(getattr(missions, 'mission_context', None)), 'missing context query')
        path = self.root / self.pbi
        original = path.read_bytes()
        for raw in (original + b'\nNew unapproved text\n', original.replace(
                self.item_id(self.pbi).encode(), str(uuid.uuid4()).encode()), None):
            if raw is None:
                path.unlink()
            else:
                path.write_bytes(raw)
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, 'stale_context'):
                self.context()
            self.assertEqual(self.snapshot(), before)

    def test_source_change_after_status_cannot_enter_context(self):
        self.assertTrue(callable(getattr(missions, 'mission_context', None)), 'missing context query')
        original = missions.mission_status
        def observed(*args):
            result = original(*args)
            path = self.root / self.pbi
            path.write_bytes(path.read_bytes() + b'\nChanged after observation\n')
            return result
        with patch.object(missions, 'mission_status', side_effect=observed):
            with self.assertRaisesRegex(ValueError, 'stale_context'):
                self.context()

    def test_draft_and_projection_conflict_remain_visible_without_repair(self):
        self.assertTrue(callable(getattr(missions, 'mission_context', None)), 'missing context query')
        self.contract(self.pbi, acceptance=[])
        missions.import_item(self.root, self.pbi, 1, str(uuid.uuid4()), dict(id='fixture', role='tech_lead'))
        revised = missions.revise_mission(self.root, self.mission['code'], self.request, 1,
                                         str(uuid.uuid4()), dict(id='fixture', role='pm'))
        path = self.root / revised['paths'][0]
        path.write_bytes(path.read_bytes() + b'\nHuman change\n')
        before = self.snapshot()
        result = self.context(revision=2)
        self.assertEqual(result['readiness']['state'], 'draft')
        self.assertTrue(result['readiness']['gaps'])
        self.assertEqual(result['readiness']['projection_state'], 'conflict')
        self.assertFalse(result['readiness']['check_available'])
        self.assertEqual(self.snapshot(), before)

    def test_uninitialized_read_does_not_create_storage(self):
        (self.root / store.DB_PATH).unlink()
        before = self.snapshot()
        result = self.cli('context', 'M999', '--pbi', self.item_id(self.pbi),
                          '--expected-revision', '1', code=2)
        self.assertEqual(result['error'], 'unknown_mission')
        self.assertEqual(self.snapshot(), before)

    def revise(self, paths):
        for path in paths:
            missions.import_item(self.root, path, 1, str(uuid.uuid4()),
                                 dict(id='fixture', role='tech_lead' if '/pbis/' in path else 'pm'))
        return missions.revise_mission(self.root, self.mission['code'], self.request, 1,
                                       str(uuid.uuid4()), dict(id='fixture', role='pm'))

    def test_explicit_ancestor_reference_preserves_bytes_without_following_prose_links(self):
        source = self.write_item('epic')
        hidden = self.write_item('epic')
        ref_id = self.item_id(source)
        path = self.root / source
        text = path.read_bytes() + ('\n[Do not follow](/' + hidden + ')\nNever execute: echo fixture\n').encode()
        path.write_bytes(b'\xef\xbb\xbf' + text.replace(b'\n', b'\r\n'))
        self.contract(self.epic, references=[dict(note_id=ref_id, path=source)])
        self.contract(self.sibling, references=[dict(note_id=self.item_id(hidden), path=hidden)])
        self.revise([self.epic, self.sibling])
        before = self.snapshot()
        result = self.context(revision=2)
        sources = {s['path']: s for s in result['sources']}
        self.assertIn(source, sources)
        self.assertNotIn(hidden, sources)
        self.assertEqual(sources[source]['content'].encode('utf-8'), path.read_bytes())
        self.assertEqual(sources[source]['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.snapshot(), before)

    def test_draft_with_stale_import_cannot_mix_old_contract_and_new_prose(self):
        path = self.root / self.pbi
        path.write_bytes(path.read_bytes() + b'\nNot imported\n')
        missions.revise_mission(self.root, self.mission['code'], self.request, 1,
                                str(uuid.uuid4()), dict(id='fixture', role='pm'))
        self.assertEqual(missions.mission_status(self.root, self.mission['code'])['stale_inputs'], [])
        with self.assertRaisesRegex(ValueError, 'stale_context'):
            self.context(revision=2)

    def test_revision_change_during_source_read_refuses_mixed_result(self):
        original = missions.read_inputs
        fired = []
        def changed(root, paths):
            data = original(root, paths)
            if len(paths) == 4 and not fired:
                fired.append(True)
                self.revise([])
            return data
        with patch.object(missions, 'read_inputs', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'revision_conflict'):
                self.context()
        self.assertEqual(fired, [True])

    def test_duplicate_source_identity_refuses_even_with_pinned_hashes(self):
        source = self.write_item('epic')
        duplicate = self.write_item('epic')
        (self.root / duplicate).write_bytes((self.root / source).read_bytes())
        ref = dict(note_id=self.item_id(source), path=source)
        self.contract(self.epic, references=[ref])
        self.contract(self.feature, references=[dict(ref, path=duplicate)])
        self.revise([self.epic, self.feature])
        with self.assertRaisesRegex(ValueError, 'context_identity_conflict'):
            self.context(revision=2)

    def test_database_removed_after_sources_returns_sanitized_refusal(self):
        original = missions.read_inputs
        def removed(root, paths):
            data = original(root, paths)
            if len(paths) == 4:
                (root / store.DB_PATH).unlink()
            return data
        with patch.object(missions, 'read_inputs', side_effect=removed):
            with self.assertRaisesRegex(ValueError, 'invalid_store'):
                self.context()

    def test_project_label_comes_from_validated_database_observation(self):
        original_read, original_reader = missions.read_inputs, store.reader
        source_read = []
        def observed(root, paths):
            data = original_read(root, paths)
            if len(paths) == 4:
                source_read.append(True)
            return data
        @contextmanager
        def replaced(root, **kwargs):
            with original_reader(root, **kwargs) as conn:
                if source_read:
                    path = root / 'vault/project.json'
                    data = json.loads(path.read_text())
                    data['project_id'] = str(uuid.uuid4())
                    path.write_text(json.dumps(data))
                yield conn
        with patch.object(missions, 'read_inputs', side_effect=observed), patch.object(store, 'reader', replaced):
            self.assertEqual(self.context()['project_id'], self.project_id)

    def test_missing_parent_refuses_and_external_dependency_is_only_an_id(self):
        external = str(uuid.uuid4())
        self.contract(self.pbi, dependencies=[external])
        self.revise([self.pbi])
        result = self.context(revision=2)
        self.assertEqual(result['dependencies'], [dict(id=external, available_in_mission=False)])
        self.assertTrue(result['readiness']['gaps'])
        self.contract(self.feature, parent_id=None)
        missions.import_item(self.root, self.feature, 1, str(uuid.uuid4()), dict(id='fixture', role='pm'))
        missions.revise_mission(self.root, self.mission['code'], self.request, 2,
                                str(uuid.uuid4()), dict(id='fixture', role='pm'))
        with self.assertRaisesRegex(ValueError, 'incomplete_context'):
            self.context(revision=3)
