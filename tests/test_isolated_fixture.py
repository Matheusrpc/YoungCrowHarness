"""Fixed loopback fixture: fake responses, no external network or model."""
import importlib.util
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]


class IsolatedFixtureTests(unittest.TestCase):
    def setUp(self):
        path = ROOT/'runtime/sbx/fixture.py'
        self.assertTrue(path.is_file(), 'fixed runtime fixture missing')
        spec = importlib.util.spec_from_file_location('isolated_fixture', path)
        self.fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.fixture)
        self.nonce, self.placeholder = uuid.uuid4().hex, 'youngcrow-probe-'+uuid.uuid4().hex
        self.phase = 'A'
        self.deadline = int(time.time()*1000)+4000
        self.injected = 'disposable-probe-'+uuid.uuid4().hex
        self.injection_sha256 = hashlib.sha256(self.injected.encode()).hexdigest()

    def body(self):
        return dict(args={'youngcrow': self.nonce+'-'+self.phase},
                    headers={'x-youngcrow-probe': self.placeholder},
                    url='https://postman-echo.com/get?youngcrow='+self.nonce+'-'+self.phase)

    def exchange(self, body=None, *, response=None, injection_sha256=None):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        seen = []
        payload = json.dumps(self.body() if body is None else body).encode()
        wire = response if response is not None else (
            b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n'+payload)
        def serve():
            right.settimeout(2)
            raw = b''
            while b'\r\n\r\n' not in raw:
                chunk = right.recv(1)
                if not chunk: return
                raw += chunk
            seen.append(raw)
            for start in range(0, len(wire), 29):
                try:
                    right.sendall(wire[start:start+29])
                except OSError:
                    break
            right.close()
        worker = threading.Thread(target=serve)
        worker.start()
        calls = []
        def connect(address, timeout):
            calls.append(address)
            self.assertEqual(address, ('127.0.0.1', 62143))
            return left
        try:
            with patch.object(self.fixture.socket, 'create_connection', side_effect=connect):
                args = {} if injection_sha256 is None else dict(injection_sha256=injection_sha256)
                value = self.fixture.request(self.nonce, self.phase, self.placeholder, self.deadline, **args)
            self.assertEqual(calls, [('127.0.0.1', 62143)])
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0], (
                f'GET /get?youngcrow={self.nonce}-{self.phase} HTTP/1.1\r\n'
                'Host: 127.0.0.1:62143\r\nConnection: close\r\n\r\n').encode())
            self.assertNotIn(self.placeholder.encode(), seen[0])
            return value
        finally:
            left.close()
            worker.join(3)
            self.assertFalse(worker.is_alive())

    def test_initialization_never_opens_network(self):
        with patch.object(self.fixture.socket, 'create_connection', side_effect=AssertionError('network')):
            value = self.fixture.initialize()
        self.assertEqual(value, dict(schema_version=1, fixture_id='isolated-egress-v1',
                                     stage='initialize', network_requests=0, model_calls=0))

    def test_fixed_get_checks_echo_and_returns_bounded_metadata(self):
        value = self.exchange()
        self.assertEqual(value['nonce'], self.nonce)
        self.assertEqual(value['phase'], 'A')
        self.assertTrue(value['echo_matches'])
        self.assertEqual(value['network_requests'], 1)
        self.assertEqual(value['model_calls'], 0)
        self.assertRegex(value['response_sha256'], r'^[0-9a-f]{64}$')
        self.assertNotIn(self.placeholder, json.dumps(value))
        self.assertLess(len(json.dumps(value)), 1024)

    def test_mismatched_echo_never_succeeds(self):
        for key, value in (('args', {'youngcrow': 'different'}), ('headers', {}),
                           ('url', 'https://example.invalid')):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'echo_mismatch'):
                self.exchange(dict(self.body(), **{key: value}))

    def test_injection_requires_distinct_value_and_returns_only_its_bound_hash(self):
        body=dict(self.body(),headers={'x-youngcrow-probe':self.injected})
        value=self.exchange(body,injection_sha256=self.injection_sha256)
        self.assertEqual(value['schema_version'],2)
        self.assertTrue(value['injection_matches'])
        self.assertEqual(value['injected_value_sha256'],self.injection_sha256)
        self.assertNotIn('echo_matches',value)
        self.assertNotIn(self.injected,json.dumps(value))

    def test_placeholder_wrong_value_duplicate_and_nonstring_never_prove_injection(self):
        for headers in ({'x-youngcrow-probe':self.placeholder},{'x-youngcrow-probe':'wrong'},
                        {'x-youngcrow-probe':self.injected,'X-Youngcrow-Probe':self.injected},
                        {'x-youngcrow-probe':[self.injected]}):
            with self.subTest(headers=headers),self.assertRaisesRegex(ValueError,'injection_mismatch'):
                self.exchange(dict(self.body(),headers=headers),injection_sha256=self.injection_sha256)

    def test_invalid_or_placeholder_hash_refuses_before_network(self):
        for digest in (True,'A'*64,'bad',hashlib.sha256(self.placeholder.encode()).hexdigest()):
            with self.subTest(digest=digest),patch.object(self.fixture.socket,'create_connection',side_effect=AssertionError('network')):
                with self.assertRaisesRegex(ValueError,'invalid_fixture_request'):
                    self.fixture.request(self.nonce,self.phase,self.placeholder,self.deadline,injection_sha256=digest)

    def test_redirect_invalid_json_and_oversized_response_refuse(self):
        for response in (b'HTTP/1.1 302 Found\r\nLocation: https://example.invalid\r\n\r\n',
                         b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{',
                         b'x'*70000):
            with self.subTest(size=len(response)), self.assertRaises(ValueError):
                self.exchange(response=response)

    def test_invalid_identity_deadline_and_extra_arguments_never_connect(self):
        import io
        from contextlib import redirect_stdout
        with patch.object(self.fixture.socket, 'create_connection', side_effect=AssertionError('network')):
            for values in (('bad', 'A', self.placeholder, self.deadline),
                           (self.nonce, 'C', self.placeholder, self.deadline),
                           (self.nonce, 'A', 'real-token-not-allowed', self.deadline),
                           (self.nonce, 'A', self.placeholder, 0)):
                with self.subTest(values=values), self.assertRaises(ValueError):
                    self.fixture.request(*values)
            output = io.StringIO()
            with redirect_stdout(output):
                code = self.fixture.main(['initialize', '--url', 'canary'])
            self.assertEqual(code, 125)
            self.assertNotIn('canary', output.getvalue())


if __name__ == '__main__':
    unittest.main()
