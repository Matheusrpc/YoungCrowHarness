"""Host destination gate: local sockets and fake resolution, no external requests."""
import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class EgressTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_egress'), 'product destination guard missing')
        import mission_egress
        self.m = mission_egress
        self.config = dict(schema_version=1,operation_id=str(uuid.uuid4()),phase='A',nonce='a'*32,
                           deadline_ms=int(time.time()*1000)+2000,host='postman-echo.com',port=443,
                           listen_port=0,forbidden_ips=[],max_connections=1)
        self.events=[]
        self.sockets=[]
        self.threads=[]
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for sock in self.sockets:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            sock.close()
        for thread in self.threads:
            thread.join(2)
            self.assertFalse(thread.is_alive(), 'socket fixture worker leaked')

    def test_mixed_dns_private_host_and_ip_transition_addresses_all_refused(self):
        for address in ('127.0.0.1','10.0.0.1','169.254.169.254','192.168.65.1','::1','ff02::1',
                        '::ffff:8.8.8.8','2002:0808:0808::','64:ff9b::808:808','1.1.1.1'):
            with self.subTest(address=address), self.assertRaisesRegex(ValueError,'destination_forbidden'):
                self.m.validate_destination('postman-echo.com',443,('8.8.8.8',address),{'1.1.1.1'})
        for host,port in [('localhost',443),('postman-echo.com',80),('8.8.8.8',443)]:
            with self.assertRaisesRegex(ValueError,'origin_forbidden'):
                self.m.validate_destination(host,port,('8.8.8.8',),set())

    def test_dials_validated_numeric_ip_once_and_checks_peer_before_payload(self):
        sock=Mock()
        sock.getpeername.return_value=('8.8.8.8',443)
        factory=Mock(return_value=sock)
        connected, report=self.m.connect_checked('postman-echo.com',443,self.config['deadline_ms'],set(),
                              resolve=lambda *_:('8.8.8.8',),socket_factory=factory)
        self.assertIs(connected,sock)
        sock.connect.assert_called_once_with(('8.8.8.8',443))
        sock.sendall.assert_not_called()
        self.assertEqual(report['peer'],'8.8.8.8')
        sock.getpeername.return_value=('127.0.0.1',443)
        with self.assertRaisesRegex(ValueError,'peer_mismatch'):
            self.m.connect_checked('postman-echo.com',443,self.config['deadline_ms'],set(),
                                   resolve=lambda *_:('8.8.8.8',),socket_factory=factory)
        sock.close.assert_called_once()

    def test_resolver_requires_complete_bounded_process_and_valid_output(self):
        import mission_process
        for result in (dict(tree_reaped=False,exit_code=0,stdout=b'["8.8.8.8"]',reason='completed'),
                       dict(tree_reaped=True,exit_code=0,stdout=b'[]',reason='timeout'),
                       dict(tree_reaped=True,exit_code=0,stdout=b'not-json',reason='completed')):
            with patch.object(mission_process,'supervise',return_value=result), self.assertRaises((ValueError,TimeoutError)):
                self.m.resolve_addresses('postman-echo.com',1)

    def launch_client(self, port, payload, body=b''):
        def run():
            try:
                sock=socket.create_connection(('127.0.0.1',port),timeout=1)
                self.sockets.append(sock)
                sock.sendall(b'\x05\x01\x00')
                if sock.recv(2) != b'\x05\x00': return
                sock.sendall(payload)
                self.reply=sock.recv(10)
                if self.reply[:2]==b'\x05\x00':
                    sock.sendall(body)
                    sock.shutdown(socket.SHUT_WR)
                    self.received=sock.recv(128)
            except OSError:
                pass
        thread=threading.Thread(target=run)
        self.threads.append(thread)
        thread.start()

    def test_numeric_socks_request_never_reaches_resolver_or_connect(self):
        def emit(kind, **row):
            self.events.append(dict(kind=kind,**row))
            if kind=='ready': self.launch_client(row['port'],b'\x05\x01\x00\x01'+b'\x7f\x00\x00\x01'+b'\x01\xbb')
        with patch.object(self.m,'connect_checked',side_effect=AssertionError('must not dial')):
            self.assertEqual(self.m.serve(self.config,emit),125)
        self.assertEqual(self.events[-1]['kind'],'closed')
        self.assertIn('socks_request',[e.get('reason') for e in self.events])

    def test_one_tunnel_preserves_bytes_and_closes_sockets(self):
        upstream,peer=socket.socketpair()
        self.sockets.extend([upstream,peer])
        def echo():
            peer.settimeout(2)
            self.sent=peer.recv(128)
            peer.sendall(b'response')
            peer.shutdown(socket.SHUT_WR)
        worker=threading.Thread(target=echo);self.threads.append(worker);worker.start()
        def emit(kind, **row):
            self.events.append(dict(kind=kind,**row))
            if kind=='ready':
                host=b'postman-echo.com'
                self.launch_client(row['port'],b'\x05\x01\x00\x03'+bytes([len(host)])+host+b'\x01\xbb',b'opaque-tls-fixture')
        with patch.object(self.m,'connect_checked',return_value=(upstream,dict(peer='8.8.8.8',peer_port=443))):
            self.assertEqual(self.m.serve(self.config,emit),0)
        for thread in self.threads: thread.join(2)
        self.assertEqual(self.sent,b'opaque-tls-fixture')
        self.assertEqual(self.received,b'response')
        self.assertEqual([e['kind'] for e in self.events],['ready','request','destination','finished','closed'])
        self.assertEqual(upstream.fileno(),-1)

    def test_idle_deadline_and_failed_journal_close_listener(self):
        self.config['deadline_ms']=int(time.time()*1000)+100
        def emit(kind,**row): self.events.append(dict(kind=kind,**row))
        started=time.monotonic()
        self.assertEqual(self.m.serve(self.config,emit),125)
        self.assertLess(time.monotonic()-started,1)
        self.assertEqual(self.events[-1]['kind'],'closed')
        self.config['deadline_ms']=int(time.time()*1000)+1000
        def fail(kind,**row):
            self.events.append(dict(kind=kind,**row))
            if kind=='ready': raise RuntimeError('durable journal unavailable')
        with self.assertRaises(RuntimeError): self.m.serve(self.config,fail)
        port=next(e['port'] for e in reversed(self.events) if e['kind']=='ready')
        with self.assertRaises(OSError): socket.create_connection(('127.0.0.1',port),timeout=.1)

    def test_invalid_config_cannot_open_a_socket(self):
        for change in ({'phase':'B'},{'max_connections':2},{'port':True},{'host':'localhost'},
                       {'deadline_ms':int(time.time()*1000)+999999},{'nonce':'bad'}):
            with patch.object(self.m.socket,'socket',side_effect=AssertionError('must not open')):
                with self.assertRaises(ValueError): self.m.serve(dict(self.config,**change),lambda *_:None)

    def test_failure_metadata_never_copies_exception_text(self):
        def emit(kind,**row):
            self.events.append(dict(kind=kind,**row))
            if kind=='ready': raise ValueError('private_credential_canary')
        self.assertEqual(self.m.serve(self.config,emit),125)
        self.assertNotIn('private_credential_canary',json.dumps(self.events))


if __name__ == '__main__': unittest.main()
