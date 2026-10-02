"""Real filesystem/Git tests for memory scope, provenance and current revisions."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import unittest

from test_documents import ProjectCase
from memory_fixture import seed, OTHER


class MemoryTests(ProjectCase):
    def setUp(self):
        super().setUp()
        self.data = seed(self.root)
        self.assertIsNotNone(importlib.util.find_spec('memory'), 'memory retrieval is not implemented')
        self.memory = importlib.import_module('memory')

    def test_selected_notes_keep_identity_and_current_evidence(self):
        originals = {p: (self.root / p).read_bytes() for p in self.data['paths']}
        result = self.memory.index(self.root, self.data['paths'])
        self.assertEqual(result['state'], 'ready')
        found = self.memory.query(self.root, 'Pagamentos')
        self.assertTrue(found['results'])
        self.assertLessEqual(len(found['results']), 5)
        self.assertEqual(found['project_id'], self.data['project_id'])
        for item in found['results']:
            self.assertEqual(item['revision'], hashlib.sha256(originals[item['path']]).hexdigest())
            self.assertIn(item['id'], self.data['ids'])
            self.assertLessEqual(len(item['excerpt']), 400)
        self.assertTrue(any(item['relations'] for item in found['results']))
        self.assertEqual(originals, {p: (self.root / p).read_bytes() for p in originals})
        self.assertEqual(self.git('ls-files', '--', 'vault/local', '.operacao-local/memory').stdout, b'')
        self.assertEqual(self.git('check-ignore', '--quiet', '.operacao-local/memory/selection.json').returncode, 0)

    def test_no_selection_only_offers_navigation(self):
        result = self.memory.query(self.root, 'Pagamentos')
        self.assertEqual(result['results'], [])
        self.assertEqual(result['index_state'], 'missing')
        self.assertIn('vault/index.md', result['navigation'])
        self.assertFalse((self.root / '.operacao-local/memory').exists())

    def test_equal_titles_are_not_merged_and_other_project_is_excluded(self):
        p = self.root / self.data['paths'][1]
        p.write_text(p.read_text(encoding='utf-8').replace('Pagamentos Portal', 'Pagamentos API'), encoding='utf-8')
        other = self.root.parent / 'other'
        other_data = seed(other, OTHER)
        snap = self.memory.snapshot(self.root, self.data['paths'])
        self.assertEqual(len(snap['notes']), 5)
        self.assertEqual(len({n['id'] for n in snap['notes']}), 5)
        with self.assertRaises(ValueError):
            self.memory.index(self.root, ['../other/' + other_data['paths'][0]])
        self.memory.index(self.root, self.data['paths'])
        hits = self.memory.query(self.root, 'Pagamentos API')['results']
        self.assertTrue(set(self.data['ids'][:2]).issubset({h['id'] for h in hits}))
        self.assertFalse(set(other_data['ids']) & {h['id'] for h in hits})

    def test_invalid_files_duplicate_uuid_and_corpus_limits(self):
        bad = self.root / 'vault/local/bad.md'
        for raw in (b'\xff', b'no metadata', b'x' * (256 * 1024 + 1)):
            bad.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.memory.index(self.root, ['vault/local/bad.md'])
        for path in ('.env', 'vault/local', '../outside.md'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.memory.index(self.root, [path])
        bad.write_bytes((self.root / self.data['paths'][0]).read_bytes())
        with self.assertRaises(ValueError):
            self.memory.index(self.root, [self.data['paths'][0], 'vault/local/bad.md'])
        with self.assertRaises(ValueError):
            self.memory.index(self.root, [f'vault/local/{i}.md' for i in range(101)])
        self.assertFalse((self.root / '.operacao-local/memory/selection.json').exists())

    def test_git_tracking_is_rejected_before_copying_content(self):
        state = self.root / '.operacao-local/memory/foreign.json'
        state.parent.mkdir(parents=True)
        state.write_text('{}')
        self.git('add', '-f', '--', '.operacao-local/memory/foreign.json')
        with self.assertRaises(ValueError):
            self.memory.index(self.root, self.data['paths'])
        self.assertFalse((state.parent / 'selection.json').exists())
        self.assertEqual(state.read_text(), '{}')

    def test_negated_ignore_in_parent_repository_is_repaired(self):
        nested = self.root / 'nested'
        data = seed(nested)
        (nested / '.gitignore').write_text('/.operacao-local/memory/\n!/.operacao-local/memory/\n')
        self.memory.index(nested, data['paths'])
        result = self.git('check-ignore', '--quiet', '--', 'nested/.operacao-local/memory/selection.json', check=False)
        self.assertEqual(result.returncode, 0)

    def test_hardlink_and_symlink_are_rejected(self):
        source = self.root / self.data['paths'][0]
        alias = self.root / 'vault/local/hard.md'
        os.link(source, alias)
        with self.assertRaises(ValueError):
            self.memory.index(self.root, ['vault/local/hard.md'])
        alias.unlink()
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest('Host cannot create symlinks; hardlink boundary was checked.')
        with self.assertRaises(ValueError):
            self.memory.index(self.root, ['vault/local/hard.md'])
        self.assertFalse((self.root / '.operacao-local/memory/selection.json').exists())

    def test_wiki_and_reference_links_preserve_evidence(self):
        source = self.root / self.data['paths'][0]
        with source.open('a', encoding='utf-8') as out:
            out.write('\n[[local/demo/portal]]\n[prova][pub]\n[pub]: release.md\n')
        snap = self.memory.snapshot(self.root, self.data['paths'])
        relations = [r for r in snap['relations'] if r['source_id'] == self.data['ids'][0]]
        self.assertIn(self.data['ids'][1], [r['target_id'] for r in relations])
        for relation in relations:
            self.assertIn(relation['quote'], source.read_text(encoding='utf-8'))
            self.assertEqual(relation['origin'], 'markdown_link')

    def test_stale_and_removed_notes_fall_back_to_current_markdown(self):
        self.memory.index(self.root, self.data['paths'])
        path = self.root / self.data['paths'][0]
        with path.open('a', encoding='utf-8') as out:
            out.write('\nNova evidência.\n')
        (self.root / self.data['paths'][1]).unlink()
        result = self.memory.query(self.root, 'Pagamentos')
        self.assertEqual(result['index_state'], 'stale')
        self.assertEqual(result['provider'], 'markdown')
        self.assertNotIn(self.data['paths'][1], [r['path'] for r in result['results']])
        for hit in result['results']:
            self.assertEqual(hit['revision'], hashlib.sha256((self.root / hit['path']).read_bytes()).hexdigest())

    def test_query_limits_and_unmatched_terms(self):
        self.memory.index(self.root, self.data['paths'])
        for question, limit in (('', 5), ('x' * 513, 5), ('API', 6), ('API', 0)):
            with self.assertRaises(ValueError):
                self.memory.query(self.root, question, limit)
        self.assertEqual(self.memory.query(self.root, 'NO_MATCH_SENTINEL')['results'], [])


if __name__ == '__main__':
    unittest.main()
