"""Closed official client profiles and the unprivileged MCP protocol."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


@unittest.skipUnless(sys.platform == 'linux', 'OCI tools require Linux')
class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_tool_clients'), 'profiles missing')
        import mission_tool_clients as clients
        self.c = clients
        managed = patch.object(self.c, "managed_gaps", return_value=[])
        managed.start();self.addCleanup(managed.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.executable = self.root / 'client'
        self.executable.write_text('fixture executable, never launched')
        self.handle = dict(operation_id=str(uuid.uuid4()), container_id='a'*64, docker='/usr/local/bin/docker', image_digest='sha256:'+'b'*64)
        self.selection = dict(model='fixture-model', effort='low')
        self.addCleanup(self.cleanup_mirror)

    def cleanup_mirror(self):
        mirror=Path('/tmp')/('youngcrow-'+self.handle['operation_id'])
        if (mirror/'cwd').exists():(mirror/'cwd').rmdir()
        if mirror.exists():mirror.rmdir()

    def profile(self, client):
        with patch.object(self.c,'verify_binary',return_value=dict(version=self.c.VERSIONS[client],sha256='c'*64)), patch.object(self.c,'managed_gaps',return_value=[]):
            return self.c.build_profile(client,self.executable,self.handle,self.root/'control',self.selection)

    def test_codex_has_no_local_environment_or_hook_route(self):
        profile = self.profile('codex')
        self.assertFalse(profile['environment_config']['include_local'])
        self.assertEqual(profile['environment_config']['default'],self.handle['container_id'])
        self.assertNotIn('--ignore-user-config',profile['argv'])
        for feature in ('hooks','plugins','apps','multi_agent','computer_use','browser_use','remote_plugin'):
            self.assertFalse(profile['configuration']['features'][feature])
        self.assertEqual(profile['configuration']['forced_login_method'],'chatgpt')
        self.assertEqual(profile['cwd'],'/tmp/youngcrow-'+self.handle['operation_id']+'/cwd')
        self.assertIn('--workdir=' + profile['cwd'], profile['environment_config']['environments'][0]['args'])
        self.assertEqual(profile['configuration']['sandbox_mode'],'workspace-write')

    def test_changed_configuration_or_missing_transport_fails_closed(self):
        profile = self.profile('codex')
        self.c.verify_profile(profile)
        Path(profile['config_files'][1]['path']).unlink()
        with self.assertRaises(ValueError): self.c.verify_profile(profile)

    def test_managed_hooks_block_profile(self):
        with patch.object(self.c,'verify_binary',return_value=dict(version='2.1.296',sha256='c'*64)), patch.object(self.c,'managed_gaps',return_value=['managed_policy_conflict']):
            with self.assertRaisesRegex(ValueError,'managed_policy_conflict'):
                self.c.build_profile('claude',self.executable,self.handle,self.root/'control',self.selection)
        self.assertFalse((self.root/'control').exists())

    def test_claude_deferred_tools_cannot_gain_builtin_permission(self):
        profile = self.profile('claude')
        self.assertEqual(profile['builtin_tools'],[])
        self.assertIn('--restricted',profile['argv'])
        self.assertIn('--strict-mcp-config',profile['argv'])
        self.assertNotIn('--bare',profile['argv'])
        self.assertNotIn('--dangerously-skip-permissions',profile['argv'])
        self.assertEqual(profile['argv'][profile['argv'].index('--tools')+1],'')
        self.assertEqual(profile['argv'][profile['argv'].index('--allowedTools')+1],'mcp__youngcrow__run')

    def test_profile_preserves_auth_and_refuses_unowned_configuration(self):
        control=self.root/'control';control.mkdir(mode=0o700)
        home=control/'account';home.mkdir(mode=0o700)
        (home/'auth.json').write_bytes(b'sentinel: never read or copy')
        p=self.profile('codex')
        self.assertEqual((home/'auth.json').read_bytes(),b'sentinel: never read or copy')
        Path(p['config_files'][0]['path']).write_text('injected config')
        with self.assertRaises(ValueError): self.profile('codex')

    def test_control_keeps_cloud_trust_but_drops_provider_keys(self):
        import mission_process
        plan=dict(execution_contract='isolated-tools',connection='authenticated',
                  environment_overrides=dict(CODEX_HOME='/private/account'))
        with patch.dict(os.environ,{'HTTPS_PROXY':'proxy-sentinel','SSL_CERT_FILE':'ca-sentinel',
                                   'OPENAI_API_KEY':'secret-sentinel','ANTHROPIC_AUTH_TOKEN':'token-sentinel'},clear=True):
            env=mission_process.environment(plan)
        self.assertEqual(env['HTTPS_PROXY'],'proxy-sentinel')
        self.assertEqual(env['SSL_CERT_FILE'],'ca-sentinel')
        self.assertEqual(env['CODEX_HOME'],'/private/account')
        self.assertNotIn('OPENAI_API_KEY',env)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN',env)

    def test_empty_or_forged_qualification_never_enables_execution(self):
        p=self.profile('codex')
        for proof in ({},{'qualified':True,'local_fallback':False}):
            with self.assertRaises(ValueError):self.c.validate_qualification(p,proof)

    def test_native_output_never_invents_missing_selection(self):
        codex=b'{"type":"thread.started","thread_id":"fixture"}\n{"type":"turn.completed","usage":{}}\n'
        observed=self.c.observe_result('codex',codex)
        self.assertIsNone(observed['observed_model'])
        self.assertIsNone(observed['observed_effort'])
        events=[dict(type='system',subtype='init',model='fixture-model',tools=['mcp__youngcrow__run']),
                dict(type='assistant',message=dict(model='fixture-model',content=[dict(type='tool_use',name='mcp__youngcrow__run')])),
                dict(type='result',subtype='success',is_error=False)]
        observed=self.c.observe_result('claude',b'\n'.join(json.dumps(e).encode() for e in events))
        self.assertEqual(observed['observed_model'],'fixture-model')
        self.assertIsNone(observed['observed_effort'])
        self.assertEqual(observed['tools_observed'],['mcp__youngcrow__run'])

    def test_invalid_terminal_or_unexpected_tool_is_refused(self):
        cases=[b'',b'not json',b'{"type":"turn.started"}',
               b'{"type":"turn.failed","error":{"message":"failed"}}',
               b'{"type":"turn.completed"}\n{"type":"turn.started"}',
               b'{"type":"item.completed","item":{"type":"web_search"}}\n{"type":"turn.completed"}',
               b'{"type":"turn.completed"}\n{"type":"turn.completed"}',
               b'{"type":"turn.completed","unused":"'+b'x'*1048576+b'"}']
        for data in cases:
            with self.subTest(size=len(data)),self.assertRaises(ValueError):self.c.observe_result('codex',data)


@unittest.skipUnless(sys.platform == 'linux', 'OCI tools require Linux')
class McpTests(unittest.TestCase):
    def module(self):
        path=Path(__file__).resolve().parents[1]/'runtime/worker/mcp.py'
        self.assertTrue(path.is_file(),'MCP server missing')
        spec=importlib.util.spec_from_file_location('worker_mcp',path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        return mod

    def exchange(self, requests):
        mod=self.module();output=io.BytesIO()
        with patch.object(mod.os,'getuid',return_value=1000),patch.object(mod,'run',return_value='fixture') as run:
            mod.serve(io.BytesIO(b''.join(json.dumps(r).encode()+b'\n' for r in requests)),output)
        return [json.loads(line) for line in output.getvalue().splitlines()],run.call_count

    def test_mcp_exposes_only_worker_run_and_repeated_id_never_reexecutes(self):
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                  {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'run','arguments':{'command':'echo harmless'}}}]
        replies,calls=self.exchange(requests+[requests[-1]])
        self.assertEqual([x['name'] for x in replies[1]['result']['tools']],['run'])
        self.assertEqual(calls,1)
        self.assertIn('error',replies[-1])

    def test_mcp_refuses_invalid_or_oversized_frames(self):
        mod=self.module()
        for data in (b'[]\n',b'{' + b'x'*1048576 + b'}\n'):
            output=io.BytesIO()
            with patch.object(mod.os,'getuid',return_value=1000),patch.object(mod,'run') as run:
                self.assertNotEqual(mod.serve(io.BytesIO(data),output),0)
                run.assert_not_called()
        replies,calls=self.exchange([{'jsonrpc':'2.0','id':True,'method':'tools/call','params':{'name':'Bash','arguments':{'command':'x'}}}])
        self.assertEqual(calls,0)
