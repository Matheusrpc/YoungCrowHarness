"""Check `youngcrow migrate` finds what setup.sh copied, removes only the unmodified copies, and installs the new layout."""
from contextlib import redirect_stderr, redirect_stdout
from importlib import util
from importlib.resources import files
from pathlib import Path
from unittest import mock
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))

from youngcrow.install import AlreadyInitialized, init  # noqa: E402
from youngcrow.manifest import load, sha256_file  # noqa: E402
from youngcrow.migrate import (  # noqa: E402
    LEGACY_PATHS, MigrationPreview, apply, dangling_references, is_legacy_path, legacy_hashes, scan, vault_check,
)
from youngcrow.settings import WIRING  # noqa: E402

FOLDERS = {'skills/*', '.claude/skills/*', '.agents/skills/*'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root):
    """Every file and folder under root: relative path -> (bytes, permission bits); None for a folder."""
    result = {}
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[rel] = ('link', os.readlink(path))
        elif path.is_file():
            result[rel] = (path.read_bytes(), stat.S_IMODE(path.lstat().st_mode))
        else:
            result[rel] = None
    return result


def setup_sh_files():
    """Every name in the FILES arrays of setup.sh, both client branches."""
    text = (REPO / 'setup.sh').read_text(encoding='utf-8')
    return [name for match in re.finditer(r'\bFILES\+?=\((.*?)\)', text, re.S) for name in match[1].split()]


class TableTests(unittest.TestCase):
    """The paths migrate looks at and the table of published hashes that ships in the package."""

    def test_table_covers_current_main_versions(self):
        table = json.loads(files('youngcrow').joinpath('legacy_hashes.json').read_text())
        self.assertIn(sha256_file(REPO / 'scripts/vault.py'), table['scripts/vault.py'])

    def test_legacy_paths_are_the_setup_sh_files_plus_the_skill_folders(self):
        self.assertEqual(len(LEGACY_PATHS), len(set(LEGACY_PATHS)))
        self.assertLessEqual(FOLDERS, set(LEGACY_PATHS))
        self.assertEqual(set(LEGACY_PATHS) - FOLDERS, {name for name in setup_sh_files() if not name.startswith('vault/')})
        for name in ('.mcp.json', '.claude/settings.json', '.codex/hooks.json', '.agents/skills/personalizer/SKILL.md',
                     'skills-lock.json', 'docs/CLAUDE.en.md', 'scripts/mission_runs.py'):
            self.assertIn(name, LEGACY_PATHS)

    def test_legacy_paths_never_include_the_vault(self):
        self.assertEqual([p for p in LEGACY_PATHS if p == 'vault' or p.startswith('vault/')], [])
        self.assertFalse(is_legacy_path('vault/index.md'))
        self.assertFalse(is_legacy_path('vault/integrations/index.md'))

    def test_is_legacy_path(self):
        for rel in ('scripts/vault.py', '.mcp.json', 'skills/mine/SKILL.md', 'skills/a/b/c.md',
                    '.claude/skills/x/SKILL.md', '.agents/skills/x/references/y.md'):
            self.assertTrue(is_legacy_path(rel), rel)
        for rel in ('README.md', 'scripts/mine.py', 'skills', 'src/skills/a.md', '.claude/settings.local.json',
                    'vault/notes/a.md', '.youngcrow/scripts/vault.py'):
            self.assertFalse(is_legacy_path(rel), rel)

    def test_committed_table_has_the_expected_shape(self):
        table = legacy_hashes()
        self.assertEqual(list(table), sorted(table))
        self.assertEqual([rel for rel in table if not is_legacy_path(rel)], [])
        self.assertEqual([rel for rel in table if rel.startswith('vault/')], [])
        for rel, hashes in table.items():
            self.assertTrue(hashes, rel)
            self.assertEqual(hashes, sorted(set(hashes)), rel)
            self.assertTrue(all(re.fullmatch(r'[0-9a-f]{64}', value) for value in hashes), rel)
        for rel in ('scripts/vault.py', 'scripts/memory.py', 'skills-lock.json', '.claude/settings.json'):
            self.assertIn(rel, table)

    def test_the_agents_copy_of_humanizer_ptbr_has_the_hashes_of_the_skills_one(self):
        table = legacy_hashes()
        self.assertEqual(table['.agents/skills/humanizer-ptbr/SKILL.md'], table['skills/humanizer-ptbr/SKILL.md'])


