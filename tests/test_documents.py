"""Document storage tests use real Git and isolated project files."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vault


class StorageTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATHEXT')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CEILING_DIRECTORIES=str(self.root.parent))
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.git('init', '-q')
        self.store = importlib.import_module('document_store')

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                              capture_output=True, check=check, timeout=10)

    def test_private_storage_is_ignored_and_vault_valid(self):
        identity = self.store.prepare_storage(self.root)
        uuid.UUID(identity)
        for rel in ('vault/local/index.md', '.operacao-local/docling/receipt.json'):
            self.assertEqual(self.git('check-ignore', '--quiet', '--', rel, check=False).returncode, 0)
        self.assertEqual(vault.check(self.root)['issues'], [])
        original = (self.root / 'vault/local/index.md').read_bytes()
        self.assertEqual(self.store.prepare_storage(self.root), identity)
        self.assertEqual((self.root / 'vault/local/index.md').read_bytes(), original)

    def test_tracked_private_file_refuses_before_changing_anything(self):
        target = self.root / 'vault/local/private.md'
        target.parent.mkdir(parents=True)
        target.write_text('private fixture', encoding='utf-8')
        self.git('add', '-f', '--', 'vault/local/private.md')
        with self.assertRaises(ValueError):
            self.store.prepare_storage(self.root)
        self.assertFalse((self.root / '.gitignore').exists())
        self.assertFalse((self.root / 'vault/project.json').exists())
        self.assertEqual(target.read_text(), 'private fixture')

    def test_parent_repository_and_negated_rule(self):
        self.root = self.root / 'nested'
        self.root.mkdir()
        ignore = self.root / '.gitignore'
        ignore.write_text('# preserve\n/vault/local/\n!/vault/local/', encoding='utf-8')
        self.store.prepare_storage(self.root)
        self.assertTrue(ignore.read_text().startswith('# preserve\n'))
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/index.md', check=False).returncode, 0)
        self.git('add', '--', '.')
        self.assertNotIn(b'vault/local/', self.git('ls-files', '-z').stdout)

    def test_nested_ignore_cannot_expose_an_existing_private_note(self):
        folder = self.root / 'vault/local'
        folder.mkdir(parents=True)
        (folder / '.gitignore').write_text('!*.md\n', encoding='utf-8')
        (folder / 'private.md').write_text('private', encoding='utf-8')
        self.store.prepare_storage(self.root)
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/private.md', check=False).returncode, 0)

    def test_without_git_rules_protect_after_git_init(self):
        self.root = Path(self.temp.name) / 'not yet git'
        self.root.mkdir()
        self.store.prepare_storage(self.root)
        self.git('init', '-q')
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/index.md', check=False).returncode, 0)

    def test_wrong_directory_type_and_hardlink_refuse_without_writes(self):
        for rel in ('vault', '.gitignore'):
            with self.subTest(rel=rel):
                root = self.root / rel.replace('.', 'dot')
                root.mkdir()
                if rel == 'vault':
                    (root / rel).write_text('preserve')
                else:
                    outside = root / 'shared'
                    outside.write_text('preserve')
                    os.link(outside, root / rel)
                with self.assertRaises(ValueError):
                    self.store.prepare_storage(root)
                self.assertFalse((root / 'vault/project.json').exists())

    def test_junction_private_root_is_rejected(self):
        if os.name != 'nt':
            self.skipTest('Windows junction')
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'vault').mkdir()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.root / 'vault/local'), str(outside)],
                       check=True, capture_output=True)
        with self.assertRaises(ValueError):
            self.store.prepare_storage(self.root)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
