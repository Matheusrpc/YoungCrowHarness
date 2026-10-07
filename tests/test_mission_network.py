"""Network coordination uses the real ledger; only sbx effects are simulated."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mission_execution as execution
import mission_transaction as tx
from test_mission_transaction import inputs, RecoveryFixture
from fixtures.transaction_storage import registry_storage
from runtime_fixtures import RuntimeCase


class SettingsFixture(RecoveryFixture):
    def __init__(self, plan, registry):
        super().__init__(plan)
        self.registry = registry
        self.lost = None

    def setting(self, key, target):
        record = self.registry.records()[0]
        self.assert_intent(record, key)
        self.effects.append('setting:'+key)
        self.current['observations']['setting_'+key.replace('.','_')] = copy.deepcopy(target)
        if self.lost == key:
            self.lost = None
            raise OSError('lost reply')

    def assert_intent(self, record, key):
        assert any(e['kind'].endswith('setting_intent') and e['payload']['key']==key
                   for e in record['network_events']), 'effect preceded intent'

    def restart(self):
        assert self.current['observations']['candidate_inspect']['state']=='stopped'
        record = self.registry.records()[0]
        assert record['network_events'][-1]['kind'].endswith('restart_intent')
        self.effects.append('restart')
        self.current['daemon_identity']['pid'] += 1
        self.current['daemon_identity']['created_at'] += '-next'
        if self.lost == 'restart':
            self.lost = None
            raise OSError('lost reply')


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_network'), 'network coordinator missing')
        import mission_network
        self.network = mission_network
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.registry = execution.Registry(Path(temporary.name)/'ledger')
        self.enterContext(registry_storage(self.registry.base))
        self.args = inputs()
        self.plan = tx.build_plan(**self.args, network=dict(resolver='system',forbidden_ips=['172.17.0.1']))
        self.op = self.plan['manifest']['operation_id']

    def ready(self):
        tx.reserve(self.registry,self.plan)
        config = self.network.guard_config(self.plan,'A',0)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        self.port = port
        for kind,payload in [('guard_intent',dict(config=config)),('guard_started',dict(pid=os.getpid())),
            ('guard_ready',dict(operation_id=config['operation_id'],phase='A',nonce=config['nonce'],
                at_ms=int(time.time()*1000),port=port,pid=os.getpid(),deadline_ms=config['deadline_ms']))]:
            self.network.event(self.registry,self.op,'A',kind,payload)
        return SettingsFixture(self.plan,self.registry)

    def test_v3_pins_network_sources_and_does_not_upgrade_legacy_plan(self):
        legacy = tx.build_plan(**self.args)
        self.assertEqual(legacy['schema_version'],2)
        self.assertEqual(self.plan['schema_version'],3)
        self.assertNotIn('network',legacy)
        self.assertIn('mission_egress.py',self.plan['code_sha256'])
        self.assertIn('mission_network.py',self.plan['code_sha256'])
        tx.validate_plan(legacy)
        tx.reserve(self.registry,legacy)
        self.assertEqual(self.registry.records()[0]['schema_version'],2)

    def test_unknown_network_or_inherited_exclusions_fail_before_reservation(self):
        for change in ('resolver','host','exclusion'):
            args = copy.deepcopy(self.args)
            config = dict(resolver='system',forbidden_ips=['172.17.0.1'])
            if change=='resolver':config['resolver']='arbitrary'
            elif change=='host':config['host']='localhost'
            else:args['baseline']['observations']['setting_no_proxy']['value']='*'
            with self.subTest(change=change),self.assertRaises(ValueError):
                tx.build_plan(**args,network=config)
        self.assertFalse(self.registry.base.exists())

    def test_ready_precedes_settings_and_default_does_not_become_override(self):
        backend = self.ready()
        self.network.activate(self.registry,self.op,backend)
        observed = backend.observe()
        self.assertEqual(observed['observations']['setting_proxy_sandbox']['value'],f'socks5h://127.0.0.1:{self.port}')
        self.assertEqual(observed['observations']['setting_no_proxy_sandbox']['source'],'default')
        self.assertEqual(backend.effects,['setting:proxy.sandbox','restart'])
        self.network.verify(self.registry.records()[0],observed)
        with self.assertRaises(ValueError):self.network.activate(self.registry,self.op,backend)
        self.assertEqual(backend.effects,['setting:proxy.sandbox','restart'])

    def test_missing_ready_or_failed_intent_write_prevents_mutation(self):
        tx.reserve(self.registry,self.plan)
        backend = SettingsFixture(self.plan,self.registry)
        with self.assertRaises(ValueError):self.network.activate(self.registry,self.op,backend)
        self.assertEqual(backend.effects,[])

    def test_failed_intent_persistence_prevents_setting(self):
        backend = self.ready()
        with patch.object(self.registry,'save',side_effect=OSError('disk')), self.assertRaises(OSError):
            self.network.activate(self.registry,self.op,backend)
        self.assertEqual(backend.effects,[])

    def expiry_during_save(self, kind, expected):
        backend=self.ready()
        wall=[time.time()]
        save=self.registry.save
        def slow_save(record):
            save(record)
            if record['network_events'][-1]['kind']==kind:
                wall[0]=self.plan['deadline_ms']/1000+1
        with patch.object(time,'time',side_effect=lambda:wall[0]), patch.object(self.registry,'save',side_effect=slow_save):
            with self.assertRaises((ValueError,tx.controller.Refused)):
                self.network.activate(self.registry,self.op,backend)
        self.assertEqual(backend.effects,expected)

    def test_deadline_expired_during_intent_write_prevents_setting(self):
        self.expiry_during_save('setting_intent',[])

    def test_deadline_expired_during_intent_write_prevents_restart(self):
        self.expiry_during_save('restart_intent',['setting:proxy.sandbox'])

    def test_lost_setting_reply_restores_by_observation_without_replaying(self):
        backend = self.ready();backend.lost='proxy.sandbox'
        with self.assertRaises(OSError):self.network.activate(self.registry,self.op,backend)
        result = tx.recover(self.registry,self.op,backend)
        self.assertEqual(result['state'],'recovered',result)
        self.assertEqual(backend.effects,['setting:proxy.sandbox','setting:proxy.sandbox','restart'])
        before=(self.registry.base/'registry.json').read_bytes()
        self.assertEqual(tx.recover(self.registry,self.op,backend),result)
        self.assertEqual((self.registry.base/'registry.json').read_bytes(),before)

    def test_external_setting_or_credential_change_is_preserved(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        backend.current['observations']['setting_proxy_sandbox']['value']='external'
        effects=backend.effects[:]
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
        self.assertEqual(backend.effects,effects)
        self.assertEqual(backend.current['observations']['setting_proxy_sandbox']['value'],'external')

    def test_new_credential_or_policy_blocks_restore(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        original=copy.deepcopy(backend.current)
        for key in ('secret_inventory','policy_global','policy_candidate'):
            backend.current=copy.deepcopy(original)
            backend.current['observations'][key]['external']=True
            effects=backend.effects[:]
            with self.subTest(key=key):
                self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
                self.assertEqual(backend.effects,effects)
                self.assertTrue(backend.current['observations'][key]['external'])

    def test_lost_restore_setting_reply_is_observed_without_repeat(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        backend.lost='proxy.sandbox'
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
        count=backend.effects.count('setting:proxy.sandbox')
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'recovered')
        self.assertEqual(backend.effects.count('setting:proxy.sandbox'),count)

    def test_consumed_restore_intent_with_no_effect_cannot_be_reissued(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        with patch.object(backend,'setting',side_effect=OSError('failed before write')):
            self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
        before=backend.effects[:]
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
        self.assertEqual(backend.effects,before)

    def test_baseline_override_is_restored_with_its_source(self):
        self.args['baseline']['observations']['setting_proxy_sandbox'].update(value='direct',source='override')
        self.plan=tx.build_plan(**self.args,network=dict(resolver='system',forbidden_ips=[]))
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'recovered')
        restored=backend.current['observations']['setting_proxy_sandbox']
        self.assertEqual((restored['value'],restored['source']),('direct','override'))

    def test_native_mutations_are_explicitly_gated(self):
        import mission_sbx
        backend=object.__new__(mission_sbx.Recovery)
        with self.assertRaisesRegex(ValueError,'native_egress_contract_unverified'):
            backend.setting('proxy.sandbox',{})
        with self.assertRaisesRegex(ValueError,'native_egress_contract_unverified'):
            backend.restart()

    def test_lost_restore_restart_reply_is_not_repeated(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        backend.lost='restart'
        self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
        count=backend.effects.count('restart')
        result=tx.recover(self.registry,self.op,backend)
        self.assertEqual(result['state'],'recovered',result)
        self.assertEqual(backend.effects.count('restart'),count)

    def test_unexpected_daemon_restart_during_restore_blocks_further_effects(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        setting=backend.setting
        def external_restart(key,target):
            setting(key,target)
            backend.current['daemon_identity']['pid'] += 5
        with patch.object(backend,'setting',side_effect=external_restart):
            result=tx.recover(self.registry,self.op,backend)
        self.assertEqual(result['state'],'blocked',result)
        self.assertEqual(backend.effects.count('restart'),1)

    def test_occupied_original_port_blocks_recovery_without_touching_listener(self):
        backend=self.ready();self.network.activate(self.registry,self.op,backend)
        with socket.socket() as sentinel:
            sentinel.bind(('127.0.0.1',self.port));sentinel.listen(1)
            before=backend.effects[:]
            self.assertEqual(tx.recover(self.registry,self.op,backend)['state'],'blocked')
            self.assertEqual(backend.effects,before)
            self.assertEqual(sentinel.getsockname()[1],self.port)


class NetworkBindingTests(RuntimeCase):
    def run_network(self, mode='success'):
        import mission_backlog
        import mission_process
        args=inputs()
        args['manifest']=dict(self.make_manifest(),fixture_id='isolated-egress-v1')
        args['project_id']=mission_backlog.project_id(self.root)
        args['project_sha256']=tx.sha(str(self.root.resolve()))
        plan=tx.build_plan(**args,network=dict(resolver='system',forbidden_ips=['172.17.0.1']))
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        registry=execution.Registry(Path(temporary.name)/'execution')
        self.enterContext(registry_storage(registry.base))
        op=plan['manifest']['operation_id']
        tx.admit(self.root,registry,plan)
        command=dict(argv=[sys.executable,'-I','-B',str(Path(__file__).parent/'fixtures/network_controller.py')],
            cwd=str(self.root),stdin=json.dumps(dict(root=str(self.root),registry=str(registry.base),
                operation_id=op,mode=mode)).encode(),timeout_seconds=15,output_limit_bytes=32768,
                client='metadata',connection='native')
        result=mission_process.supervise(command,on_started=lambda owner:tx.claim(self.root,registry,op,owner),
                                         stop_requested=lambda:False)
        self.assertEqual((result['reason'],result['exit_code']),('completed',0),result)
        self.assertTrue(result['tree_reaped'])
        return plan,registry,json.loads(result['stdout']),command

    def test_real_guards_same_port_B_absent_and_recovery_after_owner_exit(self):
        plan,registry,result,command=self.run_network()
        self.assertEqual([p['state'] for p in result['result']['phases']],
                         ['observed','blocked_unattributed','observed'],result)
        self.assertEqual(result['result']['state'],'observed',result)
        self.assertFalse(result['result']['proof_accepted'])
        events=registry.records()[0]['network_events']
        ports=[e['payload']['port'] for e in events if e['kind']=='guard_ready']
        self.assertEqual(len(ports),2)
        self.assertEqual(ports[0],ports[1])
        self.assertEqual(len([e for e in events if e['kind']=='guard_reaped']),2)
        for phase in ('A','B','A2'):
            directory=self.root/'.runtime'/('network-'+phase)
            self.assertEqual((directory/'dispatches').read_bytes(),b'1\n')
            receipt=json.loads((directory/'loopback-result.json').read_bytes())
            self.assertEqual(receipt,dict(port=ports[0],phase=phase,blocked=phase=='B'))
        backend=SettingsFixture(plan,registry)
        backend.current=result['current'];backend.active=True;backend.workload_running=False
        backend.effects=result['effects']
        recovered=tx.reconcile(self.root,registry,plan['manifest']['operation_id'],backend)
        self.assertEqual(recovered['state'],'recovered',recovered)
        self.assertEqual(backend.effects,['setting:proxy.sandbox','restart','stop_vm','setting:proxy.sandbox','restart'])
        import mission_process
        again=mission_process.supervise(command,on_started=lambda _:None,stop_requested=lambda:False)
        self.assertEqual(again['exit_code'],0,again)
        self.assertEqual(json.loads(again['stdout'])['result']['reason'],'reconciliation_required')
        self.assertEqual(len(registry.records()[0]['journal']),30)

    def test_drift_between_activation_and_prepare_blocks_dispatch(self):
        _,registry,result,_=self.run_network('drift')
        self.assertEqual(result['result']['state'],'blocked',result)
        self.assertFalse((self.root/'.runtime/network-A/dispatches').exists())
        self.assertEqual(registry.records()[0]['state'],'consumed')


if __name__=='__main__':unittest.main()
