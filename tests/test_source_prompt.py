"""Prompt intake records references only; conversion remains an explicit agent action."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shlex
import shutil
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import documents
import document_store as store
import source_prompt


class SourcePromptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(self.root.parent)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, prompt, **extra):
        with patch('documents.run_worker', side_effect=AssertionError('worker called')), \
             patch('source_fetch.fetch_source', side_effect=AssertionError('network called')):
            return source_prompt.handle_prompt(dict(prompt=prompt, session_id='test', **extra), self.root)

    def test_unrelated_empty_and_stop_are_read_only(self):
        for payload in ({}, {'prompt': 'continue'}, {'prompt': 'file.pdf', 'hook_event_name': 'Stop'}):
            self.assertEqual(source_prompt.handle_prompt(payload, self.root), {})
            self.assertEqual(list(self.root.iterdir()), [])

    def test_repeated_reference_has_one_pending_identity_and_navigable_index(self):
        result = self.call('Read "folder with spaces/spec.pdf"', turn_id='one')
        self.assertEqual(self.call('Read "folder with spaces/spec.pdf"', turn_id='one'), result)
        records = store.source_records(self.root)
        self.assertEqual(len(records), 1)
        source = records[0]
        first = documents.status(self.root)[0]['latest_attempt']
        self.call('Read "folder with spaces/spec.pdf"', turn_id='two')
        self.assertEqual(documents.status(self.root)[0]['latest_attempt'], first)
        self.assertEqual(first['state'], 'pending')
        self.assertIsNone(first['revision'])
        self.assertIn('created_at', first)
        note = self.root / 'vault/local/sources' / source['source_id'] / 'index.md'
        self.assertTrue(note.is_file())
        self.assertIn(source['source_id'], (self.root / 'vault/local/sources/index.md').read_text())
        self.assertNotIn('folder with spaces', json.dumps(result))

    def test_memory_paths_and_glob_commands_do_not_create_pending_sources(self):
        prompts = (
            'Retome vault/local/runs/previous.md',
            'Grave o handoff em vault/local/runs/claude-current.md',
            'Confira `sha256sum vault/local/demo/*.md vault/local/runs/*.md`',
            'Leia "vault/local/../index.md"',
            f'Leia "{self.root.as_posix()}/vault/local/runs/previous.md"',
            'Confira docs/spec?.pdf',
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.call(prompt), {})
                self.assertEqual(list(self.root.iterdir()), [])
        child = self.root / 'subdir'
        child.mkdir()
        self.assertEqual(self.call('../vault/index.md', cwd=str(child)), {})
        self.assertEqual(list(self.root.iterdir()), [child])

    def test_external_markdown_is_kept_alongside_internal_memory_references(self):
        self.call('Use "docs/spec with spaces.md" e vault/local/index.md '
                  'https://example.org/vault/index.md e "vault-copy/spec.md"')
        self.assertEqual({s['locator'] for s in store.source_records(self.root)}, {
            (self.root / 'docs/spec with spaces.md').as_uri(),
            'https://example.org/vault/index.md',
            (self.root / 'vault-copy/spec.md').as_uri(),
        })

    def test_secrets_and_whole_prompt_never_persist_or_enter_hook_context(self):
        output = self.call('secret=NOT_A_REAL_SECRET https://example.org/file.pdf?token=QUERY_SECRET#FRAGMENT '
                           'https://user:PASSWORD@example.org/hidden.pdf')
        stored = '\n'.join(p.read_text(encoding='utf-8') for p in self.root.rglob('*') if p.is_file())
        for secret in ('NOT_A_REAL_SECRET', 'QUERY_SECRET', 'FRAGMENT', 'PASSWORD'):
            self.assertNotIn(secret, stored + json.dumps(output))
        self.assertIn('https://example.org/file.pdf', stored)

    def test_inaccessible_attachment_and_pending_cli_can_be_resumed(self):
        self.call('Use the attached document')
        source = documents.status(self.root)[0]
        self.assertEqual(source['latest_attempt']['warnings'], ['source_unavailable'])
        self.assertIsNone(source['current_revision'])
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/documents.py'), '--root', str(self.root),
                                 'pending', '--reason', 'source_unavailable', '--json'], capture_output=True)
        self.assertEqual(result.returncode, 1)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['state'], 'pending')
        self.assertTrue((self.root / 'vault/local/sources' / receipt['source_id'] / 'index.md').exists())

    def test_oversized_or_malformed_payload_never_persists(self):
        result = self.call('x' * (1024 * 1024 + 1) + ' https://example.org/secret.pdf')
        self.assertIn('input_limit', json.dumps(result))
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(source_prompt.handle_prompt({'prompt': ['bad']}, self.root), {})

    def test_cwd_subdirectory_resolves_relative_reference_without_reading_it(self):
        child = self.root / 'sub directory'
        child.mkdir()
        self.call('spec.pdf', cwd=str(child))
        self.assertEqual(store.source_records(self.root)[0]['locator'], (child / 'spec.pdf').as_uri())

    def test_tracked_private_directory_is_rejected_before_reference_write(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        private = self.root / 'vault/local/leak.txt'
        private.parent.mkdir(parents=True)
        private.write_text('fixture')
        subprocess.run(['git', '-C', str(self.root), 'add', 'vault/local/leak.txt'], check=True)
        output = self.call('secret.pdf')
        self.assertIn('storage_unavailable', json.dumps(output))
        self.assertFalse((self.root / store.BASE).exists())

    def test_native_hook_commands_work_from_subdirectory_with_spaces_without_git(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        for name in ('source_prompt.py', 'documents.py', 'document_store.py', 'source_fetch.py', 'integrations.py', 'vault.py'):
            shutil.copyfile(ROOT / 'scripts' / name, scripts / name)
        child = self.root / 'sub dir'
        child.mkdir()
        for name in ('.claude/settings.json', '.codex/hooks.json'):
            config = json.loads((ROOT / name).read_text())
            hook = config['hooks']['UserPromptSubmit'][0]['hooks'][0]
            command = hook.get('commandWindows', hook['command']) if os.name == 'nt' else hook['command']
            args = shlex.split(command)
            args[0] = sys.executable
            result = subprocess.run(args, input=json.dumps(dict(prompt='spec.pdf', cwd=str(child))),
                                    cwd=child, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ingest-source', json.loads(result.stdout)['hookSpecificOutput']['additionalContext'])
            before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            result = subprocess.run(args, input=json.dumps(dict(
                prompt='Retome ../vault/local/runs/latest.md; confira `sha256sum ../vault/local/runs/*.md`',
                cwd=str(child))), cwd=child, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})
            self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                      for p in self.root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
