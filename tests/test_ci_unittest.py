"""Exercise the CI entry point with real disposable test modules."""
import os
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch


RUNNER = Path(__file__).with_name('ci_unittest.py')


class CIRunnerTests(unittest.TestCase):
    def test_refused_egress_diagnostics_keep_observation_without_exception_text(self):
        import ci_unittest
        cases = [
            (dict(accepted=True, eof=False, complete=False, bytes=0,
                  error='ConnectionResetError', message='private-endpoint'),
             dict(accepted=True, eof=False, complete=False, bytes=0, failure='ConnectionResetError')),
            (dict(accepted='private-accepted', eof=1, complete=None, bytes=True,
                  error='private-exception\n::error::injected'), dict(failure='other')),
            (dict(bytes=-1), {}), (dict(bytes=16385), {}),
        ]
        for observation, expected in cases:
            with self.subTest(expected=expected):
                output = io.StringIO()
                with patch.dict(os.environ, GITHUB_ACTIONS='true'), contextlib.redirect_stdout(output):
                    ci_unittest.annotate_case('test_probe.Probe.test_refusal', dict(egress=observation))
                line = output.getvalue().strip()
                self.assertEqual(json.loads(line.split(' ', 1)[1]), dict(egress=expected))
                self.assertNotIn('private', line)
                self.assertNotIn('::error::', line)

    def test_fixture_diagnostics_exclude_unselected_data_and_unknown_codes(self):
        import ci_unittest
        annotate = getattr(ci_unittest, 'annotate_case', None)
        self.assertTrue(callable(annotate), 'bounded fixture diagnostics missing')
        reports = dict(supervisor=dict(reason='timeout', exit_code=1, tree_reaped=True,
            elapsed_seconds=15.2, stdout=b'private-output', stderr=b'private-error',
            owner='private-owner'), transaction=dict(state='blocked', reason='private-code',
            failure='Refused:guard_port_occupied', journal_events=10,
            journal_ms=[23, 40, 1300], network_ms=['private-time'],
            secret='private-secret'), A=dict(network_ms=[1] * 61),
            B=dict(journal_ms=[-1]), A2=dict(network_ms=[3600001]),
            private_stage=dict(state='observed'))
        output = io.StringIO()
        with patch.dict(os.environ, GITHUB_ACTIONS='true'), contextlib.redirect_stdout(output):
            annotate('test_probe.Probe.test_network', reports)
        line = output.getvalue().strip()
        self.assertTrue(line.startswith('::notice::test_probe.Probe.test_network '))
        value = json.loads(line.split(' ', 1)[1])
        self.assertEqual(value['supervisor'], dict(reason='timeout', exit_code=1,
            tree_reaped=True, elapsed_seconds=15.2, stdout_bytes=14, stderr_bytes=13))
        self.assertEqual(value['transaction'], dict(state='blocked', reason='other',
            failure='Refused:guard_port_occupied', journal_events=10, journal_ms=[23,40,1300]))
        self.assertEqual([value[phase] for phase in ('A','B','A2')], [{},{},{}])
        self.assertNotIn('private', line)
        output = io.StringIO()
        with patch.dict(os.environ, GITHUB_ACTIONS='false'), contextlib.redirect_stdout(output):
            annotate('test_probe.Probe.test_network', reports)
        self.assertEqual(output.getvalue(), '')

    def run_suite(self, source, *arguments, actions='true', standard=False):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'test_probe.py').write_text(textwrap.dedent(source), encoding='utf-8')
            entry = ['-m', 'unittest'] if standard else [str(RUNNER)]
            return subprocess.run(
                [sys.executable, '-B', *entry, 'discover', '-s', directory,
                 '-p', 'test_probe.py', '-v', *arguments],
                env=dict(os.environ, GITHUB_ACTIONS=actions),
                capture_output=True, text=True, timeout=30,
            )

    def test_failed_outcomes_publish_only_parent_identifiers(self):
        result = self.run_suite('''
            import unittest
            class Probe(unittest.TestCase):
                def test_failure(self):
                    self.fail('private-exception-detail')
                def test_error(self):
                    raise ValueError('private-exception-detail')
                def test_subtests(self):
                    with self.subTest(credential='private-subtest-value'):
                        self.fail('private-exception-detail')
                    with self.subTest(credential='another-private-value'):
                        raise ValueError('private-exception-detail')
                @unittest.expectedFailure
                def test_unexpected_success(self):
                    pass
            class SetupError(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    raise RuntimeError('private-setup-detail')
                def test_unused(self):
                    pass
        ''')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('private-exception-detail', result.stderr)  # Normal unittest log retained.
        self.assertEqual(set(result.stdout.splitlines()), {
            '::error::test_probe.Probe.test_failure',
            '::error::test_probe.Probe.test_error',
            '::error::test_probe.Probe.test_subtests',
            '::error::test_probe.Probe.test_unexpected_success',
            '::error::setUpClass (test_probe.SetupError)',
        })
        self.assertEqual(len(result.stdout.splitlines()), 5)  # One annotation per parent.

    def test_success_skip_and_expected_failure_do_not_annotate(self):
        result = self.run_suite('''
            import unittest
            class Probe(unittest.TestCase):
                def test_pass(self):
                    pass
                @unittest.skip('fixture')
                def test_skip(self):
                    self.fail()
                @unittest.expectedFailure
                def test_expected_failure(self):
                    self.fail()
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertIn('Ran 3 tests', result.stderr)
        self.assertIn('skipped=1, expected failures=1', result.stderr)

    def test_failfast_and_nonstandard_identifier_do_not_emit_commands(self):
        result = self.run_suite('''
            import unittest
            class Probe(unittest.TestCase):
                def id(self):
                    return 'private-value\\n::warning::injected%0A'
                def test_first(self):
                    self.fail('fixture')
                def test_second(self):
                    self.fail('fixture')
        ''', '-f')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Ran 1 test', result.stderr)
        self.assertEqual(result.stdout, '::error::test_identifier_unavailable\n')

    def test_local_failure_keeps_standard_output_without_annotations(self):
        result = self.run_suite('''
            import unittest
            class Probe(unittest.TestCase):
                def test_failure(self):
                    self.fail('fixture')
        ''', actions='false')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertIn('FAILED (failures=1)', result.stderr)

    def test_empty_discovery_preserves_interpreter_exit_status(self):
        standard = self.run_suite('', standard=True)
        result = self.run_suite('')
        self.assertEqual(result.returncode, standard.returncode)
        self.assertIn('Ran 0 tests', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
