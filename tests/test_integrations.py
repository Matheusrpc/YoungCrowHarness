"""Vault behavior, independent of clients, network or provider credentials."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/integrations.py'


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, command='init', provider='example', service='payments', run='first'):
        args = [sys.executable, str(SCRIPT), command, '--provider', provider, '--service', service]
        if command == 'init':
            args += ['--run', run]
        return subprocess.run(args, cwd=self.root, capture_output=True, text=True, encoding='utf-8')

    def test_create_revisit_export_and_revision(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        vault = self.root / 'vault'
        before = {p.relative_to(vault): p.read_bytes() for p in vault.rglob('*') if p.is_file()}
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(before, {p.relative_to(vault): p.read_bytes() for p in vault.rglob('*') if p.is_file()})
        record = vault / 'integrations/example/payments/index.md'
        self.assertIn('sources.md', record.read_text())
        self.assertIn('runs/first.md', record.read_text())
        export = self.run_cli('export')
        self.assertEqual(export.returncode, 0, export.stderr)
        data = json.loads(export.stdout)
        self.assertEqual(data['sync_state'], 'pending')
        self.assertEqual(len(data['notes']), 5)
        self.assertEqual(len({n['id'] for n in data['notes']}), 5)
        note = next(n for n in data['notes'] if n['path'].endswith('/index.md'))
        self.assertEqual(note['revision'], hashlib.sha256(record.read_bytes()).hexdigest())
        record.write_text(record.read_text() + '\nDevelopment verified locally.\n', encoding='utf-8')
        newer = json.loads(self.run_cli('export').stdout)
        self.assertNotEqual(note['revision'], next(n['revision'] for n in newer['notes'] if n['id'] == note['id']))

    def test_preserve_custom_index_and_multiple_runs(self):
        index = self.root / 'vault/index.md'
        index.parent.mkdir()
        original = b'# Meu vault\r\n\r\nConhecimento existente.\r\n'
        index.write_bytes(original)
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertTrue(index.read_bytes().startswith(original))
        self.assertEqual(self.run_cli(run='second').returncode, 0)
        text = (index.parent / 'integrations/example/payments/index.md').read_text()
        self.assertEqual(text.count('(runs/first.md)'), 1)
        self.assertEqual(text.count('(runs/second.md)'), 1)

    def test_custom_service_index_gains_missing_links(self):
        index = self.root / 'vault/integrations/example/payments/index.md'
        index.parent.mkdir(parents=True)
        original = b'# Existing product knowledge\r\n'
        index.write_bytes(original)
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertTrue(index.read_bytes().startswith(original))
        for target in ('../index.md', 'sources.md', 'implementation.md', 'operations.md', 'runs/first.md'):
            self.assertIn('](' + target + ')', index.read_text())

    def test_windows_reparse_rejected_without_is_junction(self):
        vault = self.root / 'vault'
        vault.mkdir()
        namespace = runpy.run_path(str(SCRIPT))
        original = Path.lstat

        def reparse_metadata(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path == vault:
                return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
            return result

        # Model Windows junction attributes while the Python 3.12 helper is absent.
        with patch.object(Path, 'lstat', reparse_metadata), patch.object(Path, 'is_junction', return_value=False, create=True):
            with self.assertRaises(ValueError):
                namespace['check_path'](self.root, 'vault/index.md')

    def test_invalid_names_and_path_conflicts_are_read_only(self):
        for provider in ('../escape', 'UPPER', 'a/b', 'con', 'aux', 'nul', 'com1'):
            self.assertNotEqual(self.run_cli(provider=provider).returncode, 0)
            self.assertFalse((self.root / 'vault').exists())
        conflict = self.root / 'vault/integrations/example/payments/sources.md'
        conflict.mkdir(parents=True)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse((self.root / 'vault/project.json').exists())

    def test_linked_vault_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.root / 'vault').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable; exercised in Linux CI')
            raise
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_project_identity_isolation_and_missing_export(self):
        self.assertNotEqual(self.run_cli('export').returncode, 0)
        self.assertFalse((self.root / 'vault').exists())
        self.assertEqual(self.run_cli().returncode, 0)
        first = json.loads(self.run_cli('export').stdout)
        second_root = self.root / 'other-project'
        second_root.mkdir()
        self.root = second_root
        self.assertEqual(self.run_cli().returncode, 0)
        second = json.loads(self.run_cli('export').stdout)
        self.assertNotEqual(first['project_id'], second['project_id'])
        self.assertTrue(set(n['id'] for n in first['notes']).isdisjoint(n['id'] for n in second['notes']))

    def test_note_identity_survives_rename_and_duplicate_is_rejected(self):
        self.assertEqual(self.run_cli().returncode, 0)
        first = json.loads(self.run_cli('export').stdout)
        original = next(n for n in first['notes'] if n['path'].endswith('/runs/first.md'))
        path = self.root / original['path']
        renamed = path.with_name('renamed.md')
        path.rename(renamed)
        second = json.loads(self.run_cli('export').stdout)
        self.assertEqual(original['id'], next(n['id'] for n in second['notes'] if n['path'].endswith('/renamed.md')))
        path.write_bytes(renamed.read_bytes())
        result = self.run_cli('export')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
