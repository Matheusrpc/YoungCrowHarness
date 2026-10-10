"""At-most-once protocol. Windows exercises logic, not Linux durability/permissions."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime/sbx'))


class GuardianProtocolTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('guardian'), 'guardian not implemented')
        import guardian
        self.g = guardian
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.control = Path(temporary.name)
        self.config = dict(schema_version=1, operation_id=str(uuid.uuid4()), nonce=uuid.uuid4().hex,
                           deadline_ms=int(time.time() * 1000) + 5000,
                           init_argv=['/client', '--version'], dispatch_prefix=['/client', 'check'])
        if os.name == 'nt':
            # Windows cannot fsync a directory with os.open; real proof runs in Linux.
            patched = patch.object(self.g, 'sync_directory')
            patched.start()
            self.addCleanup(patched.stop)

    def message(self, action, **changes):
        value = dict(schema_version=1, operation_id=self.config['operation_id'],
                     nonce=self.config['nonce'], action=action)
        if action == 'dispatch':
            value['argv'] = ['/client', 'check', '--model', 'synthetic']
        value.update(changes)
        return json.dumps(value).encode() + b'\n'

    def injection_manifest(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import mission_controller
        return mission_controller.phase_manifest(operation_id=self.config['operation_id'],nonce=self.config['nonce'],
            deadline_ms=self.config['deadline_ms'],phase='A',proxy_ipv4='172.17.0.1',ca_sha256='b'*64,
            placeholder='youngcrow-probe-'+'c'*32,injection_sha256=hashlib.sha256(b'fake-value').hexdigest())

    def test_v4_checks_complete_fixture_commands_and_refuses_dispatch_suffix(self):
        self.config=self.injection_manifest()
        self.assertTrue(self.g.valid_relay(self.config))
        protocol=self.g.Protocol(self.control,self.config)
        with patch.object(protocol,'require_network'):
            protocol.accept(self.message('initialize'));protocol.finished(0)
            with self.assertRaisesRegex(self.g.Refused,'invalid_command'):
                protocol.accept(self.message('dispatch',argv=self.config['dispatch_prefix']+['extra']))
        self.assertFalse((self.control/'dispatch.json').exists())
        for key in ('init_argv','dispatch_prefix'):
            changed=dict(self.config,**{key:self.config[key]+['extra']})
            self.assertFalse(self.g.valid_relay(changed))

    def ready(self):
        protocol = self.g.Protocol(self.control, self.config)
        self.assertEqual(protocol.accept(self.message('initialize')), ['/client', '--version'])
        protocol.finished(0)
        return protocol

    def test_ordered_phases_are_consumed_before_returning_commands(self):
        protocol = self.ready()
        self.assertTrue((self.control / 'consumed.json').exists())
        self.assertTrue((self.control / 'initialize.json').exists())
        command = protocol.accept(self.message('dispatch'))
        self.assertEqual(command, ['/client', 'check', '--model', 'synthetic'])
        self.assertTrue((self.control / 'dispatch.json').exists())
        protocol.finished(0)
        self.assertEqual(protocol.state, 'terminal')
        with self.assertRaises(self.g.Refused):
            protocol.accept(self.message('dispatch'))

    def test_restart_and_concurrent_claim_never_get_second_lease(self):
        def claim(_):
            try:
                self.g.Protocol(self.control, self.config)
                return True
            except self.g.Refused:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(claim, range(8))), 1)
        with self.assertRaises(self.g.Refused):
            self.g.Protocol(self.control, self.config)

    def test_partial_marker_is_also_consumed(self):
        (self.control / 'consumed.json').write_bytes(b'{')
        with self.assertRaises(self.g.Refused):
            self.g.Protocol(self.control, self.config)

    def test_failed_persistence_blocks_phase_and_future_restart(self):
        protocol = self.ready()
        with patch.object(self.g.os, 'fsync', side_effect=OSError('disk error')):
            with self.assertRaises(self.g.Refused):
                protocol.accept(self.message('dispatch'))
        self.assertEqual(protocol.state, 'terminal')
        with self.assertRaises(self.g.Refused):
            self.g.Protocol(self.control, self.config)

    def test_failed_claim_never_starts_an_operation(self):
        with patch.object(self.g.os, 'fsync', side_effect=OSError('disk error')):
            with self.assertRaises(self.g.Refused):
                self.g.Protocol(self.control, self.config)
        self.assertTrue((self.control / 'consumed.json').exists())

    def test_replay_wrong_order_or_failed_discovery_stops(self):
        for mode in ('before_initialize', 'during_initialize', 'repeat_initialize', 'failed_initialize'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                protocol = self.g.Protocol(Path(directory), self.config)
                if mode != 'before_initialize':
                    protocol.accept(self.message('initialize'))
                if mode == 'repeat_initialize':
                    protocol.finished(0)
                if mode == 'failed_initialize':
                    protocol.finished(1)
                action = 'initialize' if mode == 'repeat_initialize' else 'dispatch'
                with self.assertRaises(self.g.Refused):
                    protocol.accept(self.message(action))
                self.assertEqual(protocol.state, 'terminal')
                self.assertFalse((Path(directory) / 'dispatch.json').exists())

    def test_bad_messages_fail_closed_without_dispatch(self):
        valid = self.message('dispatch')
        wall, monotonic = time.time(), time.monotonic()
        for message in (b'[]\n', b'{', valid[:-1], valid + valid,
                        b'x' * 16385, b'{"a":1,"a":2}\n', b'{"a":NaN}\n',
                        self.message('dispatch', schema_version=True),
                        self.message('dispatch', nonce='0' * 32),
                        self.message('dispatch', operation_id=str(uuid.uuid4())),
                        self.message('dispatch', extra=True), self.message('other'),
                        self.message('dispatch', argv=['/other']),
                        self.message('dispatch', argv=['/client', 'check', '\x00']),
                        self.message('dispatch', argv='/client check')):
            # Parsing cases share a fixed clock; deadline behavior has separate tests below.
            with self.subTest(message=message[:70]), tempfile.TemporaryDirectory() as directory, \
                 patch.object(self.g.time, 'time', return_value=wall), \
                 patch.object(self.g.time, 'monotonic', return_value=monotonic):
                protocol = self.g.Protocol(Path(directory), self.config)
                protocol.accept(self.message('initialize'))
                protocol.finished(0)
                with self.assertRaises(self.g.Refused):
                    protocol.accept(message)
                self.assertEqual(protocol.state, 'terminal')
                self.assertFalse((Path(directory) / 'dispatch.json').exists())

    def test_deadline_never_resets_and_backward_wall_clock_cannot_extend_it(self):
        wall, monotonic = time.time(), time.monotonic()
        with patch.object(self.g.time, 'time', return_value=wall), \
             patch.object(self.g.time, 'monotonic', return_value=monotonic):
            protocol = self.ready()
        with patch.object(self.g.time, 'time', return_value=wall - 3600), \
             patch.object(self.g.time, 'monotonic', return_value=monotonic + 6):
            with self.assertRaises(self.g.Refused):
                protocol.accept(self.message('dispatch'))
        self.assertFalse((self.control / 'dispatch.json').exists())

    def test_invalid_or_expired_manifest_never_claims(self):
        for change in ({'deadline_ms': 0}, {'deadline_ms': True},
                       {'deadline_ms': int(time.time() * 1000) + 121000},
                       {'schema_version': True}, {'nonce': '../control'},
                       {'operation_id': 'not-a-uuid'}, {'unknown': 1},
                       {'init_argv': ['relative']}, {'dispatch_prefix': []}):
            with self.subTest(change=change):
                with self.assertRaises(self.g.Refused):
                    self.g.Protocol(self.control, dict(self.config, **change))
                self.assertFalse((self.control / 'consumed.json').exists())

    def test_shutdown_window_cannot_launch_or_extend_the_original_deadline(self):
        self.config['deadline_ms'] = 105000
        for wall in (104, 100):  # A backwards wall clock cannot recover the reserve.
            with self.subTest(wall=wall), tempfile.TemporaryDirectory() as directory:
                with patch.object(self.g.time, 'time', return_value=100), \
                     patch.object(self.g.time, 'monotonic', return_value=200):
                    protocol = self.g.Protocol(Path(directory), self.config)
                    protocol.accept(self.message('initialize'))
                    protocol.finished(0)
                self.assertEqual(protocol.config['deadline_ms'], 105000)
                with patch.object(self.g.time, 'time', return_value=wall), \
                     patch.object(self.g.time, 'monotonic', return_value=204):
                    with self.assertRaises(self.g.Refused):
                        protocol.accept(self.message('dispatch'))
                self.assertFalse((Path(directory) / 'dispatch.json').exists())

    def test_shutdown_only_budget_never_claims(self):
        with patch.object(self.g.time, 'time', return_value=100):
            for deadline in (100500, 101000, 220001):
                with self.subTest(deadline=deadline), tempfile.TemporaryDirectory() as directory:
                    with self.assertRaises(self.g.Refused):
                        self.g.Protocol(Path(directory), dict(self.config, deadline_ms=deadline))
                    self.assertFalse((Path(directory) / 'consumed.json').exists())

    def test_network_manifest_needs_a_separate_protected_gate_for_each_phase(self):
        self.config.update(schema_version=2, network={'host':'api.openai.com','ipv4':'1.1.1.1'})
        try:
            protocol = self.g.Protocol(self.control, self.config)
        except self.g.Refused as error:
            self.fail('Network manifest not supported: '+str(error))
        with self.assertRaisesRegex(self.g.Refused, 'network_unverified'):
            protocol.accept(self.message('initialize'))
        self.assertFalse((self.control/'initialize.json').exists())

    def test_network_receipt_cannot_authorize_another_phase_or_namespace(self):
        self.assertTrue(hasattr(self.g, 'network_namespace'), 'network gate not implemented')
        self.config.update(schema_version=2, network={'host':'api.openai.com','ipv4':'1.1.1.1'})
        protocol = self.g.Protocol(self.control, self.config)
        gate=dict(protocol.identity,nonce=self.config['nonce'],phase='initialize',network_namespace='net:[123]')
        path=self.control/'network-initialize.json'
        path.write_text(json.dumps(gate));path.chmod(0o600)
        # OS identity is exercised in the Linux smoke; no Linux root on Windows CI.
        with patch.object(self.g,'network_namespace',return_value='net:[123]'), \
             patch.object(self.g,'protected_network_gate'):
            self.assertEqual(protocol.accept(self.message('initialize')),['/client','--version'])
            protocol.finished(0)
            with self.assertRaisesRegex(self.g.Refused,'network_unverified'):
                protocol.accept(self.message('dispatch'))
        self.assertFalse((self.control/'dispatch.json').exists())

    def test_network_address_must_be_a_single_canonical_public_ipv4(self):
        for address in ('127.0.0.1','172.17.0.2','169.254.169.254','10.0.0.1',
                        '100.64.0.1','224.0.0.1','192.0.2.1','::1','1.1.1.1/32','1.1.1.1 --help'):
            with self.subTest(address=address):
                config=dict(self.config,schema_version=2,network={'host':'api.openai.com','ipv4':address})
                with self.assertRaises(self.g.Refused):self.g.Protocol(self.control,config)
                self.assertFalse((self.control/'consumed.json').exists())

    def test_relay_manifest_is_echo_only_and_requires_phase_gate(self):
        self.config.update(schema_version=3, network={'proxy_ipv4':'192.168.65.1'},
                           relay=dict(kind='echo', phase='A', placeholder='youngcrow-probe-'+'a'*32,
                                      ca_sha256='b'*64))
        protocol = self.g.Protocol(self.control, self.config)
        with self.assertRaisesRegex(self.g.Refused, 'network_unverified'):
            protocol.accept(self.message('initialize'))
        for update in ({'kind':'provider'}, {'phase':'C'}, {'host':'api.openai.com'},
                       {'ca_sha256':'bad'}, {'placeholder':'real-secret'}):
            with self.subTest(update=update), tempfile.TemporaryDirectory() as directory:
                config = dict(self.config, relay=dict(self.config['relay'], **update))
                with self.assertRaisesRegex(self.g.Refused, 'invalid_manifest'):
                    self.g.Protocol(Path(directory), config)
        for address in ('127.0.0.1','169.254.169.254','1.1.1.1','::1','192.168.65.1/32'):
            with self.subTest(address=address), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(self.g.Refused, 'invalid_manifest'):
                    self.g.Protocol(Path(directory), dict(self.config, network={'proxy_ipv4':address}))

    def test_relay_fork_order_and_failure_cleanup(self):
        self.assertTrue(hasattr(self.g, 'spawn_child'))
        events = []
        from unittest.mock import Mock
        bridge = Mock()
        bridge.start.side_effect = lambda: events.append('threads')
        bridge.stop.return_value = True
        def spawn(*args, **kwargs):
            events.append('fork')
            self.assertTrue(kwargs['close_fds'])
            return Mock()
        with patch.object(self.g.threading, 'active_count', return_value=1), \
             patch.object(self.g.subprocess, 'Popen', side_effect=spawn):
            self.g.spawn_child(['/client'], bridge)
        self.assertEqual(events, ['fork','threads'])
        with patch.object(self.g.threading, 'active_count', return_value=2), \
             patch.object(self.g.subprocess, 'Popen') as process:
            with self.assertRaisesRegex(self.g.Refused, 'threaded_fork'):
                self.g.spawn_child(['/client'], bridge)
            process.assert_not_called()
        with patch.object(self.g.threading, 'active_count', return_value=1), \
             patch.object(self.g.subprocess, 'Popen', side_effect=OSError('failed')):
            with self.assertRaises(OSError): self.g.spawn_child(['/client'], bridge)
        bridge.stop.assert_called()

    def test_relay_failure_overrides_zero_child_exit_and_always_stops(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        for state in ('succeeded','refused','cancelled'):
            with self.subTest(state=state):
                protocol, bridge, child, selector = Mock(), Mock(), Mock(), Mock()
                protocol.config = {'schema_version':3}
                protocol.remaining.return_value = 2
                protocol.state = 'dispatch'
                protocol.accept.return_value = ['/client']
                protocol.finished.side_effect = lambda _: setattr(protocol,'state','terminal')
                bridge.stop.return_value = True
                bridge.result.return_value = dict(state=state,reason=None,requests=1,bytes_forwarded=2)
                child.poll.return_value = child.returncode = 0
                selector.select.side_effect = [
                    [(SimpleNamespace(fd=0,data='control'),None)],
                    [(SimpleNamespace(fd=1,data='stdout',fileobj=Mock()),None),
                     (SimpleNamespace(fd=2,data='stderr',fileobj=Mock()),None)]]
                with patch.object(self.g.selectors,'DefaultSelector',return_value=selector), \
                     patch.object(self.g.os,'read',side_effect=[b'{}\n',b'',b'']), \
                     patch.object(self.g,'prepare_relay',return_value=bridge), \
                     patch.object(self.g,'spawn_child',return_value=child), \
                     patch.object(self.g,'emit'):
                    result = self.g.supervise(protocol)
                self.assertEqual(result,0 if state=='succeeded' else 126)
                self.assertGreaterEqual(bridge.stop.call_count,2)
        bridge.reset_mock()
        with patch.object(self.g,'supervise_loop',side_effect=lambda p,b: (b.append(bridge),
                          (_ for _ in ()).throw(self.g.Refused('control_closed')))[1]):
            with self.assertRaisesRegex(self.g.Refused,'control_closed'):
                self.g.supervise(protocol)
        bridge.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
