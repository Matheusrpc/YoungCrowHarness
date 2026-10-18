"""Native PID namespace checks. Run without sandbox restrictions for qualification."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mission_process as processes

FIXTURE = Path(__file__).parent / 'fixtures/namespace_client.py'


@unittest.skipUnless(sys.platform == 'linux', 'Linux process observations')
class NamespaceObservationTests(unittest.TestCase):
    def test_inaccessible_proc_cannot_prove_namespace_stopped(self):
        owner = dict(kind='linux-pidns-group', name='922c6a44-43f0-49cc-b88a-c426f31b4ac7', pid=99999999)
        with patch.object(Path, 'iterdir', side_effect=PermissionError):
            self.assertFalse(processes.owner_gone(owner))

    def test_missing_namespace_launcher_refuses_before_dispatch(self):
        real = Path.is_file
        with patch.object(Path, 'is_file', lambda path: False if str(path) == '/usr/bin/unshare' else real(path)):
            with self.assertRaisesRegex(ValueError, 'unsupported_containment'):
                processes.supervise(dict(execution_contract='isolated-tools'),
                    on_started=lambda _: self.fail('ownership released'), stop_requested=lambda: False)

    def test_unreadable_or_malformed_process_cannot_prove_namespace_stopped(self):
        owner = dict(kind='linux-pidns-group', name='922c6a44-43f0-49cc-b88a-c426f31b4ac7', pid=99999999)
        for options in ({'side_effect': PermissionError}, {'return_value': 'invalid stat'}):
            with self.subTest(options=options), patch.object(Path, 'iterdir', return_value=[Path('/proc/2')]), \
                    patch.object(Path, 'read_text', **options):
                self.assertFalse(processes.owner_gone(owner))


@unittest.skipUnless(sys.platform == 'linux', 'Linux PID namespaces')
class NamespaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path('/usr/bin/unshare').is_file():
            raise unittest.SkipTest('util-linux unshare unavailable')
        probe = subprocess.run(['/usr/bin/unshare', '--user', '--map-current-user', '--pid', '--fork',
                                sys.executable, '-I', '-S', '-c', 'import os; assert os.getpid() == 1'],
                               capture_output=True, timeout=5)
        if probe.returncode:
            raise unittest.SkipTest('PID namespace unavailable in this execution environment')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def plan(self, mode='finish', seconds=2):
        return dict(argv=[sys.executable, '-I', '-S', str(FIXTURE.resolve()), mode], cwd=str(self.root),
                    stdin=b'', timeout_seconds=seconds, output_limit_bytes=4096,
                    connection='authenticated', execution_contract='isolated-tools', environment_overrides={})

    def wait_for(self, condition, seconds=5):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(condition())

    def gone(self, record):
        try:
            fields = Path(f"/proc/{record['pid']}/stat").read_text().rsplit(')', 1)[1].split()
            return fields[19] != record['start'] or fields[0] == 'Z'
        except FileNotFoundError:
            return True

    def assert_reaped(self):
        for name in ('client', 'detached', 'orphan', 'guardian'):
            path = self.root / f'{name}.json'
            self.assertTrue(path.exists(), name)
            record = json.loads(path.read_text())
            self.wait_for(lambda: self.gone(record))

    def test_new_groups_sessions_and_orphans_end_with_the_client(self):
        result = processes.supervise(self.plan(), on_started=lambda _: None, stop_requested=lambda: False)
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(result['owner']['kind'], 'linux-pidns-group')
        self.assertIn(b'groups-ready', result['stdout'])
        self.assertTrue(result['tree_reaped'])
        self.assert_reaped()
        guardian = json.loads((self.root / 'guardian.json').read_text())
        self.assertEqual(guardian['group'], result['owner']['pid'])
        self.assertTrue(processes.owner_gone(result['owner']))

    def test_timeout_and_cancellation_preserve_unrelated_process(self):
        stranger = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(15)'])
        try:
            for cancel in (False, True):
                with self.subTest(cancel=cancel):
                    for path in self.root.glob('*.json'):
                        path.unlink()
                    result = processes.supervise(self.plan('hang'), on_started=lambda _: None,
                        stop_requested=lambda: cancel and (self.root / 'orphan.json').exists())
                    self.assertEqual(result['reason'], 'cancelled' if cancel else 'timeout', result)
                    self.assertTrue(result['tree_reaped'])
                    self.assert_reaped()
                    self.assertIsNone(stranger.poll())
        finally:
            stranger.kill()
            stranger.wait(timeout=5)

    def test_coordinator_wrapper_and_guardian_crashes_are_bounded(self):
        for victim in ('coordinator', 'wrapper', 'launcher', 'guardian'):
            with self.subTest(victim=victim):
                for path in self.root.glob('*.json'):
                    path.unlink()
                controller = subprocess.Popen([sys.executable, '-I', '-S', str(FIXTURE.resolve()), 'controller'],
                    cwd=self.root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    self.wait_for(lambda: (self.root / 'orphan.json').exists())
                    owner = json.loads((self.root / 'owner.json').read_text())
                    if victim == 'guardian':
                        os.kill(json.loads((self.root / 'guardian.json').read_text())['pid'], signal.SIGKILL)
                    elif victim == 'launcher':
                        guardian = json.loads((self.root / 'guardian.json').read_text())
                        launcher = int(Path(f"/proc/{guardian['pid']}/stat").read_text().rsplit(')', 1)[1].split()[1])
                        os.kill(launcher, signal.SIGKILL)
                    elif victim == 'wrapper':
                        os.kill(owner['pid'], signal.SIGKILL)
                    controller.kill()
                    controller.wait(timeout=5)
                    self.assert_reaped()
                    self.wait_for(lambda: processes.owner_gone(owner))
                finally:
                    if controller.poll() is None:
                        controller.kill()
                    controller.wait(timeout=5)

    def test_persistence_failure_never_starts_client(self):
        def fail(_):
            raise RuntimeError('persistence failure')
        with self.assertRaisesRegex(RuntimeError, 'persistence failure'):
            processes.supervise(self.plan(), on_started=fail, stop_requested=lambda: False)
        self.assertFalse((self.root / 'client.json').exists())

    def test_coordinator_dying_before_dispatch_never_starts_client(self):
        controller = subprocess.run([sys.executable, '-I', '-S', str(FIXTURE.resolve()), 'before-dispatch'],
                                    cwd=self.root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        self.assertEqual(controller.returncode, 0)
        owner = json.loads((self.root / 'owner.json').read_text())
        self.wait_for(lambda: processes.owner_gone(owner))
        self.assertFalse((self.root / 'client.json').exists())

    def test_guardian_requires_pid_one_and_bound_outer_group(self):
        for inside in (False, True):
            with self.subTest(inside=inside):
                argv = [sys.executable, '-I', '-S', processes.__file__, '--namespace-child']
                if inside:
                    argv = ['/usr/bin/unshare', '--user', '--map-current-user', '--pid', '--fork', '--kill-child=KILL'] + argv
                request = dict(wrapper_pid=0 if inside else os.getpgrp(), deadline_monotonic=time.monotonic()+2,
                               argv=self.plan()['argv'], stdin='')
                completed = subprocess.run(argv, input=json.dumps(request).encode()+b'\n', cwd=self.root,
                                           capture_output=True, timeout=5)
                self.assertEqual(completed.returncode, 125, completed)
                self.assertFalse((self.root / 'client.json').exists())


if __name__ == '__main__':
    unittest.main()
