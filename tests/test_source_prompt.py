"""Prompt guidance must never turn a reference into a filesystem mutation."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_prompt


class SourcePromptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() if p.is_file() else None
                for p in self.root.rglob('*')}

    def call(self, prompt, **extra):
        before = self.snapshot()
        result = source_prompt.handle_prompt(dict(prompt=prompt, session_id='test', **extra), self.root)
        self.assertEqual(self.snapshot(), before)
        return result

    def test_references_only_offer_guidance_in_empty_and_existing_projects(self):
        for existing in (False, True):
            if existing:
                for name in ('vault/project.json', 'vault/local/index.md',
                             '.operacao-local/docling/prompts/old.json', '.gitignore'):
                    path = self.root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('preserve existing bytes', encoding='utf-8')
            for prompt in ('Read "folder with spaces/spec.pdf"', 'https://example.org/spec.md',
                           'Auditoria somente leitura de docs/USAGE.md'):
                with self.subTest(existing=existing, prompt=prompt):
                    result = self.call(prompt, turn_id='one')
                    self.assertEqual(self.call(prompt, turn_id='two', agent_id='reviewer'), result)
                    message = result['hookSpecificOutput']['additionalContext']
                    self.assertIn('ingest-source', message)
                    self.assertIn('authorized', message)

    def test_unrelated_attachment_words_and_memory_paths_are_noops(self):
        for prompt in ('continue', 'Não há anexo nesta tarefa', 'Use the attached document',
                       'Leia AGENTS.md CLAUDE.md SKILL.md', 'Retome vault/local/runs/previous.md',
                       'Grave em vault/local/runs/current.md', 'Confira `sha256sum vault/local/*.md`',
                       'Leia "vault/local/../index.md"', 'Confira docs/spec?.pdf'):
            with self.subTest(prompt=prompt):
                self.assertEqual(self.call(prompt), {})
        child = self.root / 'subdir'
        child.mkdir()
        self.assertEqual(self.call('../vault/index.md', cwd=str(child)), {})

    def test_secret_and_source_text_never_enter_context(self):
        output = self.call('secret=NOT_A_REAL_SECRET https://example.org/spec.pdf?token=QUERY_SECRET#FRAGMENT '
                           'https://user:PASSWORD@example.org/hidden.pdf')
        message = json.dumps(output)
        for text in ('NOT_A_REAL_SECRET', 'QUERY_SECRET', 'FRAGMENT', 'PASSWORD', 'example.org'):
            self.assertNotIn(text, message)
        self.assertIn('ingest-source', message)

    def test_malformed_stop_and_oversized_payloads_do_not_write(self):
        for payload in ({}, [], {'prompt': ['bad']}, {'prompt': 'file.pdf', 'hook_event_name': 'Stop'}):
            self.assertEqual(source_prompt.handle_prompt(payload, self.root), {})
        output = json.dumps(self.call('x' * (1024 * 1024 + 1) + ' spec.pdf'))
        self.assertIn('input_limit', output)
        self.assertNotIn('ingest-source', output)
        self.assertEqual(self.snapshot(), {})

    def test_native_commands_from_subdirectory_do_not_write_or_require_python_alias(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        shutil.copyfile(ROOT / 'scripts/source_prompt.py', scripts / 'source_prompt.py')
        child = self.root / 'sub dir'
        child.mkdir()
        env = os.environ.copy()
        if os.name != 'nt':
            binary = self.root / 'bin'
            binary.mkdir()
            (binary / 'python3').symlink_to(sys.executable)
            env['PATH'] = str(binary)
        for name in ('.claude/settings.json', '.codex/hooks.json'):
            hook = json.loads((ROOT / name).read_text())['hooks']['UserPromptSubmit'][0]['hooks'][0]
            command = hook.get('commandWindows', hook['command']) if os.name == 'nt' else hook['command']
            args = shlex.split(command)
            if os.name == 'nt':
                # Installer's Windows interpreter choice is checked in test_setup.
                args[0] = sys.executable
            for prompt in ('spec.pdf', 'https://example.org/spec.pdf', 'Não há anexo'):
                before = self.snapshot()
                result = subprocess.run(args, input=json.dumps(dict(prompt=prompt, cwd=str(child))),
                                        cwd=child, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(bool(output), prompt != 'Não há anexo')
                self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
