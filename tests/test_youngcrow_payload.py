"""Check the youngcrow package exposes the scripts and requirements it installs."""
from pathlib import Path
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import youngcrow  # noqa: E402
from youngcrow.payload import PAYLOAD, payload_root  # noqa: E402


class PayloadTests(unittest.TestCase):
    def test_payload_lists_core_files_only(self):
        self.assertIn('scripts/vault.py', PAYLOAD)
        self.assertIn('scripts/adoption_acl.ps1', PAYLOAD)
        self.assertIn('requirements/graphify.txt', PAYLOAD)
        self.assertFalse([p for p in PAYLOAD if p.startswith('scripts/mission')])

    def test_every_payload_file_exists(self):
        root = payload_root()
        self.assertEqual([p for p in PAYLOAD if not (root / p).is_file()], [])

    def test_wheel_force_includes_exactly_the_payload(self):
        config = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        included = config['tool']['hatch']['build']['targets']['wheel']['force-include']
        self.assertEqual(set(included), set(PAYLOAD))
        self.assertEqual({src: dst for src, dst in included.items() if dst != f'youngcrow/payload/{src}'}, {})

    def test_version(self):
        self.assertEqual(youngcrow.__version__, '0.1.0.dev0')


if __name__ == '__main__':
    unittest.main()
