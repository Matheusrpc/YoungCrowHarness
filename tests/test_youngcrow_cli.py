"""Check the `youngcrow` command line: what each command prints, and the exit code of each outcome."""
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
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
        self.assertEqual(list(report), REPORT_KEYS)
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

    # Refusals: exit 3 and the message on stderr.

    def assertRefused(self, run, *words):
        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
        self.assertEqual(run.stdout, '')
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
        self.assertRefused(self._cli('init', '--root', str(self.root)), 'youngcrow:start', 'no matching')
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

    def test_migrate_confirm_refuses_a_project_that_is_already_set_up(self):
        self._init()
        self.assertRefused(self._cli('migrate', '--root', str(self.root), '--confirm'), 'manifest.json')

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
            'applied': False, 'matches': ['scripts/vault.py'], 'modified': ['scripts/memory.py'], 'legacy_rules': []})

    def test_migrate_confirm_removes_the_matches_and_installs(self):
        shutil.copy(REPO / 'scripts/vault.py', self._dest('scripts/vault.py'))
        self._legacy('scripts/memory.py', b'# my change\n')
        run = self._cli('migrate', '--root', str(self.root), '--confirm', '--json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {
            'applied': True, 'matches': ['scripts/vault.py'], 'modified': ['scripts/memory.py'], 'legacy_rules': []})
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

    def test_no_notice_when_the_rule_files_are_unmodified_or_absent(self):
        shutil.copy(REPO / 'CLAUDE.md', self._dest('CLAUDE.md'))
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Note:', run.stdout)
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual(report['matches'], ['CLAUDE.md'])
        self.assertEqual(report['legacy_rules'], [])

    def test_a_modified_docs_claude_en_is_a_legacy_rule_file_too(self):
        self._legacy('docs/CLAUDE.en.md', b'# Mine\n')
        report = json.loads(self._cli('migrate', '--root', str(self.root), '--json').stdout)
        self.assertEqual(report['legacy_rules'], ['docs/CLAUDE.en.md'])
        self.assertEqual(report['matches'], [])

    def test_a_modified_file_that_is_not_a_rule_file_gets_no_notice(self):
        self._legacy('scripts/memory.py', b'# my change\n')
        run = self._cli('migrate', '--root', str(self.root))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Note:', run.stdout)


if __name__ == '__main__':
    unittest.main()
