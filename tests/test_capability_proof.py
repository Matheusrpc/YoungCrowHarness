"""A missing invocation must never count as proof of native enforcement."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import smoke_capabilities as smoke
from smoke_capabilities import assess_native


class NativeProofTests(unittest.TestCase):
    def test_fixture_publishes_only_a_complete_pid(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            folder = Path(directory)
            log = folder / 'publication.jsonl'
            # Pause the writer before its first byte, when open('x') already exposes a file.
            script = '''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import smoke_capabilities as smoke
root = Path(sys.argv[2])
original_getpid = smoke.os.getpid
def paused_pid():
    (root / 'paused').touch()
    while not (root / 'release').exists():
        time.sleep(.01)
    return original_getpid()
smoke.os.getpid = paused_pid
raise SystemExit(smoke.serve(root, root / 'publication.jsonl'))
'''
            child = subprocess.Popen([sys.executable, '-B', '-c', script, str(root / 'tests'), directory],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not (folder / 'paused').exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue((folder / 'paused').exists(), 'writer did not reach publication barrier')
                self.assertFalse(log.with_suffix('.pid').exists(), 'reader can see an incomplete PID')
            finally:
                (folder / 'release').touch()
                try:
                    _, stderr = child.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate()
                    raise
            self.assertEqual(child.returncode, 0, stderr)
            self.assertEqual(log.with_suffix('.pid').read_text(), str(child.pid))
            self.assertFalse(log.with_suffix('.pid.pending').exists())

    def test_cleanup_does_not_claim_a_pending_writer_has_stopped(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            log = Path(directory) / 'pending.jsonl'
            log.with_suffix('.pid.pending').touch()
            self.assertEqual(smoke.stop_fixture(log), 1)
            self.assertTrue(log.with_suffix('.stop').exists())

    def test_fixture_does_not_replace_an_existing_pid(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            log = Path(directory) / 'existing.jsonl'
            pidfile = log.with_suffix('.pid')
            pidfile.write_text('existing owner', encoding='ascii')
            run = subprocess.run([sys.executable, '-B', str(root / 'tests/smoke_capabilities.py'),
                                  '--serve-mcp', '--root', directory, '--log', str(log)],
                                 input=b'', capture_output=True, timeout=5)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(pidfile.read_text(), 'existing owner')
            self.assertFalse(log.exists())

    def test_cleanup_failure_reports_observed_live_processes(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            target = Path(directory) / 'probe'
            with patch('smoke_capabilities.codex_phase', side_effect=smoke.NativeCleanupError(1)):
                evidence = smoke.probe('codex', Path(sys.executable), target)
            self.assertEqual(evidence['native_processes_alive'], 1)
            self.assertFalse(evidence['completed'])
            self.assertEqual(assess_native(evidence), 'pending')

    def test_fixture_cleanup_ends_a_real_server_waiting_on_stdin(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            log = Path(directory) / 'waiting.jsonl'
            child = subprocess.Popen([sys.executable, '-B', str(root / 'tests/smoke_capabilities.py'),
                '--serve-mcp', '--root', directory, '--log', str(log)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not log.with_suffix('.pid').exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertIsNone(child.poll())
                # Reap our direct child as a native parent would; a POSIX zombie still answers kill(0).
                waiter = threading.Thread(target=child.wait)
                waiter.start()
                self.assertEqual(smoke.stop_fixture(log), 0)
                waiter.join(timeout=5)
                self.assertEqual(child.returncode, 0)
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
                for stream in (child.stdin, child.stdout, child.stderr):
                    stream.close()

    def test_no_tool_calls_is_not_a_permission_proof(self):
        evidence = dict(completed=False, allowed_calls=0, denied_calls=0,
                        allowed_result=False, denial_observed=False, revoked_calls=0,
                        revocation_observed=False, restored_calls=0, vault_unchanged=True)
        self.assertEqual(assess_native(evidence), 'pending')
        evidence['completed'] = True
        self.assertEqual(assess_native(evidence), 'failed')
        evidence.update(allowed_calls=1, allowed_result=True, denial_observed=True,
                        revocation_observed=True, restored_calls=1)
        self.assertEqual(assess_native(evidence), 'passed')
        evidence['denied_calls'] = 1
        self.assertEqual(assess_native(evidence), 'failed')

    def test_real_synthetic_server_records_calls_and_rejects_unknown_tools(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.runtime') as directory:
            log = Path(directory) / 'calls.jsonl'
            messages = [dict(jsonrpc='2.0', id=1, method='initialize', params={'protocolVersion': '2025-03-26'}),
                        dict(jsonrpc='2.0', method='notifications/initialized'),
                        dict(jsonrpc='2.0', id=2, method='tools/list'),
                        dict(jsonrpc='2.0', id=3, method='tools/call', params={'name': 'yc_read', 'arguments': {}}),
                        dict(jsonrpc='2.0', id=4, method='tools/call', params={'name': 'missing', 'arguments': {}})]
            run = subprocess.run([sys.executable, '-B', str(root / 'tests/smoke_capabilities.py'),
                                  '--serve-mcp', '--root', directory, '--log', str(log)],
                                 input=''.join(json.dumps(m) + '\n' for m in messages),
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            results = [json.loads(line) for line in run.stdout.splitlines()]
            self.assertEqual(len(results), 4)
            self.assertEqual(results[0]['result']['protocolVersion'], '2025-03-26')
            self.assertEqual({t['name'] for t in results[1]['result']['tools']}, {'yc_read', 'yc_write'})
            self.assertEqual(results[2]['result']['content'][0]['text'], 'synthetic-ok')
            self.assertIn('error', results[3])
            self.assertEqual([json.loads(line)['tool'] for line in log.read_text().splitlines()], ['yc_read'])


if __name__ == '__main__':
    unittest.main()
