"""Check the `youngcrow` command line: what each command prints, and the exit code of each outcome."""
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))

REPORT_KEYS = ['written', 'kept_modified', 'removed', 'skipped']


class CliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'project'
        self.root.mkdir()

    def _cli(self, *args, cwd=None):
        """Run `python -m youngcrow` from the source tree, as a person would from a checkout."""
        env = {**os.environ, 'PYTHONPATH': str(REPO / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
        return subprocess.run([sys.executable, '-B', '-m', 'youngcrow', *args], cwd=cwd, env=env,
                              capture_output=True, text=True, encoding='utf-8')

    def _init(self, *args):
        run = self._cli('init', '--root', str(self.root), *args)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run

    def _tree(self):
        """Every file and folder under the project: relative path -> bytes (None for a folder)."""
        return {path.relative_to(self.root).as_posix(): path.read_bytes() if path.is_file() else None
                for path in sorted(self.root.rglob('*'))}

    def _legacy(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    # The brief's tests.

    def test_init_json(self):
        run = self._cli('init', '--root', str(self.root), '--json')
        self.assertEqual(run.returncode, 0)
        self.assertIn('.youngcrow/VERSION', json.loads(run.stdout)['written'])

    def test_refusals_exit_3(self):
        self._cli('init', '--root', str(self.root))
        self.assertEqual(self._cli('init', '--root', str(self.root)).returncode, 3)

    def test_migrate_previews_by_default(self):
        run = self._cli('migrate', '--root', str(self.root), '--json')
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)['applied'], False)

    # init, upgrade, undo: the report.

    def test_init_json_is_the_whole_report_and_nothing_else(self):
        run = self._cli('init', '--root', str(self.root), '--json')
        self.assertEqual(list(json.loads(run.stdout)), REPORT_KEYS)
        self.assertEqual(run.stderr, '')

    def test_init_prints_a_heading_per_non_empty_list_with_indented_paths(self):
        run = self._init()
        lines = run.stdout.splitlines()
        self.assertEqual(lines[0], 'Written:')
        self.assertIn('  .youngcrow/VERSION', lines)
        self.assertIn('  CLAUDE.md', lines)
        for heading in ('Kept (you changed these):', 'Removed:'):
            self.assertNotIn(heading, lines)
        self.assertEqual([line for line in lines if line and not line.startswith(' ')], ['Written:'])

    def test_init_names_what_it_skipped(self):
        (self.root / '.gitignore').write_text('# youngcrow:start\n.env\n# youngcrow:end\n')
        run = self._init()
        lines = run.stdout.splitlines()
        self.assertIn('Skipped:', lines)
        self.assertEqual(lines[lines.index('Skipped:') + 1], '  .gitignore')

    def test_init_client_codex_leaves_claude_md_alone(self):
        self._init('--client', 'codex')
        self.assertFalse((self.root / 'CLAUDE.md').exists())
        self.assertTrue((self.root / 'AGENTS.md').is_file())

    def test_root_defaults_to_the_current_folder(self):
        run = self._cli('init', '--json', cwd=self.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((self.root / '.youngcrow/VERSION').is_file())

    def test_init_creates_a_project_folder_that_is_missing(self):
        target = self.root / 'new' / 'project'
        run = self._cli('init', '--root', str(target), '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((target / '.youngcrow/manifest.json').is_file())

    def test_a_refused_init_leaves_no_folder_it_made(self):
        run = self._cli('init', '--root', str(self.root / 'new' / 'project'), '--client', 'cursor')
        self.assertEqual(run.returncode, 3, run.stderr)
        self.assertFalse((self.root / 'new').exists())

    def test_a_root_with_dot_dot_through_a_missing_folder_works_and_a_refusal_leaves_nothing(self):
        refused = self._cli('init', '--root', 'nope/../proj', '--client', 'cursor', cwd=self.root)
        self.assertRefused(refused, "'cursor'")
        self.assertEqual(self._tree(), {})
        done = self._cli('init', '--root', 'nope/../proj', cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.root / 'proj/.youngcrow/manifest.json').is_file())

    def test_commands_that_do_not_install_never_create_the_folder(self):
        for args in (('upgrade',), ('undo',), ('undo', '--confirm')):
            self.assertEqual(self._cli(*args, '--root', str(self.root / 'new')).returncode, 3, args)
        self.assertEqual(self._cli('migrate', '--root', str(self.root / 'new')).returncode, 0)
        self.assertFalse((self.root / 'new').exists())

    def test_migrate_confirm_creates_a_missing_folder_and_a_refusal_takes_it_back(self):
        refused = self._cli('migrate', '--root', str(self.root / 'a'), '--confirm', '--client', 'cursor')
        self.assertEqual(refused.returncode, 3, refused.stderr)
        self.assertFalse((self.root / 'a').exists())
        done = self._cli('migrate', '--root', str(self.root / 'b'), '--confirm')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.root / 'b/.youngcrow/manifest.json').is_file())

    def test_upgrade_on_a_current_install_changes_nothing(self):
        self._init()
        before = self._tree()
        run = self._cli('upgrade', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), 'Nothing changed.')
        self.assertEqual(self._tree(), before)

    def test_upgrade_json_has_the_report_keys(self):
        self._init()
        run = self._cli('upgrade', '--root', str(self.root), '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), dict.fromkeys(REPORT_KEYS, []))

    def test_upgrade_keeps_a_file_the_user_changed_and_lists_it(self):
        self._init()
        (self.root / '.youngcrow/scripts/vault.py').write_text('# mine\n')
        run = self._cli('upgrade', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        lines = run.stdout.splitlines()
        self.assertEqual(lines[lines.index('Kept (you changed these):') + 1], '  .youngcrow/scripts/vault.py')

    def test_undo_without_confirm_is_a_preview(self):
        self._init()
        before = self._tree()
        run = self._cli('undo', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        first = run.stdout.splitlines()[0]
        self.assertIn('Preview', first)
        self.assertIn('--confirm', first)
        self.assertIn('  .youngcrow/manifest.json', run.stdout.splitlines())
        self.assertEqual(self._tree(), before)

    def test_undo_confirm_takes_the_install_out(self):
        self._init()
        run = self._cli('undo', '--root', str(self.root), '--confirm')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Preview', run.stdout)
        self.assertEqual(self._tree(), {})
        self.assertIn('Removed:', run.stdout.splitlines())

    def test_undo_json_preview_is_the_plain_report_and_changes_nothing(self):
        self._init()
        before = self._tree()
        run = self._cli('undo', '--root', str(self.root), '--json')
        report = json.loads(run.stdout)
        self.assertEqual(list(report), REPORT_KEYS + ['warnings'])
        self.assertIn('.youngcrow/manifest.json', report['removed'])
        self.assertEqual(self._tree(), before)

    def test_undo_reports_restored_files_as_written_and_deleted_ones_as_removed(self):
        original = b'# My rules\r\n'
        (self.root / 'CLAUDE.md').write_bytes(original)
        self._init()
        run = self._cli('undo', '--root', str(self.root), '--confirm', '--json')
        report = json.loads(run.stdout)
        self.assertEqual(report['written'], ['CLAUDE.md'])
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), original)
        self.assertIn('.youngcrow/VERSION', report['removed'])
        self.assertIn('.youngcrow/', report['removed'])
        self.assertNotIn('CLAUDE.md', report['removed'])

    def test_undo_warns_on_stderr_and_in_json_when_an_env_file_loses_its_ignore_rule(self):
        self._init()
        (self.root / '.env').write_text('TOKEN=x\n')
        (self.root / '.env.example').write_text('TOKEN=\n')
        run = self._cli('undo', '--root', str(self.root), '--confirm', '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        warnings = json.loads(run.stdout)['warnings']
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith('.env: '), warnings)
        self.assertEqual(run.stderr, f'youngcrow: warning: {warnings[0]}\n')
        self.assertEqual(sorted(self._tree()), ['.env', '.env.example'])

    def test_undo_without_env_files_has_no_warning(self):
        self._init()
        run = self._cli('undo', '--root', str(self.root), '--confirm')
        self.assertEqual(run.stderr, '')
        self.assertEqual(json.loads(self._cli('init', '--root', str(self.root), '--json').stdout).get('warnings'), None)

    # Refusals: exit 3 and the message on stderr.

    def assertRefused(self, run, *words):
        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
        self.assertEqual(run.stdout, '')
        self.assertTrue(run.stderr.startswith('youngcrow: '), run.stderr)
        self.assertNotIn('Traceback', run.stderr)
        for word in words:
            self.assertIn(word, run.stderr)

    def test_init_twice_names_the_manifest_on_stderr(self):
        self._init()
        before = self._tree()
        self.assertRefused(self._cli('init', '--root', str(self.root)), 'manifest.json', 'already')
        self.assertEqual(self._tree(), before)

    def test_upgrade_and_undo_refuse_a_project_that_was_not_set_up(self):
        for command in ('upgrade', 'undo'):
            self.assertRefused(self._cli(command, '--root', str(self.root)), 'manifest.json', 'not found')
        self.assertRefused(self._cli('undo', '--root', str(self.root), '--confirm'), 'manifest.json')
        self.assertEqual(self._tree(), {})

    def test_a_root_that_is_a_file_is_a_refusal(self):
        (self.root / 'afile').write_text('x\n')
        for command in ('init', 'upgrade', 'undo', 'migrate'):
            self.assertRefused(self._cli(command, '--root', str(self.root / 'afile')), 'not a folder')

    def test_broken_markers_in_agents_md_refuse_before_any_write(self):
        (self.root / 'AGENTS.md').write_text('<!-- youngcrow:start -->\nno end marker\n')
        before = self._tree()
        self.assertRefused(self._cli('init', '--root', str(self.root)), 'AGENTS.md', 'youngcrow:start', 'no matching')
        self.assertEqual(self._tree(), before)

    def test_upgrade_and_undo_refuse_markers_the_user_broke_and_name_the_file(self):
        self._init()
        agents = self.root / 'AGENTS.md'
        agents.write_text(agents.read_text().replace('<!-- youngcrow:end -->', ''))
        before = self._tree()
        for args in (('upgrade',), ('undo', '--confirm')):
            self.assertRefused(self._cli(*args, '--root', str(self.root)), 'AGENTS.md')
        self.assertEqual(self._tree(), before)

    def test_a_linked_claude_md_refuses_before_any_write(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('# elsewhere\n')
        try:
            os.symlink(outside, self.root / 'CLAUDE.md')
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')
        self.assertRefused(self._cli('init', '--root', str(self.root)), 'CLAUDE.md')
        self.assertFalse((self.root / '.youngcrow').exists())
        self.assertEqual(outside.read_text(), '# elsewhere\n')

    def test_an_unsupported_client_is_a_refusal_not_a_usage_error(self):
        run = self._cli('init', '--root', str(self.root), '--client', 'cursor')
        self.assertRefused(run, "'cursor'")
        self.assertFalse((self.root / '.youngcrow').exists())

    def test_migrate_confirm_refuses_an_unsupported_client(self):
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--client', 'cursor')
        self.assertRefused(run, "'cursor'")
        self.assertEqual(self._tree(), {})

    def test_files_youngcrow_cannot_work_with_are_refusals_too(self):
        (self.root / 'CLAUDE.md').write_bytes(b'\xff\xfe not text\n')
        self.assertRefused(self._cli('init', '--root', str(self.root)), 'CLAUDE.md', 'UTF-8')
        (self.root / 'CLAUDE.md').unlink()
        (self.root / '.youngcrow').mkdir()
        (self.root / '.youngcrow/VERSION').write_text('left over\n')
        self.assertRefused(self._cli('init', '--root', str(self.root)), '.youngcrow/VERSION', 'manifest.json')
        shutil.rmtree(self.root / '.youngcrow')
        self._init()
        (self.root / '.youngcrow/manifest.json').write_text('{\n')
        self.assertRefused(self._cli('upgrade', '--root', str(self.root)), 'manifest.json', 'not valid JSON')

    def test_migrate_confirm_refuses_a_project_that_is_already_set_up(self):
        self._init()
        self.assertRefused(self._cli('migrate', '--root', str(self.root), '--confirm'), 'manifest.json')

    def _main(self, *args):
        """Run `main` in this process: its exit code, stdout and stderr."""
        from youngcrow.cli import main
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_an_os_error_is_exit_3_with_the_message_and_no_traceback(self):
        from youngcrow import install
        real = install._replace_file

        def fail_on_agents(target, data):
            if target.name == 'AGENTS.md':
                raise PermissionError(13, 'Permission denied', str(target))
            real(target, data)
        with mock.patch('youngcrow.install._replace_file', side_effect=fail_on_agents):
            code, out, err = self._main('init', '--root', str(self.root))
        self.assertEqual(code, 3)
        self.assertEqual(out, '')
        self.assertTrue(err.startswith('youngcrow: '), err)
        self.assertIn('Permission denied', err)
        self.assertIn('AGENTS.md', err)
        self.assertNotIn('Traceback', err)
        self.assertEqual(self._tree(), {})  # init rolled back what it wrote

    def test_the_roll_back_notes_are_printed(self):
        with mock.patch('youngcrow.install._replace_file', side_effect=OSError(28, 'No space left on device')), \
                mock.patch('youngcrow.install._roll_back', return_value=['CLAUDE.md (still there)']):
            code, out, err = self._main('init', '--root', str(self.root))
        self.assertEqual(code, 3)
        self.assertEqual(err.splitlines(), ['youngcrow: [Errno 28] No space left on device',
                                            'youngcrow: Could not undo these changes: CLAUDE.md (still there)'])

    def test_a_refusal_prints_its_notes_too(self):
        from youngcrow.install import NotInitialized
        refusal = NotInitialized('not set up')
        refusal.add_note('a note for the person')
        with mock.patch('youngcrow.cli.upgrade', side_effect=refusal):
            code, _, err = self._main('upgrade', '--root', str(self.root))
        self.assertEqual(code, 3)
        self.assertEqual(err.splitlines(), ['youngcrow: not set up', 'youngcrow: a note for the person'])

    def test_version(self):
        import youngcrow
        run = self._cli('--version')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, f'youngcrow {youngcrow.__version__}\n')

    # Usage errors: exit 2.

    def test_unknown_subcommand_and_missing_subcommand_exit_2(self):
        for args in (('frobnicate',), (), ('init', '--no-such-option')):
            run = self._cli(*args)
            self.assertEqual(run.returncode, 2, args)
            self.assertEqual(run.stdout, '', args)
            self.assertIn('usage: youngcrow', run.stderr, args)

    def test_main_returns_the_exit_code_instead_of_raising(self):
        from youngcrow.cli import main
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['frobnicate']), 2)
            self.assertEqual(main(['--help']), 0)
            self.assertEqual(main(['init', '--root', str(self.root), '--client', 'cursor']), 3)
        self.assertIn('usage: youngcrow', err.getvalue())

    # migrate.

    def test_migrate_preview_lists_matches_and_modified_and_changes_nothing(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('scripts/memory.py', b'# my change\n')
        before = self._tree()
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        lines = run.stdout.splitlines()
        self.assertIn('Preview', lines[0])
        self.assertIn('--confirm', lines[0])
        self.assertEqual(lines[lines.index('Will be removed (unmodified setup.sh copies):') + 1], '  scripts/vault.py')
        self.assertEqual(lines[lines.index('Kept (you changed these):') + 1], '  scripts/memory.py')
        self.assertEqual(self._tree(), before)

    def test_migrate_preview_json_lists_both_lists_and_the_legacy_rules_key(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('scripts/memory.py', b'# my change\n')
        run = self._cli('migrate', '--root', str(self.root), '--json')
        self.assertEqual(json.loads(run.stdout), {
            'applied': False, 'matches': ['scripts/vault.py'], 'modified': ['scripts/memory.py'], 'legacy_rules': [],
            'dangling_references': {}, 'vault_check': None})

    def test_migrate_confirm_removes_the_matches_and_installs(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('scripts/memory.py', b'# my change\n')
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {
            'applied': True, 'matches': ['scripts/vault.py'], 'modified': ['scripts/memory.py'], 'legacy_rules': [],
            'dangling_references': {},
            'vault_check': {'exit_code': 0, 'summary': 'Vault: 3 notes checked; 0 issues. No files changed.'}})
        self.assertFalse((self.root / 'scripts/vault.py').exists())
        self.assertTrue((self.root / 'scripts/memory.py').is_file())
        self.assertTrue((self.root / '.youngcrow/VERSION').is_file())

    def test_migrate_confirm_prints_the_install_report(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        run = self._cli('migrate', '--root', str(self.root), '--confirm')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Preview', run.stdout)
        lines = run.stdout.splitlines()
        self.assertIn('  .youngcrow/VERSION', lines)
        self.assertEqual(lines[lines.index('Removed:') + 1], '  scripts/vault.py')

    def test_a_migrate_preview_does_not_check_the_client(self):
        run = self._cli('migrate', '--root', str(self.root), '--client', 'cursor', '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['applied'], False)

    def test_migrate_confirm_puts_back_the_rule_files_the_client_uses_and_only_removes_the_docs_copy(self):
        for client, expected in (('claude', ['CLAUDE.md']), ('codex', ['AGENTS.md']), ('both', ['AGENTS.md', 'CLAUDE.md'])):
            project = self.root / client
            for rel in ('CLAUDE.md', 'AGENTS.md', 'docs/CLAUDE.en.md'):
                shutil.copy(REPO / rel, self._dest(f'{client}/{rel}'))
            run = self._cli('migrate', '--root', str(project), '--confirm', '--client', client, '--json')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['matches'], ['AGENTS.md', 'CLAUDE.md', 'docs/CLAUDE.en.md'], client)
            self.assertEqual([name for name in ('AGENTS.md', 'CLAUDE.md') if (project / name).exists()], expected, client)
            self.assertFalse((project / 'docs').exists(), client)

    def test_migrate_confirm_leaves_an_edited_file_alone_when_the_client_does_not_use_it(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('AGENTS.md', b'# Mine\n')
        self._legacy('docs/CLAUDE.en.md', b'# Mine\n')
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--client', 'claude', '--json')
        self.assertEqual(json.loads(run.stdout)['legacy_rules'], ['AGENTS.md', 'docs/CLAUDE.en.md'])
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), b'# Mine\n')
        self.assertEqual((self.root / 'docs/CLAUDE.en.md').read_bytes(), b'# Mine\n')

    def test_migrate_confirm_with_nothing_to_remove_installs_like_init(self):
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        self.assertEqual(json.loads(run.stdout)['applied'], True)
        self.assertTrue((self.root / '.youngcrow/manifest.json').is_file())

    def _dest(self, rel):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # R26: the old rule files that are kept.

    def _old_rule_files(self):
        """CLAUDE.md and AGENTS.md as someone edited them after setup.sh, docs/CLAUDE.en.md untouched."""
        self._legacy('CLAUDE.md', b'# Mine\n\nOld harness rules, then my own lines.\n')
        self._legacy('AGENTS.md', b'# Mine\n\nOld harness rules, then my own lines.\n')
        shutil.copy(REPO / 'docs/CLAUDE.en.md', self._dest('docs/CLAUDE.en.md'))

    def test_migrate_preview_notice_names_the_kept_rule_files(self):
        self._old_rule_files()
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('setup.sh', run.stdout)
        self.assertIn('.youngcrow/HARNESS.md', run.stdout)
        self.assertIn('by hand', run.stdout)
        notice = run.stdout[run.stdout.index('Note:'):]
        self.assertIn('  CLAUDE.md', notice)
        self.assertIn('  AGENTS.md', notice)
        self.assertNotIn('docs/CLAUDE.en.md', notice)  # unmodified: migrate removes it

    def test_migrate_preview_json_has_legacy_rules(self):
        self._old_rule_files()
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual(report['legacy_rules'], ['AGENTS.md', 'CLAUDE.md'])
        self.assertEqual(report['matches'], ['docs/CLAUDE.en.md'])
        self.assertEqual(report['modified'], ['AGENTS.md', 'CLAUDE.md'])

    def test_migrate_confirm_keeps_the_rule_files_and_says_to_trim_them(self):
        self._old_rule_files()
        run = self._cli('migrate', '--root', str(self.root), '--confirm')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('Note:', run.stdout)
        self.assertIn('  CLAUDE.md', run.stdout[run.stdout.index('Note:'):])
        self.assertTrue((self.root / 'AGENTS.md').read_text().startswith('# Mine\n\nOld harness rules'))
        self.assertFalse((self.root / 'docs/CLAUDE.en.md').exists())
        report = json.loads(self._cli('undo', '--root', str(self.root), '--json').stdout)
        self.assertIn('CLAUDE.md', report['written'] + report['kept_modified'])

    def test_migrate_confirm_json_has_legacy_rules_and_no_notice_text(self):
        self._old_rule_files()
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        report = json.loads(run.stdout)
        self.assertEqual(report['legacy_rules'], ['AGENTS.md', 'CLAUDE.md'])
        self.assertEqual(report['applied'], True)
        for text in ('Note:', 'setup.sh', 'by hand', 'HARNESS.md'):
            self.assertNotIn(text, run.stdout)
        self.assertEqual(run.stderr, '')

    def test_no_notice_when_the_rule_files_are_unmodified_or_absent(self):
        shutil.copy(REPO / 'CLAUDE.md', self._dest('CLAUDE.md'))
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Note:', run.stdout)
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual(report['matches'], ['CLAUDE.md'])
        self.assertEqual(report['legacy_rules'], [])

    def test_a_modified_docs_claude_en_is_a_legacy_rule_file_too(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('docs/CLAUDE.en.md', b'# Mine\n')
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual(report['legacy_rules'], ['docs/CLAUDE.en.md'])
        self.assertEqual(report['matches'], ['scripts/vault.py'])

    def test_a_modified_file_that_is_not_a_rule_file_gets_no_notice(self):
        self._legacy('scripts/memory.py', b'# my change\n')
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Note:', run.stdout)

    # A project setup.sh never touched: its own files at legacy paths are not called setup.sh copies.

    def test_without_any_setup_sh_copy_nothing_is_listed_as_changed_or_legacy(self):
        self._legacy('CLAUDE.md', b'# My own rules\n')
        self._legacy('scripts/vault.py', b'# my own vault script\n')
        preview = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(preview.stdout.splitlines(),
                         ['Preview only, nothing was changed. Add --confirm to migrate.', 'No setup.sh install found.'])
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual((report['matches'], report['modified'], report['legacy_rules']), ([], [], []))
        done = self._cli('migrate', '--root', str(self.root), '--confirm')
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.splitlines()
        self.assertIn('No setup.sh install found.', lines)
        for text in ('Kept (you changed these):', 'Note:', 'setup.sh install and still'):
            self.assertNotIn(text, done.stdout)
        self.assertTrue((self.root / 'CLAUDE.md').read_text().startswith('# My own rules\n'))

    # R30: what still points at the files migrate removes, and the vault check after it.

    def _setup_sh_project(self):
        """The vault setup.sh created (the repository's own vault/ is that template), the skills and
        scripts it links to or names, and a .claude/settings.json the person merged with their own."""
        for rel in ('vault/index.md', 'vault/integrations/index.md', 'vault/capabilities/index.md',
                    'scripts/integrations.py', 'scripts/source_prompt.py', 'scripts/vault.py',
                    *(f'skills/{name}/SKILL.md' for name in (
                        'govern-capabilities', 'personalizer', 'integrate-from-docs', 'ingest-source',
                        'retrieve-memory', 'yc-personalizer', 'yc-config', 'yc-missao', 'yc-status'))):
            shutil.copy(REPO / rel, self._dest(rel))
        settings = json.loads((REPO / '.claude/settings.json').read_text(encoding='utf-8'))
        settings['permissions'] = {'allow': ['Bash(make test)']}
        self._legacy('.claude/settings.json', json.dumps(settings, indent=2).encode() + b'\n')

    def test_migrate_names_the_files_that_point_at_what_it_removes(self):
        self._setup_sh_project()
        for args in ((), ('--confirm',)):
            run = self._cli('migrate', '--root', str(self.root), '--json', *args)
            self.assertEqual(run.returncode, 0, run.stderr)
            refs = json.loads(run.stdout)['dangling_references']
            self.assertEqual(refs['.claude/settings.json'], ['scripts/source_prompt.py'], args)
            self.assertEqual(refs['vault/integrations/index.md'], ['scripts/integrations.py'], args)
            self.assertIn('skills/govern-capabilities/SKILL.md', refs['vault/capabilities/index.md'], args)
            self.assertEqual(sorted(refs), ['.claude/settings.json', 'vault/capabilities/index.md',
                                            'vault/integrations/index.md'], args)

    def test_migrate_confirm_runs_the_vault_check_and_reports_it(self):
        self._setup_sh_project()
        preview = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertIsNone(preview['vault_check'])
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        check = json.loads(run.stdout)['vault_check']
        direct = subprocess.run([sys.executable, '-B', '.youngcrow/scripts/vault.py', 'check'], cwd=self.root,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(check, {'exit_code': 1, 'summary': direct.stdout.splitlines()[-1]})
        self.assertNotIn(' 0 issues', check['summary'])
        self.assertEqual(sorted(p.name for p in self.root.rglob('__pycache__')), [])

    def test_migrate_plain_output_shows_the_references_and_the_check(self):
        self._setup_sh_project()
        preview = self._cli('migrate', '--root', str(self.root))
        section = preview.stdout[preview.stdout.index('These files still point at files migrate removes:'):]
        self.assertIn('  .claude/settings.json: scripts/source_prompt.py', section)
        self.assertIn('  vault/integrations/index.md: scripts/integrations.py', section)
        self.assertNotIn('Vault: ', preview.stdout)
        done = self._cli('migrate', '--root', str(self.root), '--confirm')
        self.assertIn('These files still point at files migrate removes:', done.stdout)
        summary = [line for line in done.stdout.splitlines() if line.startswith('Vault: ')]
        self.assertEqual(len(summary), 1, done.stdout)
        self.assertRegex(summary[0], r'^Vault: 3 notes checked; [1-9]\d* issues\. No files changed\.$')

    def test_a_clean_migrate_has_no_references_and_a_clean_vault_check(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        report = json.loads(run.stdout)
        self.assertEqual(report['dangling_references'], {})
        self.assertEqual(report['vault_check']['exit_code'], 0)
        plain = self._cli('undo', '--root', str(self.root), '--confirm')
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(self._tree(), {})

    def test_migrate_confirm_with_a_relative_root_checks_that_project(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        run = self._cli('migrate', '--root', self.root.name, '--confirm', '--json', cwd=self.root.parent)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['vault_check'],
                         {'exit_code': 0, 'summary': 'Vault: 3 notes checked; 0 issues. No files changed.'})


if __name__ == '__main__':
    unittest.main()
