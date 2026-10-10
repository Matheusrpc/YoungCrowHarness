"""Private installation selection; no native runtime or model calls."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from test_adoption_storage import StorageFixture, ROOT
from test_setup import snapshot_bytes


class ExecutionEnvironmentTests(StorageFixture):
    def setUp(self):
        super().setUp()
        self.root = self.project
        self.write('.gitignore', b'/.operacao-local/execution/\n')
        self.assertIsNotNone(importlib.util.find_spec('mission_environment'), 'selection helper not implemented')
        self.env = importlib.import_module('mission_environment')

    def snapshot(self):
        return snapshot_bytes(self.root)

    def test_missing_is_local_without_writes(self):
        before = self.snapshot()
        report = self.env.read_selection(self.root)
        self.assertEqual((report['location'], report['origin'], report['digest']), ('local', 'default', None))
        self.assertEqual(self.snapshot(), before)
        missing = self.root / 'missing'
        self.assertEqual(self.env.read_selection(missing)['origin'], 'default')
        self.assertFalse(missing.exists())

    def test_configured_same_value_preserves_bytes(self):
        first = self.env.configure_selection(self.root, 'dedicated', None)
        before = self.snapshot()
        self.assertEqual(self.env.configure_selection(self.root, 'dedicated', first['digest']), first)
        self.assertEqual(self.env.setup_selection(self.root, None, apply=True), first)
        self.assertEqual(self.snapshot(), before)
        data = (self.root / '.operacao-local/execution/selection.json').read_bytes()
        self.assertEqual(first['digest'], hashlib.sha256(data).hexdigest())
        self.assertEqual(set(json.loads(data)), {'schema_version', 'location', 'selected_at'})

    def test_stale_digest_refuses_before_write(self):
        before = self.snapshot()
        for location, digest, reason in [('remote', None, 'invalid_execution_selection'),
                                          ('local', 'bad', 'invalid_execution_selection'),
                                          ('local', 'f' * 64, 'execution_selection_conflict')]:
            with self.assertRaisesRegex(ValueError, '^' + reason + '$'):
                self.env.configure_selection(self.root, location, digest)
            self.assertEqual(self.snapshot(), before)
        first = self.env.configure_selection(self.root, 'dedicated', None)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'execution_location_conflict'):
            self.env.setup_selection(self.root, 'local', apply=False)
        with self.assertRaisesRegex(ValueError, 'execution_selection_conflict'):
            self.env.configure_selection(self.root, 'local', None)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.env.configure_selection(self.root, 'local', first['digest'])['location'], 'local')

    def test_malformed_selection_refused_without_repair(self):
        self.env.configure_selection(self.root, 'local', None)
        path = self.root / '.operacao-local/execution/selection.json'
        invalid = [b'{', b'x' * 65537,
                   b'{"schema_version":1,"schema_version":1,"location":"local","selected_at":"2026-10-05T00:00:00+00:00"}']
        base = dict(schema_version=1, location='local', selected_at='2026-10-05T00:00:00+00:00')
        for key, value in [('schema_version', True), ('location', 'remote'), ('selected_at', '2026-10-05'),
                           ('selected_at', '2026-10-05T00:00:00+03:00'), ('token', 'secret-canary')]:
            invalid.append(json.dumps(dict(base, **{key: value})).encode())
        for data in invalid:
            path.write_bytes(data)
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, '^invalid_execution_selection$'):
                self.env.read_selection(self.root)
            self.assertEqual(self.snapshot(), before)

    def test_unsafe_or_tracked_selection_refused(self):
        self.env.configure_selection(self.root, 'local', None)
        path = self.root / '.operacao-local/execution/selection.json'
        alias = self.sandbox / 'alias'
        os.link(path, alias)
        with self.assertRaises(ValueError):
            self.env.read_selection(self.root)
        alias.unlink()
        self.git('init', '-q', str(self.root))
        self.git('-C', str(self.root), 'add', '-f', '.operacao-local/execution/selection.json')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
            self.env.read_selection(self.root)
        self.assertEqual(self.snapshot(), before)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction boundary')
    def test_junction_selection_never_reads_or_writes_external_directory(self):
        outside = self.sandbox / 'outside'
        self.fs.private_dir(outside)
        sentinel = outside / 'selection.json'
        sentinel.write_bytes(b'private outside')
        (self.root / '.operacao-local').mkdir()
        junction = self.root / '.operacao-local/execution'
        result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(junction), str(outside)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            for call in (lambda: self.env.read_selection(self.root),
                         lambda: self.env.configure_selection(self.root, 'local', None)):
                with self.assertRaises(ValueError):
                    call()
            self.assertEqual(sentinel.read_bytes(), b'private outside')
        finally:
            junction.rmdir()

    def test_missing_ignore_and_override_refuse_without_writes(self):
        self.write('.gitignore', b'')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
            self.env.configure_selection(self.root, 'local', None)
        self.assertEqual(self.snapshot(), before)
        self.git('init', '-q', str(self.root))
        self.write('.gitignore', b'/.operacao-local/execution/*\n!/.operacao-local/execution/selection.json\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
            self.env.configure_selection(self.root, 'local', None)
        self.assertEqual(self.snapshot(), before)


    def test_setup_refuses_deleted_but_tracked_area_before_copying(self):
        self.git('init', '-q', str(self.root))
        self.write('.operacao-local/execution/selection.json', b'tracked')
        self.git('-C', str(self.root), 'add', '-f', '.operacao-local/execution/selection.json')
        (self.root / '.operacao-local/execution/selection.json').unlink()
        (self.root / '.operacao-local/execution').rmdir()
        (self.root / '.operacao-local').rmdir()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
            self.env.setup_selection(self.root, None, apply=False)
        self.assertEqual(self.snapshot(), before)

    def test_selection_does_not_change_mission_state(self):
        originals = {'youngcrow/agents.json': b'human config', 'vault/local/operations/state.sqlite3': b'opaque state',
                     'vault/local/operations/receipt.json': b'opaque receipt'}
        for name, data in originals.items():
            self.write(name, data)
        self.env.configure_selection(self.root, 'dedicated', None)
        for name, data in originals.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        self.assertFalse((self.root / 'vault/project.json').exists())

    def child(self, code, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts'))
        return subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root), *args],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def assert_selection_contention(self, existing, read, during_check=False):
        first = self.env.configure_selection(self.root, 'local', None) if existing else {'digest': None}
        code = """import json,sys,time
