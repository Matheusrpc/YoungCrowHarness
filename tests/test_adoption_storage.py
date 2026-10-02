"""Real disposable filesystem proofs; no user repositories or credentials."""
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class StorageFixture(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('adoption_fs'), 'adoption storage not implemented')
        self.fs = importlib.import_module('adoption_fs')
        self.temp = tempfile.TemporaryDirectory(prefix='youngcrow-adoption-')
        self.addCleanup(self.temp.cleanup)
        self.sandbox = Path(self.temp.name).resolve()
        self.project = self.sandbox / 'project with spaces'
        self.project.mkdir()
        self.base = self.sandbox / 'backups'
        self.fs.validate_storage(self.project, self.base, create=True)
        self.copy = self.base / 'copy'

    def write(self, name, data):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0')
        return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], env=env,
                                       stderr=subprocess.PIPE)

    def seed_dirty_git(self):
        self.git('init', '-q', str(self.project))
        self.write('tracked.txt', b'commit\n')
        self.git('-C', str(self.project), 'add', '.')
        self.git('-C', str(self.project), '-c', 'user.name=Test', '-c',
                 'user.email=test@example.invalid', 'commit', '-qm', 'initial')
        self.write('tracked.txt', b'staged\n')
        self.git('-C', str(self.project), 'add', 'tracked.txt')
        self.write('tracked.txt', b'unstaged\n')
        self.write('.gitignore', b'.env\n')
        self.write('.env', b'TOKEN=SYNTHETIC_ONLY\n')
        self.write('new file ç.bin', b'\x00\xff')
        (self.project / 'empty').mkdir()


