"""Immutable adoption records and recovery use only synthetic disposable projects."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_adoption_storage import StorageFixture


class AdoptionTests(StorageFixture):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('adoption'), 'adoption records not implemented')
        self.a = importlib.import_module('adoption')

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


if __name__ == '__main__':
    unittest.main()