from pathlib import Path
import mission_environment as environment
root=Path(sys.argv[1])
original=environment.atomic_write
def paused(root,relative,data,before_write=None):
 def ready(name):
  before_write(name)
  (root/'ready').touch()
  deadline=time.monotonic()+45
  while not (root/'release').exists():
   if time.monotonic()>=deadline: raise RuntimeError('barrier deadline')
   time.sleep(.01)
 return original(root,relative,data,before_write=ready)
environment.atomic_write=paused
print(json.dumps(environment.configure_selection(root,'dedicated',json.loads(sys.argv[2]))))
"""
        child = None
        def start_writer():
            nonlocal child
            child = self.child(code, json.dumps(first['digest']))
            deadline = time.monotonic() + 45
            while not (self.root / 'ready').exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue((self.root / 'ready').exists(), 'writer did not reach the temporary-file barrier')
        git_check = self.env._git_boundary
        def start_during_check(root):
            if child is None:
                start_writer()
            return git_check(root)
        try:
            if not during_check:
                start_writer()
            selection = self.root / self.env.SELECTION
            before = selection.read_bytes() if selection.exists() else None
            checked = self.env.fs.checked_path
            def release_after_enumeration(path):
                if Path(path).name.startswith('.yc-'):
                    (self.root / 'release').touch()
                    child.wait(timeout=45)
                return checked(path)
            # The old pre-lock inventory meets a real rename after enumerating its temporary.
            expected = 'execution_selection_conflict' if during_check and not read else 'execution_selection_busy'
            with patch.object(self.env.fs, 'checked_path', side_effect=release_after_enumeration), \
                 patch.object(self.env, '_git_boundary', side_effect=start_during_check):
                with self.assertRaisesRegex(ValueError, '^' + expected + '$'):
                    if read:
                        self.env.read_selection(self.root)
                    else:
                        self.env.configure_selection(self.root, 'local', first['digest'])
            if during_check and not read:
                self.assertTrue((self.root / 'release').exists(), 'bootstrap did not meet the inventory race')
            else:
                self.assertFalse((self.root / 'release').exists(), 'contender entered the active writer inventory')
                self.assertEqual(selection.read_bytes() if selection.exists() else None, before)
        finally:
            (self.root / 'release').touch()
            if child is not None:
                try:
                    output, errors = child.communicate(timeout=45)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)
        self.assertEqual(child.returncode, 0, errors)
        result = json.loads(output)
        self.assertEqual(result['location'], 'dedicated')
        self.assertEqual(self.env.read_selection(self.root), result)
        with self.assertRaisesRegex(ValueError, '^execution_selection_conflict$'):
            self.env.configure_selection(self.root, 'local', first['digest'])

    def test_reader_during_paused_first_selection_is_busy(self):
        self.assert_selection_contention(existing=False, read=True)

    def test_reader_during_paused_selection_update_is_busy(self):
        self.assert_selection_contention(existing=True, read=True)

    def test_writer_during_paused_first_selection_is_busy(self):
        self.assert_selection_contention(existing=False, read=False)

    def test_writer_during_paused_selection_update_is_busy(self):
        self.assert_selection_contention(existing=True, read=False)

    def test_readonly_or_empty_selection_lock_is_not_modified(self):
        first = self.env.configure_selection(self.root, 'local', None)
        lock = self.root / self.env.AREA / 'reclaim.lock'
        for data in (b'', b'0'):
            with self.subTest(empty=not data):
                lock.write_bytes(data)
                os.chmod(lock, 0o400)
                try:
                    before = self.snapshot()
                    self.assertEqual(self.env.read_selection(self.root), first)
                    self.assertEqual(self.env.setup_selection(self.root, None, apply=False), first)
                    self.assertEqual(self.snapshot(), before)
                finally:
                    os.chmod(lock, 0o600)
        lock.unlink()
        before = self.snapshot()
        self.assertEqual(self.env.read_selection(self.root), first)
        self.assertEqual(self.snapshot(), before)

    def test_existing_empty_lock_and_unsafe_storage_are_not_repaired(self):
        first = self.env.configure_selection(self.root, 'local', None)
        lock = self.root / self.env.AREA / 'reclaim.lock'
        lock.write_bytes(b'')
        self.write('.gitignore', b'')
        before = self.snapshot()
        for call in (lambda: self.env.read_selection(self.root),
                     lambda: self.env.configure_selection(self.root, 'dedicated', first['digest'])):
            with self.assertRaisesRegex(ValueError, '^execution_storage_unprotected$'):
                call()
            self.assertEqual(self.snapshot(), before)

    def test_reader_rechecks_when_first_writer_appears_during_git_check(self):
        self.assert_selection_contention(existing=False, read=True, during_check=True)

    def test_first_writer_inventory_race_rechecks_under_new_lock(self):
        self.assert_selection_contention(existing=False, read=False, during_check=True)

    def test_two_writers_one_digest(self):
        first = self.env.configure_selection(self.root, 'local', None)
        code = """import sys,json,time