class StorageTests(StorageFixture):
    def test_snapshot_keeps_dirty_git_ignored_bytes_and_empty_directories(self):
        self.seed_dirty_git()
        before = self.fs.inspect_tree(self.project)
        self.fs.copy_verified(self.project, self.copy, before)
        self.assertEqual(self.fs.tree_digest(self.fs.inspect_tree(self.copy)), self.fs.tree_digest(before))
        self.assertEqual((self.copy / '.git/index').read_bytes(), (self.project / '.git/index').read_bytes())
        self.assertEqual((self.copy / '.env').read_bytes(), b'TOKEN=SYNTHETIC_ONLY\n')
        self.assertEqual((self.copy / 'tracked.txt').read_bytes(), b'unstaged\n')
        self.assertTrue((self.copy / 'empty').is_dir())
        self.assertEqual(self.git('-C', str(self.copy), 'show', ':tracked.txt'), b'staged\n')
        self.assertEqual(self.git('-C', str(self.copy), 'show', 'HEAD:tracked.txt'), b'commit\n')
        self.fs.inspect_permissions(self.copy, role='snapshot')

    def test_absence_is_preserved_without_creating_a_fake_tree(self):
        missing = self.sandbox / 'absent'
        initial = self.fs.inspect_tree(missing)
        self.assertFalse(initial['exists'])
        self.fs.copy_verified(missing, self.copy, initial)
        self.assertFalse(self.copy.exists())
        self.assertFalse(missing.exists())

    def test_refuses_existing_copy_and_changed_source(self):
        self.write('app', b'initial')
        initial = self.fs.inspect_tree(self.project)
        self.write('app', b'changed')
        with self.assertRaisesRegex(ValueError, 'source_changed'):
            self.fs.copy_verified(self.project, self.copy, initial)
        self.assertFalse(self.copy.exists())
        self.copy.mkdir()
        (self.copy / 'sentinel').write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.fs.copy_verified(self.project, self.copy, self.fs.inspect_tree(self.project))
        self.assertEqual((self.copy / 'sentinel').read_bytes(), b'keep')

    def test_rejects_storage_inside_git_even_with_ceiling_override(self):
        self.git('init', '-q', str(self.project))
        for base in (self.project / 'backups', self.project, self.sandbox):
            with self.subTest(base=base), self.assertRaises(ValueError):
                self.fs.validate_storage(self.project, base, create=True)
        other = self.sandbox / 'other'
        other.mkdir()
        self.git('init', '-q', str(other))
        with patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(other)}):
            with self.assertRaisesRegex(ValueError, 'storage_in_git'):
                self.fs.validate_storage(self.project, other / 'nested' / 'backups', create=True)
        self.assertFalse((other / 'nested').exists())

    def test_hardlinks_are_rejected(self):
        self.write('original', b'preserve')
        os.link(self.project / 'original', self.project / 'alias')
        with self.assertRaisesRegex(ValueError, 'unsupported_entry'):
            self.fs.inspect_tree(self.project)

    def test_link_is_rejected_without_following_it(self):
        target = self.sandbox / 'outside'
        target.mkdir()
        link = self.project / 'link'
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        else:
            link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'unsupported_entry'):
            self.fs.inspect_tree(self.project)

    @unittest.skipIf(os.name == 'nt', 'POSIX FIFO and mode proof')
    def test_fifo_and_extended_attributes_are_rejected(self):
        os.mkfifo(self.project / 'pipe')
        with self.assertRaisesRegex(ValueError, 'unsupported_entry'):
            self.fs.inspect_tree(self.project)
        (self.project / 'pipe').unlink()
        self.write('app', b'content')
        os.setxattr(self.project / 'app', 'user.youngcrow_test', b'metadata')
        with self.assertRaisesRegex(ValueError, 'unsupported_permissions'):
            self.fs.inspect_permissions(self.project, role='project')

    def test_limits_and_mutation_during_streaming(self):
        self.write('large', b'a' * (2 * 1024 * 1024))
        with patch.object(self.fs, 'MAX_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'inventory_limit'):
                self.fs.inspect_tree(self.project)
        with patch.object(self.fs, 'MAX_ENTRIES', 0):
            with self.assertRaisesRegex(ValueError, 'inventory_limit'):
                self.fs.inspect_tree(self.project)
        original = self.fs.hash_file
        def changing(path):
            digest = original(path)
            if path.name == 'large':
                path.write_bytes(b'changed')
            return digest
        with patch.object(self.fs, 'hash_file', changing):
            with self.assertRaisesRegex(ValueError, 'source_changed'):
                self.fs.inspect_tree(self.project)

    def test_untrusted_inventory_paths_cannot_escape(self):
        self.write('file', b'data')
        for path in ('../escape', '/escape', 'C:/escape', 'a\\..\\escape', 'bad\x00name'):
            inventory = self.fs.inspect_tree(self.project)
            inventory['entries'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.fs.copy_verified(self.project, self.copy, inventory)
        self.assertFalse((self.sandbox / 'escape').exists())

    def test_private_storage_and_permission_round_trip(self):
        self.write('run', b'executable')
        if os.name != 'nt':
            (self.project / 'run').chmod(0o751)
        policy = self.fs.inspect_permissions(self.project, role='project')
        original = self.fs.inspect_tree(self.project)
        self.fs.copy_verified(self.project, self.copy, original)
        self.fs.inspect_permissions(self.copy, role='snapshot')
        restored = self.sandbox / 'restored'
        os.rename(self.copy, restored)
        self.fs.restore_permissions(restored, original, policy)
        self.assertEqual(self.fs.inspect_permissions(restored, role='project'), policy)
        self.assertEqual(self.fs.tree_digest(self.fs.inspect_tree(restored)), self.fs.tree_digest(original))

    @unittest.skipUnless(os.name == 'nt', 'Windows ADS proof')
    def test_alternate_data_stream_is_refused(self):
        self.write('file', b'data')
        Path(str(self.project / 'file') + ':extra').write_bytes(b'SYNTHETIC_ONLY')
        with self.assertRaisesRegex(ValueError, 'unsupported_permissions'):
            self.fs.inspect_permissions(self.project, role='project')

    @unittest.skipUnless(os.name == 'nt', 'Windows directory ADS proof')
    def test_directory_stream_is_not_silently_omitted(self):
        Path(str(self.project) + ':extra').write_bytes(b'SYNTHETIC_ONLY')
        with self.assertRaisesRegex(ValueError, 'unsupported_permissions'):
            self.fs.inspect_permissions(self.project, role='project')

    def test_profile_rejects_custom_permissions_without_changing_them(self):
        self.write('file', b'data')
        if os.name == 'nt':
            self.fs.protect_for_storage(self.project)
        else:
            (self.project / 'file').chmod(0o4755)
        with self.assertRaisesRegex(ValueError, 'unsupported_permissions'):
            self.fs.inspect_permissions(self.project, role='project')
        self.assertEqual((self.project / 'file').read_bytes(), b'data')


if __name__ == '__main__':
    unittest.main()
