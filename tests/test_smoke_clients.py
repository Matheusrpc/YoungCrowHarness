"""Discovery protocol regressions use local child fixtures, never a provider."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import smoke_clients as smoke

SKILLS = ['yc-personalizer', 'yc-config', 'yc-missao', 'yc-status']
FIXTURE = r'''
import json, pathlib, sys, time
log, fault = pathlib.Path(sys.argv[1]), sys.argv[2]
if 'mcp' in sys.argv:
    print('n8n.SEU-DOMINIO.example Pending approval')
    sys.exit(0)
if '--version' in sys.argv:
    print('fixture-client 1.0')
    sys.exit(0)
for line in sys.stdin:
    message = json.loads(line)
    with log.open('a') as stream:
        stream.write(json.dumps(message) + '\n')
    if fault == 'invalid':
        print('not-json', flush=True)
        continue
    if fault == 'envelope':
        print(json.dumps({'type':'control_response','response':None,'id':message.get('id'),'result':None}), flush=True)
        continue
    if fault == 'silent':
        continue
    names = ['yc-personalizer', 'yc-config', 'yc-missao', 'yc-status']
    if fault == 'missing':
        names.remove('yc-status')
    if message.get('method') == 'initialize':
        response = {'id':message['id'],'result':{}}
    elif message.get('method') == 'initialized':
        continue
    elif message.get('method') == 'skills/list':
        response = {'id':message['id'],'result':{'data':[{'skills':[{'name':n} for n in names],'errors':[]}]}}
    elif message.get('type') == 'control_request':
        response = {'type':'control_response','response':{'subtype':'success','request_id':'init','response':{'commands':[{'name':n} for n in names]}}}
    else:
        raise SystemExit('Unexpected model/tool request: ' + str(message))
    print(json.dumps(response), flush=True)
'''


class ClientDiscoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.fixture = self.base / 'protocol.py'
        self.fixture.write_text(FIXTURE)
        self.log = self.base / 'requests.jsonl'
        self.executable = self.base / 'native-client.exe'
        self.executable.touch()
        self.children = []
        self.fault = ''
        real_popen = subprocess.Popen

        def spawn(argv, *args, **kwargs):
            if str(argv[0]) == str(self.executable):
                argv = [sys.executable, '-B', str(self.fixture), str(self.log), self.fault, *argv[1:]]
                child = real_popen(argv, *args, **kwargs)
                self.children.append(child)
                return child
            return real_popen(argv, *args, **kwargs)
        self.patch = patch('subprocess.Popen', side_effect=spawn)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def probe(self, client):
        fn = smoke.check_codex if client == 'codex' else smoke.check_claude_discovery
        self.assertIn('discovery_only', __import__('inspect').signature(fn).parameters,
                      'The existing probe cannot run only mission-skill discovery')
        return fn(str(self.executable), self.base, os.environ.copy(), discovery_only=True)

    def requests(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_selected_client_loads_four_skills_without_user_or_model_request(self):
        for client in ('codex', 'claude'):
            with self.subTest(client=client), redirect_stdout(io.StringIO()):
                if self.log.exists(): self.log.unlink()
                result = self.probe(client)
                self.assertEqual(result['skills'], sorted(SKILLS))
                expected = ['initialize', 'initialized', 'skills/list'] if client == 'codex' else ['initialize']
                observed = [m.get('method', m.get('request', {}).get('subtype')) for m in self.requests()]
                self.assertEqual(observed, expected)
                self.assertTrue(all(c.poll() is not None for c in self.children))

    def test_missing_skill_invalid_json_and_timeout_fail_and_stop_child(self):
        for client in ('codex', 'claude'):
            for fault in ('missing', 'invalid', 'silent', 'envelope'):
                with self.subTest(client=client, fault=fault), redirect_stdout(io.StringIO()):
                    self.fault = fault
                    self.assertTrue(hasattr(smoke, 'DISCOVERY_SECONDS'), 'Discovery deadline unavailable')
                    with patch.object(smoke, 'DISCOVERY_SECONDS', .5), self.assertRaises((ValueError, TimeoutError, TypeError)):
                        self.probe(client)
                    self.assertTrue(all(c.poll() is not None for c in self.children))

    def test_receipt_records_one_client_and_preserves_existing_destination(self):
        self.assertIn('argv', __import__('inspect').signature(smoke.main).parameters,
                      'The smoke cannot select one discovery client')
        report = self.base / 'receipt.json'
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = smoke.main(['--discovery-only','--codex',str(self.executable),'--report',str(report)])
        self.assertEqual(code, 0)
        result = json.loads(report.read_text())
        self.assertEqual(result['state'], 'passed')
        self.assertEqual(result['clients']['claude']['state'], 'not_run')
        codex = result['clients']['codex']
        self.assertEqual(codex['state'], 'passed')
        self.assertEqual(codex['version'], 'fixture-client 1.0')
        self.assertEqual(codex['skills'], sorted(SKILLS))
        self.assertEqual(len(codex['skill_sha256']), 8)
        self.assertEqual(result['user_prompts_sent'], 0)
        self.assertFalse(result['application_verified'])
        self.assertEqual(result['platform'],sys.platform)
        self.assertEqual(codex['executable_sha256'],__import__('hashlib').sha256(b'').hexdigest())
        before, calls = report.read_bytes(), self.log.read_bytes()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(FileExistsError):
            smoke.main(['--discovery-only','--codex',str(self.executable),'--report',str(report)])
        self.assertEqual(report.read_bytes(), before)
        self.assertEqual(self.log.read_bytes(), calls)

    def test_legacy_mode_keeps_all_probes_and_requires_both_clients(self):
        calls = []
        def remember(name):
            return lambda *args, **kwargs: calls.append(name)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                smoke.main(['--codex',str(self.executable)])
            with patch.object(smoke,'check_codex',remember('codex')), \
                 patch.object(smoke,'check_claude_discovery',remember('claude')), \
                 patch.object(smoke,'check_codex_agent',remember('agent')):
                code = smoke.main(['--codex',str(self.executable),'--claude',str(self.executable)])
        self.assertEqual(code,0)
        self.assertEqual(calls,['codex','claude','agent'])

    def test_invalid_envelope_is_a_failed_receipt_not_a_running_attempt(self):
        self.fault = 'envelope'
        report = self.base / 'envelope.json'
        with redirect_stdout(io.StringIO()):
            try:
                code = smoke.main(['--discovery-only','--claude',str(self.executable),'--report',str(report)])
            except AttributeError as error:
                self.fail(f'Invalid native envelope escaped the receipt: {error}')
        self.assertEqual(code,1)
        self.assertEqual(json.loads(report.read_text())['clients']['claude']['state'],'failed')


    def test_cleanup_failure_keeps_a_failed_receipt_and_nonzero_exit(self):
        report = self.base / 'cleanup.json'
        cleanup = smoke.SetupTests.doCleanups
        def fail_cleanup(test):
            cleanup(test)
            return False
        with patch.object(smoke.SetupTests, 'doCleanups', fail_cleanup), redirect_stdout(io.StringIO()):
            code = smoke.main(['--discovery-only','--codex',str(self.executable),'--report',str(report)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(report.read_text())['state'], 'failed')


    def test_failed_discovery_is_recorded_without_marking_client_passed(self):
        self.assertIn('argv', __import__('inspect').signature(smoke.main).parameters,
                      'The smoke has no per-client discovery receipt')
        self.fault = 'missing'
        report = self.base / 'failed.json'
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = smoke.main(['--discovery-only','--claude',str(self.executable),'--report',str(report)])
        self.assertEqual(code, 1)
        result = json.loads(report.read_text())
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['clients']['claude']['state'], 'failed')
        self.assertEqual(result['clients']['codex']['state'], 'not_run')
        self.assertTrue(all(c.poll() is not None for c in self.children))


if __name__ == '__main__':
    unittest.main()
