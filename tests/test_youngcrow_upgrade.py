"""Check `upgrade` refreshes only what is still the installer's and `undo` takes the install back out."""
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
import os
import shutil
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import youngcrow.install as install  # noqa: E402
from youngcrow.blocks import MD_END, MD_START, ManagedBlockError  # noqa: E402
from youngcrow.install import NotInitialized, init, undo, upgrade  # noqa: E402
from youngcrow.manifest import UnsafePathError, load, save, sha256_file  # noqa: E402
from youngcrow.payload import PAYLOAD, payload_root  # noqa: E402

NEW_RULES = '# YoungCrow rules\n\nThe rules of the next release.\n'
REQUIREMENTS = tuple(rel for rel in PAYLOAD if rel.startswith('requirements/'))


def failing(name, real):
    """A stand-in for `real` (os.replace, os.unlink, os.rmdir) that fails when the path ends in `name`."""
    at = -1 if real is os.replace else 0  # os.replace(source, destination): check the destination

    def call(*args):
        if Path(args[at]).name == name:
            raise OSError('disk full')
        return real(*args)
    return call


class UpgradeUndoTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / 'project'
        self.other = self.tmp / 'other'
        self.root.mkdir()
        self.other.mkdir()

    def _tree_bytes(self):
        """Every file and folder under the project: relative path -> bytes (None for a folder)."""
        return {path.relative_to(self.root).as_posix(): path.read_bytes() if path.is_file() else None
                for path in sorted(self.root.rglob('*'))}

    def _record_as_installed(self, path):
        """Put the file's current hash in the manifest, as if an older release had written it."""
        manifest = load(self.root)
        manifest.files[path.relative_to(self.root).as_posix()] = sha256_file(path)
        save(self.root, manifest)

    @contextmanager
    def _release(self, *, version=None, rules=None, add=None, drop=()):
        """Pretend the package is another release: another version, HARNESS text or payload."""
        source = Path(tempfile.mkdtemp(dir=self.tmp))
        payload = tuple(rel for rel in PAYLOAD if rel not in drop) + tuple(add or {})
        for rel in payload:
            (source / rel).parent.mkdir(parents=True, exist_ok=True)
            if rel in (add or {}):
                (source / rel).write_bytes(add[rel])
            else:
                shutil.copyfile(payload_root() / rel, source / rel)
        real = install._template

        def template(*parts):
            return rules if rules is not None and parts[0].startswith('HARNESS.') else real(*parts)

        with mock.patch.object(install, 'PAYLOAD', payload), \
                mock.patch.object(install, 'payload_root', return_value=source), \
                mock.patch.object(install, '_template', template), \
                mock.patch.object(install, '__version__', version or install.__version__):
            yield

    def symlink(self, target, link, directory=False):
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'this OS refused to create a symlink: {error}')

    # The brief's tests.

    def test_upgrade_replaces_untouched_and_keeps_modified(self):
        init(self.root)
        script = self.root / '.youngcrow/scripts/vault.py'
        script.write_text(script.read_text() + '# mine\n')
        stale = self.root / '.youngcrow/scripts/memory.py'
        stale.write_text('old')
        self._record_as_installed(stale)  # simula versão antiga intocada
        report = upgrade(self.root)
        self.assertIn('.youngcrow/scripts/vault.py', report.kept_modified)
        self.assertIn('.youngcrow/scripts/memory.py', report.written)
        self.assertTrue(script.read_text().endswith('# mine\n'))

    def test_upgrade_refuses_broken_markers(self):
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_text(agents.read_text().replace('<!-- youngcrow:end -->', ''))
        snapshot = self._tree_bytes()
        with self.assertRaises(ManagedBlockError):
            upgrade(self.root)
        self.assertEqual(self._tree_bytes(), snapshot)

    def test_undo_dry_run_changes_nothing(self):
        init(self.root)
        snapshot = self._tree_bytes()
        report = undo(self.root)
        self.assertIn('.youngcrow/scripts/vault.py', report.removed)
        self.assertEqual(self._tree_bytes(), snapshot)

    def test_undo_restores_original_bytes(self):
        (self.root / 'CLAUDE.md').write_bytes(b'# Mine\r\nline')
        init(self.root)
        undo(self.root, confirm=True)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), b'# Mine\r\nline')
        self.assertFalse((self.root / '.youngcrow').exists())

    def test_undo_keeps_user_notes_and_modified_files(self):
        init(self.root)
        (self.root / 'vault/decision.md').write_text('mine')
        (self.root / '.youngcrow/HARNESS.md').write_text('edited')
        report = undo(self.root, confirm=True)
        self.assertTrue((self.root / 'vault/decision.md').exists())
        self.assertIn('.youngcrow/HARNESS.md', report.kept_modified)

    # No manifest.

    def test_upgrade_and_undo_refuse_a_project_without_a_manifest(self):
        (self.root / 'CLAUDE.md').write_bytes(b'mine\n')
        for call in (upgrade, undo, lambda root: undo(root, confirm=True)):
            with self.assertRaises(NotInitialized):
                call(self.root)
        self.assertEqual(self._tree_bytes(), {'CLAUDE.md': b'mine\n'})
        init(self.root)
        undo(self.root, confirm=True)
        with self.assertRaises(NotInitialized):
            undo(self.root, confirm=True)

    # Undo of a fresh init gives the project back as it was.

    def test_undo_of_a_fresh_init_leaves_an_empty_project_empty(self):
        for client in ('both', 'claude', 'codex'):
            with self.subTest(client=client):
                init(self.root, client=client)
                report = undo(self.root, confirm=True)
                self.assertEqual(self._tree_bytes(), {})
                self.assertEqual((report.written, report.kept_modified, report.skipped), ([], [], []))
                self.assertIn('.youngcrow/', report.removed)
                self.assertIn('.youngcrow/manifest.json', report.removed)

    def test_undo_of_a_fresh_init_restores_crlf_files_that_existed_byte_for_byte(self):
        (self.root / 'CLAUDE.md').write_bytes(b'# Mine\r\nline\r\n')
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\r\nmore')
        (self.root / '.gitignore').write_bytes(b'dist/\r\nbuild/\r\n')
        (self.root / 'src').mkdir()
        (self.root / 'src/app.py').write_bytes(b'print(1)\n')
        (self.root / 'vault/decisions').mkdir(parents=True)
        (self.root / 'vault/decisions/one.md').write_bytes(b'note\r\n')
        before = self._tree_bytes()
        init(self.root)
        report = undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), before)
        self.assertEqual(sorted(report.written), ['.gitignore', 'AGENTS.md', 'CLAUDE.md'])
        self.assertNotIn('vault/', report.removed)
        self.assertIn('vault/integrations/', report.removed)

    def test_undo_leaves_an_own_vault_index_and_its_folder(self):
        (self.root / 'vault').mkdir()
        (self.root / 'vault/index.md').write_bytes(b'# My vault\n')
        before = self._tree_bytes()
        init(self.root)
        undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), before)

    def test_init_works_again_after_undo(self):
        init(self.root)
        undo(self.root, confirm=True)
        init(self.root)
        self.assertIsNotNone(load(self.root))

    def test_undo_dry_run_reports_exactly_what_confirm_does(self):
        (self.root / 'CLAUDE.md').write_bytes(b'Mine\n')
        init(self.root)
        (self.root / '.youngcrow/VERSION').write_bytes(b'edited\n')
        before = self._tree_bytes()
        preview = undo(self.root)
        self.assertEqual(self._tree_bytes(), before)
        self.assertEqual(undo(self.root, confirm=True).to_json(), preview.to_json())
        self.assertEqual(preview.written, ['CLAUDE.md'])
        self.assertEqual(preview.kept_modified, ['.youngcrow/VERSION'])
        self.assertNotIn('.youngcrow/', preview.removed)
        self.assertEqual((self.root / '.youngcrow/VERSION').read_bytes(), b'edited\n')

    # Undo never deletes or rewrites what the user changed.

    def test_undo_takes_only_the_block_out_of_a_created_file_the_user_extended(self):
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_bytes(agents.read_bytes() + b'My own rule\n')
        report = undo(self.root, confirm=True)
        self.assertEqual(agents.read_bytes(), b'My own rule\n')
        self.assertIn('AGENTS.md', report.kept_modified)
        self.assertNotIn('AGENTS.md', report.removed)

    def assertUndoLeaves(self, rel, edit, existing):
        """R20: once the user typed inside the block of `rel`, undo leaves that whole file as it is."""
        for existed in (True, False):
            with self.subTest(existed=existed):
                if existed:
                    (self.root / rel).write_bytes(existing)
                init(self.root)
                path = self.root / rel
                path.write_bytes(edit(path.read_bytes()))
                before = path.read_bytes()
                preview = undo(self.root)
                report = undo(self.root, confirm=True)
                self.assertEqual(report.to_json(), preview.to_json())
                self.assertEqual(path.read_bytes(), before)
                self.assertIn(rel, report.kept_modified)
                self.assertNotIn(rel, report.written + report.removed)
                path.unlink()
                self.assertEqual(self._tree_bytes(), {})

    def test_undo_leaves_a_gitignore_whose_block_the_user_typed_in(self):
        self.assertUndoLeaves('.gitignore', lambda data: data.replace(b'vault/local/\n', b'vault/local/\nnode_modules/\n'),
                              b'dist/\n')

    def test_undo_leaves_an_agents_md_whose_block_the_user_edited(self):
        self.assertUndoLeaves('AGENTS.md', lambda data: data.replace(b'Four rules', b'My five rules'),
                              b'Agent notes\r\n')

    def test_undo_removes_an_untouched_block_even_when_harness_md_was_edited(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\r\n')
        init(self.root)
        (self.root / '.youngcrow/HARNESS.md').write_text('my rules\n')
        report = undo(self.root, confirm=True)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), b'Agent notes\r\n')
        self.assertIn('AGENTS.md', report.written)
        self.assertEqual(report.kept_modified, ['.youngcrow/HARNESS.md'])

    def test_a_block_neither_its_body_nor_its_file_hash_vouches_for_is_left_alone(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\n')
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_bytes(agents.read_bytes() + b'More notes\n')
        (self.root / '.youngcrow/HARNESS.md').write_text('my rules\n')
        before = agents.read_bytes()
        with self._release(rules=NEW_RULES):
            self.assertIn('AGENTS.md', upgrade(self.root).kept_modified)
        self.assertEqual(agents.read_bytes(), before)
        self.assertIn('AGENTS.md', undo(self.root, confirm=True).kept_modified)
        self.assertEqual(agents.read_bytes(), before)

    def test_undo_lists_a_pre_existing_file_whose_managed_text_the_user_removed(self):
        (self.root / 'CLAUDE.md').write_bytes(b'Mine\n')
        init(self.root)
        (self.root / 'CLAUDE.md').write_bytes(b'Mine\nmore\n')
        report = undo(self.root, confirm=True)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), b'Mine\nmore\n')
        self.assertIn('CLAUDE.md', report.kept_modified)
        self.assertNotIn('CLAUDE.md', report.written)

    def test_undo_keeps_a_created_file_whose_managed_text_the_user_removed(self):
        init(self.root)
        (self.root / 'CLAUDE.md').write_bytes(b'# Rewritten by me\n')
        report = undo(self.root, confirm=True)
        self.assertEqual((self.root / 'CLAUDE.md').read_bytes(), b'# Rewritten by me\n')
        self.assertIn('CLAUDE.md', report.kept_modified)

    def test_undo_skips_a_created_file_the_user_deleted(self):
        init(self.root)
        (self.root / 'vault/capabilities/index.md').unlink()
        report = undo(self.root, confirm=True)
        self.assertNotIn('vault/capabilities/index.md', report.removed)
        self.assertEqual(self._tree_bytes(), {'vault': None, 'vault/capabilities': None})

    def test_undo_refuses_broken_markers_without_writing_and_names_the_file(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\n')
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_text(agents.read_text().replace(MD_END, ''))
        before = self._tree_bytes()
        for confirm in (False, True):
            with self.assertRaises(ManagedBlockError) as caught:
                undo(self.root, confirm=confirm)
            self.assertIn('AGENTS.md', str(caught.exception))
        self.assertEqual(self._tree_bytes(), before)

    def test_undo_refuses_a_managed_path_that_became_a_symlink(self):
        init(self.root)
        (self.root / 'CLAUDE.md').unlink()
        (self.other / 'x.md').write_bytes(b'not yours\n')
        self.symlink(self.other / 'x.md', self.root / 'CLAUDE.md')
        before = self._tree_bytes()
        for confirm in (False, True):
            with self.assertRaises(UnsafePathError) as caught:
                undo(self.root, confirm=confirm)
            self.assertIn('CLAUDE.md', str(caught.exception))
        self.assertEqual(self._tree_bytes(), before)
        self.assertEqual((self.other / 'x.md').read_bytes(), b'not yours\n')

    def test_undo_refuses_a_vault_folder_that_became_a_symlink(self):
        init(self.root)
        shutil.move(self.root / 'vault', self.other / 'vault')
        self.symlink(self.other / 'vault', self.root / 'vault', directory=True)
        before = self._tree_bytes()
        outside = sorted(p.relative_to(self.other).as_posix() for p in self.other.rglob('*'))
        with self.assertRaises(UnsafePathError):
            undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), before)
        self.assertEqual(sorted(p.relative_to(self.other).as_posix() for p in self.other.rglob('*')), outside)

    # Upgrade (R19).

    def test_upgrade_to_a_new_release_writes_and_records_new_files(self):
        init(self.root)
        with self._release(version='0.2.0', add={'scripts/new_tool.py': b'print("new")\n'}):
            report = upgrade(self.root)
            self.assertEqual(sorted(report.written), ['.youngcrow/VERSION', '.youngcrow/scripts/new_tool.py'])
            self.assertEqual((report.kept_modified, report.removed), ([], []))
            self.assertEqual((self.root / '.youngcrow/VERSION').read_bytes(), b'0.2.0\n')
            manifest = load(self.root)
            self.assertEqual(manifest.version, '0.2.0')
            for rel in ('.youngcrow/VERSION', '.youngcrow/scripts/new_tool.py'):
                self.assertEqual(manifest.files[rel], sha256_file(self.root / rel), rel)
            self.assertIn('.youngcrow/scripts/new_tool.py', manifest.created)
            again = self._tree_bytes()
            self.assertEqual(upgrade(self.root).to_json(),
                             {'written': [], 'kept_modified': [], 'removed': [], 'skipped': []})
            self.assertEqual(self._tree_bytes(), again)
        undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), {})

    def test_upgrade_writes_back_a_harness_file_the_user_deleted(self):
        init(self.root)
        (self.root / '.youngcrow/scripts/memory.py').unlink()
        report = upgrade(self.root)
        self.assertEqual(report.written, ['.youngcrow/scripts/memory.py'])
        self.assertEqual((self.root / '.youngcrow/scripts/memory.py').read_bytes(),
                         (payload_root() / 'scripts/memory.py').read_bytes())

    def test_upgrade_deletes_a_dropped_payload_file_only_when_unmodified(self):
        with self._release(add={'scripts/old_tool.py': b'old\n', 'scripts/old_mine.py': b'old\n'}):
            init(self.root)
        (self.root / '.youngcrow/scripts/old_mine.py').write_bytes(b'my change\n')
        report = upgrade(self.root)
        self.assertEqual(report.removed, ['.youngcrow/scripts/old_tool.py'])
        self.assertEqual(report.kept_modified, ['.youngcrow/scripts/old_mine.py'])
        self.assertFalse((self.root / '.youngcrow/scripts/old_tool.py').exists())
        self.assertEqual((self.root / '.youngcrow/scripts/old_mine.py').read_bytes(), b'my change\n')
        manifest = load(self.root)
        self.assertNotIn('.youngcrow/scripts/old_tool.py', manifest.files)
        self.assertNotIn('.youngcrow/scripts/old_tool.py', manifest.created)
        self.assertIn('.youngcrow/scripts/old_mine.py', manifest.files)
        self.assertIn('.youngcrow/scripts/old_mine.py', undo(self.root).kept_modified)

    def test_upgrade_does_not_overwrite_a_file_already_at_a_new_payload_path(self):
        init(self.root)
        (self.root / '.youngcrow/scripts/new_tool.py').write_bytes(b'mine\n')
        with self._release(add={'scripts/new_tool.py': b'print("new")\n'}):
            report = upgrade(self.root)
        self.assertEqual(report.kept_modified, ['.youngcrow/scripts/new_tool.py'])
        self.assertEqual((self.root / '.youngcrow/scripts/new_tool.py').read_bytes(), b'mine\n')
        self.assertNotIn('.youngcrow/scripts/new_tool.py', load(self.root).files)

    def test_upgrade_replaces_an_untouched_agents_block_and_nothing_around_it(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\r\nmore')
        init(self.root)
        with self._release(rules=NEW_RULES):
            report = upgrade(self.root)
        self.assertEqual(sorted(report.written), ['.youngcrow/HARNESS.md', 'AGENTS.md'])
        self.assertEqual((self.root / '.youngcrow/HARNESS.md').read_text(), NEW_RULES)
        agents = (self.root / 'AGENTS.md').read_bytes()
        self.assertEqual(agents, b'Agent notes\r\nmore\r\n' + f'{MD_START}\r\n# YoungCrow rules\r\n\r\n'
                         f'The rules of the next release.\r\n{MD_END}\r\n'.encode())
        undo(self.root, confirm=True)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), b'Agent notes\r\nmore')

    def test_upgrade_refreshes_the_block_of_a_created_agents_md_and_undo_keeps_the_users_text(self):
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_bytes(b'My own rule\n\n' + agents.read_bytes())
        with self._release(rules=NEW_RULES):
            self.assertIn('AGENTS.md', upgrade(self.root).written)
        self.assertIn(b'The rules of the next release.', agents.read_bytes())
        report = undo(self.root, confirm=True)
        self.assertIn('AGENTS.md', report.kept_modified)
        self.assertEqual(agents.read_bytes(), b'My own rule\n')

    def test_upgrade_of_an_untouched_created_agents_md_records_its_new_hash(self):
        init(self.root)
        with self._release(rules=NEW_RULES):
            upgrade(self.root)
        self.assertEqual(load(self.root).files['AGENTS.md'], sha256_file(self.root / 'AGENTS.md'))
        self.assertIn('AGENTS.md', undo(self.root).removed)

    def test_upgrade_keeps_an_agents_block_the_user_edited(self):
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_text(agents.read_text().replace('Four rules', 'My five rules'))
        before = agents.read_bytes()
        with self._release(rules=NEW_RULES):
            report = upgrade(self.root)
        self.assertEqual(agents.read_bytes(), before)
        self.assertIn('AGENTS.md', report.kept_modified)
        self.assertIn('.youngcrow/HARNESS.md', report.written)

    def test_an_untouched_block_mirrors_a_harness_md_the_user_edited(self):
        init(self.root)
        (self.root / '.youngcrow/HARNESS.md').write_text('my rules\n')
        report = upgrade(self.root)
        self.assertEqual((report.written, report.kept_modified), (['AGENTS.md'], ['.youngcrow/HARNESS.md']))
        mirrored = f'{MD_START}\nmy rules\n{MD_END}\n'.encode()
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), mirrored)
        with self._release(rules=NEW_RULES):
            report = upgrade(self.root)
        self.assertEqual((report.written, report.kept_modified), ([], ['.youngcrow/HARNESS.md']))
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), mirrored)
        self.assertEqual((self.root / '.youngcrow/HARNESS.md').read_text(), 'my rules\n')
        self.assertIn('AGENTS.md', undo(self.root).removed)

    def test_upgrade_refreshes_an_untouched_block_after_harness_md_was_deleted(self):
        init(self.root)
        (self.root / '.youngcrow/HARNESS.md').unlink()
        with self._release(rules=NEW_RULES):
            report = upgrade(self.root)
        self.assertEqual(sorted(report.written), ['.youngcrow/HARNESS.md', 'AGENTS.md'])
        self.assertEqual(report.kept_modified, [])
        self.assertEqual((self.root / 'AGENTS.md').read_text(), f'{MD_START}\n{NEW_RULES}{MD_END}\n')
        undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), {})

    def test_upgrade_refuses_to_copy_a_marker_line_from_harness_md(self):
        init(self.root)
        (self.root / '.youngcrow/HARNESS.md').write_text(f'my rules\n{MD_END}\n')
        before = self._tree_bytes()
        with self.assertRaises(ManagedBlockError) as caught:
            upgrade(self.root)
        self.assertIn('.youngcrow/HARNESS.md', str(caught.exception))
        self.assertEqual(self._tree_bytes(), before)

    def test_upgrade_removes_a_folder_its_deletions_empty(self):
        init(self.root)
        with self._release(drop=REQUIREMENTS):
            report = upgrade(self.root)
        self.assertIn('.youngcrow/requirements/', report.removed)
        self.assertFalse((self.root / '.youngcrow/requirements').exists())
        undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), {})

    def test_upgrade_keeps_a_folder_that_gets_a_new_file(self):
        init(self.root)
        with self._release(drop=REQUIREMENTS, add={'requirements/new.txt': b'new\n'}):
            report = upgrade(self.root)
        self.assertNotIn('.youngcrow/requirements/', report.removed)
        self.assertEqual([p.name for p in (self.root / '.youngcrow/requirements').iterdir()], ['new.txt'])

    def test_upgrade_leaves_a_block_the_user_wrote_before_init(self):
        own = f'{MD_START}\nmy own words\n{MD_END}\n'.encode()
        (self.root / 'AGENTS.md').write_bytes(own)
        init(self.root)
        with self._release(rules=NEW_RULES):
            report = upgrade(self.root)
        self.assertEqual((self.root / 'AGENTS.md').read_bytes(), own)
        self.assertNotIn('AGENTS.md', report.written + report.kept_modified)

    def test_upgrade_never_touches_vault(self):
        init(self.root)
        (self.root / 'vault/capabilities/index.md').unlink()
        (self.root / 'vault/index.md').write_bytes(b'# Edited\n')
        (self.root / 'vault/note.md').write_bytes(b'note\n')
        vault = {k: v for k, v in self._tree_bytes().items() if k.startswith('vault')}
        files = {k: v for k, v in load(self.root).files.items() if k.startswith('vault/')}
        real = install._template
        with mock.patch.object(install, '_template', lambda *parts: real(*parts) + 'changed\n'):
            report = upgrade(self.root)
        self.assertEqual({k: v for k, v in self._tree_bytes().items() if k.startswith('vault')}, vault)
        self.assertEqual({k: v for k, v in load(self.root).files.items() if k.startswith('vault/')}, files)
        self.assertEqual([rel for rel in report.written + report.kept_modified if 'vault' in rel], [])

    def test_upgrade_refuses_a_linked_scripts_folder_without_writing(self):
        init(self.root)
        shutil.move(self.root / '.youngcrow/scripts', self.other / 'scripts')
        self.symlink(self.other / 'scripts', self.root / '.youngcrow/scripts', directory=True)
        before = self._tree_bytes()
        with self._release(version='0.2.0', rules=NEW_RULES), self.assertRaises(UnsafePathError):
            upgrade(self.root)
        self.assertEqual(self._tree_bytes(), before)

    def test_upgrade_refuses_broken_markers_before_writing_any_harness_file(self):
        init(self.root)
        agents = self.root / 'AGENTS.md'
        agents.write_text(agents.read_text().replace(MD_START, ''))
        before = self._tree_bytes()
        with self._release(version='0.2.0', rules=NEW_RULES), self.assertRaises(ManagedBlockError) as caught:
            upgrade(self.root)
        self.assertIn('AGENTS.md', str(caught.exception))
        self.assertEqual(self._tree_bytes(), before)

    # A manifest that points outside the project.

    def _tamper(self, rel, target):
        manifest = load(self.root)
        manifest.files[rel] = sha256_file(target)
        manifest.created.append(rel)
        save(self.root, manifest)

    def test_undo_refuses_a_manifest_path_that_leaves_the_project(self):
        init(self.root)
        outside = self.other / 'x.md'
        outside.write_bytes(b'outside\n')
        clean = load(self.root)
        for rel, target in (('../other/x.md', outside), (str(outside), outside),
                            ('.youngcrow/../CLAUDE.md', self.root / 'CLAUDE.md')):
            with self.subTest(rel=rel):
                self._tamper(rel, target)
                before = self._tree_bytes()
                for confirm in (False, True):
                    with self.assertRaises(UnsafePathError):
                        undo(self.root, confirm=confirm)
                self.assertEqual(self._tree_bytes(), before)
                self.assertEqual(outside.read_bytes(), b'outside\n')
                save(self.root, clean)

    def test_upgrade_ignores_manifest_paths_outside_youngcrow_and_refuses_a_climbing_one(self):
        init(self.root)
        outside = self.other / 'x.md'
        outside.write_bytes(b'outside\n')
        for rel in ('../other/x.md', str(outside)):
            self._tamper(rel, outside)
        with self._release(version='0.2.0'):
            self.assertEqual(upgrade(self.root).written, ['.youngcrow/VERSION'])
        self.assertEqual(outside.read_bytes(), b'outside\n')
        self._tamper('.youngcrow/../CLAUDE.md', self.root / 'CLAUDE.md')
        before = self._tree_bytes()
        with self._release(version='0.3.0'), self.assertRaises(UnsafePathError):
            upgrade(self.root)
        self.assertEqual(self._tree_bytes(), before)
        self.assertEqual(list(self.other.iterdir()), [outside])

    # All or nothing.

    def test_a_temp_name_already_taken_is_never_deleted(self):
        (self.root / 'CLAUDE.md').write_bytes(b'Mine\n')
        taken = self.root / f'CLAUDE.md.{os.getpid()}.tmp'
        taken.write_bytes(b'not a temp file\n')
        before = self._tree_bytes()
        with self.assertRaises(FileExistsError):
            init(self.root)
        self.assertEqual(self._tree_bytes(), before)
        taken.unlink()
        init(self.root)
        taken.write_bytes(b'not a temp file\n')
        before = self._tree_bytes()
        with self.assertRaises(FileExistsError):
            undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), before)

    def test_a_failed_upgrade_puts_back_the_folder_it_removed(self):
        init(self.root)
        before = self._tree_bytes()
        cases = (
            ('youngcrow.install.save', mock.Mock(side_effect=OSError('disk full'))),  # after the rmdir
            ('os.rmdir', failing('requirements', os.rmdir)),  # the manifest must not be saved yet
        )
        for target, stand_in in cases:
            with self.subTest(failing=target), self._release(drop=REQUIREMENTS), \
                    mock.patch(target, stand_in), self.assertRaises(OSError):
                upgrade(self.root)
            self.assertEqual(self._tree_bytes(), before)

    def test_a_failed_upgrade_rolls_back_everything(self):
        (self.root / 'AGENTS.md').write_bytes(b'Agent notes\n')
        with self._release(add={'scripts/old_tool.py': b'old\n'}):
            init(self.root)
        before = self._tree_bytes()
        cases = (
            ('os.replace', failing('AGENTS.md', os.replace)),
            ('youngcrow.install.save', mock.Mock(side_effect=OSError('disk full'))),
        )
        for target, stand_in in cases:
            with self.subTest(failing=target), \
                    self._release(version='0.2.0', rules=NEW_RULES, add={'scripts/new_tool.py': b'new\n'}), \
                    mock.patch(target, stand_in), self.assertRaises(OSError):
                upgrade(self.root)
            self.assertEqual(self._tree_bytes(), before)
        self.assertIn('.youngcrow/scripts/old_tool.py', upgrade(self.root).removed)

    def test_a_failed_undo_rolls_back_everything(self):
        (self.root / 'CLAUDE.md').write_bytes(b'# Mine\r\nline')
        init(self.root)
        script = self.root / '.youngcrow/scripts/vault.py'
        script.chmod(0o750)
        mode = stat.S_IMODE(script.stat().st_mode)
        before = self._tree_bytes()
        cases = (
            ('os.rmdir', failing('.youngcrow', os.rmdir)),       # the very last thing undo does
            ('os.unlink', failing('memory.py', os.unlink)),     # a deletion halfway
            ('os.replace', failing('CLAUDE.md', os.replace)),   # restoring an edited file
        )
        for target, stand_in in cases:
            with self.subTest(failing=target), mock.patch(target, stand_in), self.assertRaises(OSError):
                undo(self.root, confirm=True)
            self.assertEqual(self._tree_bytes(), before)
            self.assertEqual(stat.S_IMODE(script.stat().st_mode), mode)
        undo(self.root, confirm=True)
        self.assertEqual(self._tree_bytes(), {'CLAUDE.md': b'# Mine\r\nline'})


if __name__ == '__main__':
    unittest.main()
