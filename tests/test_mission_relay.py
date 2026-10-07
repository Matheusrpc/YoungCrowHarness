"""Real local sockets, fake upstream bytes. No Docker, credentials or model calls."""
import importlib.util
import hashlib
import os
import socket
import sys
import threading
import tempfile
import stat
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime/sbx'))


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('relay'), 'restricted relay not implemented')
        import relay
        self.r = relay
        self.claims, self.upstream_requests, self.workers = [], [], []
        self.peers = []
        self.policy = relay.Policy('postman-echo.com', 'GET', '/get?youngcrow=fixture',
                                   (('X-Youngcrow-Probe', 'dummy-sentinel'),))
        self.response = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}'
        self.fragments = None
        self.stall = False
        self.closed = threading.Event()
        self.stop_fixture = threading.Event()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.stop_fixture.set()
        for peer in self.peers:
            try: peer.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            peer.close()
        for thread in self.workers:
            thread.join(2)
            self.assertFalse(thread.is_alive(), 'fixture socket worker leaked')

    def upstream(self, proxy, host, timeout, register, context):
        self.assertEqual(host, self.policy.host)
        self.assertEqual(self.claims, ['consumed'])
        client, peer = socket.socketpair()
        register(client)
        self.peers.extend([client, peer])
        def serve():
            try:
                peer.settimeout(2)
                raw = b''
                while b'\r\n\r\n' not in raw:
                    raw += peer.recv(1)
                length = next((int(line.split(b':', 1)[1]) for line in raw.split(b'\r\n')
                               if line.lower().startswith(b'content-length:')), 0)
                body = b''
                while len(body) < length:
                    body += peer.recv(length-len(body))
                self.upstream_requests.append(raw+body)
                if self.stall:
                    while not self.stop_fixture.is_set():
                        if not peer.recv(1):
                            self.closed.set()
                            return
                else:
                    for fragment in self.fragments or [self.response]:
                        peer.sendall(fragment)
            except OSError:
                self.closed.set()
            finally:
                peer.close()
        thread = threading.Thread(target=serve, daemon=True)
        self.workers.append(thread)
        thread.start()
        return client

    def server(self, seconds=5):
        with patch.object(self.r, 'PORT', 0):
            server = self.r.Relay(deadline_ms=int((time.time()+seconds)*1000),
                                  proxy_ipv4='192.0.2.1', policy=self.policy,
                                  claim=lambda: self.claims.append('consumed'), context=None)
        self.addCleanup(server.stop)
        return server

    def test_ca_snapshot_is_private_hash_bound_and_parsed_from_same_bytes(self):
        raw = b'public-ca-fixture'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ca.pem'
            path.write_bytes(raw)
            info = SimpleNamespace(st_mode=stat.S_IFREG|0o600, st_uid=0)
            with patch.object(Path,'lstat',return_value=info), \
                 patch.object(self.r.os,'fstat',return_value=info), \
                 patch.object(self.r.os,'O_NOFOLLOW',getattr(os,'O_NOFOLLOW',0),create=True), \
                 patch.object(self.r.os,'O_NONBLOCK',getattr(os,'O_NONBLOCK',0),create=True), \
                 patch.object(self.r.ssl,'SSLContext') as context:
                saved, parsed = self.r.read_ca(path,hashlib.sha256(raw).hexdigest())
                self.assertEqual(saved,raw)
                self.assertIs(parsed,context.return_value)
                parsed.load_verify_locations.assert_called_once_with(cadata=raw.decode())
                with self.assertRaisesRegex(self.r.Refused,'ca_changed'):
                    self.r.read_ca(path,'0'*64)
                info.st_mode = stat.S_IFREG|0o666
                with self.assertRaisesRegex(self.r.Refused,'unprotected_ca'):
                    self.r.read_ca(path,hashlib.sha256(raw).hexdigest())

    def test_claim_failure_and_limits_never_approve_exchange(self):
        with patch.object(self.r,'open_upstream',side_effect=self.upstream) as upstream:
            server = self.server()
            server.claim = lambda: (_ for _ in ()).throw(OSError('private-path-canary'))
            server.start()
            self.assertEqual(self.request(server),b'')
            self.assertTrue(server.done.wait(1))
            self.assertEqual(server.result()['reason'],'transport_failed')
            upstream.assert_not_called()
        for response in (b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 9\r\n\r\n{}',
                         b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 99999999\r\n\r\n'):
            with self.subTest(response=response), patch.object(self.r,'open_upstream',side_effect=self.upstream):
                self.claims.clear()
                self.response = response
                server = self.server()
                server.start()
                self.request(server)
                self.assertTrue(server.done.wait(1))
                self.assertEqual(server.result()['state'],'refused')

    def test_tls_keeps_fixed_authority_and_supplied_context(self):
        from unittest.mock import Mock
        raw, context, register = Mock(), Mock(), Mock()
        raw.connect.side_effect = lambda *_: register.assert_called_once_with(raw)
        with patch.object(self.r.socket,'socket',return_value=raw) as create, \
             patch.object(self.r,'header_block',return_value=('HTTP/1.1 200 OK',{})):
            tls = self.r.open_upstream('192.168.65.1','postman-echo.com',2,register,context)
        create.assert_called_once_with(socket.AF_INET,socket.SOCK_STREAM)
        raw.connect.assert_called_once_with(('192.168.65.1',3128))
        raw.sendall.assert_called_once_with(b'CONNECT postman-echo.com:443 HTTP/1.1\r\nHost: postman-echo.com:443\r\n\r\n')
        context.wrap_socket.assert_called_once_with(raw,server_hostname='postman-echo.com',do_handshake_on_connect=False)
        tls.do_handshake.assert_called_once()
        self.assertEqual(register.call_count,2)

    def test_chunked_requires_crlf_and_complete_final_chunk(self):
        for body in (b'2\r\n{}XX0\r\n\r\n', b'2\r\n{}\r\n0\r\n', b'0\r\nX-Trailer: hidden\r\n\r\n'):
            with self.subTest(body=body), patch.object(self.r,'open_upstream',side_effect=self.upstream):
                self.claims.clear()
                self.response = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n'+body
                server = self.server()
                server.start()
                self.request(server)
                self.assertTrue(server.done.wait(1))
                self.assertEqual(server.result()['state'],'refused')

    def test_cancelled_terminal_state_cannot_become_success(self):
        server = self.server()
        server.abort('cancelled','client_closed')
        self.assertTrue(hasattr(server,'succeed'))
        with self.assertRaises(self.r.Refused): server.succeed()
        self.assertEqual(server.result()['state'],'cancelled')

    def test_partial_thread_start_is_refused_and_only_started_thread_is_joined(self):
        from unittest.mock import Mock
        first, second = Mock(), Mock()
        first.is_alive.return_value = False
        second.start.side_effect = RuntimeError('cannot start thread')
        second.join.side_effect = RuntimeError('cannot join unstarted thread')
        server = self.server()
        with patch.object(self.r.threading,'Thread',side_effect=[first,second]):
            with self.assertRaisesRegex(self.r.Refused,'relay_start_failed'):
                server.start()
        first.join.assert_called()
        second.join.assert_not_called()
        self.assertTrue(server.stop())
        with self.assertRaises(self.r.Refused): server.start()

    def request(self, server, request=None):
        client = socket.create_connection(('127.0.0.1', server.port), timeout=3)
        self.addCleanup(client.close)
        raw = request or (f'GET {self.policy.target} HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n'
                          'Authorization: private-canary\r\nCookie: private-canary\r\n\r\n').encode()
        client.sendall(raw.replace(b'{PORT}', str(server.port).encode()))
        data = b''
        while True:
            part = client.recv(4096)
            if not part: break
            data += part
        server.stop()
        return data

    def test_fixed_destination_and_headers_with_claim_before_upstream(self):
        server = self.server()
        with patch.object(self.r, 'open_upstream', side_effect=self.upstream):
            server.start()
            reply = self.request(server)
        self.assertTrue(reply.endswith(b'{}'))
        self.assertEqual(len(self.upstream_requests), 1)
        self.assertIn(b'Host: postman-echo.com\r\n', self.upstream_requests[0])
        self.assertIn(b'X-Youngcrow-Probe: dummy-sentinel\r\n', self.upstream_requests[0])
        self.assertNotIn(b'private-canary', self.upstream_requests[0]+reply)
        self.assertEqual(server.result()['state'], 'succeeded')

    def test_bad_destination_and_ambiguous_framing_never_open_upstream(self):
        lines = [
            b'CONNECT api.openai.com:443 HTTP/1.1\r\nHost: 127.0.0.1:{PORT}\r\n\r\n',
            b'GET https://mcp.invalid/ HTTP/1.1\r\nHost: 127.0.0.1:{PORT}\r\n\r\n',
            b'GET //127.0.0.1/ HTTP/1.1\r\nHost: 127.0.0.1:{PORT}\r\n\r\n',
        ]
        headers = [b'Host: wrong', b'Host: 127.0.0.1:{PORT}\r\nHost: 127.0.0.1:{PORT}',
                   b'Host: 127.0.0.1:{PORT}\r\nContent-Length: 0\r\ncontent-length: 0',
                   b'Host: 127.0.0.1:{PORT}\r\nTransfer-Encoding: chunked',
                   b'Host: 127.0.0.1:{PORT}\r\nContent-Length: +1',
                   b'Host: 127.0.0.1:{PORT}\r\nHost : bad',
                   b'Host: 127.0.0.1:{PORT}\r\nConnection: upgrade',
                   b'Host: 127.0.0.1:{PORT}\r\nExpect: 100-continue',
                   b'Host: 127.0.0.1:{PORT}\r\nContent-Encoding: gzip']
        lines += [b'GET /get?youngcrow=fixture HTTP/1.1\r\n'+h+b'\r\n\r\n' for h in headers]
        for raw in lines:
            with self.subTest(raw=raw), patch.object(self.r, 'open_upstream') as upstream:
                server = self.server()
                server.start()
                self.request(server, raw)
                upstream.assert_not_called()
                self.assertFalse(self.claims)
                self.assertEqual(server.result()['state'], 'refused')

    def test_fragmented_chunked_sse_preserves_bytes_and_drops_secret_headers(self):
        self.policy = self.r.Policy('api.anthropic.com', 'POST', '/v1/messages', ())
        body = 'event: message_start\ndata: {"text":"olá"}\n\nevent: ping\ndata: {}\n\nevent: message_stop\ndata: {}\n\n'.encode()
        chunked = b''.join(f'{len(b):x}\r\n'.encode()+b+b'\r\n' for b in [body[:37], body[37:38], body[38:]])+b'0\r\n\r\n'
        raw = (b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n'
               b'Set-Cookie: private-canary\r\nAuthorization: private-canary\r\n\r\n'+chunked)
        self.fragments = [raw[i:i+3] for i in range(0,len(raw),3)]
        server = self.server()
        with patch.object(self.r, 'open_upstream', side_effect=self.upstream):
            server.start()
            result = self.request(server, b'POST /v1/messages HTTP/1.1\r\nHost: 127.0.0.1:{PORT}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}')
        head, received = result.split(b'\r\n\r\n',1)
        self.assertEqual(received,body)
        self.assertNotIn(b'private-canary',head)
        self.assertEqual(server.result()['state'],'succeeded')

    def test_redirect_and_response_smuggling_are_refused_without_following(self):
        for response in [b'HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1/private-canary\r\n\r\n',
                         b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nTransfer-Encoding: chunked\r\n\r\n',
                         b'HTTP/1.1 101 Switching Protocols\r\n\r\n']:
            with self.subTest(response=response), patch.object(self.r, 'open_upstream', side_effect=self.upstream) as upstream:
                self.claims.clear()
                self.response=response
                server=self.server();server.start()
                result=self.request(server)
                self.assertEqual(upstream.call_count,1)
                self.assertNotIn(b'private-canary',result)
                self.assertEqual(server.result()['state'],'refused')

    def test_deadline_and_cancellation_close_silent_upstream_without_retry(self):
        self.stall=True
        for cancel in (False,True):
            self.claims.clear();self.closed.clear()
            server=self.server(seconds=2)
            with patch.object(self.r,'open_upstream',side_effect=self.upstream) as upstream:
                server.start()
                client=socket.create_connection(('127.0.0.1',server.port),timeout=2)
                client.sendall(f'GET {self.policy.target} HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n\r\n'.encode())
                self.assertTrue(server.upstream_started.wait(1))
                if cancel: client.close()
                self.assertTrue(self.closed.wait(2), 'upstream socket leaked')
                client.close();server.stop()
                self.assertEqual(upstream.call_count,1)
                self.assertIn(server.result()['state'],('deadline','cancelled'))


if __name__ == '__main__':
    unittest.main()