from pathlib import Path
from mission_environment import configure_selection
root=Path(sys.argv[1])
while not (root/'go').exists(): time.sleep(.01)
try: print(json.dumps(configure_selection(root,'dedicated',sys.argv[2])))
except ValueError as e: print(json.dumps({'error':str(e)}))
"""
        children = [self.child(code, first['digest']) for _ in range(2)]
        try:
            (self.root / 'go').touch()
            outputs = [json.loads(p.communicate(timeout=45)[0]) for p in children]
        finally:
            for p in children:
                if p.poll() is None: p.kill()
                p.wait()
        self.assertEqual(sum('digest' in o for o in outputs), 1, outputs)
        self.assertIn(next(o['error'] for o in outputs if 'error' in o),
                      ('execution_selection_conflict', 'execution_selection_busy'))
        self.assertEqual(self.env.read_selection(self.root)['location'], 'dedicated')

    def test_process_death_releases_selection_lock(self):
        first = self.env.configure_selection(self.root, 'local', None)
        code = """import sys,time
from pathlib import Path
from adoption import lock_guard
with lock_guard(Path(sys.argv[1])/'.operacao-local/execution'):
 print('locked',flush=True)
 time.sleep(60)
"""
        child = self.child(code)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(ValueError, 'execution_selection_busy'):
                self.env.configure_selection(self.root, 'dedicated', first['digest'])
        finally:
            child.kill(); child.communicate(timeout=10)
        self.assertEqual(self.env.configure_selection(self.root, 'dedicated', first['digest'])['location'], 'dedicated')
