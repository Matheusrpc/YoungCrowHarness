"""Durable OCI receipts; external effects are deterministic fixtures here."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import uuid
import sys
import unittest
from unittest.mock import patch

from runtime_fixtures import RuntimeCase
import mission_execution as execution
import mission_worker as worker


@unittest.skipUnless(sys.platform == 'linux', 'OCI tools require Linux')
class WorkerRunTests(RuntimeCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('mission_worker_runs'),'worker coordinator missing')
        import mission_worker_runs as coordinator
        self.c=coordinator
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.private=Path(self.temp.name)
        self.registry=execution.Registry(self.private/'registry')
        self.manifest=self.make_manifest()
        self.manifest.update(contract='isolated-tools',fixture_id='clamp-v1',client='codex',
                             image_digest='sha256:'+'a'*64,source='fixture',paths=['clamp.py'],
                             package_sha256=worker.sha(worker.archive_bytes({'clamp.py':self.c.ORIGINAL})),
                             model='fixture-model',effort='low')
        (self.root/'fixture').mkdir();(self.root/'fixture/clamp.py').write_bytes(self.c.ORIGINAL)
        self.effects=[]
        agent,config=self.c.runs.mission_agent(self.root,self.manifest)
        self.prepared=dict(agent=agent,config=config,engine=dict(id='fixture',version='28.4.0',boot_id=str(uuid.uuid4())),
                           version='0.159.2',executable_sha256='b'*64)
        # The pinned native protocols lack effort; simulate a qualified observation
        # only for ledger tests. Native parsing is exercised separately below.
        self.native_observe=self.c.clients.observe_result
        self.observation=dict(observed_model='fixture-model',observed_effort='low',tools_observed=['command_execution'])
        for target,field,replacement in ((self.c,'preflight',lambda *a,**k:self.prepared),
            (self.c.clients,'build_profile',lambda *a,**k:dict(argv=['/fixture/client'],cwd=str(self.private),environment_overrides={},profile_sha256='c'*64,client='codex')),
            (self.c.clients,'validate_qualification',lambda *a,**k:None),
            (self.c.clients,'observe_result',lambda *a,**k:self.observation.copy()),
            (self.c,'check_auth',lambda *a,**k:None),
            (worker,'start',self.start_worker),(worker,'stop',self.stop_worker),
            (worker,'observe',lambda h:dict(running=False,pid=0,finished_ms=h['deadline_ms']-1000)),
            (worker,'collect',self.collect),(self.c.processes,'supervise',self.client)):
            p=patch.object(target,field,side_effect=replacement);p.start();self.addCleanup(p.stop)

    def start_worker(self,plan,package,docker,persist):
        persist('create_intent',dict(plan_sha256=worker.sha(self.c.fs.canonical(plan))))
        self.effects.append('create')
        handle=dict(container_id='d'*64,docker=str(docker),engine=plan['engine'],image_digest=plan['image_digest'],
                    operation_id=plan['operation_id'],deadline_ms=plan['deadline_ms'],
                    plan_sha256=worker.sha(self.c.fs.canonical(plan)),config_sha256='e'*64)
        persist('created',handle);persist('start_intent',handle);persist('ready',handle)
        return handle

    def stop_worker(self,handle,persist):
        self.effects.append('stop')
        stopped=dict(running=False,pid=0,finished_ms=handle['deadline_ms']-1000)
        persist('stopped',stopped);return stopped

    def collect(self,handle,destination,persist):
        self.stop_worker(handle,persist)
        destination.mkdir(mode=0o700)
        (destination/'clamp.py').write_bytes(self.c.FIXED)
        result=dict(files={'clamp.py':worker.sha(self.c.FIXED)},snapshot_sha256='f'*64,test={'cases':3,'exit_code':0},
                    worker_stopped_before_publish=True,finished_ms=handle['deadline_ms']-1000)
        persist('collected',result);return result

    def client(self,plan,*,on_started,stop_requested):
        on_started(dict(kind='linux-pidns-group',name=str(uuid.uuid4()),pid=987654321))
        self.effects.append('client')
        data=b'{"type":"thread.started","thread_id":"fixture"}\n{"type":"turn.started"}\n{"type":"turn.completed","usage":{}}\n'
        return dict(tree_reaped=True,reason='completed',exit_code=0,stdout=data,stderr=b'',elapsed_seconds=.1)

    def check(self):
        return self.c.check_worker(self.root,self.manifest,Path('/fixture/client'),Path('/fixture/docker'),
                                   _registry=self.registry,_storage=self.private/'artifacts')

    def test_repeated_operation_returns_same_receipt_without_dispatch(self):
        first=self.check();repeated=self.check()
        self.assertEqual(repeated['id'],first['id'])
        self.assertEqual(self.effects.count('client'),1)
        self.assertEqual(first['state'],'succeeded')
        self.assertFalse(first['runtime_available'])
        self.assertEqual(first['observed_model'],'fixture-model')
        self.assertEqual(first['observed_effort'],'low')
        self.assertEqual(self.registry.status()['state'],'available')

    def assert_crash_cut(self,cut):
        real=self.c.save_observation
        def crashing(reg,record,kind,payload):
            result=real(reg,record,kind,payload)
            if kind==cut:raise KeyboardInterrupt('simulated controller loss')
            return result
        with patch.object(self.c,'save_observation',side_effect=crashing):
            with self.assertRaises(KeyboardInterrupt):self.check()
        count=self.effects.count('client')
        repeated=self.check()
        self.assertEqual(self.effects.count('client'),count)
        self.assertEqual(repeated['operation_id'],self.manifest['operation_id'])
        with patch.object(self.c.processes,'process_missing',return_value=True),patch.object(self.c.processes,'owner_gone',return_value=True):
            if cut=='create_intent':
                with self.assertRaisesRegex(ValueError,'worker_identity_unknown'):
                    self.c.reconcile_worker(self.root,repeated['id'],repeated['revision'],str(uuid.uuid4()),Path('/fixture/docker'),_registry=self.registry)
                self.assertNotEqual(self.registry.status()['state'],'available')
            else:
                self.c.reconcile_worker(self.root,repeated['id'],repeated['revision'],str(uuid.uuid4()),Path('/fixture/docker'),_registry=self.registry)
                self.assertEqual(self.registry.status()['state'],'available')
        self.assertEqual(self.effects.count('client'),count)

    def test_dead_client_with_live_worker_keeps_reservation(self):
        with patch.object(worker,'collect',side_effect=ValueError('unavailable')),patch.object(worker,'stop',side_effect=ValueError('transport_lost')):
            run=self.check()
        self.assertEqual(run['state'],'uncertain')
        self.assertNotEqual(self.registry.status()['state'],'available')

    def test_namespace_owner_and_legacy_owner_receipts_remain_readable(self):
        self.check()
        record = self.c._find(self.registry, self.manifest['operation_id'])
        for kind in ('linux-pidns-group', 'linux-group'):
            record['client_owner']['kind'] = kind
            self.c.validate_record(record)
        record['client_owner']['kind'] = 'unconfined'
        with self.assertRaises(ValueError):
            self.c.validate_record(record)

    def test_global_reservation_cut_can_be_linked_without_dispatch(self):
        with patch.object(self.c.runs,'_record_check',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.check()
        self.assertEqual(self.effects,[])
        repeated=self.check()
        self.assertEqual(repeated['operation_id'],self.manifest['operation_id'])
        self.assertEqual(self.effects,[])

    def test_admission_rejection_releases_unused_global_reservation(self):
        self.prepared['config']['limits']['max_agent_runs']=1
        self.check()
        self.manifest['operation_id']=str(uuid.uuid4())
        effects=self.effects.copy()
        for _ in range(2):
            with self.assertRaisesRegex(ValueError,'limit_exceeded'):self.check()
            self.assertEqual(self.registry.status()['state'],'available')
            self.assertEqual(self.effects,effects)

    def test_missing_native_selection_cannot_publish_success(self):
        with patch.object(self.c.clients,'observe_result',side_effect=self.native_observe):run=self.check()
        self.assertEqual(run['state'],'failed')
        self.assertEqual(run['reason'],'worker_selection_unobservable')
        self.assertNotIn('artifact',run)

    def test_divergent_observed_selection_cannot_publish_success(self):
        self.observation['observed_effort']='high'
        run=self.check()
        self.assertEqual(run['state'],'failed')
        self.assertEqual(run['reason'],'worker_selection_mismatch')
        self.assertNotIn('artifact',run)

    def test_failed_global_closure_cannot_publish_success_in_sqlite(self):
        real=self.c.save_observation
        def reject_closure(reg,record,kind,payload):
            if kind=='closed':raise OSError('lost global storage')
            return real(reg,record,kind,payload)
        with patch.object(self.c,'save_observation',side_effect=reject_closure):run=self.check()
        self.assertEqual(run['state'],'uncertain')
        self.assertNotIn('artifact',run)

    def test_recovery_without_checkout_never_starts_worker(self):
        with patch.object(worker,'collect',side_effect=ValueError('unavailable')),patch.object(worker,'stop',side_effect=ValueError('transport_lost')):
            run=self.check()
        count=self.effects.count('create')
        with patch.object(self.c.processes,'process_missing',return_value=True),patch.object(self.c.processes,'owner_gone',return_value=True):
            self.c.recover_record(self.registry,run['operation_id'],Path('/fixture/docker'))
        self.assertEqual(self.effects.count('create'),count)
        self.assertEqual(self.registry.status()['state'],'available')

    def test_stale_ledger_writer_is_refused(self):
        self.check()
        first=self.registry.records()[0];stale=copy.deepcopy(first)
        self.c.save_observation(self.registry,first,'recovered',{})
        with self.assertRaisesRegex(ValueError,'revision_conflict'):
            self.c.save_observation(self.registry,stale,'recovered',{})

    def test_reconciliation_uuid_replays_without_native_effects(self):
        with patch.object(worker,'collect',side_effect=ValueError('unavailable')),patch.object(worker,'stop',side_effect=ValueError('transport_lost')):
            run=self.check()
        operation=str(uuid.uuid4())
        args=(self.root,run['id'],run['revision'],operation,Path('/fixture/docker'))
        with patch.object(self.c.processes,'process_missing',return_value=True),patch.object(self.c.processes,'owner_gone',return_value=True):
            first=self.c.reconcile_worker(*args,_registry=self.registry)
            effects=len(self.effects)
            repeated=self.c.reconcile_worker(*args,_registry=self.registry)
        self.assertEqual(first,repeated)
        self.assertEqual(effects,len(self.effects))

    def test_unknown_contract_never_falls_through_to_sbx(self):
        record={'contract':'unknown','schema_version':1}
        with self.assertRaises(ValueError):self.registry.validate_record(record,None)

    def test_oci_and_sbx_share_exclusion(self):
        with patch.object(worker,'start',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.check()
        row=self.registry.records()[0]
        with self.assertRaisesRegex(ValueError,'execution_reserved'):
            self.registry.reserve(dict(schema_version=1,operation_id=str(uuid.uuid4()),mission_id=str(uuid.uuid4()),project_id=str(uuid.uuid4()),
                project_sha256='a'*64,manifest_sha256='b'*64,baseline_sha256='c'*64,executable_sha256='d'*64,candidate_digest='sha256:'+'e'*64,
                authorization_sha256='f'*64,deadline_ms=int(time.time()*1000)+30000))
        damaged=copy.deepcopy(row);damaged['request']['deadline_ms']=True
        with self.assertRaises(ValueError):self.c.validate_record(damaged)


def crash_case(cut):
    def test(self):self.assert_crash_cut(cut)
    return test

for cut in ('linked','create_intent','created','start_intent','ready','client_intent','client_started','client_finished','stopped','collected','closed'):
    setattr(WorkerRunTests,'test_crash_at_each_store_or_effect_boundary_never_redispatches_'+cut,crash_case(cut))