class RealTableTests(unittest.TestCase):
    """scan and apply against the table that ships in the package."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'project'
        self.root.mkdir()

    def test_scan_and_apply_keep_modified(self):
        for rel in ('scripts/vault.py', 'scripts/memory.py'):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.root / rel)
        (self.root / 'scripts/memory.py').write_text('# my change\n')
        preview = scan(self.root)
        self.assertEqual(preview.matches, ['scripts/vault.py'])
        self.assertEqual(preview.modified, ['scripts/memory.py'])
        apply(self.root, preview)
        self.assertFalse((self.root / 'scripts/vault.py').exists())
        self.assertTrue((self.root / 'scripts/memory.py').exists())
        self.assertIsNotNone(load(self.root))

    def test_files_that_are_not_in_the_table_are_ignored(self):
        for rel, data in (('scripts/mine.py', b'mine\n'), ('skills/mine/SKILL.md', b'mine\n'), ('README.md', b'mine\n'),
                          ('.agents/skills/humanizer/SKILL.md', b'upstream clone\n')):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(data)
        self.assertEqual(scan(self.root), MigrationPreview([], []))

    def test_an_empty_project_has_nothing_to_migrate(self):
        self.assertEqual(scan(self.root), MigrationPreview([], []))

    def test_the_humanizer_ptbr_copy_in_agents_skills_is_matched_and_removed(self):
        for rel, source in (('.agents/skills/humanizer-ptbr/SKILL.md', REPO / 'skills/humanizer-ptbr/SKILL.md'),
                            ('.agents/skills/humanizer/SKILL.md', None)):
            (self.root / rel).parent.mkdir(parents=True)
            if source:
                shutil.copy(source, self.root / rel)
            else:
                (self.root / rel).write_text('upstream clone\n')
        preview = scan(self.root)
        self.assertEqual(preview, MigrationPreview(['.agents/skills/humanizer-ptbr/SKILL.md'], []))
        report = apply(self.root, preview)
        self.assertFalse((self.root / '.agents/skills/humanizer-ptbr').exists())
        self.assertIn('.agents/skills/humanizer-ptbr/', report.removed)
        self.assertTrue((self.root / '.agents/skills/humanizer/SKILL.md').is_file())


class MigrateTests(unittest.TestCase):
    """scan and apply against a table made for the test, so they do not depend on the repository's files."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / 'project'
        self.other = self.tmp / 'other'
        self.root.mkdir()
        self.other.mkdir()
        self.table = {}
        patcher = mock.patch('youngcrow.migrate.legacy_hashes', side_effect=lambda: self.table)
        patcher.start()
        self.addCleanup(patcher.stop)

    def publish(self, rel, data=b'published\n'):
        """Record `data` as a version the harness published for `rel`, and return it."""
        self.table[rel] = sorted({*self.table.get(rel, ()), sha(data)})
        return data

    def put(self, rel, data, mode=None):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if mode is not None:
            os.chmod(path, mode)
        return path

    def legacy(self, rel, data=b'published\n', mode=None):
        """A project file that setup.sh copied and nobody touched."""
        self.publish(rel, data)
        return self.put(rel, data, mode)

    def symlink(self, target, link, directory=False):
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')

    # What scan finds.

    def test_scan_sorts_matches_and_modified_and_ignores_the_rest(self):
        self.legacy('scripts/vault.py')
        self.legacy('.mcp.json')
        self.legacy('skills/personalizer/SKILL.md')
        self.publish('scripts/memory.py', b'published memory\n')
        self.put('scripts/memory.py', b'my change\n')
        self.publish('scripts/capabilities.py')
        self.put('scripts/capabilities.py', b'published\nplus mine\n')
        self.put('scripts/mine.py', b'not harness\n')
        preview = scan(self.root)
        self.assertEqual(preview.matches, ['.mcp.json', 'scripts/vault.py', 'skills/personalizer/SKILL.md'])
        self.assertEqual(preview.modified, ['scripts/capabilities.py', 'scripts/memory.py'])

    def test_any_published_version_matches(self):
        self.publish('scripts/vault.py', b'old release\n')
        self.legacy('scripts/vault.py', b'newer release\n')
        self.assertEqual(scan(self.root).matches, ['scripts/vault.py'])

    def test_a_missing_legacy_file_is_not_listed(self):
        self.publish('scripts/vault.py')
        self.assertEqual(scan(self.root), MigrationPreview([], []))

    def test_scan_is_read_only(self):
        self.legacy('scripts/vault.py')
        self.put('scripts/memory.py', b'mine\n')
        self.publish('scripts/memory.py', b'other\n')
        before = snapshot(self.root)
        scan(self.root)
        self.assertEqual(snapshot(self.root), before)

    def test_scan_never_lists_the_vault(self):
        # Even a table that (wrongly) holds vault keys cannot make migrate touch the notes (R22).
        for rel in ('vault/index.md', 'vault/integrations/index.md', 'vault/notes/decision.md'):
            self.legacy(rel)
        self.legacy('scripts/vault.py')
        self.assertEqual(scan(self.root), MigrationPreview(['scripts/vault.py'], []))

    def test_apply_keeps_every_vault_note(self):
        for rel in ('vault/index.md', 'vault/notes/decision.md'):
            self.legacy(rel)
        self.legacy('scripts/vault.py')
        before = {rel: snapshot(self.root)[rel] for rel in ('vault/index.md', 'vault/notes/decision.md')}
        apply(self.root, scan(self.root))
        after = snapshot(self.root)
        self.assertEqual({rel: after[rel] for rel in before}, before)

    def test_a_symlinked_legacy_file_is_neither_a_match_nor_deleted(self):
        data = self.publish('scripts/vault.py')
        (self.other / 'vault.py').write_bytes(data)
        (self.root / 'scripts').mkdir()
        self.symlink(self.other / 'vault.py', self.root / 'scripts/vault.py')
        preview = scan(self.root)
        self.assertEqual(preview, MigrationPreview([], []))
        # Even a preview that names the link by hand does not get it removed.
        apply(self.root, MigrationPreview(['scripts/vault.py'], []))
        self.assertTrue((self.root / 'scripts/vault.py').is_symlink())
        self.assertEqual((self.other / 'vault.py').read_bytes(), data)

    def test_files_behind_a_symlinked_folder_are_neither_a_match_nor_deleted(self):
        data = self.publish('skills/personalizer/SKILL.md')
        (self.other / 'personalizer').mkdir()
        (self.other / 'personalizer/SKILL.md').write_bytes(data)
        self.symlink(self.other, self.root / 'skills', directory=True)
        self.assertEqual(scan(self.root), MigrationPreview([], []))
        apply(self.root, MigrationPreview(['skills/personalizer/SKILL.md'], []))
        self.assertEqual((self.other / 'personalizer/SKILL.md').read_bytes(), data)
        self.assertTrue((self.root / 'skills').is_symlink())

    def test_a_legacy_file_that_cannot_be_read_is_modified_and_does_not_stop_the_scan(self):
        self.legacy('scripts/vault.py')
        self.legacy('scripts/memory.py')
        self.legacy('.mcp.json')
        real = sha256_file

        def reading(path):
            if Path(path).name == 'memory.py':
                raise PermissionError(13, 'Permission denied')
            return real(path)

        with mock.patch('youngcrow.migrate.sha256_file', reading):
            preview = scan(self.root)
            self.assertEqual(preview, MigrationPreview(['.mcp.json', 'scripts/vault.py'], ['scripts/memory.py']))
            report = apply(self.root, preview)
        self.assertTrue((self.root / 'scripts/memory.py').is_file())
        self.assertEqual(report.kept_modified, ['scripts/memory.py'])

    def test_a_file_the_operating_system_will_not_let_us_read_is_modified(self):
        path = self.legacy('scripts/memory.py')
        self.legacy('scripts/vault.py')
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        if os.access(path, os.R_OK):
            self.skipTest('this user can read any file (root), so the permission cannot be tested')
        self.assertEqual(scan(self.root), MigrationPreview(['scripts/vault.py'], ['scripts/memory.py']))

    def test_a_folder_in_place_of_a_legacy_file_is_skipped(self):
        self.publish('scripts/vault.py')
        (self.root / 'scripts/vault.py').mkdir(parents=True)
        self.assertEqual(scan(self.root), MigrationPreview([], []))

    # What apply does.

    def test_apply_removes_every_unmodified_file_skills_included_and_installs(self):
        for rel in ('scripts/vault.py', 'skills/personalizer/SKILL.md', '.claude/skills/personalizer/SKILL.md',
                    '.agents/skills/personalizer/SKILL.md', 'skills-lock.json', '.codex/config.toml'):
            self.legacy(rel)
        self.publish('.claude/settings.json', b'published\n')
        self.put('.claude/settings.json', b'{"mine": true}\n')
        preview = scan(self.root)
        report = apply(self.root, preview)
        for rel in preview.matches:
            self.assertFalse((self.root / rel).exists(), rel)
            self.assertIn(rel, report.removed)
        self.assertEqual(preview.modified, ['.claude/settings.json'])
        # Kept, with the plugin wired in after the user's own key; init saved the bytes it found.
        self.assertEqual(json.loads((self.root / '.claude/settings.json').read_bytes()), {'mine': True, **WIRING})
        self.assertEqual((self.root / '.youngcrow/originals/.claude/settings.json').read_bytes(), b'{"mine": true}\n')
        self.assertEqual(report.kept_modified, ['.claude/settings.json'])
        self.assertIn('.youngcrow/scripts/vault.py', report.written)
        self.assertTrue((self.root / '.youngcrow/scripts/vault.py').is_file())
        self.assertEqual(load(self.root).client, 'both')

    def test_unmodified_legacy_client_files_are_removed_and_written_anew(self):
        settings, agent = '.claude/settings.json', '.codex/agents/integration-specialist.toml'
        self.legacy(settings, b'{"hooks": {"old": []}}\n')
        self.legacy(agent, b'name = "old"\n')
        report = apply(self.root, scan(self.root))
        self.assertEqual(json.loads((self.root / settings).read_bytes()), WIRING)
        self.assertEqual((self.root / agent).read_bytes(),
                         files('youngcrow').joinpath('templates/codex/integration-specialist.toml').read_bytes())
        manifest = load(self.root)
        for rel in (settings, agent):
            self.assertIn(rel, report.removed)
            self.assertIn(rel, report.written)
            self.assertIn(rel, manifest.created)
        self.assertFalse((self.root / '.youngcrow/originals').exists())

    def test_apply_removes_the_folders_it_empties_and_only_those(self):
        self.legacy('scripts/vault.py')
        self.legacy('skills/personalizer/SKILL.md')
        self.legacy('skills/personalizer/references/interview.md')
        self.legacy('.agents/skills/personalizer/SKILL.md')
        self.put('.agents/skills/humanizer/SKILL.md', b'upstream clone\n')
        self.put('scripts/mine.py', b'mine\n')
        report = apply(self.root, scan(self.root))
        self.assertFalse((self.root / 'skills').exists())
        self.assertFalse((self.root / '.agents/skills/personalizer').exists())
        self.assertTrue((self.root / '.agents/skills/humanizer/SKILL.md').is_file())
        self.assertTrue((self.root / 'scripts/mine.py').is_file())
        self.assertEqual(sorted(rel for rel in report.removed if rel.endswith('/')),
                         ['.agents/skills/personalizer/', 'skills/', 'skills/personalizer/',
                          'skills/personalizer/references/'])

    def test_apply_with_nothing_to_remove_just_installs(self):
        report = apply(self.root, scan(self.root))
        self.assertEqual(report.removed, [])
        self.assertEqual(report.kept_modified, [])
        self.assertIn('.youngcrow/VERSION', report.written)
        self.assertIsNotNone(load(self.root))

    def test_apply_passes_the_client_to_init(self):
        self.legacy('scripts/vault.py')
        apply(self.root, scan(self.root), client='codex')
        self.assertEqual(load(self.root).client, 'codex')
        self.assertTrue((self.root / 'AGENTS.md').is_file())
        self.assertFalse((self.root / 'CLAUDE.md').exists())

    def test_a_legacy_claude_md_is_replaced_by_one_that_imports_the_harness(self):
        self.legacy('CLAUDE.md', b'# Rules as setup.sh copied them\n')
        self.legacy('AGENTS.md', b'# Agents as setup.sh copied them\n')
        report = apply(self.root, scan(self.root))
        self.assertEqual((self.root / 'CLAUDE.md').read_text().count('@.youngcrow/HARNESS.md'), 1)
        self.assertNotIn('as setup.sh copied', (self.root / 'CLAUDE.md').read_text())
        self.assertNotIn('as setup.sh copied', (self.root / 'AGENTS.md').read_text())
        self.assertIn('CLAUDE.md', report.removed)
        self.assertIn('CLAUDE.md', report.written)
        manifest = load(self.root)
        self.assertIn('CLAUDE.md', manifest.created)
        self.assertEqual(manifest.files['CLAUDE.md'], sha256_file(self.root / 'CLAUDE.md'))

    def test_a_modified_claude_md_is_kept_and_gets_the_import_line(self):
        self.publish('CLAUDE.md', b'# Rules as setup.sh copied them\n')
        self.put('CLAUDE.md', b'# My rules\n')
        report = apply(self.root, scan(self.root))
        text = (self.root / 'CLAUDE.md').read_text()
        self.assertTrue(text.startswith('# My rules\n'))
        self.assertEqual(text.count('@.youngcrow/HARNESS.md'), 1)
        self.assertEqual(report.kept_modified, ['CLAUDE.md'])

    def test_apply_refuses_when_the_project_is_already_set_up(self):
        init(self.root)
        self.legacy('scripts/vault.py')
        preview = scan(self.root)
        before = snapshot(self.root)
        with self.assertRaises(AlreadyInitialized):
            apply(self.root, preview)
        self.assertEqual(snapshot(self.root), before)

    def test_apply_refuses_before_removing_anything_when_init_would_refuse(self):
        self.legacy('scripts/vault.py')
        self.put('CLAUDE.md', b'x\n')
        self.symlink(self.other, self.root / '.youngcrow', directory=True)
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            apply(self.root, scan(self.root))
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(list(self.other.iterdir()), [])

    def test_apply_refuses_a_path_that_is_not_a_legacy_file(self):
        self.put('README.md', b'mine\n')
        for rel in ('README.md', 'vault/index.md', '../outside.md'):
            with self.subTest(rel), self.assertRaises(ValueError):
                apply(self.root, MigrationPreview([rel], []))
        self.assertEqual((self.root / 'README.md').read_bytes(), b'mine\n')
        self.assertFalse((self.root / '.youngcrow').exists())

    def test_a_file_the_user_changed_after_the_scan_is_kept(self):
        self.legacy('scripts/vault.py')
        self.legacy('scripts/memory.py')
        preview = scan(self.root)
        self.put('scripts/vault.py', b'edited after the scan\n')
        report = apply(self.root, preview)
        self.assertEqual((self.root / 'scripts/vault.py').read_bytes(), b'edited after the scan\n')
        self.assertFalse((self.root / 'scripts/memory.py').exists())
        self.assertEqual(report.kept_modified, ['scripts/vault.py'])
        self.assertNotIn('scripts/vault.py', report.removed)

    def test_a_file_that_is_gone_since_the_scan_is_not_an_error(self):
        self.legacy('scripts/vault.py')
        self.legacy('scripts/memory.py')
        preview = scan(self.root)
        (self.root / 'scripts/vault.py').unlink()
        report = apply(self.root, preview)
        self.assertEqual([rel for rel in report.removed if not rel.endswith('/')], ['scripts/memory.py'])

    def test_a_file_that_matches_only_after_the_scan_is_not_removed(self):
        self.publish('scripts/vault.py')
        self.put('scripts/vault.py', b'my change\n')
        preview = scan(self.root)
        self.put('scripts/vault.py', b'published\n')
        apply(self.root, preview)
        self.assertTrue((self.root / 'scripts/vault.py').is_file())

    # A failure in the middle puts everything back.

    def legacy_project(self):
        self.legacy('CLAUDE.md', b'# Rules as setup.sh copied them\n')
        self.legacy('scripts/vault.py', b'#!/usr/bin/env python3\n', mode=0o755)
        self.legacy('.claude/skills/personalizer/SKILL.md')
        self.legacy('.claude/skills/personalizer/references/interview.md')
        self.legacy('skills/personalizer/SKILL.md')
        self.legacy('.mcp.json', b'{}\n')
        self.publish('scripts/memory.py', b'published\n')
        self.put('scripts/memory.py', b'my change\n')
        return snapshot(self.root)

    def test_a_failed_write_restores_the_removed_files_byte_for_byte(self):
        before = self.legacy_project()
        real = os.replace

        def replace(source, destination):
            if Path(destination).name == 'AGENTS.md':
                raise OSError('disk full')
            return real(source, destination)

        preview = scan(self.root)
        with mock.patch('os.replace', replace), self.assertRaises(OSError):
            apply(self.root, preview)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(scan(self.root), preview)

    def test_a_failed_manifest_save_restores_files_and_removed_folders(self):
        before = self.legacy_project()
        preview = scan(self.root)
        with mock.patch('youngcrow.install.save', side_effect=OSError('disk full')), self.assertRaises(OSError):
            apply(self.root, preview)
        self.assertEqual(snapshot(self.root), before)
        self.assertTrue((self.root / '.claude/skills/personalizer/references').is_dir())

    def test_a_project_restored_after_a_failure_migrates_on_the_next_run(self):
        self.legacy_project()
        with mock.patch('youngcrow.install.save', side_effect=OSError('disk full')), self.assertRaises(OSError):
            apply(self.root, scan(self.root))
        report = apply(self.root, scan(self.root))
        self.assertIn('scripts/vault.py', report.removed)
        self.assertIsNotNone(load(self.root))


