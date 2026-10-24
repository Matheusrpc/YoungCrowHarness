"""Check the manifest round trip and that safe_target refuses every path that could write outside."""
from pathlib import Path
from unittest import mock
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.manifest import (  # noqa: E402
    Manifest, UnsafePathError, load, safe_target, save, sha256_file,
)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'project'
        self.other = Path(tmp.name) / 'other'
        self.root.mkdir()
        self.other.mkdir()

    def link_youngcrow(self):
        try:
            os.symlink(self.other, self.root / '.youngcrow', target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')

    def test_round_trip(self):
        m = Manifest('0.1.0.dev0', 'both', 'en', 'light', {'a': 'x'}, ['a'], ['CLAUDE.md'])
        save(self.root, m)
        self.assertEqual(load(self.root), m)

    def test_missing_manifest_is_none(self):
        self.assertIsNone(load(self.root))

    def test_symlinked_component_refused(self):
        self.link_youngcrow()
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, '.youngcrow/VERSION')

    def test_symlinked_last_component_refused(self):
        (self.other / 'real.md').write_text('mine')
        try:
            os.symlink(self.other / 'real.md', self.root / 'CLAUDE.md')
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, 'CLAUDE.md')

    def test_escape_refused(self):
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, '../outside.txt')

    def test_dot_dot_inside_the_path_refused(self):
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, 'a/../b.txt')

    def test_absolute_path_refused(self):
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, str(self.other / 'x.txt'))

    def test_empty_path_refused(self):
        for relative in ('', '.'):
            with self.subTest(relative=relative), self.assertRaises(UnsafePathError):
                safe_target(self.root, relative)

    def test_file_where_a_directory_is_expected_refused(self):
        (self.root / '.youngcrow').write_text('not a directory')
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, '.youngcrow/VERSION')

    def test_directory_where_a_file_is_expected_refused(self):
        (self.root / 'CLAUDE.md').mkdir()
        with self.assertRaises(UnsafePathError):
            safe_target(self.root, 'CLAUDE.md')

    def test_junction_attribute_refused(self):
        (self.root / '.youngcrow').mkdir()
        real = Path.lstat

        def lstat(path):
            if path.name == '.youngcrow':
                return mock.Mock(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)
            return real(path)

        with mock.patch.object(Path, 'lstat', lstat), self.assertRaises(UnsafePathError):
            safe_target(self.root, '.youngcrow/VERSION')

    def test_missing_components_allowed_and_nothing_created(self):
        target = safe_target(self.root, '.youngcrow/scripts/vault.py')
        self.assertEqual(target, self.root / '.youngcrow' / 'scripts' / 'vault.py')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_file_and_directory_allowed(self):
        (self.root / '.youngcrow').mkdir()
        (self.root / '.youngcrow' / 'VERSION').write_text('0.1.0.dev0\n')
        self.assertEqual(safe_target(self.root, '.youngcrow/VERSION'), self.root / '.youngcrow' / 'VERSION')

    def test_sha256_file_matches_hashlib(self):
        data = b'harness\r\n' * 200000
        path = self.root / 'big.bin'
        path.write_bytes(data)
        self.assertEqual(sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_saved_json_has_schema_version_and_sorted_keys(self):
        save(self.root, Manifest('0.1.0.dev0', 'claude', 'pt', 'full', {'b': '2', 'a': '1'}, [], []))
        text = (self.root / '.youngcrow' / 'manifest.json').read_text(encoding='utf-8')
        data = json.loads(text)
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(list(data), sorted(data))
        self.assertEqual(list(data['files']), ['a', 'b'])
        self.assertTrue(text.endswith('\n'))

    def test_save_replaces_and_leaves_no_temp_file(self):
        save(self.root, Manifest('0.1.0.dev0', 'claude', 'en', 'light', {}, [], []))
        second = Manifest('0.1.0.dev0', 'codex', 'pt', 'full', {'a': 'x'}, ['a'], [])
        save(self.root, second)
        self.assertEqual(load(self.root), second)
        self.assertEqual([p.name for p in (self.root / '.youngcrow').iterdir()], ['manifest.json'])

    def test_failed_write_keeps_the_old_manifest_and_cleans_up(self):
        old = Manifest('0.1.0.dev0', 'claude', 'en', 'light', {}, [], [])
        save(self.root, old)
        with mock.patch('os.replace', side_effect=OSError('disk full')), self.assertRaises(OSError):
            save(self.root, Manifest('0.1.0.dev0', 'codex', 'pt', 'full', {}, [], []))
        self.assertEqual(load(self.root), old)
        self.assertEqual([p.name for p in (self.root / '.youngcrow').iterdir()], ['manifest.json'])

    def test_save_refuses_a_symlinked_directory_and_writes_nothing(self):
        self.link_youngcrow()
        with self.assertRaises(UnsafePathError):
            save(self.root, Manifest('0.1.0.dev0', 'claude', 'en', 'light', {}, [], []))
        self.assertEqual(list(self.other.iterdir()), [])

    def test_load_refuses_a_symlinked_directory(self):
        (self.other / 'manifest.json').write_text('{}')
        self.link_youngcrow()
        with self.assertRaises(UnsafePathError):
            load(self.root)

    def write_manifest(self, text):
        (self.root / '.youngcrow').mkdir()
        (self.root / '.youngcrow' / 'manifest.json').write_text(text, encoding='utf-8')

    def test_malformed_json_raises(self):
        self.write_manifest('{"schema_version": 1,')
        with self.assertRaises(ValueError):
            load(self.root)

    def test_wrong_schema_version_raises(self):
        save(self.root, Manifest('0.1.0.dev0', 'both', 'en', 'light', {}, [], []))
        path = self.root / '.youngcrow' / 'manifest.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['schema_version'] = 2
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            load(self.root)

    def test_missing_or_mistyped_field_raises(self):
        good = dict(schema_version=1, version='0.1.0.dev0', client='both', lang='en', rigor='light',
                    files={'a': 'x'}, created=['a'], edits=[])
        cases = {
            'not an object': [],
            'missing field': {k: v for k, v in good.items() if k != 'rigor'},
            'files not a dict': {**good, 'files': ['a']},
            'hash not a string': {**good, 'files': {'a': 1}},
            'created not a list': {**good, 'created': 'a'},
            'edits item not a string': {**good, 'edits': [1]},
            'client not a string': {**good, 'client': None},
        }
        for name, data in cases.items():
            with self.subTest(name):
                self.write_manifest(json.dumps(data))
                with self.assertRaises(ValueError):
                    load(self.root)
                (self.root / '.youngcrow' / 'manifest.json').unlink()
                (self.root / '.youngcrow').rmdir()


if __name__ == '__main__':
    unittest.main()
