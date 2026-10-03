import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import unittest
import uuid

from mission_fixtures import MissionCase, START, END, NOW
import personalize
import vault


class BacklogTests(MissionCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('mission_backlog'), 'backlog reader not implemented')
        self.backlog = importlib.import_module('mission_backlog')

    def test_existing_feature_is_read_without_rewrite(self):
        personalize.prepare(self.root, 'feature', 'fixture', feature='legacy')
        path = 'vault/features/legacy/index.md'
        before = self.snapshot()
        item = self.backlog.read_item(self.root, path)
        self.assertEqual(item['kind'], 'feature')
        self.assertIn('missing_contract', item['gaps'])
        self.assertEqual(self.snapshot(), before)

    def test_valid_tree_and_draft_renderer(self):
        items = [self.backlog.read_item(self.root, p) for p in self.tree()]
        before = copy.deepcopy(items)
        self.assertEqual(self.backlog.validate_graph(items), [])
        self.assertEqual(items, before)
        self.assertTrue(all(not item['gaps'] for item in items))
        self.assertEqual(vault.check(self.root)['issues'], [])
        renderer = importlib.import_module('mission_vault')
        path = self.write_item('feature', items[0]['id'])
        identity = self.item_id(path)
        (self.root / path).write_text(renderer.render_item(self.project_id, identity, 'feature', 'A draft', items[0]['id'], NOW), encoding='utf-8')
        draft = self.backlog.read_item(self.root, path)
        self.assertEqual(draft['id'], identity)
        self.assertIn('objective', draft['gaps'])

    def test_changed_reference_changes_evidence_revision(self):
        path = self.tree()[-1]
        first = self.backlog.read_item(self.root, path)
        source = self.root / first['references'][0]['path']
        source.write_text(source.read_text(encoding='utf-8') + '\nNew evidence.\n', encoding='utf-8')
        second = self.backlog.read_item(self.root, path)
        self.assertNotEqual(first['references'][0]['sha256'], second['references'][0]['sha256'])
        self.assertEqual(first['note_sha256'], second['note_sha256'])

    def test_invalid_graph_reports_cycle_and_wrong_parent(self):
        epic, feature, a, b = self.tree()
        self.contract(a, dependencies=[self.item_id(b)], parent_id=self.item_id(epic))
        self.contract(b, dependencies=[self.item_id(a)])
        items = [self.backlog.read_item(self.root, p) for p in (epic, feature, a, b)]
        codes = {d['code'] for d in self.backlog.validate_graph(items)}
        self.assertTrue({'dependency_cycle', 'invalid_parent'} <= codes)
        self.assertIn('duplicate_id', {d['code'] for d in self.backlog.validate_graph(items + [items[0]])})

    def test_invalid_contract_and_references_are_read_only(self):
        path = self.tree()[-1]
        original = (self.root / path).read_text(encoding='utf-8')
        cases = [dict(project_id=str(uuid.uuid4())), dict(schema_version=True), dict(owner='developer'),
                 dict(references=[dict(note_id=str(uuid.uuid4()), path='vault/product/profile.md')]),
                 dict(references=[dict(note_id=self.item_id(path), path='../outside.md')]),
                 dict(references=[dict(note_id=self.item_id(path), path='vault/local/missing.md')]),
                 dict(dependencies=[True]), dict(dor=['']), dict(unexpected='secret-fixture')]
        for patch in cases:
            (self.root / path).write_text(original, encoding='utf-8')
            self.contract(path, **patch)
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.backlog.read_item(self.root, path)
            self.assertEqual(self.snapshot(), before)
        for broken in [original + START + '\n```json\n{}\n```\n' + END, original.replace('```json', '```python'), original.replace('"schema_version": 1', '"schema_version": NaN')]:
            (self.root / path).write_text(broken, encoding='utf-8')
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.backlog.read_item(self.root, path)
            self.assertEqual(self.snapshot(), before)

    def test_public_to_private_and_linked_sources_are_rejected(self):
        epic, feature, pbi, _ = self.tree()
        public = 'vault/features/public.md'
        (self.root / public).write_bytes((self.root / feature).read_bytes())
        self.contract(public, references=[dict(note_id=self.item_id(pbi), path=pbi)])
        with self.assertRaises(ValueError):
            self.backlog.read_item(self.root, public)
        linked = self.root / 'vault/product/hard.md'
        os.link(self.root / 'vault/product/profile.md', linked)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.backlog.read_item(self.root, pbi)
        self.assertEqual(self.snapshot(), before)

    def test_reparse_path_is_rejected(self):
        path = self.tree()[-1]
        target = self.root / 'vault/local/linked'
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(target), str(self.root / 'vault/product')], check=True, capture_output=True)
        else:
            target.symlink_to(self.root / 'vault/product', target_is_directory=True)
        self.contract(path, references=[dict(note_id=self.item_id('vault/product/profile.md'), path='vault/local/linked/profile.md')])
        with self.assertRaises(ValueError):
            self.backlog.read_item(self.root, path)


if __name__ == '__main__':
    unittest.main()