class ReferenceTests(unittest.TestCase):
    """dangling_references: which kept files and vault notes still name a file migrate removes."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'project'
        self.root.mkdir()

    def put(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_links_commands_and_hooks_count_as_references(self):
        self.put('vault/capabilities/index.md', '| x | [Skill](../../skills/a/SKILL.md) |\n')
        self.put('vault/integrations/index.md', '```bash\npython3 scripts/integrations.py init\n```\n')
        self.put('.claude/settings.json', '{"command": "python3 \\"$CLAUDE_PROJECT_DIR/scripts/hook.py\\""}\n')
        self.put('CLAUDE.md', "Run `scripts/vault.py check`; see skills/a/SKILL.md.\n")
        found = dangling_references(self.root, ['skills/a/SKILL.md', 'scripts/integrations.py', 'scripts/hook.py',
                                                'scripts/vault.py'], ['.claude/settings.json', 'CLAUDE.md'])
        self.assertEqual(found, {
            '.claude/settings.json': ['scripts/hook.py'],
            'CLAUDE.md': ['scripts/vault.py', 'skills/a/SKILL.md'],
            'vault/capabilities/index.md': ['skills/a/SKILL.md'],
            'vault/integrations/index.md': ['scripts/integrations.py'],
        })

    def test_a_longer_path_that_ends_the_same_is_not_a_reference(self):
        self.put('vault/index.md', 'Run .youngcrow/scripts/vault.py check. See .claude/skills/a/SKILL.md, '
                                   'scripts/vault.pyc and scripts/vault.py.bak.\n')
        self.assertEqual(dangling_references(self.root, ['scripts/vault.py', 'skills/a/SKILL.md'], []), {})

    def test_only_markdown_notes_under_the_vault_and_the_kept_files_are_read(self):
        self.put('vault/notes/data.json', '"scripts/vault.py"\n')
        self.put('README.md', 'scripts/vault.py\n')
        self.put('vault/notes/a.md', 'scripts/vault.py\n')
        self.assertEqual(dangling_references(self.root, ['scripts/vault.py'], []), {'vault/notes/a.md': ['scripts/vault.py']})

    def test_links_and_files_that_cannot_be_read_as_text_are_skipped(self):
        outside = Path(self.root.parent) / 'outside.md'
        outside.write_text('scripts/vault.py\n')
        self.put('vault/a.md', 'scripts/vault.py\n')
        (self.root / 'vault/b.md').write_bytes(b'\xff scripts/vault.py\n')  # bytes that are not UTF-8 still read
        try:
            os.symlink(outside, self.root / 'vault/linked.md')
            os.symlink(outside.parent, self.root / 'vault/linked-folder', target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')
        before = snapshot(self.root)
        found = dangling_references(self.root, ['scripts/vault.py'], ['vault/linked.md', 'missing.json'])
        self.assertEqual(found, {'vault/a.md': ['scripts/vault.py'], 'vault/b.md': ['scripts/vault.py']})
        self.assertEqual(snapshot(self.root), before)

    def test_the_youngcrow_block_is_the_installers_text_and_does_not_count(self):
        self.put('AGENTS.md', '# Mine\n\n<!-- youngcrow:start -->\n`.env.example` holds fake values only.\n'
                              '<!-- youngcrow:end -->\n')
        self.assertEqual(dangling_references(self.root, ['.env.example'], ['AGENTS.md']), {})
        self.put('AGENTS.md', '# Mine\n\nCopy .env.example first.\n<!-- youngcrow:start -->\nno end\n')
        self.assertEqual(dangling_references(self.root, ['.env.example'], ['AGENTS.md']), {'AGENTS.md': ['.env.example']})

    def test_nothing_removed_means_nothing_to_report(self):
        self.put('vault/index.md', 'scripts/vault.py\n')
        self.assertEqual(dangling_references(self.root, [], ['vault/index.md']), {})

    def test_vault_check_reports_the_exit_code_and_the_summary_line(self):
        init(self.root)
        self.assertEqual(vault_check(self.root),
                         {'exit_code': 0, 'summary': 'Vault: 3 notes checked; 0 issues. No files changed.'})
        self.put('vault/notes/a.md', '[gone](missing.md)\n')
        result = vault_check(self.root)
        self.assertEqual(result['exit_code'], 1)
        self.assertRegex(result['summary'], r'^Vault: \d+ notes checked; [1-9]\d* issues\. No files changed\.$')

    def test_vault_check_that_cannot_run_says_so(self):
        init(self.root)
        with mock.patch('subprocess.run', side_effect=OSError(2, 'No such file or directory')):
            result = vault_check(self.root)
        self.assertIsNone(result['exit_code'])
        self.assertIn('No such file or directory', result['summary'])


def load_tool():
    spec = util.spec_from_file_location('legacy_hashes_tool', REPO / 'tools' / 'legacy_hashes.py')
    tool = util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def git(repo, *args):
    return subprocess.run(
        ['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
         '-c', 'commit.gpgsign=false', *args],
        check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(shutil.which('git'), 'git is not available')
class LegacyHashesToolTests(unittest.TestCase):
    """`tools/legacy_hashes.py` builds the table from the history of one ref."""

    VERSIONS = {name: f'{name} version\n'.encode() for name in ('a', 'b', 'c', 'skill', 'agents', 'note', 'side')}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'history'
        self.repo.mkdir()
        self.tool = load_tool()
        git(self.repo, 'init', '-q')
        git(self.repo, 'symbolic-ref', 'HEAD', 'refs/heads/main')

    def commit(self, message, put=(), remove=()):
        for rel, data in put:
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_bytes(data)
        for rel in remove:
            (self.repo / rel).unlink()
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', message)

    def make_history(self):
        v = self.VERSIONS
        self.commit('one', put=[('scripts/vault.py', v['a']), ('vault/index.md', v['note']), ('README.md', v['a']),
                                ('skills/x/SKILL.md', v['skill'])])
        self.commit('two', put=[('scripts/vault.py', v['b'])])
        git(self.repo, 'checkout', '-q', '-b', 'feature')
        self.commit('side', put=[('scripts/vault.py', v['side']), ('scripts/memory.py', v['side'])])
        git(self.repo, 'checkout', '-q', 'main')
        self.commit('three', put=[('scripts/vault.py', v['a']), ('.agents/skills/y/SKILL.md', v['agents']),
                                  ('scripts/mine.py', v['c'])], remove=['skills/x/SKILL.md'])

    def test_every_version_a_legacy_path_had_on_the_ref(self):
        self.make_history()
        v = self.VERSIONS
        table = self.tool.build_table(self.repo, 'main')
        self.assertEqual(table, {
            '.agents/skills/y/SKILL.md': [sha(v['agents'])],
            'scripts/vault.py': sorted([sha(v['a']), sha(v['b'])]),
            'skills/x/SKILL.md': [sha(v['skill'])],
        })

    def test_history_outside_the_ref_does_not_count(self):
        self.make_history()
        table = self.tool.build_table(self.repo, 'main')
        self.assertNotIn(sha(self.VERSIONS['side']), json.dumps(table))
        self.assertNotIn('scripts/memory.py', table)
        self.assertIn('scripts/memory.py', self.tool.build_table(self.repo, 'feature'))

    def test_the_vault_and_other_files_are_not_in_the_table(self):
        self.make_history()
        table = self.tool.build_table(self.repo, 'main')
        self.assertEqual([rel for rel in table if rel.startswith('vault/') or rel in ('README.md', 'scripts/mine.py')], [])

    def test_output_is_deterministic(self):
        self.make_history()
        first = self.tool.render(self.tool.build_table(self.repo, 'main'))
        second = self.tool.render(self.tool.build_table(self.repo, 'main'))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith('}\n'))
        data = json.loads(first)
        self.assertEqual(first, json.dumps(data, indent=2, sort_keys=True) + '\n')
        for hashes in data.values():
            self.assertEqual(hashes, sorted(hashes))

    def test_humanizer_ptbr_is_also_recorded_where_setup_sh_copied_it(self):
        v = self.VERSIONS
        self.commit('one', put=[('skills/humanizer-ptbr/SKILL.md', v['a']), ('skills/humanizer-ptbr/references/x.md', v['c'])])
        self.commit('two', put=[('skills/humanizer-ptbr/SKILL.md', v['b'])])
        table = self.tool.build_table(self.repo, 'main')
        both = sorted([sha(v['a']), sha(v['b'])])
        self.assertEqual(table['skills/humanizer-ptbr/SKILL.md'], both)
        self.assertEqual(table['.agents/skills/humanizer-ptbr/SKILL.md'], both)
        self.assertEqual(table['.agents/skills/humanizer-ptbr/references/x.md'], [sha(v['c'])])
        self.assertEqual([rel for rel in table if 'humanizer' in rel and rel.startswith('.claude')], [])

    def test_a_legacy_file_changed_but_not_committed_counts_too(self):
        self.make_history()
        v = self.VERSIONS
        edited = b'edited, not committed\n'
        (self.repo / 'scripts/vault.py').write_bytes(edited)
        table = self.tool.build_table(self.repo, 'main')
        self.assertEqual(table['scripts/vault.py'], sorted([sha(v['a']), sha(v['b']), sha(edited)]))
        # Only the working tree changed, so a build from the commit alone is what it was.
        git(self.repo, 'stash', '-q')
        self.assertEqual(self.tool.build_table(self.repo, 'main')['scripts/vault.py'], sorted([sha(v['a']), sha(v['b'])]))

    def test_new_untracked_legacy_files_count_but_ignored_and_other_files_do_not(self):
        self.make_history()
        self.commit('ignore', put=[('.gitignore', b'.agents/skills/humanizer/\n')])
        new = b'a skill nobody committed yet\n'
        for rel, data in (('skills/new/SKILL.md', new), ('.agents/skills/humanizer/SKILL.md', b'upstream clone\n'),
                          ('notes.txt', b'not harness\n'), ('vault/index.md', b'changed note\n'),
                          ('scripts/mine.py', b'mine\n')):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_bytes(data)
        table = self.tool.build_table(self.repo, 'main')
        self.assertEqual(table['skills/new/SKILL.md'], [sha(new)])
        self.assertEqual([rel for rel in table if 'humanizer' in rel or rel.startswith('vault/') or rel in (
            'notes.txt', 'scripts/mine.py')], [])
        self.assertNotIn(sha(self.VERSIONS['note']), json.dumps(table))

    def test_a_legacy_file_deleted_from_the_working_tree_keeps_its_history(self):
        self.make_history()
        v = self.VERSIONS
        (self.repo / 'scripts/vault.py').unlink()
        self.assertEqual(self.tool.build_table(self.repo, 'main')['scripts/vault.py'], sorted([sha(v['a']), sha(v['b'])]))

    def test_links_in_the_working_tree_are_never_followed(self):
        self.make_history()
        v = self.VERSIONS
        outside = self.repo.parent / 'outside'
        (outside / 'agents').mkdir(parents=True)
        (outside / 'agents/SKILL.md').write_bytes(b'behind a linked folder\n')
        (outside / 'config.json').write_bytes(b'behind a linked file\n')
        try:
            (self.repo / '.mcp.json').symlink_to(outside / 'config.json')
            shutil.rmtree(self.repo / '.agents/skills/y')
            (self.repo / '.agents/skills/y').symlink_to(outside / 'agents', target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')
        table = self.tool.build_table(self.repo, 'main')
        self.assertNotIn('.mcp.json', table)
        self.assertEqual(table['.agents/skills/y/SKILL.md'], [sha(v['agents'])])
        self.assertNotIn(sha(b'behind a linked folder\n'), json.dumps(table))
        self.assertNotIn(sha(b'behind a linked file\n'), json.dumps(table))

    def test_the_working_tree_copy_of_humanizer_ptbr_counts_for_both_places(self):
        v = self.VERSIONS
        self.commit('one', put=[('skills/humanizer-ptbr/SKILL.md', v['a'])])
        edited = b'edited humanizer, not committed\n'
        (self.repo / 'skills/humanizer-ptbr/SKILL.md').write_bytes(edited)
        table = self.tool.build_table(self.repo, 'main')
        both = sorted([sha(v['a']), sha(edited)])
        self.assertEqual(table['skills/humanizer-ptbr/SKILL.md'], both)
        self.assertEqual(table['.agents/skills/humanizer-ptbr/SKILL.md'], both)

    def test_a_repository_without_a_working_tree_gives_the_history_alone(self):
        self.make_history()
        bare = self.repo.parent / 'bare.git'
        git(self.repo.parent, 'clone', '-q', '--bare', str(self.repo), str(bare))
        self.assertEqual(self.tool.build_table(bare, 'main'), self.tool.build_table(self.repo, 'main'))

    def test_a_ref_that_looks_like_an_option_or_a_folder_is_taken_as_a_ref(self):
        self.make_history()
        git(self.repo, 'branch', 'scripts', 'main')  # a branch named like the scripts/ folder
        self.assertEqual(self.tool.build_table(self.repo, 'scripts'), self.tool.build_table(self.repo, 'main'))
        out = self.repo.parent / 'table.json'
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = self.tool.main(['--repo', str(self.repo), '--ref=--all', '--out', str(out)])
        self.assertEqual(code, 1)  # `--all` as an option would have read every branch
        self.assertFalse(out.exists())

    def test_without_git_the_command_says_so_and_fails(self):
        errors = io.StringIO()
        out = self.repo.parent / 'table.json'
        with mock.patch('subprocess.run', side_effect=FileNotFoundError(2, 'No such file', 'git')), redirect_stderr(errors):
            code = self.tool.main(['--repo', str(self.repo), '--ref', 'main', '--out', str(out)])
        self.assertEqual(code, 1)
        self.assertIn('git is not installed', errors.getvalue())
        self.assertFalse(out.exists())

    def test_a_folder_that_is_not_a_repository_fails_with_a_message(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = self.tool.main(['--repo', str(self.repo.parent / 'missing'), '--out', str(self.repo.parent / 't.json')])
        self.assertEqual(code, 1)
        self.assertIn('legacy_hashes:', errors.getvalue())

    def test_the_command_writes_the_same_bytes_every_run(self):
        self.make_history()
        outputs = []
        for name in ('one.json', 'two.json'):
            out = self.repo.parent / name
            with redirect_stdout(io.StringIO()):
                self.assertEqual(self.tool.main(['--repo', str(self.repo), '--ref', 'main', '--out', str(out)]), 0)
            outputs.append(out.read_bytes())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], self.tool.render(self.tool.build_table(self.repo, 'main')).encode())

    def test_the_command_reads_head_when_no_ref_is_given(self):
        self.make_history()
        out = self.repo.parent / 'head.json'
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tool.main(['--repo', str(self.repo), '--out', str(out)]), 0)
        self.assertEqual(out.read_text(), self.tool.render(self.tool.build_table(self.repo, 'main')))

    def test_an_unknown_ref_fails_without_writing(self):
        self.make_history()
        out = self.repo.parent / 'table.json'
        errors = io.StringIO()
        with redirect_stderr(errors):
            self.assertEqual(self.tool.main(['--repo', str(self.repo), '--ref', 'nope', '--out', str(out)]), 1)
        self.assertIn('nope', errors.getvalue())
        self.assertFalse(out.exists())

    def test_the_committed_table_is_what_the_generator_gives_for_head_and_the_working_tree(self):
        # R27/R28: the table comes from the branch head plus the files as they are now, so it holds what
        # origin/main published and what this branch is about to publish, and a change to a legacy
        # file can land in the same commit as its regenerated table.
        def run(*args):
            return subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True)

        shallow = run('rev-parse', '--is-shallow-repository')
        if shallow.returncode != 0 or shallow.stdout.strip() != 'false':
            self.skipTest('the git history is not available (not a repository, or a shallow checkout)')
        committed = (REPO / 'src/youngcrow/legacy_hashes.json').read_text(encoding='utf-8')
        self.assertEqual(committed, self.tool.render(self.tool.build_table(REPO, 'HEAD')),
                         'src/youngcrow/legacy_hashes.json is stale; run: python3 tools/legacy_hashes.py --repo . --ref HEAD')


if __name__ == '__main__':
    unittest.main()
