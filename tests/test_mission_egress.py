"""Host destination gate: local sockets and fake resolution, no external requests."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
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

    def inherited(self, mode, *, exit_code=0):
        import mission_process
        result, stage = None, 'fixture_setup'
        try:
            with tempfile.TemporaryDirectory() as temporary:
                config = dict(self.config, deadline_ms=int(time.time()*1000)+5000)
                stage = 'fixture_supervise'
                result = mission_process.supervise(dict(argv=[sys.executable,'-I','-B',
                    str(Path(__file__).parent/'fixtures/egress_controller.py')], cwd=temporary,
                    stdin=json.dumps(dict(mode=mode,config=config)).encode(), timeout_seconds=6,
                    output_limit_bytes=16384, client='metadata', connection='native'),
                    on_started=lambda _:None, stop_requested=lambda:False)
                stage = 'fixture_cleanup'
        except Exception as error:
            from ci_unittest import annotate_case
            # Last stage reached, not a claim about the cause of an unwinding error.
            reports = dict(fixture=dict(reason=stage, failure=type(error).__name__))
            if result is not None:
                reports['supervisor'] = result
            try:
                annotate_case(self.id(), reports)
            except OSError:
                pass  # A closed CI output must not replace the fixture exception.
            raise
        if exit_code or (result['reason'],result['exit_code']) != ('completed',exit_code) or not result['tree_reaped']:
            from ci_unittest import annotate_case
            reports = dict(supervisor=result)
            try:
                receipt = json.loads(result['stdout'])
            except (ValueError, UnicodeError, RecursionError):
                receipt = None
            if isinstance(receipt, dict) and isinstance(receipt.get('upstream_observation'), dict):
                reports['egress'] = receipt['upstream_observation']
            annotate_case(self.id(), reports)
        self.assertEqual((result['reason'],result['exit_code']),('completed',exit_code),result)
        self.assertTrue(result['tree_reaped'])
        if exit_code:
            self.assertTrue(mission_process.owner_gone(result['owner']))
            return result
        return json.loads(result['stdout'])

    def test_incomplete_or_invalid_receipt_still_fails_with_bounded_diagnostics(self):
        receipt = dict(upstream_observation=dict(accepted=True, eof=False, complete=False,
            bytes=0, error='ConnectionResetError', path='private-path'))
        for stdout in (json.dumps(receipt).encode(), b'not-json', b'\xff', b'[]', b'[' * 2000):
            with self.subTest(stdout_bytes=len(stdout)):
                result = dict(reason='completed', exit_code=1, tree_reaped=True,
                              stdout=stdout, stderr=b'private-traceback')
                output = io.StringIO()
                with patch('mission_process.supervise', return_value=result), \
                     patch.dict(os.environ, GITHUB_ACTIONS='true'), contextlib.redirect_stdout(output):
                    with self.assertRaises(AssertionError):
                        self.inherited('guard_domain_persistfail')
                line = output.getvalue().strip()
                self.assertNotIn('private', line)
                diagnostics = json.loads(line.split(' ', 1)[1])
                self.assertEqual(diagnostics['supervisor']['exit_code'], 1)
                if stdout == json.dumps(receipt).encode():
                    self.assertEqual(diagnostics['egress'], dict(accepted=True, eof=False,
                        complete=False, bytes=0, failure='ConnectionResetError'))
                else:
                    self.assertNotIn('egress', diagnostics)

    def test_fixture_exceptions_publish_bounded_diagnostics_and_still_raise(self):
        original_temporary = tempfile.TemporaryDirectory
        private_error = type('private-error\n::error::injected', (Exception,), {})
        for stage, error_type in (('fixture_setup', PermissionError),
                                  ('fixture_supervise', ValueError),
                                  ('fixture_cleanup', PermissionError),
                                  ('fixture_supervise', private_error)):
            for actions in ('true', 'false'):
                with self.subTest(stage=stage, actions=actions, error_type=error_type):
                    error = error_type('private-path-and-credential\n::error::injected')
                    @contextlib.contextmanager
                    def temporary():
                        if stage == 'fixture_setup':
                            raise error
                        with original_temporary() as directory:
                            yield directory
                        if stage == 'fixture_cleanup':
                            raise error
                    result = dict(reason='completed', exit_code=71, tree_reaped=True,
                                  stdout=b'private-output', stderr=b'private-traceback')
                    output = io.StringIO()
                    with patch.object(tempfile, 'TemporaryDirectory', temporary), \
                         patch('mission_process.supervise', return_value=result,
                               side_effect=error if stage == 'fixture_supervise' else None), \
                         patch.dict(os.environ, GITHUB_ACTIONS=actions), contextlib.redirect_stdout(output):
                        with self.assertRaises(error_type) as raised:
                            self.inherited('kill_before_config', exit_code=71)
                    self.assertIs(raised.exception, error)
                    if actions == 'false':
                        self.assertEqual(output.getvalue(), '')
                        continue
                    lines = output.getvalue().splitlines()
                    self.assertEqual(len(lines), 1, output.getvalue())
                    diagnostics = json.loads(lines[0].split(' ', 1)[1])
                    self.assertEqual(diagnostics['fixture'], dict(reason=stage,
                        failure='other' if error_type is private_error else error_type.__name__))
                    self.assertEqual('supervisor' in diagnostics, stage == 'fixture_cleanup')
                    self.assertNotIn('private', output.getvalue())
                    self.assertNotIn('::error::', output.getvalue())

    def test_fixture_exception_survives_annotation_output_failure(self):
        class ClosedOutput(io.StringIO):
            def write(self, value):
                raise BrokenPipeError('private-output-failure')
        error = ValueError('private-original-failure')
        with patch('mission_process.supervise', side_effect=error), \
             patch.dict(os.environ, GITHUB_ACTIONS='true'), contextlib.redirect_stdout(ClosedOutput()):
            with self.assertRaises(Exception) as raised:
                self.inherited('kill_before_config', exit_code=71)
        self.assertIs(raised.exception, error)

    def test_dns_inherits_existing_containment_without_starting_nested_supervisor(self):
        result = self.inherited('dns_success')
        self.assertEqual(result.get('addresses'), ['8.8.8.8'],result)
        self.assertEqual(result['children'],1)
        self.assertTrue(result['collected'])

    def test_inherited_dns_timeout_and_oversized_reply_reap_child(self):
        for mode in ('dns_hang','dns_oversized'):
            with self.subTest(mode=mode):
                result = self.inherited(mode)
                self.assertIn('error',result)
                self.assertEqual(result['children'],1)
                self.assertTrue(result['collected'])

    def test_guard_records_identity_before_ready_and_observes_process_exit(self):
        self.assertTrue(callable(getattr(self.m,'Guard',None)), 'owned guard missing')
        result = self.inherited('guard')
        self.assertEqual(result['exit_code'],125)
        self.assertTrue(result['port_free'])
        kinds = [row['kind'] for row in result['events']]
        self.assertEqual(kinds[:3], ['guard_intent','guard_started','guard_ready'])
        self.assertEqual(kinds[-1], 'guard_reaped')
        self.assertTrue(any(row['payload'].get('reason')=='socks_request' for row in result['events']))

    def test_failed_guard_identity_persistence_never_releases_config(self):
        self.assertTrue(callable(getattr(self.m,'Guard',None)), 'owned guard missing')
        result = self.inherited('persist_failure')
        self.assertEqual([row['kind'] for row in result['events']],['guard_intent','guard_started'])
        self.assertIn('error',result)

    def test_guard_persists_destination_while_controller_waits_for_client(self):
        result = self.inherited('guard_domain')
        self.assertEqual(result.get('exit_code'),0,result)
        self.assertTrue(result['port_free'])
        self.assertEqual(result['upstream_bytes'],len(b'local-request'),result)
        self.assertTrue(result['upstream_observed_after_close'],result)
        self.assertEqual([row['kind'] for row in result['events']],
            ['guard_intent','guard_started','guard_ready','guard_request','guard_destination',
             'guard_finished','guard_closed','guard_reaped'])

    def test_upstream_closes_first_without_blocking_port_reuse(self):
        result = self.inherited('guard_domain_upstream_first')
        self.assertEqual(result.get('exit_code'),0,result)
        self.assertTrue(result['port_free'])

    def test_failed_destination_receipt_forwards_zero_upstream_bytes(self):
        # Exercise scheduling around forced helper shutdown on every platform.
        for attempt in range(8):
            with self.subTest(attempt=attempt):
                result = self.inherited('guard_domain_persistfail')
                self.assertTrue(result['upstream_observed_after_close'],result)
                self.assertEqual(result['offered_bytes'],len(b'local-request'),result)
                self.assertEqual(result['upstream_bytes'],0,result)
                self.assertNotIn('guard_finished',[r['kind'] for r in result['events']])

    def test_abrupt_controller_exit_before_config_reaps_the_waiting_guard(self):
        self.inherited('kill_before_config',exit_code=71)

    def test_port_probe_refuses_an_existing_listener_even_with_reuseaddr(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(('127.0.0.1',0));listener.listen(1)
            self.assertFalse(self.m.port_available(listener.getsockname()[1]))

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
