"""Persistent onboarding without clients, network, or deployment."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PersonalizeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/personalize.py'), *args],
                              cwd=self.root, capture_output=True, encoding='utf-8')

    def snapshot(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_new_then_feature_and_repeat_preserves_notes(self):
        result = self.run_cli('init', '--mode', 'new', '--run', 'first')
        self.assertEqual(result.returncode, 0, result.stderr)
        profile = self.root / 'vault/product/profile.md'
        profile.write_text(profile.read_text(encoding='utf-8') + '\nAudience: solo barbers.\n', encoding='utf-8')
        first = self.snapshot()
        self.assertEqual(self.run_cli('init', '--mode', 'new', '--run', 'first').returncode, 0)
        self.assertEqual(first, self.snapshot())
        result = self.run_cli('feature', '--slug', 'bookings', '--run', 'slice-one')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'vault/features/bookings/delivery.md').exists())
        second = self.snapshot()
        self.assertEqual(self.run_cli('feature', '--slug', 'bookings', '--run', 'slice-one').returncode, 0)
        self.assertEqual(second, self.snapshot())
        identities = []
        for path in (self.root / 'vault').rglob('*.md'):
            content = path.read_text(encoding='utf-8')
            identities.append(re.search(r'^id: (.+)$', content, re.MULTILINE)[1])
            for target in re.findall(r'\]\(([^)]+)\)', content):
                self.assertTrue((path.parent / target).exists(), (path, target))
        self.assertEqual(len(identities), len(set(identities)))

    def test_existing_audit_preserves_guides_and_mode_conflict_is_read_only(self):
        (self.root / 'AGENTS.md').write_bytes(b'# My instructions\r\n')
        self.assertEqual(self.run_cli('init', '--mode', 'existing', '--run', 'audit').returncode, 0)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), b'# My instructions\r\n')
        self.assertTrue((self.root / 'vault/product/audit.md').exists())
        before = self.snapshot()
        self.assertNotEqual(self.run_cli('init', '--mode', 'new', '--run', 'second').returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_reuses_integration_project_identity_and_custom_root(self):
        (self.root / 'vault').mkdir()
        (self.root / 'vault/index.md').write_bytes(b'# Keep this index\r\n')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/integrations.py'), 'init',
                                 '--provider', 'example', '--service', 'api', '--run', 'first'],
                                cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0)
        before = (self.root / 'vault/project.json').read_bytes()
        self.assertEqual(self.run_cli('init', '--mode', 'existing', '--run', 'adoption').returncode, 0)
        self.assertEqual(before, (self.root / 'vault/project.json').read_bytes())
        self.assertTrue((self.root / 'vault/index.md').read_bytes().startswith(b'# Keep this index\r\n'))

    def test_bad_paths_and_missing_profile_leave_no_writes(self):
        self.assertNotEqual(self.run_cli('feature', '--slug', 'bookings', '--run', 'first').returncode, 0)
        self.assertEqual(self.snapshot(), {})
        for value in ('../escape', 'con', 'with space'):
            self.assertNotEqual(self.run_cli('init', '--mode', 'new', '--run', value).returncode, 0)
            self.assertEqual(self.snapshot(), {})
        conflict = self.root / 'vault/product/interviews/first.md'
        conflict.mkdir(parents=True)
        self.assertNotEqual(self.run_cli('init', '--mode', 'new', '--run', 'first').returncode, 0)
        self.assertEqual(self.snapshot(), {})

    def test_linked_feature_parent_is_rejected(self):
        self.assertEqual(self.run_cli('init', '--mode', 'new', '--run', 'first').returncode, 0)
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.root / 'vault/features/bookings').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable; exercised in Linux CI')
            raise
        self.assertNotEqual(self.run_cli('feature', '--slug', 'bookings', '--run', 'first').returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_hardlinked_index_is_rejected_before_writes(self):
        outside = self.root / 'outside.md'
        outside.write_bytes(b'# Private index\n')
        index = self.root / 'vault/index.md'
        index.parent.mkdir()
        os.link(outside, index)
        before = self.snapshot()
        self.assertNotEqual(self.run_cli('init', '--mode', 'new', '--run', 'first').returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_readonly_index_is_rejected_before_writes(self):
        index = self.root / 'vault/index.md'
        index.parent.mkdir()
        index.write_bytes(b'# Keep this index\n')
        before = self.snapshot()
        index.chmod(stat.S_IREAD)
        try:
            self.assertNotEqual(self.run_cli('init', '--mode', 'new', '--run', 'first').returncode, 0)
            self.assertEqual(before, self.snapshot())
        finally:
            index.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_previous_installed_helper_is_compatible(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        shutil.copy2(ROOT / 'scripts/personalize.py', scripts / 'personalize.py')
        helper = (ROOT / 'scripts/integrations.py').read_text(encoding='utf-8')
        # Signature and metadata of the helper shipped before personalizer.
        helper = helper.replace(", origin='youngcrow/integrations'", '')
        helper = helper.replace("'origin': origin", "'origin': 'youngcrow/integrations'")
        (scripts / 'integrations.py').write_text(helper, encoding='utf-8')
        result = subprocess.run([sys.executable, str(scripts / 'personalize.py'), 'init',
                                 '--mode', 'existing', '--run', 'first'], cwd=self.root,
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('origin: "youngcrow/personalizer"',
                      (self.root / 'vault/product/profile.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
