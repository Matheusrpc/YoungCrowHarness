"""Trusted launcher: preserve intent, verify Docker configuration, never retry start."""
import importlib.util
import hashlib
from fnmatch import fnmatchcase
from contextlib import nullcontext
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


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('launcher'), 'launcher not implemented')
        import launcher
        self.module = launcher
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = dict(schema_version=1, operation_id=str(uuid.uuid4()), nonce=uuid.uuid4().hex,
                             deadline_ms=int(time.time()*1000)+5000, init_argv=['/client','version'],
                             dispatch_prefix=['/client','check'])
        self.image = 'sha256:'+'a'*64
        self.cid = 'b'*64
        self.calls = []
        if os.name == 'nt':
            patched=patch.object(self.module.guardian,'sync_directory')
            patched.start()
            self.addCleanup(patched.stop)
        elif os.getuid() != 0:
            # Unprivileged CI tests contracts only. The VM smoke checks root ownership.
            patched=patch.object(self.module,'protected')
            patched.start()
            self.addCleanup(patched.stop)

    def docker(self, *args):
        self.calls.append(args)
        if args[0]=='create':
            directory=self.root/self.manifest['operation_id']
            self.assertTrue((directory/'consumed.json').exists())
            self.assertTrue((directory/'control/launch.json').exists())
            return self.cid.encode()+b'\n'
        if args==('inspect',self.cid):
            return json.dumps([self.inspection]).encode()
        raise AssertionError('unexpected effect '+repr(args))

    def create(self):
        control=self.root/self.manifest['operation_id']/'control'
        self.inspection = dict(Id=self.cid, Image=self.image, State=dict(Status='created', Running=False, Pid=0),
            Config=dict(User='0:0', Entrypoint=['/usr/bin/python3.14'],
                        Cmd=['-I','-B','/opt/youngcrow/guardian.py'], OpenStdin=True, Tty=False,
                        WorkingDir='/', Healthcheck={'Test':['NONE']},
                        Labels={'youngcrow.operation':self.manifest['operation_id'],'youngcrow.nonce':self.manifest['nonce']}),
            HostConfig=dict(ReadonlyRootfs=True, Privileged=False, NetworkMode='none',
                NanoCpus=2000000000, Memory=4294967296, MemorySwap=4294967296, PidsLimit=64,
                RestartPolicy=dict(Name='no',MaximumRetryCount=0), CapDrop=['ALL'],
                CapAdd=['CAP_SETGID','CAP_SETPCAP','CAP_SETUID'], SecurityOpt=['no-new-privileges=true'],
                Tmpfs={'/home/client':'rw,noexec,nosuid,nodev,size=16m,uid=1000,gid=1000,mode=0700'},
                Binds=None, PortBindings={}, Devices=None, DeviceRequests=None, VolumesFrom=None,
                LogConfig={'Type':'none','Config':{}}, PublishAllPorts=False, AutoRemove=False,
                ExtraHosts=['api.openai.com:1.1.1.1'] if self.manifest['schema_version']==2 else None,
                PidMode='', IpcMode='private', CgroupnsMode='private', UsernsMode=''),
            Mounts=[dict(Type='bind',Source=str(control),Destination='/control',RW=True)])
        with patch.object(self.module, 'docker', side_effect=self.docker):
            return self.module.prepare(self.root,self.image,self.manifest)

    def test_prepare_persists_before_create_and_run_is_consumed_before_start(self):
        record=self.create()
        self.assertEqual(record['container_id'],self.cid)
        self.assertFalse(any(c[0]=='start' for c in self.calls))
        with patch.object(self.module,'docker',side_effect=self.docker):
            command=self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
            self.assertEqual(command,['/usr/bin/docker','start','-ai',self.cid])
            self.assertTrue((self.root/self.manifest['operation_id']/'start.json').exists())
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])

    def test_repeated_prepare_or_lost_create_reply_cannot_create_again(self):
        self.create()
        before=len(self.calls)
        with patch.object(self.module,'docker',side_effect=self.docker):
            with self.assertRaises(self.module.guardian.Refused):
                self.module.prepare(self.root,self.image,self.manifest)
        self.assertEqual(len(self.calls),before)
        manifest=dict(self.manifest,operation_id=str(uuid.uuid4()))
        with patch.object(self.module,'docker',side_effect=OSError('lost reply')) as call:
            with self.assertRaises(self.module.guardian.Refused): self.module.prepare(self.root,self.image,manifest)
            with self.assertRaises(self.module.guardian.Refused): self.module.prepare(self.root,self.image,manifest)
        self.assertEqual(call.call_count,1)

    def test_widened_configuration_never_returns_start_command(self):
        for key,value in [('Privileged',True),('NetworkMode','host'),('ReadonlyRootfs',False),
                          ('PidsLimit',0),('PidMode','host'),('IpcMode','host'),
                          ('CapAdd',['CAP_SYS_ADMIN']),('SecurityOpt',[]),
                          ('PortBindings',{'80/tcp':[{'HostPort':'80'}]})]:
            with self.subTest(key=key):
                self.manifest['operation_id']=str(uuid.uuid4())
                self.create()
                self.inspection['HostConfig'][key]=value
                with patch.object(self.module,'docker',side_effect=self.docker):
                    with self.assertRaises(self.module.guardian.Refused):
                        self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])

    def test_expired_wrong_nonce_or_changed_manifest_does_not_start(self):
        self.create()
        with patch.object(self.module,'docker',side_effect=self.docker):
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],'0'*32)
            with patch.object(self.module.guardian.time,'time',return_value=time.time()+10):
                with self.assertRaises(self.module.guardian.Refused):
                    self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
            path=self.root/self.manifest['operation_id']/'control/launch.json'
            value=json.loads(path.read_bytes());value['init_argv']=['/other']
            path.write_text(json.dumps(value))
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])

    def test_unpinned_image_or_invalid_manifest_never_calls_docker(self):
        with patch.object(self.module,'docker',side_effect=AssertionError('must not call')):
            for image,manifest in [('python:latest',self.manifest),
                                    (self.image,dict(self.manifest,operation_id='../escape')),
                                    (self.image,dict(self.manifest,deadline_ms=0))]:
                with self.assertRaises(self.module.guardian.Refused): self.module.prepare(self.root,image,manifest)

    def test_start_refuses_shutdown_window_before_inspection(self):
        self.create()
        with patch.object(self.module.guardian.time, 'time', return_value=self.manifest['deadline_ms']/1000-.5), \
             patch.object(self.module, 'docker', side_effect=self.docker):
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
        self.assertFalse((self.root/self.manifest['operation_id']/'start.json').exists())

    def test_inspection_cannot_consume_shutdown_reserve_and_still_start(self):
        self.create()
        def inspect(*args):
            result = self.docker(*args)
            clock.return_value = self.manifest['deadline_ms']/1000-.5
            return result
        with patch.object(self.module.guardian.time, 'time', return_value=self.manifest['deadline_ms']/1000-2) as clock, \
             patch.object(self.module, 'docker', side_effect=inspect):
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
        self.assertTrue((self.root/self.manifest['operation_id']/'start.json').exists())

    def test_image_healthcheck_mounts_and_logging_must_match(self):
        for section,key,value in [('Config','Healthcheck',{'Test':['CMD','/other']}),
                                  ('Config','Entrypoint',['/other']),
                                  ('HostConfig','LogConfig',{'Type':'json-file','Config':{}}),
                                  ('HostConfig','PublishAllPorts',True),
                                  ('HostConfig','AutoRemove',True),
                                  (None,'Image','sha256:'+'c'*64),
                                  (None,'Mounts',[])]:
            with self.subTest(key=key):
                self.manifest['operation_id']=str(uuid.uuid4())
                self.create()
                target=self.inspection if section is None else self.inspection[section]
                target[key]=value
                with patch.object(self.module,'docker',side_effect=self.docker):
                    with self.assertRaises(self.module.guardian.Refused):
                        self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])

    def test_network_failure_leaves_a_consumed_claim_without_phase_permission(self):
        self.assertTrue(hasattr(self.module,'configure_network'),'network launcher not implemented')
        self.manifest.update(schema_version=2,network={'host':'api.openai.com','ipv4':'1.1.1.1'})
        self.create()
        with patch.object(self.module,'docker',side_effect=self.docker):
            self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
        self.inspection['State'].update(Status='running',Running=True,Pid=123)
        self.inspection['NetworkSettings']={'Networks':{'none':{}}}
        directory=self.root/self.manifest['operation_id']
        def fail(*args,**kwargs):
            self.assertTrue((directory/'network-initialize-intent.json').exists())
            raise OSError('connection lost')
        with patch.object(self.module,'docker',side_effect=self.docker), \
             patch.object(self.module,'network_handle',return_value=nullcontext((42,'net:[123]'))), \
             patch.object(self.module,'net_command',side_effect=fail):
            for _ in range(2):
                with self.assertRaises(self.module.guardian.Refused):
                    self.module.configure_network(self.root,self.manifest['operation_id'],self.manifest['nonce'],'initialize')
        self.assertFalse((directory/'control/network-initialize.json').exists())
        self.assertFalse(any(c[0]=='network' for c in self.calls))

    def test_network_hostname_is_pinned_before_creation(self):
        self.manifest.update(schema_version=2,network={'host':'api.openai.com','ipv4':'1.1.1.1'})
        self.create()
        args=next(c for c in self.calls if c[0]=='create')
        self.assertIn('--add-host',args)
        self.assertEqual(args[args.index('--add-host')+1],'api.openai.com:1.1.1.1')
        self.inspection['HostConfig']['ExtraHosts']=['api.openai.com:127.0.0.1']
        with patch.object(self.module,'docker',side_effect=self.docker):
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])

    def test_network_installs_before_link_and_changed_rules_block_dispatch(self):
        self.assert_network_installation(2)

    def test_relay_rules_install_before_link_and_gate_each_phase(self):
        with patch.object(self.module.guardian.relay,'read_ca',return_value=(b'public-test-ca',None)), \
             patch.object(self.module.guardian,'require_unmapped') as check:
            self.assert_network_installation(3)
            self.assertGreaterEqual(check.call_count,3)

    def assert_network_installation(self, version):
        self.assertTrue(hasattr(self.module,'configure_network'),'network launcher not implemented')
        self.manifest.update(schema_version=2,network={'host':'api.openai.com','ipv4':'1.1.1.1'})
        if version == 3:
            self.manifest.update(schema_version=3, network={'proxy_ipv4':'192.168.65.1'},
                                 relay=dict(kind='echo',phase='A',placeholder='youngcrow-probe-'+'a'*32,
                                            ca_sha256=hashlib.sha256(b'public-test-ca').hexdigest()))
        self.create()
        with patch.object(self.module,'docker',side_effect=self.docker):
            self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
        self.inspection['State'].update(Status='running',Running=True,Pid=123)
        self.inspection['NetworkSettings']={'Networks':{'none':{}}}
        rules={tool:['-P INPUT ACCEPT','-P FORWARD ACCEPT','-P OUTPUT ACCEPT'] for tool in ('iptables','ip6tables')}
        def net(fd,tool,*args,**kwargs):
            self.assertEqual(fd,42)
            if args==('-S',):return ('\n'.join(rules[tool])+'\n').encode()
            if args[0]=='-P':
                rules[tool]=[('-P '+args[1]+' '+args[2]) if r.startswith('-P '+args[1]+' ') else r for r in rules[tool]]
            elif args[0]=='-A':rules[tool].append(' '.join(args))
            else:raise AssertionError(args)
            return b''
        def docker(*args):
            if args[0]=='network':
                self.assertIn('-P OUTPUT DROP',rules['iptables'])
                self.assertIn('-P OUTPUT DROP',rules['ip6tables'])
                self.inspection['NetworkSettings']['Networks']={} if args[1]=='disconnect' else {'bridge':{}}
                return b''
            return self.docker(*args)
        directory=self.root/self.manifest['operation_id']
        with patch.object(self.module,'docker',side_effect=docker), \
             patch.object(self.module,'network_handle',return_value=nullcontext((42,'net:[123]'))), \
             patch.object(self.module,'net_command',side_effect=net):
            self.module.configure_network(self.root,self.manifest['operation_id'],self.manifest['nonce'],'initialize')
            gate=json.loads((directory/'control/network-initialize.json').read_text())
            self.assertEqual(gate['phase'],'initialize')
            self.assertEqual(gate['network_namespace'],'net:[123]')
            rules['iptables'].append('-A OUTPUT -j ACCEPT')
            with self.assertRaisesRegex(self.module.guardian.Refused,'network'):
                self.module.configure_network(self.root,self.manifest['operation_id'],self.manifest['nonce'],'dispatch')
        self.assertFalse((directory/'control/network-dispatch.json').exists())

    def test_relay_ca_is_bound_before_create_and_rechecked_before_start(self):
        ca = b'public-test-ca'
        digest = hashlib.sha256(ca).hexdigest()
        self.manifest.update(schema_version=3, network={'proxy_ipv4':'192.168.65.1'},
                             relay=dict(kind='echo',phase='A',placeholder='youngcrow-probe-'+'a'*32,
                                        ca_sha256=digest))
        self.assertTrue(hasattr(self.module.guardian, 'relay'))
        reads = []
        def read_ca(path, expected, *, snapshot=True):
            reads.append((path, snapshot))
            raw = path.read_bytes() if snapshot else ca
            if hashlib.sha256(raw).hexdigest() != expected:
                raise self.module.guardian.relay.Refused('ca_changed')
            return raw, None
        with patch.object(self.module.guardian.relay, 'read_ca', side_effect=read_ca), \
             patch.object(self.module,'docker',side_effect=self.docker):
            self.create()
            control = self.root/self.manifest['operation_id']/'control'
            self.assertEqual((control/'relay-ca.pem').read_bytes(), ca)
            self.assertFalse(reads[0][1])
            self.assertTrue(reads[-1][1])
            (control/'relay-ca.pem').write_bytes(b'changed')
            with self.assertRaises(self.module.guardian.Refused):
                self.module.start_command(self.root,self.manifest['operation_id'],self.manifest['nonce'])
            self.assertFalse((control.parent/'start.json').exists())

    def test_relay_firewall_scopes_client_loopback_and_root_proxy(self):
        self.assertTrue(hasattr(self.module,'network_rules'))
        v3 = dict(schema_version=3,network={'proxy_ipv4':'192.168.65.1'})
        ipv4, ipv6 = self.module.network_rules(v3)
        self.assertEqual(ipv6, [('-P',c,'DROP') for c in ('INPUT','FORWARD','OUTPUT')])
        accepts = [r for r in ipv4 if r[0]=='-A']
        self.assertEqual(len(accepts), 6)
        outgoing = [r for r in accepts if r[1]=='OUTPUT']
        self.assertEqual(len(outgoing),3)
        for rule in outgoing:
            self.assertIn('--uid-owner',rule)
            uid = rule[rule.index('--uid-owner')+1]
            if uid == '1000':
                self.assertIn('127.0.0.1/32',rule)
                self.assertIn(str(self.module.guardian.relay.PORT),rule)
                self.assertIn('lo',rule)
            else:
                self.assertEqual(uid,'0')
                self.assertTrue('--sport' in rule or ('192.168.65.1/32' in rule and '3128' in rule))

    def test_remapped_identity_refused(self):
        self.assertTrue(hasattr(self.module.guardian,'require_unmapped'))
        with patch.object(Path,'read_text',return_value='0 100000 65536\n'):
            with self.assertRaisesRegex(self.module.guardian.Refused,'uid_gid_remapping'):
                self.module.guardian.require_unmapped(123)
        with patch.object(Path,'read_text',return_value='         0          0 4294967295\n') as read:
            self.module.guardian.require_unmapped(123)
            self.assertEqual(read.call_count,2)


class BuildContextTests(unittest.TestCase):
    def test_copy_sources_are_present_in_allowlisted_build_context(self):
        import shlex
        root = Path(__file__).resolve().parents[1] / 'runtime/sbx'
        rules = root.joinpath('.dockerignore').read_text().splitlines()
        for line in root.joinpath('youngcrow.dockerfile').read_text().splitlines():
            if not line.startswith('COPY '):
                continue
            sources = [part for part in shlex.split(line)[1:-1] if not part.startswith('--')]
            for source in sources:
                with self.subTest(source=source):
                    self.assertTrue((root / source).is_file(), 'COPY source missing')
                    included = True
                    for rule in rules:
                        rule = rule.strip()
                        if rule and not rule.startswith('#') and fnmatchcase(source, rule.lstrip('!')):
                            included = rule.startswith('!')
                    self.assertTrue(included, 'COPY source excluded from Docker build context')


if __name__=='__main__':
    unittest.main()
