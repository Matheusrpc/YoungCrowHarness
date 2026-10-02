"""Network acquisition regressions; only explicitly allowed loopback is contacted."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


@contextmanager
def server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith('/redirect'):
                self.send_response(302)
                self.send_header('Location', 'http://private.example/secret')
                self.end_headers()
                return
            if self.path.startswith('/loop'):
                self.send_response(302)
                self.send_header('Location', '/loop')
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Disposition', 'attachment; filename="../../outside.pdf"')
            if self.path.startswith('/sized'):
                self.send_header('Content-Length', str(len(b'%PDF-1.4\ncontrolled bytes')))
            if self.path.startswith('/lying'):
                self.send_header('Content-Length', '2')
                self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            try:
                if self.path.startswith('/slow'):
                    for _ in range(20):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        time.sleep(0.1)
                elif self.path.startswith('/large'):
                    self.wfile.write(b'%PDF-1.4\n' + b'x' * 10000)
                elif self.path.startswith('/lying'):
                    self.wfile.write(b'2710\r\n' + b'x' * 10000 + b'\r\n0\r\n\r\n')
                elif self.path.startswith('/watch'):
                    self.wfile.write(b'<html><body><video src="private.mp4"></video></body></html>')
                else:
                    self.wfile.write(b'%PDF-1.4\ncontrolled bytes')
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.fetch = importlib.import_module('source_fetch')
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / 'download'

    def test_rejects_any_non_public_dns_answer_and_embedded_addresses(self):
        for address in ('127.0.0.1', '10.2.3.4', '169.254.169.254', '::1', 'fe80::1',
                        '::ffff:127.0.0.1', '224.0.0.1', '64:ff9b::a00:1'):
            with self.subTest(address=address), patch('socket.getaddrinfo', return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443)),
                (socket.AF_INET6, socket.SOCK_STREAM, 6, '', (address, 443))]):
                with self.assertRaises(ValueError):
                    self.fetch.public_addresses('public-looking.example', 443)

    def test_pins_approved_ip_preserves_sni_and_never_resolves_twice(self):
        sock = MagicMock()
        sock.makefile.return_value = io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\n%PDF-1.4\nfixture')
        with patch('socket.getaddrinfo', side_effect=[
            [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))],
            [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]]) as dns, \
             patch('socket.socket', return_value=sock), \
             patch('ssl.create_default_context') as tls:
            tls.return_value.wrap_socket.return_value = sock
            result = self.fetch.fetch_source('https://public.example/source?token=secret', self.target, max_bytes=1000)
        self.assertEqual(dns.call_count, 1)
        sock.connect.assert_called_once_with(('8.8.8.8', 443))
        tls.return_value.wrap_socket.assert_called_once_with(sock, server_hostname='public.example')
        self.assertIn(b'Host: public.example', sock.sendall.call_args.args[0])
        self.assertNotIn('secret', json.dumps(result))
        self.assertEqual(result['extension'], '.pdf')

    def test_url_validation_never_exposes_credentials(self):
        for url in ('file:///private', 'ftp://example.org/a', 'http://user:secret@example.org/a',
                    'http://example.org/\r\nsecret', 'http://[fe80::1%25eth0]/a'):
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as raised:
                    self.fetch.fetch_source(url, self.target, max_bytes=1000)
                self.assertNotIn('secret', str(raised.exception))
                self.assertFalse(self.target.exists())

    def test_real_download_is_bounded_and_ignores_suggested_filename(self):
        with server() as origin:
            result = self.fetch.fetch_source(origin + '/document?token=secret#private', self.target,
                                             max_bytes=1000, allowed_private_hosts=('127.0.0.1',))
        self.assertEqual(Path(result['path']), self.target)
        self.assertEqual(self.target.read_bytes(), b'%PDF-1.4\ncontrolled bytes')
        self.assertEqual(result['extension'], '.pdf')
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('private', json.dumps(result))
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_private_redirect_is_rejected_despite_initial_allowlist(self):
        with server() as origin, patch('socket.getaddrinfo', return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 80))]):
            with self.assertRaises(ValueError):
                self.fetch.fetch_source(origin + '/redirect', self.target, max_bytes=1000,
                                         allowed_private_hosts=('127.0.0.1',))
        self.assertFalse(self.target.exists())

    def test_limits_actual_bytes_ambiguous_headers_redirects_and_total_time(self):
        with server() as origin:
            for route in ('large', 'lying', 'loop', 'slow'):
                with self.subTest(route=route):
                    started = time.monotonic()
                    with self.assertRaises(ValueError):
                        self.fetch.fetch_source(origin + '/' + route, self.target, max_bytes=1000,
                                                 timeout_seconds=0.25, allowed_private_hosts=('127.0.0.1',))
                    self.assertFalse(self.target.exists())
                    self.assertLess(time.monotonic() - started, 1.5)

    def test_existing_destination_preserved_and_watch_page_pending(self):
        self.target.write_bytes(b'preserve')
        with server() as origin:
            with self.assertRaises(ValueError):
                self.fetch.fetch_source(origin, self.target, max_bytes=1000, allowed_private_hosts=('127.0.0.1',))
            self.assertEqual(self.target.read_bytes(), b'preserve')
            self.target.unlink()
            result = self.fetch.fetch_source(origin + '/watch', self.target, max_bytes=1000,
                                             allowed_private_hosts=('127.0.0.1',))
        self.assertEqual(result['state'], 'pending')
        self.assertIn('media_source_unavailable', result['warnings'])

    def test_sized_response_closes_cleanly_after_last_byte(self):
        with server() as origin:
            result = self.fetch.fetch_source(origin + '/sized', self.target, max_bytes=1000,
                                             allowed_private_hosts=('127.0.0.1',))
        self.assertEqual(result['state'], 'ready')
        self.assertEqual(result['bytes'], len(b'%PDF-1.4\ncontrolled bytes'))

    def test_stalled_dns_obeys_total_deadline_without_connecting(self):
        def stalled(*args):
            time.sleep(0.5)
            return ['8.8.8.8']
        started = time.monotonic()
        with patch('source_fetch.public_addresses', side_effect=stalled), patch('source_fetch.connect') as connect:
            with self.assertRaises(ValueError):
                self.fetch.fetch_source('https://example.org/doc', self.target, max_bytes=1000, timeout_seconds=0.1)
        connect.assert_not_called()
        self.assertLess(time.monotonic() - started, 0.4)


if __name__ == '__main__':
    unittest.main()
