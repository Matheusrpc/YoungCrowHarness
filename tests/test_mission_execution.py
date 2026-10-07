"""Durable installation reservation. Fixtures never mutate Docker or real user state."""
import importlib.util
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_execution'), 'shared reservation missing')
        import mission_execution as execution
        self.m = execution
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)/'shared'
        # Storage/ACL contracts are separately native-tested through adoption_fs.
        # These fixtures exercise journal and OS locks without changing account storage.
        import adoption_fs as fs
        self.addCleanup(patch.stopall)
        patch.object(execution,'check_private',side_effect=lambda p: fs.checked_path(p)).start()
        patch.object(fs,'private_dir',side_effect=lambda p:p.mkdir(mode=0o700)).start()
        patch.object(fs,'protect_for_storage').start()
        patch.object(fs,'outside_git').start()
        self.registry = execution.Registry(self.base)
        self.request = dict(schema_version=1,operation_id=str(uuid.uuid4()),mission_id=str(uuid.uuid4()),
                            project_id=str(uuid.uuid4()),project_sha256='a'*64,manifest_sha256='b'*64,
                            baseline_sha256='c'*64,executable_sha256='d'*64,
                            candidate_digest='sha256:'+'e'*64,authorization_sha256='f'*64,
                            deadline_ms=int(time.time()*1000)+120000)

    def test_read_only_status_never_creates_storage(self):
        self.assertEqual(self.registry.status()['state'],'available')
        self.assertFalse(self.base.exists())

    def test_other_project_and_expiry_never_release_reservation(self):
        first = self.registry.reserve(self.request)
        self.assertTrue(first['new'])
        other = dict(self.request,project_id=str(uuid.uuid4()),operation_id=str(uuid.uuid4()))
        with self.assertRaisesRegex(ValueError,'execution_reserved'):
            self.m.Registry(self.base).reserve(other)
        with patch.object(self.m.time,'time',return_value=time.time()+1000):
            self.assertEqual(self.registry.status()['state'],'reserved')
        self.assertFalse(self.registry.reserve(self.request)['new'])
        with self.assertRaisesRegex(ValueError,'operation_conflict'):
            self.registry.reserve(dict(self.request,manifest_sha256='0'*64))

    def test_intent_is_durable_and_never_replayed(self):
        self.registry.reserve(self.request)
        args=(self.request['operation_id'],'configure_proxy',dict(before_sha256='a'*64,after_sha256='b'*64))
        record=self.registry.intent(*args)
        self.assertEqual(record['state'],'consumed')
        self.assertEqual(self.m.Registry(self.base).status()['state'],'consumed')
        with self.assertRaisesRegex(ValueError,'effect_consumed'): self.registry.intent(*args)
        with self.assertRaisesRegex(ValueError,'execution_reconciliation_required'):
            self.registry.abandon_unused(self.request['operation_id'],lambda:'c'*64)

    def test_unchanged_unused_reservation_can_close_but_id_stays_consumed(self):
        self.registry.reserve(self.request)
        with self.assertRaisesRegex(ValueError,'configuration_changed'):
            self.registry.abandon_unused(self.request['operation_id'],lambda:'0'*64)
        self.assertEqual(self.registry.status()['state'],'reserved')
        result=self.registry.abandon_unused(self.request['operation_id'],lambda:'c'*64)
        self.assertEqual(result['state'],'abandoned')
        self.assertEqual(self.registry.status()['state'],'available')
        self.assertFalse(self.registry.reserve(self.request)['new'])
        self.assertTrue(self.registry.reserve(dict(self.request,operation_id=str(uuid.uuid4())))['new'])

    def test_corrupt_record_and_missing_effect_receipt_fail_closed(self):
        self.registry.reserve(self.request)
        file=self.base/'registry.json'
        file.write_bytes(b'{')
        with self.assertRaises(ValueError): self.registry.status()
        with self.assertRaises(ValueError):
            self.registry.reserve(dict(self.request,operation_id=str(uuid.uuid4())))

    def test_missing_ledger_after_intent_never_becomes_an_empty_installation(self):
        self.registry.reserve(self.request)
        self.registry.intent(self.request['operation_id'],'configure_proxy',dict(before_sha256='a'*64,after_sha256='b'*64))
        (self.base/'registry.json').unlink()
        with self.assertRaisesRegex(ValueError,'execution_reservation_invalid'): self.registry.status()
        with self.assertRaisesRegex(ValueError,'execution_reservation_invalid'):
            self.registry.reserve(dict(self.request,operation_id=str(uuid.uuid4())))

    def test_live_guard_blocks_second_coordinator(self):
        from adoption import lock_guard
        self.registry.reserve(self.request)
        with lock_guard(self.base):
            with self.assertRaisesRegex(ValueError,'locked'):
                self.registry.reserve(dict(self.request,operation_id=str(uuid.uuid4())))

    def test_concurrent_initialization_cannot_reset_existing_ledger(self):
        import adoption_fs as fs
        def created_by_other_process(path):
            path.mkdir(mode=0o700)
            self.registry.create_empty('reclaim.lock')
            self.registry.persist([])
            self.registry.reserve(self.request)
        with patch.object(fs,'private_dir',side_effect=created_by_other_process):
            with self.assertRaisesRegex(ValueError,'execution_reserved'):
                self.registry.reserve(dict(self.request,operation_id=str(uuid.uuid4())))
        self.assertEqual(self.registry.status()['operation_id'],self.request['operation_id'])

    def test_failed_persistence_cannot_grant_effect(self):
        self.registry.reserve(self.request)
        with patch('document_store.atomic_write',side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.registry.intent(self.request['operation_id'],'configure_proxy',dict(before_sha256='a'*64,after_sha256='b'*64))
        self.assertEqual(self.registry.status()['state'],'reserved')

    def test_environment_shows_reservation_without_creating_or_dispatching(self):
        import mission_sandbox as sandbox
        executable = Path(self.temp.name)/'sbx.exe'
        executable.write_bytes(b'fixture')
        facts = dict(system='Windows',machine='AMD64',build='26200',whp_state=1,
                     distribution=None,kvm_access=None)
        with patch.object(self.m,'user_storage',return_value=self.base), \
             patch.object(sandbox,'_host_facts',return_value=facts), \
             patch.object(sandbox,'_exchange',return_value='sbx version: v0.46.0 abc123'):
            first=sandbox.inspect_environment(Path(self.temp.name),executable)
            self.assertEqual(first['execution_reservation']['state'],'available')
            self.assertFalse(self.base.exists())
            self.registry.reserve(self.request)
            second=sandbox.inspect_environment(Path(self.temp.name),executable)
        self.assertEqual(second['execution_reservation']['operation_id'],self.request['operation_id'])
        self.assertFalse(second['execution_reservation']['effects_allowed'])
        self.assertIn('execution_reserved',second['gaps'])

    def test_unexpected_storage_entry_blocks_mutations(self):
        self.registry.reserve(self.request)
        (self.base/'unexpected.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'execution_reservation_invalid'):
            self.registry.abandon_unused(self.request['operation_id'],lambda:'c'*64)

    def test_storage_timeout_is_publicly_classified_without_raw_command(self):
        with patch.object(self.m,'user_storage',return_value=self.base), \
             patch.object(self.m.Registry,'check',side_effect=subprocess.TimeoutExpired(['private-canary'],15)):
            result=self.m.status()
        self.assertEqual(result['state'],'unknown')
        self.assertEqual(result['reason'],'permission_query_timeout')
        self.assertFalse(result['effects_allowed'])
        self.assertNotIn('private-canary',str(result))


@unittest.skipUnless(os.name == 'nt' and os.environ.get('YC_NATIVE_RESERVATION') == '1',
                     'native ACL fixture is explicitly selected through windows_fixture_runner')
class NativeReservationTests(unittest.TestCase):
    def test_private_reservation_survives_reopen_with_native_permissions(self):
        import mission_execution as execution
        import adoption_fs as fs
        with tempfile.TemporaryDirectory() as temporary:
            # Parent is the private fixture created by windows_fixture_runner.
            fs.protect_for_storage(Path(temporary))
            base=Path(temporary)/'shared'
            registry=execution.Registry(base)
            self.assertFalse(base.exists())
            self.assertEqual(registry.status()['state'],'available')
            request=dict(schema_version=1,operation_id=str(uuid.uuid4()),mission_id=str(uuid.uuid4()),
                         project_id=str(uuid.uuid4()),project_sha256='a'*64,manifest_sha256='b'*64,
                         baseline_sha256='c'*64,executable_sha256='d'*64,candidate_digest='sha256:'+'e'*64,
                         authorization_sha256='f'*64,deadline_ms=int(time.time()*1000)+600000)
            self.assertTrue(registry.reserve(request)['new'])
            reopened=execution.Registry(base)
            self.assertEqual(reopened.status()['operation_id'],request['operation_id'])
            self.assertFalse(reopened.reserve(request)['new'])
            fs.inspect_permissions(base,role='snapshot')
            actual=execution.user_storage()
            with patch.dict(os.environ,{'LOCALAPPDATA':'Z:/invalid-fixture','USERPROFILE':'Z:/invalid-fixture'}):
                self.assertEqual(execution.user_storage(),actual)


if __name__ == '__main__': unittest.main()
