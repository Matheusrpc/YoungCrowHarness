"""Exercise the read-only vault check against real notes and generated projects."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/vault.py'


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def note(self, relative, body='', **overrides):
        fields = dict(id=relative, type='index' if relative.endswith('index.md') else 'note',
                      title='Example', origin='test', updated='2026-10-01', index='index.md')
        fields.update(overrides)
        path = self.root / 'vault' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\n' + ''.join(f'{k}: {json.dumps(v)}\n' for k, v in fields.items())
                        + '---\n\n' + body, encoding='utf-8')
        return path

    def check(self, expected=1):
        result = subprocess.run([sys.executable, str(SCRIPT), 'check', '--json'],
                                cwd=self.root, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        self.assertTrue(result.stdout.startswith('{'), result.stderr)
        return json.loads(result.stdout)

    def codes(self, result):
        return {issue['code'] for issue in result['issues']}

    def test_template_vault_is_valid_without_project_identity(self):
        shutil.copytree(ROOT / 'vault', self.root / 'vault', ignore=shutil.ignore_patterns('local', 'project.json'))
        shutil.copytree(ROOT / 'skills', self.root / 'skills')
        result = self.check(0)
        self.assertEqual(result['notes_checked'], 3)
        self.assertEqual(result['issues'], [])

    def test_private_root_is_optional_independent_and_can_link_public_notes(self):
        self.note('index.md')
        self.note('local/index.md', '[Sources](sources/index.md) [Vault](../index.md)')
        self.note('local/sources/index.md', '[Note](note.md)', index='../index.md')
        self.note('local/sources/note.md')
        self.assertEqual(self.check(0)['notes_checked'], 4)

    def test_public_links_to_private_locations_fail_even_when_missing(self):
        self.note('index.md', '[Private](local/index.md) [Receipt](../.operacao-local/docling/receipt.json)')
        result = self.check()
        self.assertIn('private_reference', self.codes(result))
        self.assertNotIn('receipt.json', json.dumps(result))

    def test_public_parent_cannot_be_a_private_index(self):
        self.note('index.md', '[Note](note.md)')
        self.note('note.md', index='local/index.md')
        self.note('local/index.md', '[Public](../note.md)')
        self.assertIn('private_reference', self.codes(self.check()))

    def test_public_capability_bundle_link_is_private_even_if_missing(self):
        self.note('index.md', '[Review](../.operacao-local/capabilities/reviews/private.json)')
        result = self.check()
        self.assertEqual(self.codes(result), {'private_reference'})
        self.assertNotIn('private.json', json.dumps(result))

    def test_file_uri_is_rejected_instead_of_treated_as_remote(self):
        self.note('index.md', '[Local file](file:///private.txt)')
        self.assertTrue(self.check()['issues'])

    def test_generated_product_feature_and_integration_are_valid_and_unchanged(self):
        for script, args in (
            ('personalize.py', ['init', '--mode', 'existing', '--run', 'discovery']),
            ('personalize.py', ['feature', '--slug', 'bookings', '--run', 'first']),
            ('integrations.py', ['init', '--provider', 'example', '--service', 'api', '--run', 'first']),
        ):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                                    cwd=self.root, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.check(0)['notes_checked'], 19)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                  for p in self.root.rglob('*') if p.is_file()})

    def test_duplicate_identity_and_missing_metadata_are_reported_without_content(self):
        self.note('index.md', '[A](a.md) [B](b.md) [C](c.md)')
        self.note('a.md', id='same')
        self.note('b.md', id='same')
        path = self.note('c.md')
        path.write_text('# Private sample: do-not-print-this-value\n', encoding='utf-8')
        result = self.check()
        self.assertTrue({'duplicate_id', 'metadata'} <= self.codes(result))
        self.assertNotIn('do-not-print-this-value', json.dumps(result))

    def test_broken_file_links_fail_but_examples_and_remote_urls_are_ignored(self):
        self.note('index.md', '''[Note](note.md) [External](https://example.invalid/no-network)
`[example](not-a-file.md)`
```md
[example](another-example.md)
```
<!-- [hidden](hidden.md) -->
''')
        path = self.note('note.md', '[Lost](missing.md#section)')
        result = self.check()
        self.assertEqual(self.codes(result), {'broken_link'})
        self.assertEqual(result['issues'][0]['path'], 'vault/note.md')
        path.write_text(path.read_text(encoding='utf-8').replace('missing.md#section', 'index.md#section'), encoding='utf-8')
        self.check(0)

    def test_unlisted_note_and_unreachable_island_fail(self):
        self.note('index.md')
        self.note('orphan.md')
        self.note('island/index.md', '[Note](note.md)', index='../index.md')
        self.note('island/note.md')
        result = self.check()
        self.assertTrue({'missing_index_link', 'unreachable'} <= self.codes(result))
        unreachable = {x['path'] for x in result['issues'] if x['code'] == 'unreachable'}
        self.assertEqual(unreachable, {'vault/orphan.md', 'vault/island/index.md', 'vault/island/note.md'})

    def test_parent_cycles_and_non_index_parent_are_rejected(self):
        self.note('index.md', '[A](a/index.md) [B](b/index.md) [Note](note.md)')
        self.note('a/index.md', '[B](../b/index.md)', index='../b/index.md')
        self.note('b/index.md', '[A](../a/index.md)', index='../a/index.md')
        self.note('note.md', index='a/index.md')
        self.note('bad.md', index='note.md')
        codes = self.codes(self.check())
        self.assertTrue({'index_cycle', 'invalid_index'} <= codes)

    def test_relative_encoded_angle_reference_and_wiki_links(self):
        self.note('index.md', '''[One](<notes/a note.md>) [Two](notes/b%20note.md "Title")
[Ref][record]
[record]: notes/c.md
[[notes/d|Wiki alias]] [[unique]]
[Code](../app.py#L1)
''')
        for name in ('a note', 'b note', 'c', 'd', 'unique'):
            self.note(f'notes/{name}.md', index='../index.md')
        (self.root / 'app.py').write_text('pass\n', encoding='utf-8')
        self.check(0)

    def test_ambiguous_wiki_link_does_not_silently_choose_a_note(self):
        self.note('index.md', '[A](a/note.md) [B](b/note.md) [[note]]')
        self.note('a/note.md', index='../index.md')
        self.note('b/note.md', index='../index.md')
        self.assertIn('ambiguous_link', self.codes(self.check()))

    def test_missing_vault_and_missing_root_index_fail_without_creating_files(self):
        self.assertIn('missing_vault', self.codes(self.check()))
        self.assertEqual(list(self.root.iterdir()), [])
        self.note('note.md')
        self.assertIn('missing_root_index', self.codes(self.check()))

    def test_invalid_metadata_is_reported_without_traceback(self):
        self.note('index.md', '[Note](note.md)')
        path = self.note('note.md', updated='yesterday', title='')
        path.write_text(path.read_text(encoding='utf-8').replace('type: "note"', 'type: [note]'), encoding='utf-8')
        self.assertIn('metadata', self.codes(self.check()))

    def test_link_outside_project_and_hardlinked_note_are_rejected(self):
        self.note('index.md', '[Outside](../../outside.md) [Hardlink](linked.md)')
        outside = self.root / 'private.md'
        outside.write_text('do-not-read-or-print\n', encoding='utf-8')
        os.link(outside, self.root / 'vault/linked.md')
        result = self.check()
        self.assertTrue({'unsafe_path', 'unsafe_link'} <= self.codes(result))
        self.assertNotIn('do-not-read-or-print', json.dumps(result))

    def test_symlink_directory_is_not_followed(self):
        self.note('index.md', '[Linked](linked/index.md)')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'index.md').write_text('private-outside-content', encoding='utf-8')
        try:
            (self.root / 'vault/linked').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable; exercised in Linux CI')
            raise
        result = self.check()
        self.assertIn('unsafe_path', self.codes(result))
        self.assertEqual(result['notes_checked'], 1)
        self.assertNotIn('private-outside-content', json.dumps(result))

    def test_special_file_is_rejected_before_reading(self):
        self.note('index.md', '[Pipe](pipe.md)')
        pipe = self.note('pipe.md')
        # Emulate a FIFO's lstat on Windows too; reading a real FIFO would block.
        with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
            import vault
        original = Path.lstat
        def special(path, *args, **kwargs):
            if path == pipe:
                return SimpleNamespace(st_mode=stat.S_IFIFO, st_nlink=1)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', special):
            result = vault.check(self.root)
        self.assertIn('unsafe_path', self.codes(result))
        self.assertEqual(result['notes_checked'], 1)

    def test_junction_root_is_rejected_on_windows(self):
        if os.name != 'nt':
            self.skipTest('Windows junction behavior')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'index.md').write_text('private-junction-content', encoding='utf-8')
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.root / 'vault'), str(outside)],
                       check=True, capture_output=True)
        result = self.check()
        self.assertIn('unsafe_path', self.codes(result))
        self.assertEqual(result['notes_checked'], 0)
        self.assertNotIn('private-junction-content', json.dumps(result))

    def test_comment_only_metadata_is_not_a_value(self):
        path = self.note('index.md')
        path.write_text(path.read_text(encoding='utf-8').replace('title: "Example"', 'title: # pending'), encoding='utf-8')
        self.assertIn('metadata', self.codes(self.check()))

    def test_nested_list_links_are_checked_and_count_toward_navigation(self):
        index = self.note('index.md', '- Notes\n    - [Missing](missing.md)\n')
        self.assertIn('broken_link', self.codes(self.check()))
        self.note('note.md')
        index.write_text(index.read_text(encoding='utf-8').replace('missing.md', 'note.md'), encoding='utf-8')
        self.check(0)

    def test_malformed_escaped_link_does_not_hang(self):
        self.note('index.md', '[broken](' + '\\' * 80 + ' ')
        try:
            result = subprocess.run([sys.executable, str(SCRIPT), 'check', '--json'],
                                    cwd=self.root, capture_output=True, encoding='utf-8', timeout=3)
        except subprocess.TimeoutExpired:
            self.fail('Malformed Markdown link must not cause unbounded parsing time.')
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
