"""Check the harness scripts work when run from `<project>/.youngcrow/scripts`, as `youngcrow init` installs them."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.install import init, undo  # noqa: E402
from youngcrow.payload import PAYLOAD  # noqa: E402

GUIDANCE = 'Textual source reference detected'
# The command each script answers without doing any work; the others take --help. A module with no
# command line of its own just runs its top level and exits.
NO_OP = {'scripts/docling_worker.py': ('versions',)}


class InstalledScriptsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'project'
        self.root.mkdir()

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes() if path.is_file() else None
                for path in sorted(self.root.rglob('*'))}

    def hook(self, script, prompt, cwd):
        payload = json.dumps({'prompt': prompt, 'cwd': str(cwd)})
        return subprocess.run([sys.executable, '-B', str(script)], cwd=cwd, input=payload,
                              capture_output=True, text=True)

    def test_vault_check_from_installed_scripts(self):
        init(self.root)
        run = subprocess.run([sys.executable, '-B', '.youngcrow/scripts/vault.py', 'check'], cwd=self.root,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('0 issues', run.stdout)

    def test_prompt_hook_uses_project_root_and_writes_nothing(self):
        init(self.root)
        before = self.snapshot()
        run = self.hook(self.root / '.youngcrow/scripts/source_prompt.py', 'read https://example.com/doc', self.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(GUIDANCE, run.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_prompt_hook_treats_project_vault_notes_as_memory(self):
        init(self.root)
        before = self.snapshot()
        note = self.root / 'vault' / 'decisions' / 'choice.md'
        run = self.hook(self.root / '.youngcrow/scripts/source_prompt.py', f'resume from {note}', self.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {})
        self.assertEqual(self.snapshot(), before)

    def test_running_the_installed_scripts_leaves_no_bytecode_and_undo_empties_the_project(self):
        init(self.root)
        # Bytecode on, as a person's Python has it: no -B, no PYTHONDONTWRITEBYTECODE, no cache prefix.
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX')}
        for rel in (rel for rel in PAYLOAD if rel.endswith('.py')):
            args = NO_OP.get(rel, ('--help',))
            run = subprocess.run([sys.executable, f'.youngcrow/{rel}', *args], cwd=self.root, env=env,
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 0, f'{rel}: {run.stderr}')
            self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('__pycache__')),
                             [], rel)
        undo(self.root, confirm=True)
        self.assertEqual(self.snapshot(), {})

    def test_prompt_hook_in_the_repository_still_uses_the_repository_root(self):
        note = ROOT / 'vault' / 'decisions' / 'choice.md'
        run = self.hook(ROOT / 'scripts' / 'source_prompt.py', f'resume from {note}', ROOT)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {})


if __name__ == '__main__':
    unittest.main()
