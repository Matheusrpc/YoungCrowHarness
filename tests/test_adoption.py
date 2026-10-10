"""Immutable adoption records and recovery use only synthetic disposable projects."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_adoption_storage import StorageFixture


class AdoptionFixture(StorageFixture):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('adoption'), 'adoption records not implemented')
        self.a = importlib.import_module('adoption')


class AdoptionTests(AdoptionFixture):

    def test_private_execution_after_baseline_can_reinstall_and_restore(self):
        self.write('.gitignore', b'/.operacao-local/execution/\n')
        self.write('human.txt', b'before')
        before = self.fs.inspect_tree(self.project)
        first = self.a.prepare(self.project, self.base)
        environment = importlib.import_module('mission_environment')
        environment.configure_selection(self.project, 'dedicated', None)
        second = self.a.prepare(self.project, self.base)
        self.assertEqual(second['baseline_digest'], first['baseline_digest'])
        proposal = self.a.preview(self.project, self.base)
        restored = self.a.restore(self.project, self.base, proposal['digest'])
        self.assertEqual(restored['state'], 'restored')
        self.assertEqual(self.fs.inspect_tree(self.project), before)

    @unittest.skipUnless(os.name == 'nt', 'Windows private ACL boundary')
    def test_private_unrelated_directory_still_refuses_reinstall(self):
        self.a.prepare(self.project, self.base)
        self.fs.private_dir(self.project / 'unrelated')
        with self.assertRaisesRegex(ValueError, 'unsupported_permissions'):
            self.a.prepare(self.project, self.base)

    def test_older_recovery_contract_refuses_install_before_project_writes(self):
        shorter = tempfile.TemporaryDirectory(prefix='r-', dir=self.sandbox.parent)
        self.addCleanup(shorter.cleanup)
        self.base = Path(shorter.name) / 'b'
        self.write('human.txt', b'baseline')
        self.a.prepare(self.project, self.base)
        source = self.sandbox / 'distribution'
        (source / 'scripts').mkdir(parents=True)
        for name in ('adoption.py', 'adoption_fs.py', 'adoption_acl.ps1'):
            data = (Path(self.a.__file__).parent / name).read_bytes()
            (source / 'scripts' / name).write_bytes(data + b'\n# different recovery version\n')
        before = self.fs.inspect_tree(self.project)
        with self.assertRaisesRegex(ValueError, '^incompatible_recovery_runner$'):
            self.a.run_install(self.project, self.base, source, ['--client', 'codex'])
        self.assertEqual(self.fs.inspect_tree(self.project), before)

    def test_prepare_never_replaces_the_original_baseline(self):
        self.write('app.txt', b'before')
        first = self.a.prepare(self.project, self.base)
        self.write('app.txt', b'during trial')
        second = self.a.prepare(self.project, self.base)
        self.assertEqual(second['adoption_id'], first['adoption_id'])
        self.assertEqual(second['baseline_digest'], first['baseline_digest'])
        self.assertEqual((self.project / 'app.txt').read_bytes(), b'during trial')
        baseline = Path(first['runner']).parent.parent / 'baseline/tree/app.txt'
        self.assertEqual(baseline.read_bytes(), b'before')

    def test_status_without_a_baseline_is_read_only(self):
        missing = self.sandbox / 'uncreated'
        self.assertEqual(self.a.status(self.project, missing)['state'], 'missing_baseline')
        self.assertFalse(missing.exists())

    def test_missing_root_is_not_created_by_prepare(self):
        self.project.rmdir()
        result = self.a.prepare(self.project, self.base)
        self.assertEqual(result['state'], 'ready')
        self.assertFalse(result['root_exists'])
        self.assertFalse(self.project.exists())

    def test_runner_still_reads_state_outside_project(self):
        result = self.a.prepare(self.project, self.base)
        command = [sys.executable, '-B', result['runner'], '--root', str(self.project),
                   '--backup-root', str(self.base), 'status', '--json']
        actual = subprocess.run(command, capture_output=True, text=True, timeout=40)
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertEqual(json.loads(actual.stdout)['adoption_id'], result['adoption_id'])

    def test_changed_repository_at_the_same_path_is_refused(self):
        self.a.prepare(self.project, self.base)
        self.project.rename(self.sandbox / 'original')
        self.project.mkdir()
        with self.assertRaisesRegex(ValueError, 'root_identity_changed'):
            self.a.prepare(self.project, self.base)

    def test_corruption_never_recaptures_baseline(self):
        self.write('app.txt', b'before')
        result = self.a.prepare(self.project, self.base)
        store = Path(result['runner']).parent.parent
        (store / 'baseline/tree/app.txt').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'baseline_corrupt'):
            self.a.prepare(self.project, self.base)
        self.assertEqual((self.project / 'app.txt').read_bytes(), b'before')

    def test_runner_and_duplicate_json_are_rejected(self):
        result = self.a.prepare(self.project, self.base)
        runner = Path(result['runner'])
        runner.write_bytes(runner.read_bytes() + b'\n# altered\n')
        with self.assertRaisesRegex(ValueError, 'runner_corrupt'):
            self.a.status(self.project, self.base)
        store = runner.parent.parent
        (store / 'state.json').write_text('{"schema":1,"schema":1}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'invalid_record'):
            self.a.status(self.project, self.base)

    def test_git_in_progress_and_external_metadata_are_refused(self):
        self.git('init', '-q', str(self.project))
        for name in ('index.lock', 'MERGE_HEAD', 'commondir', 'objects/info/alternates'):
            path = self.project / '.git' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'not a supported state')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.a.prepare(self.project, self.base)
            path.unlink()
        self.assertEqual(list(self.base.iterdir()), [])

    def test_nested_git_and_legacy_adoption_are_refused(self):
        nested = self.project / 'nested'
        nested.mkdir()
        self.git('init', '-q', str(nested))
        with self.assertRaisesRegex(ValueError, 'unsupported_git'):
            self.a.prepare(self.project, self.base)
        nested.rename(self.sandbox / 'parked')
        self.write('skills-lock.json', b'{"capabilities": []}')
        self.write('scripts/vault.py', b'# fixture')
        self.write('skills/personalizer/SKILL.md', b'# fixture')
        with self.assertRaisesRegex(ValueError, 'legacy_without_baseline'):
            self.a.prepare(self.project, self.base)

    def test_no_space_never_changes_project(self):
        self.write('keep', b'untouched')
        before = self.fs.inspect_tree(self.project)
        usage = self.fs.shutil.disk_usage(self.base)
        with patch.object(self.fs.shutil, 'disk_usage', return_value=usage._replace(free=0)):
            with self.assertRaisesRegex(ValueError, 'insufficient_space'):
                self.a.prepare(self.project, self.base)
        self.assertEqual(self.fs.inspect_tree(self.project), before)

    def test_live_lease_and_orphan_child_cannot_be_reclaimed(self):
        result = self.a.prepare(self.project, self.base)
        store = Path(result['runner']).parent.parent
        with self.a.adoption_lease(store) as lease:
            with self.assertRaisesRegex(ValueError, 'locked'):
                self.a.prepare(self.project, self.base)
            with self.assertRaisesRegex(ValueError, 'owner_alive'):
                self.a.recover_lock(self.project, self.base, lease['lock_id'])
        child = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
        try:
            lock = self.a.new_lock()
            lock.update(pid=99999999, child_pid=child.pid)
            self.a.write_record(store, 'lock.json', lock)
            with self.assertRaisesRegex(ValueError, 'owner_alive'):
                self.a.recover_lock(self.project, self.base, lock['lock_id'])
        finally:
            child.stdin.close()
            child.wait(timeout=10)
        self.a.recover_lock(self.project, self.base, lock['lock_id'])
        self.assertFalse((store / 'lock.json').exists())
        self.assertTrue((store / 'locks' / (lock['lock_id'] + '.json')).exists())

    def test_interrupted_capture_is_preserved_and_can_retry(self):
        self.write('app', b'original')
        original = self.a.fs.copy_verified
        def interrupted(source, destination, expected):
            original(source, destination, expected)
            raise OSError('synthetic interruption')
        with patch.object(self.a.fs, 'copy_verified', interrupted):
            with self.assertRaises(OSError):
                self.a.prepare(self.project, self.base)
        self.assertEqual((self.project / 'app').read_bytes(), b'original')
        resumed = self.a.prepare(self.project, self.base)
        self.assertEqual(resumed['state'], 'ready')
        store = Path(resumed['runner']).parent.parent
        self.assertTrue(list((store / 'incomplete').iterdir()))

    def test_two_projects_sharing_storage_keep_separate_baselines(self):
        self.write('app', b'first')
        first = self.a.prepare(self.project, self.base)
        other = self.sandbox / 'other project'
        other.mkdir()
        (other / 'app').write_bytes(b'second')
        second = self.a.prepare(other, self.base)
        self.assertNotEqual(first['adoption_id'], second['adoption_id'])
        for result, data in ((first, b'first'), (second, b'second')):
            self.assertEqual((Path(result['runner']).parent.parent / 'baseline/tree/app').read_bytes(), data)

    def test_pid_reuse_does_not_make_an_abandoned_lock_permanent(self):
        result = self.a.prepare(self.project, self.base)
        store = Path(result['runner']).parent.parent
        lock = self.a.new_lock()
        self.assertIsNotNone(lock.get('owner_start'), 'record the native process start identity')
        lock['owner_start'] = 'previous-process-with-same-pid'
        self.a.write_record(store, 'lock.json', lock)
        self.a.recover_lock(self.project, self.base, lock['lock_id'])
        self.assertTrue(self.a.process_alive(os.getpid()))

    def test_concurrent_recovery_guard_is_released_when_process_exits(self):
        result = self.a.prepare(self.project, self.base)
        store = Path(result['runner']).parent.parent
        lock = self.a.new_lock()
        lock['pid'] = 99999999
        self.a.write_record(store, 'lock.json', lock)
        code = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                'import adoption\nwith adoption.lock_guard(Path(sys.argv[2])):\n'
                ' print("ready",flush=True)\n sys.stdin.read()\n')
        child = subprocess.Popen([sys.executable, '-B', '-c', code, str(Path(self.a.__file__).parent), str(store)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline().strip(), b'ready')
            with self.assertRaisesRegex(ValueError, 'locked'):
                self.a.recover_lock(self.project, self.base, lock['lock_id'])
        finally:
            child.stdin.close()
            child.wait(timeout=15)
            child.stdout.close()
            child.stderr.close()
        self.a.recover_lock(self.project, self.base, lock['lock_id'])


class RestoreTests(AdoptionFixture):
    def setUp(self):
        super().setUp()
        self.assertTrue(callable(getattr(self.a, 'restore', None)), 'restore not implemented')

    def git_state(self):
        queries = [('rev-parse', 'HEAD'), ('symbolic-ref', 'HEAD'),
                   ('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv'),
                   ('diff', '--binary', '--no-ext-diff', '--no-textconv'), ('status', '--porcelain=v1', '-z')]
        return [self.git('-C', str(self.project), *query) for query in queries]

    def external(self, runner, *args):
        result = subprocess.run([sys.executable, '-B', str(runner), '--root', str(self.project),
                                 '--backup-root', str(self.base), *args, '--json'],
                                cwd=self.sandbox, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_restore_keeps_trial_work_and_returns_dirty_git_state(self):
        self.seed_dirty_git()
        before = self.fs.inspect_tree(self.project)
        initial_git = self.git_state()
        index = (self.project / '.git/index').read_bytes()
        self.a.prepare(self.project, self.base)
        self.write('trial.txt', b'keep this work')
        self.write('tracked.txt', b'changed during trial')
        self.git('-C', str(self.project), 'checkout', '-qb', 'trial-branch')
        current = self.fs.inspect_tree(self.project)
        proposal = self.a.preview(self.project, self.base)
        result = self.a.restore(self.project, self.base, proposal['digest'])
        self.assertEqual(result['state'], 'restored')
        self.assertEqual((self.project / '.git/index').read_bytes(), index)
        self.assertEqual(self.fs.inspect_tree(self.project), before)
        self.assertEqual(self.fs.inspect_tree(Path(result['recovery_path'])), current)
        self.assertEqual((Path(result['recovery_path']) / 'trial.txt').read_bytes(), b'keep this work')
        self.assertEqual(self.git_state(), initial_git)

    def test_stale_preview_and_dry_run_do_not_change_the_project(self):
        self.write('app', b'before')
        self.a.prepare(self.project, self.base)
        before = self.fs.inspect_tree(self.project)
        proposal = self.a.preview(self.project, self.base)
        self.assertEqual(self.a.preview(self.project, self.base)['digest'], proposal['digest'])
        self.assertEqual(self.fs.inspect_tree(self.project), before)
        self.write('new', b'after preview')
        observed = self.fs.inspect_tree(self.project)
        with self.assertRaisesRegex(ValueError, 'stale_preview'):
            self.a.restore(self.project, self.base, proposal['digest'])
        self.assertEqual(self.fs.inspect_tree(self.project), observed)

    @unittest.skipIf(os.name == 'nt', 'POSIX secondary group permissions')
    def test_posix_secondary_groups_survive_return(self):
        groups = set(os.getgroups()) - {os.getegid()}
        if not groups:
            self.skipTest('requires an existing secondary group; Linux CI must exercise this')
        group = min(groups)
        self.write('shared/config', b'original')
        paths = (self.project, self.project / 'shared', self.project / 'shared/config')
        for path in paths:
            os.chown(path, -1, group)
        paths[-1].chmod(0o640)
        self.a.prepare(self.project, self.base)
        self.write('shared/config', b'trial')
        preview = self.a.preview(self.project, self.base)
        result = self.a.restore(self.project, self.base, preview['digest'])
        self.assertEqual([p.stat().st_gid for p in paths], [group] * len(paths))
        self.assertEqual(paths[-1].stat().st_mode & 0o777, 0o640)
        self.assertEqual(paths[-1].read_bytes(), b'original')
        self.assertEqual((Path(result['recovery_path']) / 'shared/config').stat().st_gid, group)

    def test_invalid_journal_revision_refuses_recovery_without_writes(self):
        self.write('app', b'original')
        initial = self.a.prepare(self.project, self.base)
        self.write('app', b'trial')
        preview = self.a.preview(self.project, self.base)
        crash = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('adoption_crash.py')),
                                str(self.project), str(self.base), preview['digest'], 'prepared'],
                               capture_output=True, timeout=180)
        self.assertEqual(crash.returncode, 73, crash.stderr)
        status = self.a.status(self.project, self.base)
        self.a.recover_lock(self.project, self.base, status['lock_id'])
        store = Path(initial['runner']).parent.parent
        transaction = self.a.transaction_for(store, status['transaction_id'])
        journal = self.a.read_record(transaction, 'journal.json')
        before = self.fs.inspect_tree(self.project)
        for revision in (-99, 0, 1, True, '2', 2.0, 2**63):
            invalid = dict(journal, revision=revision)
            self.a.write_record(transaction, 'journal.json', invalid)
            with self.assertRaisesRegex(ValueError, 'invalid_transaction'):
                self.a.recover(self.project, self.base, status['transaction_id'])
            self.assertEqual(self.fs.inspect_tree(self.project), before)
            self.assertEqual(self.a.read_record(transaction, 'journal.json'), invalid)

    def test_return_to_absence_preserves_new_project_work(self):
        self.project.rmdir()
        initial = self.a.prepare(self.project, self.base)
        store = Path(initial['runner']).parent.parent
        with self.a.adoption_lease(store):
            state = self.a.read_state(store)
            self.a.create_and_bind_root_if_absent(self.project, store, state)
        self.write('new-product', b'keep this')
        proposal = self.a.preview(self.project, self.base)
        result = self.a.restore(self.project, self.base, proposal['digest'])
        self.assertFalse(self.project.exists())
        self.assertEqual((Path(result['recovery_path']) / 'new-product').read_bytes(), b'keep this')

    def test_repeat_restore_never_overwrites_work_after_restoration(self):
        self.write('app', b'original')
        self.a.prepare(self.project, self.base)
        self.write('app', b'trial')
        preview = self.a.preview(self.project, self.base)
        self.a.restore(self.project, self.base, preview['digest'])
        self.write('app', b'new work after restore')
        result = self.a.restore(self.project, self.base, preview['digest'])
        self.assertTrue(result['historical'])
        self.assertTrue(result['drift'])
        self.assertEqual((self.project / 'app').read_bytes(), b'new work after restore')

    def test_no_space_for_trial_copy_keeps_current_work(self):
        self.write('app', b'original')
        self.a.prepare(self.project, self.base)
        self.write('app', b'trial')
        proposal = self.a.preview(self.project, self.base)
        usage = self.fs.shutil.disk_usage(self.base)
        with patch.object(self.fs.shutil, 'disk_usage', return_value=usage._replace(free=0)):
            with self.assertRaisesRegex(ValueError, 'insufficient_space'):
                self.a.restore(self.project, self.base, proposal['digest'])
        self.assertEqual((self.project / 'app').read_bytes(), b'trial')

    def test_confirm_digest_cannot_be_a_path_or_missing_proposal(self):
        self.a.prepare(self.project, self.base)
        for digest in ('../state', '0' * 64):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.a.restore(self.project, self.base, digest)
        self.assertTrue(self.project.is_dir())

    def test_changes_during_copy_invalidate_transaction_without_losing_work(self):
        self.write('app', b'original')
        initial = self.a.prepare(self.project, self.base)
        self.write('app', b'trial')
        proposal = self.a.preview(self.project, self.base)
        original = self.a.ensure_snapshot
        def changed(source, target, inventory, transaction):
            if target.name == 'trial-copy':
                self.write('app', b'new work')
            return original(source, target, inventory, transaction)
        with patch.object(self.a, 'ensure_snapshot', changed), self.assertRaises(ValueError):
            self.a.restore(self.project, self.base, proposal['digest'])
        status = self.a.status(self.project, self.base)
        with self.assertRaisesRegex(ValueError, 'stale_preview'):
            self.a.recover(self.project, self.base, status['transaction_id'])
        self.assertEqual((self.project / 'app').read_bytes(), b'new work')
        self.assertEqual(self.a.status(self.project, self.base)['state'], 'ready')
        self.assertNotEqual(self.a.preview(self.project, self.base)['digest'], proposal['digest'])

    def test_corrupt_transaction_and_new_hardlink_are_refused(self):
        self.write('app', b'original')
        initial = self.a.prepare(self.project, self.base)
        proposal = self.a.preview(self.project, self.base)
        os.link(self.project / 'app', self.project / 'alias')
        with self.assertRaisesRegex(ValueError, 'unsupported_entry'):
            self.a.restore(self.project, self.base, proposal['digest'])
        (self.project / 'alias').unlink()
        store = Path(initial['runner']).parent.parent
        state = self.a.read_state(store)
        self.a.write_state(store, state, state='restoring', transaction_id='../escape')
        with self.assertRaisesRegex(ValueError, 'invalid_transaction'):
            self.a.recover(self.project, self.base, '../escape')
        self.assertEqual((self.project / 'app').read_bytes(), b'original')

    def test_interruption_at_each_exchange_boundary_recovers_outside_project(self):
        points = ['prepared', 'before-rename-1', 'after-rename-1',
                  'before-rename-2', 'after-rename-2', 'baseline_activated', 'complete']
        if os.name == 'nt':
            points += ['privatizing_current', 'current_private']
        helper = Path(__file__).with_name('adoption_crash.py')
        for point in points:
            with self.subTest(point=point):
                self.project = self.sandbox / point
                self.project.mkdir()
                self.write('app', b'original')
                before = self.fs.inspect_tree(self.project)
                initial = self.a.prepare(self.project, self.base)
                self.write('app', b'trial')
                self.write('feature', b'preserve')
                trial = self.fs.inspect_tree(self.project)
                proposal = self.a.preview(self.project, self.base)
                crashed = subprocess.run([sys.executable, '-B', str(helper), str(self.project),
                                          str(self.base), proposal['digest'], point],
                                         capture_output=True, text=True, timeout=180)
                self.assertEqual(crashed.returncode, 73, crashed.stdout + crashed.stderr)
                status = self.external(initial['runner'], 'status')
                self.assertFalse(status['owner_alive'])
                self.external(initial['runner'], 'recover-lock', '--confirm', status['lock_id'])
                restored = self.external(initial['runner'], 'recover', '--confirm', status['transaction_id'])
                self.assertEqual(self.fs.inspect_tree(self.project), before)
                self.assertEqual(self.fs.inspect_tree(Path(restored['recovery_path'])), trial)

    @unittest.skipUnless(os.name == 'nt', 'real Windows non-share-delete handle')
    def test_open_file_prevents_exchange_without_losing_trial(self):
        import ctypes
        from ctypes import wintypes
        self.write('app', b'original')
        self.a.prepare(self.project, self.base)
        self.write('app', b'trial')
        proposal = self.a.preview(self.project, self.base)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(self.project / 'app'), 0x80000000, 1, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with self.assertRaises((OSError, ValueError)):
                self.a.restore(self.project, self.base, proposal['digest'])
            self.assertEqual((self.project / 'app').read_bytes(), b'trial')
        finally:
            kernel.CloseHandle(handle)


if __name__ == '__main__':
    unittest.main()
