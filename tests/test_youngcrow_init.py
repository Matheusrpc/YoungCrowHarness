"""Check `youngcrow init` installs the harness into a project and records exactly what it wrote."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import youngcrow  # noqa: E402
from youngcrow.blocks import MD_END, MD_START, ManagedBlockError  # noqa: E402
from youngcrow.install import AlreadyInitialized, Report, init  # noqa: E402
from youngcrow.manifest import UnsafePathError, load, sha256_file  # noqa: E402
from youngcrow.payload import PAYLOAD, VAULT_TEMPLATES, payload_root  # noqa: E402

IMPORT = '@.youngcrow/HARNESS.md'
GITIGNORE_BLOCK = ('# youngcrow:start\n.env\n.env.*\n!.env.example\n.operacao-local/\nvault/local/\n'
                   '# youngcrow:end\n')


class InitTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'project'
        self.other = Path(tmp.name) / 'other'
        self.root.mkdir()
        self.other.mkdir()

    def symlink(self, target, link, directory=False):
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')

    def assertNothingWritten(self):
        self.assertFalse((self.root / '.youngcrow').exists())
        self.assertEqual(list(self.other.iterdir()), [])

    def test_fresh_project(self):
        report = init(self.root)
        for rel in ('.youngcrow/VERSION', '.youngcrow/HARNESS.md', '.youngcrow/scripts/vault.py',
                    'vault/index.md', 'CLAUDE.md', 'AGENTS.md', '.gitignore'):
            self.assertTrue((self.root / rel).is_file(), rel)
        self.assertIn('@.youngcrow/HARNESS.md', (self.root / 'CLAUDE.md').read_text())
        self.assertEqual(load(self.root).files['.youngcrow/scripts/vault.py'],
                         sha256_file(self.root / '.youngcrow/scripts/vault.py'))

    def test_second_init_refuses_without_duplicating(self):
        init(self.root)
        before = (self.root / 'AGENTS.md').read_bytes()
        with self.assertRaises(AlreadyInitialized):
            init(self.root)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), before)

    def test_existing_files_are_kept(self):
        (self.root / 'CLAUDE.md').write_text('My rules\n')
        init(self.root)
        self.assertTrue((self.root / 'CLAUDE.md').read_text().startswith('My rules\n'))

    def test_user_scripts_do_not_collide(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/vault.py').write_text('print("USER CODE")\n')
        init(self.root)
        run = subprocess.run([sys.executable, '.youngcrow/scripts/memory.py', '--root', '.', 'status'],
                             cwd=self.root, capture_output=True, text=True)
        self.assertNotIn('USER CODE', run.stdout + run.stderr)
        self.assertEqual((self.root / 'scripts/vault.py').read_text(), 'print("USER CODE")\n')

    def test_symlinked_claude_md_refused_before_any_write(self):
        self.symlink(self.other / 'x.md', self.root / 'CLAUDE.md')
        with self.assertRaises(UnsafePathError):
            init(self.root)
        self.assertFalse((self.root / '.youngcrow').exists())

    def test_codex_only_skips_claude_md(self):
        init(self.root, client='codex')
        self.assertFalse((self.root / 'CLAUDE.md').exists())
        self.assertIn('<!-- youngcrow:start -->', (self.root / 'AGENTS.md').read_text())

    # The layout and the files themselves.

    def test_claude_only_skips_agents_md(self):
        init(self.root, client='claude')
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertTrue((self.root / 'CLAUDE.md').is_file())

    def test_payload_is_copied_byte_for_byte_and_version_is_written(self):
        init(self.root)
        for rel in PAYLOAD:
            self.assertEqual((self.root / '.youngcrow' / rel).read_bytes(),
                             (payload_root() / rel).read_bytes(), rel)
        self.assertEqual((self.root / '.youngcrow/VERSION').read_text(), youngcrow.__version__ + '\n')
        self.assertEqual(sorted(p.name for p in (self.root / '.youngcrow').iterdir()),
                         ['HARNESS.md', 'VERSION', 'manifest.json', 'requirements', 'scripts'])

    def test_harness_md_states_the_light_core(self):
        init(self.root)
        text = (self.root / '.youngcrow/HARNESS.md').read_text(encoding='utf-8')
        for words in ('Measure before you claim', 'secrets', 'Stop when', 'One writer per checkout',
                      'vault'):
            self.assertIn(words, text)
        self.assertNotIn('\r', text)

    def test_new_claude_md_is_a_title_a_blank_line_and_the_import(self):
        init(self.root)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(),
                         b'# Project rules\n\n@.youngcrow/HARNESS.md\n')

    def test_agents_block_holds_exactly_the_harness_text(self):
        init(self.root)
        harness = (self.root / '.youngcrow/HARNESS.md').read_text(encoding='utf-8')
        agents = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertEqual(agents, f'{MD_START}\n{harness.rstrip(chr(10))}\n{MD_END}\n')

    def test_gitignore_block_has_the_five_lines_in_order(self):
        init(self.root)
        self.assertEqual((self.root / '.gitignore').read_text(), GITIGNORE_BLOCK)

    def test_existing_gitignore_keeps_its_lines(self):
        (self.root / '.gitignore').write_text('node_modules/\n')
        init(self.root)
        self.assertEqual((self.root / '.gitignore').read_text(), 'node_modules/\n\n' + GITIGNORE_BLOCK)

    def test_vault_indexes_are_created_from_the_templates(self):
        init(self.root)
        for rel in VAULT_TEMPLATES:
            self.assertEqual((self.root / rel).read_bytes(), (payload_root() / rel).read_bytes(), rel)

    def test_existing_vault_index_is_left_alone_and_the_others_are_created(self):
        (self.root / 'vault').mkdir()
        (self.root / 'vault/index.md').write_bytes(b'# My vault\n')
        report = init(self.root)
        manifest = load(self.root)
        self.assertEqual((self.root / 'vault/index.md').read_bytes(), b'# My vault\n')
        self.assertIn('vault/index.md', report.skipped)
        self.assertNotIn('vault/index.md', manifest.files)
        self.assertNotIn('vault/index.md', manifest.created)
        self.assertTrue((self.root / 'vault/integrations/index.md').is_file())
        self.assertTrue((self.root / 'vault/capabilities/index.md').is_file())

    def test_vault_notes_are_never_touched(self):
        (self.root / 'vault/decisions').mkdir(parents=True)
        (self.root / 'vault/decisions/one.md').write_bytes(b'note\r\n')
        init(self.root)
        self.assertEqual((self.root / 'vault/decisions/one.md').read_bytes(), b'note\r\n')

    # The manifest (R1, R7).

    def test_manifest_records_what_a_fresh_init_wrote(self):
        report = init(self.root, client='both')
        manifest = load(self.root)
        self.assertEqual((manifest.version, manifest.client, manifest.lang, manifest.rigor),
                         (youngcrow.__version__, 'both', 'en', 'light'))
        expected = {'.youngcrow/VERSION', '.youngcrow/HARNESS.md', 'CLAUDE.md', 'AGENTS.md', '.gitignore',
                    *(f'.youngcrow/{rel}' for rel in PAYLOAD), *VAULT_TEMPLATES}
        self.assertEqual(set(manifest.files), expected)
        self.assertEqual(set(manifest.created), expected)
        self.assertEqual(len(manifest.created), len(expected))
        self.assertEqual(sorted(manifest.edits), ['.gitignore', 'AGENTS.md', 'CLAUDE.md'])
        self.assertNotIn('.youngcrow/manifest.json', manifest.files)
        for rel, digest in manifest.files.items():
            self.assertEqual(digest, hashlib.sha256((self.root / rel).read_bytes()).hexdigest(), rel)
        self.assertEqual(sorted(report.written), sorted(manifest.files))
        self.assertEqual((report.kept_modified, report.removed, report.skipped), ([], [], []))

    def test_manifest_json_is_on_disk_where_the_layout_says(self):
        init(self.root)
        data = json.loads((self.root / '.youngcrow/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(data['schema_version'], 1)

    def test_pre_existing_files_are_edits_not_created(self):
        (self.root / 'CLAUDE.md').write_bytes(b'My rules\n')
        (self.root / '.gitignore').write_bytes(b'dist/\n')
        init(self.root)
        manifest = load(self.root)
        for rel in ('CLAUDE.md', '.gitignore'):
            self.assertIn(rel, manifest.edits)
            self.assertNotIn(rel, manifest.created)
            self.assertEqual(manifest.files[rel], sha256_file(self.root / rel))
        self.assertIn('AGENTS.md', manifest.created)

    def test_existing_import_line_is_not_an_edit_and_the_bytes_stay(self):
        original = b'# Mine\n\n@.youngcrow/HARNESS.md\n\nrest\n'
        (self.root / 'CLAUDE.md').write_bytes(original)
        report = init(self.root)
        manifest = load(self.root)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), original)
        for names in (manifest.edits, manifest.created, manifest.files):
            self.assertNotIn('CLAUDE.md', names)
        self.assertNotIn('CLAUDE.md', report.written)
        self.assertIn('CLAUDE.md', report.skipped)

    def test_existing_block_is_left_alone_even_when_its_text_differs(self):
        original = f'{MD_START}\nmy own words\n{MD_END}\n'.encode()
        gitignore = b'# youngcrow:start\nmine\n# youngcrow:end\n'
        (self.root / 'AGENTS.md').write_bytes(original)
        (self.root / '.gitignore').write_bytes(gitignore)
        report = init(self.root)
        manifest = load(self.root)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), original)
        self.assertEqual((self.root / '.gitignore').read_bytes(), gitignore)
        for rel in ('AGENTS.md', '.gitignore'):
            self.assertNotIn(rel, manifest.edits)
            self.assertNotIn(rel, manifest.files)
            self.assertIn(rel, report.skipped)

    # Line endings.

    def test_crlf_claude_md_gets_the_import_with_crlf(self):
        (self.root / 'CLAUDE.md').write_bytes(b'My rules\r\nsecond\r\n')
        init(self.root)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(),
                         b'My rules\r\nsecond\r\n\r\n@.youngcrow/HARNESS.md\r\n')

    def test_crlf_agents_md_and_gitignore_get_crlf_blocks(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\r\n')
        (self.root / '.gitignore').write_bytes(b'dist/\r\n')
        init(self.root)
        for rel in ('AGENTS.md', '.gitignore'):
            data = (self.root / rel).read_bytes()
            self.assertEqual(data.replace(b'\r\n', b'').count(b'\n'), 0, rel)
            self.assertEqual(data.count(b'\r\n'), data.count(b'\n'), rel)
        self.assertTrue((self.root / 'AGENTS.md').read_bytes().startswith(b'Agent notes\r\n\r\n<!--'))

    def test_claude_md_without_a_final_newline_gets_the_import_on_its_own_line(self):
        (self.root / 'CLAUDE.md').write_bytes(b'My rules')
        init(self.root)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), b'My rules\n@.youngcrow/HARNESS.md\n')

    def test_bom_and_non_ascii_text_survive(self):
        original = '﻿Regras do projeto – acentuação\n'.encode('utf-8')
        (self.root / 'CLAUDE.md').write_bytes(original)
        init(self.root)
        self.assertTrue((self.root / 'CLAUDE.md').read_bytes().startswith(original))

    # Refusals: nothing may be written first.

    def test_symlinked_youngcrow_refused_before_any_write(self):
        self.symlink(self.other, self.root / '.youngcrow', directory=True)
        with self.assertRaises(UnsafePathError):
            init(self.root)
        self.assertEqual(list(self.other.iterdir()), [])
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_symlinked_vault_refused_before_any_write(self):
        self.symlink(self.other, self.root / 'vault', directory=True)
        with self.assertRaises(UnsafePathError):
            init(self.root)
        self.assertNothingWritten()
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_symlinked_agents_md_refused_before_any_write(self):
        self.symlink(self.other / 'a.md', self.root / 'AGENTS.md')
        with self.assertRaises(UnsafePathError):
            init(self.root)
        self.assertNothingWritten()
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_client_claude_does_not_inspect_agents_md(self):
        self.symlink(self.other / 'a.md', self.root / 'AGENTS.md')
        init(self.root, client='claude')
        self.assertTrue((self.root / '.youngcrow/manifest.json').is_file())
        self.assertEqual(list(self.other.iterdir()), [])

    def test_broken_markers_refuse_before_any_write(self):
        (self.root / 'AGENTS.md').write_bytes(f'{MD_START}\nnever closed\n'.encode())
        with self.assertRaises(ManagedBlockError):
            init(self.root)
        self.assertFalse((self.root / '.youngcrow').exists())
        self.assertFalse((self.root / 'CLAUDE.md').exists())
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), f'{MD_START}\nnever closed\n'.encode())

    def test_text_that_is_not_utf8_refuses_before_any_write(self):
        (self.root / 'CLAUDE.md').write_bytes(b'caf\xe9\n')
        with self.assertRaises(ValueError) as caught:
            init(self.root)
        self.assertIn('CLAUDE.md', str(caught.exception))
        self.assertFalse((self.root / '.youngcrow').exists())
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), b'caf\xe9\n')

    def test_a_directory_in_place_of_a_file_refuses_before_any_write(self):
        (self.root / '.gitignore').mkdir()
        with self.assertRaises(UnsafePathError):
            init(self.root)
        self.assertFalse((self.root / '.youngcrow').exists())
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_leftover_file_without_a_manifest_refuses_and_keeps_it(self):
        (self.root / '.youngcrow/scripts').mkdir(parents=True)
        (self.root / '.youngcrow/scripts/vault.py').write_bytes(b'left over\n')
        with self.assertRaises(AlreadyInitialized) as caught:
            init(self.root)
        self.assertIn('.youngcrow/scripts/vault.py', str(caught.exception))
        self.assertEqual((self.root / '.youngcrow/scripts/vault.py').read_bytes(), b'left over\n')
        self.assertFalse((self.root / '.youngcrow/manifest.json').exists())
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_an_unreadable_manifest_still_counts_as_initialized(self):
        (self.root / '.youngcrow').mkdir()
        (self.root / '.youngcrow/manifest.json').write_text('{not json')
        with self.assertRaises(AlreadyInitialized):
            init(self.root)
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_unsupported_options_raise_before_writing(self):
        cases = (
            (dict(lang='pt'), "lang 'pt' is not available yet"),
            (dict(rigor='full'), "rigor 'full' is not available yet"),
            (dict(client='vim'), "client 'vim'"),
        )
        for options, message in cases:
            with self.subTest(**options), self.assertRaises(ValueError) as caught:
                init(self.root, **options)
            self.assertIn(message, str(caught.exception))
            self.assertEqual(list(self.root.iterdir()), [])

    def test_a_failed_write_leaves_no_manifest(self):
        from unittest import mock
        with mock.patch('os.replace', side_effect=OSError('disk full')), self.assertRaises(OSError):
            init(self.root)
        self.assertFalse((self.root / '.youngcrow/manifest.json').exists())
        self.assertEqual([p.name for p in self.root.rglob('*.tmp')], [])

    def test_report_is_json(self):
        report = init(self.root)
        self.assertIsInstance(report, Report)
        data = report.to_json()
        self.assertEqual(sorted(data), ['kept_modified', 'removed', 'skipped', 'written'])
        self.assertEqual(json.loads(json.dumps(data)), data)


if __name__ == '__main__':
    unittest.main()
