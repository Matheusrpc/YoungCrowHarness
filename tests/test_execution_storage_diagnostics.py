"""Storage failures retain a safe cause without weakening private-file checks."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import adoption_fs as fs
import mission_environment as environment
import mission_sbx
import missions


class StorageDiagnosticsTests(unittest.TestCase):
    def test_first_and_existing_storage_git_failures_are_sanitized_readonly(self):
        for existing in (False, True):
            for error, reason in ((subprocess.TimeoutExpired(['git', 'private-path-canary'], 30), 'git_query_timeout'),
                                  (OSError('private-path-canary'), 'inspection_failed'),
                                  (subprocess.CalledProcessError(1, ['git', 'private-path-canary']), 'inspection_failed')):
                with self.subTest(existing=existing, reason=reason), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    if existing:
                        (root/environment.AREA).mkdir(parents=True, mode=0o700)
                    before = {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None for p in root.rglob('*')}
                    output, stderr = io.StringIO(), io.StringIO()
                    with patch.object(environment.fs, 'git_read', side_effect=error), \
                         patch('mission_process.supervise') as process, \
                         contextlib.redirect_stdout(output), contextlib.redirect_stderr(stderr):
                        code = missions.main(['--root', str(root), 'environment', 'show', '--json'])
                    self.assertEqual(code, 2)
                    result = json.loads(output.getvalue())
                    self.assertEqual(result['error'], 'execution_storage_unprotected')
                    self.assertEqual(result['diagnostic'], {'phase': 'git_boundary', 'reason': reason})
                    self.assertTrue(result['guidance'])
                    self.assertEqual(stderr.getvalue(), '')
                    self.assertNotIn('private-path-canary', output.getvalue())
                    self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None for p in root.rglob('*')})
                    process.assert_not_called()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_acl_keeps_only_enumerated_cause(self):
        for reported, expected in [('owner_mismatch', 'owner_mismatch'),
                                   ('private-token-canary', 'inspection_failed')]:
            with self.subTest(reported=reported):
                child = Mock(returncode=2)
                child.communicate.return_value = (json.dumps({'reason': reported}), 'secret-canary')
                with patch('adoption_fs.subprocess.Popen', return_value=child):
                    with self.assertRaisesRegex(ValueError, '^unsupported_permissions$') as caught:
                        fs.acl('private-check', self.root)
                self.assertEqual(getattr(caught.exception, 'reason', None), expected)

    def test_storage_identifies_missing_git_exclusion_without_repair(self):
        before = list(self.root.iterdir())
        with self.assertRaisesRegex(ValueError, '^execution_storage_unprotected$') as caught:
            environment._storage(self.root)
        self.assertEqual(getattr(caught.exception, 'diagnostic', None),
                         {'phase': 'git_exclusion', 'reason': 'git_exclusion_missing'})
        self.assertEqual(list(self.root.iterdir()), before)

    def test_temporary_owner_failure_precedes_sensitive_bytes_and_docker(self):
        area = self.root / environment.AREA
        area.mkdir(parents=True)
        existing = area / 'existing.json'
        existing.write_bytes(b'old-receipt')
        exe = self.root / 'sbx.exe'
        exe.write_bytes(b'fixture')
        driver = mission_sbx.Sbx(exe, self.root, version='0.46.0', evidence_path=area / 'sbx-test.json')
        driver.evidence.append({'stderr_b64':'secret-canary'})
        def inspect(path):
            if path.suffix == '.tmp':
                self.assertEqual(path.read_bytes(), b'')
                error = ValueError('unsupported_permissions')
                error.reason = 'owner_mismatch'
                raise error
        with patch('mission_environment._git_boundary', return_value=True), \
             patch('adoption_fs.git_read', return_value=Mock(returncode=0)), \
             patch('mission_environment._private', side_effect=inspect), \
             patch('adoption_fs.protect_for_storage', side_effect=inspect) as protect, \
             patch('mission_process.supervise') as process:
            with self.assertRaisesRegex(ValueError, '^execution_storage_unprotected$') as caught:
                driver.query('daemon_before', ('daemon','status','--json'))
        self.assertEqual(getattr(caught.exception, 'diagnostic', None),
                         {'phase':'temporary_evidence','reason':'owner_mismatch'})
        self.assertEqual(existing.read_bytes(), b'old-receipt')
        self.assertEqual(list(area.iterdir()), [existing])
        process.assert_not_called()
        if os.name == 'nt':
            self.assertEqual(protect.call_count, 1)

    def test_cli_reports_specific_storage_guidance_before_runtime_queries(self):
        error_type = getattr(environment, 'StorageError', None)
        self.assertIsNotNone(error_type)
        output = io.StringIO()
        with patch('mission_sandbox.inspect_environment', side_effect=error_type('existing_storage', 'owner_mismatch')), \
             patch('mission_process.supervise') as process, contextlib.redirect_stdout(output):
            code = missions.main(['--root',str(self.root),'client','environment','--executable',str(self.root/'sbx.exe'),'--preflight','--json'])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['diagnostic'], {'phase':'existing_storage','reason':'owner_mismatch'})
        self.assertIn('owner', result['guidance'])
        process.assert_not_called()

    def test_git_timeout_during_evidence_check_is_not_permission_timeout(self):
        exe = self.root / 'sbx.exe'
        exe.write_bytes(b'fixture')
        driver = mission_sbx.Sbx(exe, self.root, version='0.46.0')
        with patch('mission_environment._git_boundary', side_effect=subprocess.TimeoutExpired('git', 30)):
            with self.assertRaises(ValueError) as caught:
                driver.private_destination(self.root / 'sbx-test.json', temporary=True)
        self.assertEqual(caught.exception.diagnostic,
                         {'phase':'temporary_evidence','reason':'git_query_timeout'})

    def test_storage_creation_timeout_is_structured_before_queries(self):
        (self.root / '.gitignore').write_text('/.operacao-local/execution/\n')
        with patch('adoption_fs.private_dir', side_effect=subprocess.TimeoutExpired('powershell', 120)), \
             patch('mission_process.supervise') as process:
            with self.assertRaises(ValueError) as caught:
                mission_sbx.inspect_preflight(self.root, self.root / 'sbx.exe', '0.46.0')
        self.assertEqual(caught.exception.diagnostic,
                         {'phase':'storage_creation','reason':'permission_query_timeout'})
        process.assert_not_called()

    def test_preserved_storage_helper_refuses_before_queries(self):
        output = io.StringIO()
        with patch.object(environment, 'StorageError', None), \
             patch('mission_process.supervise') as process, contextlib.redirect_stdout(output):
            code = missions.main(['--root',str(self.root),'client','environment','--executable',str(self.root/'sbx.exe'),'--preflight','--json'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'incompatible_helper')
        process.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows private file creation')
    def test_new_empty_temporary_gets_private_acl_before_data(self):
        area = self.root / environment.AREA
        area.parent.mkdir()
        fs.private_dir(area)
        exe = self.root / 'sbx.exe'
        exe.write_bytes(b'fixture')
        receipt = area / 'sbx-test.json'
        driver = mission_sbx.Sbx(exe, self.root, version='0.46.0', evidence_path=receipt)
        driver.evidence.append({'stdout_b64':'fixture-data'})
        original = fs.protect_for_storage
        protected = []
        def protect(path):
            self.assertEqual(path.parent, area)
            self.assertNotEqual(path, receipt)
            self.assertEqual(path.read_bytes(), b'')
            protected.append(fs.identity(path))
            original(path)  # Native helper, while atomic_write still holds the file open.
            self.assertEqual(fs.identity(path), protected[-1])
        with patch('mission_environment._git_boundary', return_value=True), \
             patch('adoption_fs.git_read', return_value=Mock(returncode=0)), \
             patch('adoption_fs.protect_for_storage', side_effect=protect):
            driver.persist()
        self.assertEqual(len(protected), 1)
        self.assertEqual(json.loads(receipt.read_text())['evidence'], driver.evidence)
        environment._private(receipt)
        self.assertEqual(list(area.iterdir()), [receipt])

    @unittest.skipUnless(os.name == 'nt', 'Windows private file creation')
    def test_unsafe_temporary_never_changes_permissions(self):
        exe = self.root / 'sbx.exe'
        exe.write_bytes(b'fixture')
        driver = mission_sbx.Sbx(exe, self.root, version='0.46.0', evidence_path=self.root/'sbx.json')
        for kind in ('nonempty', 'wrong_parent', 'directory'):
            with self.subTest(kind=kind):
                path = self.root / ('.yc-' + kind + '.tmp')
                path.mkdir() if kind == 'directory' else path.write_bytes(b'existing-data' if kind == 'nonempty' else b'')
                expected = None if kind == 'wrong_parent' else fs.identity(self.root)
                with patch('mission_environment._git_boundary', return_value=True), \
                     patch('adoption_fs.git_read', return_value=Mock(returncode=0)), \
                     patch('adoption_fs.protect_for_storage') as protect:
                    with self.assertRaisesRegex(ValueError, 'execution_storage_unprotected'):
                        driver.private_destination(path, temporary=True, parent_identity=expected)
                protect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
