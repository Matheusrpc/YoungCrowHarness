import importlib
from datetime import datetime, timedelta
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
FIXTURE = Path(__file__).parent / 'fixtures/mission_client.py'


class ProcessTests(unittest.TestCase):
    def test_separate_stderr_retained_and_joint_output_bounded(self):
        plan = self.plan('success')
        plan['argv'] = [sys.executable, '-I', '-S', '-c',
                        'import sys; sys.stdout.write("{}"); sys.stdout.flush(); '
                        'sys.stderr.write("denied-token-canary"); sys.exit(7)']
        result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
        self.assertEqual(result.get('stderr'), b'denied-token-canary')
        self.assertEqual(result['stdout'], b'{}')
        self.assertEqual(result['exit_code'], 7)
        plan['output_limit_bytes'] = 4
        result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
        self.assertEqual(result['reason'], 'output_limit')
        self.assertLessEqual(len(result['stdout']) + len(result['stderr']), 4)

    def test_supervisor_observation_covers_success_missing_and_timeout(self):
        for mode in ('success', 'missing', 'hang'):
            plan = self.plan('success' if mode == 'missing' else mode)
            plan['timeout_seconds'] = 0.4
            if mode == 'missing':
                plan['argv'] = [str(self.root / 'absent.exe')]
            result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
            self.assertEqual(result['reason'], {'success': 'completed', 'missing': 'spawn_failed', 'hang': 'timeout'}[mode])
            start, end = [datetime.fromisoformat(result[k]) for k in ('started_at', 'ended_at')]
            self.assertEqual(start.utcoffset(), timedelta(0))
            self.assertEqual(end.utcoffset(), timedelta(0))
            self.assertGreaterEqual(end, start)
            self.assertGreaterEqual(result['elapsed_seconds'], 0)
            self.assertTrue(result['tree_reaped'])

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_process'), 'supervisor not implemented')
        self.module = importlib.import_module('mission_process')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def plan(self, mode):
        return dict(argv=[sys.executable, '-I', '-S', str(FIXTURE.resolve()), mode], cwd=str(self.root),
                    stdin=b'', timeout_seconds=5, output_limit_bytes=4096,
                    client='codex', connection='authenticated', credential_env=None)

    def test_timeout_reaps_owned_child_only(self):
        stranger = subprocess.Popen([sys.executable, '-I', '-S', str(FIXTURE.resolve()), 'hang'])
        try:
            result = self.module.supervise(self.plan('child'), on_started=lambda owner: None, stop_requested=lambda: False)
            self.assertEqual(result['reason'], 'timeout')
            self.assertTrue(result['tree_reaped'])
            self.assertTrue((self.root / 'child.pid').exists())
            self.assertIsNone(stranger.poll())
            self.assertTrue(self.module.owner_gone(result['owner']))
        finally:
            stranger.terminate()
            stranger.wait(timeout=5)

    def test_output_limit_is_bounded_and_reaped(self):
        result = self.module.supervise(self.plan('flood'), on_started=lambda _: None, stop_requested=lambda: False)
        self.assertEqual(result['reason'], 'output_limit')
        self.assertLessEqual(len(result['stdout']), 4096)
        self.assertTrue(result['tree_reaped'])

    def test_spawn_failure_is_sanitized_before_effect(self):
        plan = self.plan('success')
        plan['argv'] = [str(self.root / 'missing-private-executable')]
        result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
        self.assertFalse(result['effect_started'])
        self.assertEqual(result['reason'], 'spawn_failed')
        self.assertNotIn('missing-private', repr(result))

    def test_callback_failure_never_dispatches(self):
        def abort(_):
            raise RuntimeError('simulated coordinator persistence failure')
        with self.assertRaises(RuntimeError):
            self.module.supervise(self.plan('child'), on_started=abort, stop_requested=lambda: False)
        self.assertFalse((self.root / 'child.pid').exists())

    def test_unproven_process_identity_is_never_assumed_dead(self):
        self.assertFalse(self.module.owner_gone({'pid': os.getpid()}))
        self.assertFalse(self.module.process_missing(os.getpid()))
        child = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'pass'])
        child.wait(timeout=20)
        self.assertTrue(self.module.process_missing(child.pid))

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object boundary')
    def test_failed_job_assignment_reaps_the_unassigned_bootstrap(self):
        original_job, original_spawn = self.module.new_job, subprocess.Popen
        owned, closed = [], []
        class Api:
            def __init__(self, actual):
                self.actual = actual
            def __getattr__(self, name):
                return getattr(self.actual, name)
            def AssignProcessToJobObject(self, *args):
                return False
            def CloseHandle(self, handle):
                closed.append(handle)
                return self.actual.CloseHandle(handle)
        def job(name):
            api, handle = original_job(name)
            return Api(api), handle
        def spawn(*args, **kwargs):
            child = original_spawn(*args, **kwargs)
            owned.append(child)
            return child
        try:
            with patch.object(self.module, 'new_job', side_effect=job), patch.object(subprocess, 'Popen', side_effect=spawn):
                with self.assertRaisesRegex(ValueError, '^unsupported_containment$'):
                    self.module.supervise(self.plan('child'), on_started=lambda _: self.fail('client released'), stop_requested=lambda: False)
            self.assertTrue(owned and all(p.poll() is not None for p in owned))
            self.assertTrue(closed)
            self.assertFalse((self.root / 'child.pid').exists())
        finally:
            for child in owned:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=5)
                for stream in (child.stdin, child.stdout, child.stderr):
                    stream.close()

    def test_linux_group_signal_precedes_any_reap(self):
        events = []
        class Child:
            pid = 999999
            stdin, stdout, stderr = io.BytesIO(), io.BytesIO(), io.BytesIO()
            def poll(self):
                events.append('reap')
                return 0
            def wait(self, timeout=None):
                events.append('reap')
                return 0
        plan = self.plan('success')
        paths = {plan['argv'][0]: Path(plan['argv'][0]), self.module.__file__: Path(self.module.__file__)}
        peek = SimpleNamespace(si_code=1, si_status=0)
        # Simulated OS boundary: no real PID or process group receives a signal.
        with patch.object(self.module, 'Path', side_effect=lambda value: paths[value]), \
             patch.object(self.module.os, 'name', 'posix'), patch.object(self.module.sys, 'platform', 'linux'), \
             patch.object(self.module.platform, 'machine', return_value='x86_64'), \
             patch.object(self.module.subprocess, 'Popen', return_value=Child()), \
             patch.object(self.module.os, 'waitid', return_value=peek, create=True), \
             patch.object(self.module.os, 'P_PID', 1, create=True), \
             patch.object(self.module.os, 'WEXITED', 4, create=True), \
             patch.object(self.module.os, 'WNOHANG', 1, create=True), \
             patch.object(self.module.os, 'WNOWAIT', 0x1000000, create=True), \
             patch.object(self.module.os, 'CLD_EXITED', 1, create=True), \
             patch.object(self.module.signal, 'SIGKILL', 9, create=True), \
             patch.object(self.module.os, 'killpg', side_effect=lambda *args: events.append('kill'), create=True), \
             patch.object(self.module, 'linux_members', return_value=[]):
            result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
        self.assertTrue(result['tree_reaped'])
        self.assertLess(events.index('kill'), events.index('reap'), events)

    @unittest.skipUnless(os.name == 'nt', 'Discovery regression contained by an outer Windows Job')
    def test_discovery_descendant_cannot_hold_stdout_past_deadline(self):
        plan = self.plan('discover-exchange')
        plan['timeout_seconds'] = 12
        result = self.module.supervise(plan, on_started=lambda _: None, stop_requested=lambda: False)
        self.assertTrue(result['tree_reaped'])
        self.assertEqual(result['reason'], 'completed', result)
        self.assertIn(b'exchange-finished', result['stdout'])
        self.assertTrue(self.module.process_missing(int((self.root / 'child.pid').read_text())))

    def test_discovery_preserves_request_response_order_under_supervision(self):
        import mission_clients
        responses = mission_clients._exchange(Path(sys.executable), ['-I', '-S', str(FIXTURE.resolve()), 'metadata-rpc'],
                                               self.root, [({'id': 1}, 1), ({'id': 2}, 2)])
        self.assertEqual([response['id'] for response in responses], [1, 2])

    @unittest.skipIf(os.name == 'nt', 'Linux seccomp boundary')
    def test_child_cannot_escape_process_group(self):
        result = self.module.supervise(self.plan('escape'), on_started=lambda _: None, stop_requested=lambda: False)
        self.assertIn(b'escape_refused', result['stdout'])
        self.assertTrue(result['tree_reaped'])
