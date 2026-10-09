"""P06 regressions use local fixtures only; never launch Claude or a model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))


class PilotClaudeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('pilot_claude'), 'P06 correction missing')
        import pilot_claude
        self.p = pilot_claude
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.context = self.base / 'context'
        skills = self.base / 'skills'
        for name in ('karpathy', 'ponytail'):
            (skills / name).mkdir(parents=True)
            (skills / name / 'SKILL.md').write_text('Fixture skill, no external actions.')
        self.p.make_context(ROOT, self.context, skills)
        self.before = self.p.snapshot(self.context)
        self.gate = self.p.ToolGate(self.context, self.before)

    def hook(self, number, tool='Read', args=None, phase='PreToolUse'):
        return dict(tool_use_id=f'tool-{number}', hook_event_name=phase,
                    tool_name=tool, tool_input=args or {'file_path':'vault/index.md'})

    def test_twenty_fifth_tool_and_replayed_id_are_refused_before_admission(self):
        for number in range(24):
            self.gate.admit(self.hook(number))
        self.assertEqual(len(self.gate.admitted), 24)
        with self.assertRaisesRegex(ValueError, 'tool_budget'):
            self.gate.admit(self.hook(24))
        self.assertEqual(len(self.gate.admitted), 24)
        with self.assertRaises(ValueError):
            self.gate.admit(self.hook(0))

    def test_gate_confines_paths_and_accepts_only_literal_hash_commands(self):
        bad = [('Read', {'file_path':'../outside'}),
               ('Read', {'file_path':str(self.base / 'private.txt')}),
               ('Glob', {'pattern':'../*'}),
               ('Grep', {'pattern':'x','path':'../'}),
               ('Bash', {'command':'sha256sum -- vault/index.md; echo leaked'}),
               ('Bash', {'command':'sha256sum -- $(echo vault/index.md)'}),
               ('Bash', {'command':'sha256sum -- vault/index.md','run_in_background':True}),
               ('Write', {'file_path':'vault/index.md','content':'x'})]
        for number, (tool, args) in enumerate(bad):
            with self.subTest(tool=tool, args=args), self.assertRaises(ValueError):
                self.gate.admit(self.hook(number,tool,args))
        self.assertEqual(len(self.gate.admitted), 0)
        self.gate.admit(self.hook(50, 'Bash', {'command':'sha256sum -- vault/index.md vault/operations/index.md'}))
        self.assertEqual(len(self.gate.admitted), 1)

    def test_changed_file_is_refused_before_read(self):
        (self.context / 'vault/index.md').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'context_changed'):
            self.gate.admit(self.hook(1))

    def test_operation_reservation_does_not_reset_existing_attempt(self):
        marker = self.base / 'started.json'
        self.p.reserve(marker, {'operation_id':'one'})
        first=marker.read_bytes()
        with self.assertRaises(FileExistsError):
            self.p.reserve(marker, {'operation_id':'two'})
        self.assertEqual(marker.read_bytes(), first)

    def test_temporary_credential_cleanup_includes_copy_failures(self):
        source=self.base/'source.json'
        source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':int((time.time()+3600)*1000)}}))
        original=source.read_bytes()
        profile=self.base/'profile'
        self.assertTrue(hasattr(self.p,'temporary_auth'), 'Credential cleanup missing')
        def partial_copy(src,dst):
            Path(dst).write_text('partial synthetic copy')
            raise OSError('simulated copy failure')
        with patch.object(self.p.shutil,'copyfile',side_effect=partial_copy):
            with self.assertRaises(OSError):
                with self.p.temporary_auth(source,profile):
                    self.fail('copy failure released client')
        self.assertFalse((profile/'.credentials.json').exists())
        profile=self.base/'second-profile'
        with self.assertRaises(RuntimeError):
            with self.p.temporary_auth(source,profile):
                raise RuntimeError('simulated authentication failure')
        self.assertFalse((profile/'.credentials.json').exists())
        self.assertEqual(source.read_bytes(),original)

    def test_credential_expiry_and_session_margin_are_checked_without_leaking_contents(self):
        source=self.base/'source.json'
        now=1000
        for number, expiry in enumerate((None, True, 'private-fixture', float('inf'), 0,
                                          (now+359)*1000, (now+360)*1000)):
            with self.subTest(expiry=expiry):
                source.write_text(json.dumps({'claudeAiOauth':{
                    'accessToken':'private-fixture', 'expiresAt':expiry}}))
                profile=self.base/f'profile-{number}'
                with patch.object(self.p,'time',SimpleNamespace(time=lambda:now),create=True):
                    with self.assertRaisesRegex(ValueError,'subscription_') as failure:
                        with self.p.temporary_auth(source,profile):
                            pass
                self.assertNotIn('private-fixture',str(failure.exception))
                self.assertFalse((profile/'.credentials.json').exists())
        source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':(now+360)*1000+1}}))
        with patch.object(self.p,'time',SimpleNamespace(time=lambda:now),create=True):
            with self.p.temporary_auth(source,self.base/'fresh-profile'):
                self.assertEqual((self.base/'fresh-profile/.credentials.json').read_bytes(),source.read_bytes())

    def test_actual_credential_copy_is_checked_before_releasing_client(self):
        source=self.base/'source.json'
        source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':int((time.time()+3600)*1000)}}))
        original=source.read_bytes()
        def stale_copy(src,dst):
            Path(dst).write_text(json.dumps({'claudeAiOauth':{'expiresAt':0}}))
        profile=self.base/'profile'
        with patch.object(self.p.shutil,'copyfile',side_effect=stale_copy):
            with self.assertRaisesRegex(ValueError,'subscription_login_expired_or_expiring'):
                with self.p.temporary_auth(source,profile):
                    pass
        self.assertEqual(source.read_bytes(),original)
        self.assertFalse((profile/'.credentials.json').exists())

    def test_expired_login_blocks_prepare_before_creating_package(self):
        source=self.base/'.credentials.json'
        source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':0}}))
        package=self.base/'package'
        local_os=SimpleNamespace(name='nt',environ={'CLAUDE_CONFIG_DIR':str(self.base)},
                                 walk=self.p.os.walk,fsync=self.p.os.fsync)
        with patch.object(self.p,'os',local_os), patch.object(self.p,'BASE',str(package)), \
                patch.object(self.p,'native_executable',return_value=Path(sys.executable)), \
                patch.object(self.p,'supervised_worker',side_effect=ValueError('client_started')) as worker:
            with self.assertRaisesRegex(ValueError,'subscription_login_expired_or_expiring'):
                self.p.campaign('prepare',skills_dir=self.base/'skills')
            worker.assert_not_called()
        self.assertFalse(package.exists())

    def test_login_expiring_after_prepare_blocks_run_before_reservation(self):
        source=self.base/'.credentials.json'
        source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':int((time.time()+3600)*1000)}}))
        package=self.base/'package'
        local_os=SimpleNamespace(name='nt',environ={'CLAUDE_CONFIG_DIR':str(self.base)},
                                 walk=self.p.os.walk,fsync=self.p.os.fsync)
        observed=dict(reason='completed',exit_code=0,tree_reaped=True,
                      stdout=b'{"type":"p06_initialized"}\n',stderr=b'')
        with patch.object(self.p,'os',local_os), patch.object(self.p,'BASE',str(package)), \
                patch.object(self.p,'native_executable',return_value=Path(sys.executable)), \
                patch.object(self.p,'supervised_worker',side_effect=lambda *args:dict(observed)) as worker:
            result=self.p.campaign('prepare',skills_dir=self.base/'skills')
            self.assertEqual(result['state'],'prepared_no_model_prompt')
            setup_before=(package/'setup.json').read_bytes()
            source.write_text(json.dumps({'claudeAiOauth':{'expiresAt':0}}))
            worker.reset_mock()
            with self.assertRaisesRegex(ValueError,'subscription_login_expired_or_expiring'):
                self.p.campaign('run')
            worker.assert_not_called()
        self.assertFalse((package/'started.json').exists())
        self.assertFalse((package/'profile-run').exists())
        self.assertEqual((package/'setup.json').read_bytes(),setup_before)

    def run_fixture(self, mode, seconds=5):
        self.assertTrue(hasattr(self.p,'supervised_worker'), 'Supervised protocol worker missing')
        request=dict(context=str(self.context),before=self.before,profile=str(self.base/'profile'),
                     client_argv=[sys.executable,'-B',str(ROOT/'tests/fixtures/pilot_claude.py'),mode],
                     mode='run',model='default')
        return self.p.supervised_worker(request, self.base/'owner.json', seconds)

    def test_protocol_gate_blocks_twenty_fifth_before_fixture_effect(self):
        observed=self.run_fixture('over_budget')
        rows=self.p.parse_events(observed['stdout'])
        self.assertEqual(sum(r['type']=='p06_admitted' for r in rows),24)
        self.assertFalse((self.context/'twenty-fifth-executed').exists())
        self.assertNotEqual(observed['exit_code'],0)
        self.assertTrue(observed['tree_reaped'])

    def test_outer_timeout_stops_unresponsive_fixture(self):
        observed=self.run_fixture('hang',.4)
        self.assertEqual(observed['reason'],'timeout')
        self.assertTrue(observed['tree_reaped'])

    def test_authentication_failure_never_sends_prompt(self):
        observed=self.run_fixture('unauthenticated')
        self.assertNotEqual(observed['exit_code'],0)
        self.assertNotIn(b'p06_prompt_sent',observed['stdout'])
        self.assertTrue(observed['tree_reaped'])

    def test_successful_protocol_exchange_reconciles_actual_fixture_outputs(self):
        observed=self.run_fixture('success')
        rows=self.p.parse_events(observed['stdout'])
        result=self.p.verify(self.context,self.before,rows,observed)
        self.assertEqual(result['state'],'evidence_verified_pending_semantic_review')

    def test_binary_checksum_marker_is_valid_but_conflicting_hash_is_not(self):
        rows=self.complete_events()
        for event in rows:
            if event['type']=='user':
                item=event['message']['content'][0]
                if '  vault/' in item['content']:
                    item['content']=item['content'].replace('  vault/',' *vault/')
        self.assertEqual(self.p.verify(self.context,self.before,rows,self.supervision())['state'],
                         'evidence_verified_pending_semantic_review')

    def test_modified_prepared_model_is_refused(self):
        self.assertTrue(hasattr(self.p,'read_prepared'), 'Prepared package identity missing')
        setup=self.base/'setup.json'
        self.p.reserve(setup,dict(model='default'))
        self.p.save(self.base/'prepare-receipt.json',dict(state='prepared_no_model_prompt',setup_sha256=self.p.digest(setup)))
        self.assertEqual(self.p.read_prepared(self.base)['model'],'default')
        self.p.save(setup,dict(model='different-model'))
        with self.assertRaisesRegex(ValueError,'prepared_package_changed'):
            self.p.read_prepared(self.base)

    def test_package_binds_native_acl_helper(self):
        self.assertEqual(self.p.package_hashes(ROOT).get(str(Path('scripts')/'adoption_acl.ps1')),
                         self.p.digest(ROOT/'scripts/adoption_acl.ps1'))

    def evidence(self):
        output=[]
        for relative in sorted(self.p.REQUIRED_EVIDENCE):
            raw=(self.context/relative).read_bytes()
            output.append(dict(path=relative, note_id=self.p.vault.metadata(raw.decode())[0]['id'],
                               sha256=hashlib.sha256(raw).hexdigest()))
        return output

    def complete_events(self, project_grep=False):
        evidence=self.evidence()
        result=dict(project_id=json.loads((self.context/'vault/project.json').read_text())['project_id'],
                    feature_id=next(e['note_id'] for e in evidence if e['path'].endswith('delivery-board/index.md')),
                    decision='Static site', development='Verified development',
                    production='Observed production; semantic review still required',
                    evidence=evidence, next_action='Review this new proof',
                    capabilities_used=['retrieve-memory','karpathy','ponytail'], warnings=[])
        rows=[dict(type='p06_prompt_sent'), dict(type='system', subtype='init', session_id='session-1', model='fixture')]
        reads=set(self.p.REQUIRED_READS)|{e['path'] for e in evidence}
        hashes={e['path'] for e in evidence}
        if project_grep:
            reads.remove('vault/project.json')
            hashes.add('vault/project.json')
        calls=[('Read',{'file_path':p}) for p in sorted(reads)]
        if project_grep:
            calls.append(('Grep',{'pattern':'project_id','path':'vault','output_mode':'content','-n':True}))
        calls.append(('Bash',{'command':'sha256sum -- '+' '.join(sorted(hashes))}))
        for number,(tool,args) in enumerate(calls):
            hook=self.hook(number,tool,args)
            admitted=self.gate.admit(hook)
            rows.append(dict(type='p06_admitted', **admitted))
            rows.append(dict(type='assistant', session_id='session-1', message={'content':[dict(type='tool_use',id=hook['tool_use_id'],name=tool,input=args)]}))
            rows.append(dict(type='p06_completed', **self.gate.complete({**hook,'hook_event_name':'PostToolUse'})))
            if tool=='Grep':
                content='\n'.join(f'vault\\project.json:{n}:{line}' for n,line in
                                  enumerate((self.context/'vault/project.json').read_text().splitlines(),1)
                                  if '"project_id"' in line)
            else:
                content='\n'.join(self.before[p]+'  '+p for p in admitted['paths']) if tool=='Bash' else (self.context/admitted['paths'][0]).read_text(encoding='utf-8')
            rows.append(dict(type='user', session_id='session-1', message={'content':[dict(type='tool_result',tool_use_id=hook['tool_use_id'],content=content)]}))
        rows.append(dict(type='result',subtype='success',is_error=False,session_id='session-1',result=json.dumps(result)))
        return rows

    def supervision(self):
        return dict(reason='completed',exit_code=0,tree_reaped=True,elapsed_seconds=1)

    def test_skill_mirrors_require_identical_reviewed_bytes(self):
        encoded=json.dumps(self.complete_events())
        for name in self.p.SKILLS:
            path=f'skills/{name}/SKILL.md'
            encoded=encoded.replace('"'+path+'"','".claude/'+path+'"')
        rows=json.loads(encoded)
        try:
            verified=self.p.verify(self.context,self.before,rows,self.supervision())
        except ValueError as error:
            self.fail(f'Identical staged skills were rejected: {error}')
        self.assertEqual(len(verified['verification_details']['skill_mirrors']),3)
        mirror='.claude/skills/karpathy/SKILL.md'
        with (self.context/mirror).open('a') as stream:
            stream.write('\nDifferent skill instructions.\n')
        before={**self.before,mirror:self.p.digest(self.context/mirror)}
        with self.assertRaisesRegex(ValueError,'missing_memory_navigation'):
            self.p.verify(self.context,before,rows,self.supervision())

    def test_project_grep_requires_exact_source_line_and_verified_hash(self):
        rows=self.complete_events(project_grep=True)
        try:
            verified=self.p.verify(self.context,self.before,rows,self.supervision())
        except ValueError as error:
            self.fail(f'Project identity with source and hash was rejected: {error}')
        self.assertEqual(verified['verification_details']['project_identity'],'grep_with_hash')
        grep_id=next(e['tool_use_id'] for e in rows if e['type']=='p06_admitted' and e['tool_name']=='Grep')
        grep_result=next(e['message']['content'][0] for e in rows if e['type']=='user'
                         and e['message']['content'][0]['tool_use_id']==grep_id)
        original=grep_result['content']
        for bad in (original.replace('vault\\project.json','vault\\other.json'),
                    original.replace(':2:',':1:'),original+' extra',
                    original.replace(verified['handoff']['project_id'],'wrong-id'),
                    'vault\\project.json'):
            with self.subTest(output=bad), self.assertRaises(ValueError):
                grep_result['content']=bad
                self.p.verify(self.context,self.before,rows,self.supervision())
        grep_result['content']=original.replace('\\','/')
        self.assertEqual(self.p.verify(self.context,self.before,rows,self.supervision())['state'],
                         'evidence_verified_pending_semantic_review')
        grep_input=next(e['tool_input'] for e in rows if e['type']=='p06_admitted' and e['tool_name']=='Grep')
        for option,value in (('output_mode','files_with_matches'),('-n',False)):
            previous=grep_input[option]
            with self.subTest(option=option), self.assertRaises(ValueError):
                grep_input[option]=value
                self.p.verify(self.context,self.before,rows,self.supervision())
            grep_input[option]=previous
        for event in rows:
            if event['type'] in ('p06_admitted','p06_completed') and event['tool_name']=='Bash':
                event['paths']=[p for p in event['paths'] if p!='vault/project.json']
                event['tool_input']['command']=event['tool_input']['command'].replace(' vault/project.json','')
            if event['type']=='assistant':
                for item in event['message']['content']:
                    if item.get('name')=='Bash':
                        item['input']['command']=item['input']['command'].replace(' vault/project.json','')
            if event['type']=='user':
                item=event['message']['content'][0]
                item['content']='\n'.join(line for line in item['content'].splitlines()
                                           if not line.endswith('  vault/project.json'))
        with self.assertRaisesRegex(ValueError,'missing_memory_navigation'):
            self.p.verify(self.context,self.before,rows,self.supervision())

    def test_single_json_fence_is_reported_but_extra_text_is_rejected(self):
        rows=self.complete_events()
        raw=rows[-1]['result']
        fenced='```json\n'+raw+'\n```'
        rows[-1]['result']=fenced
        try:
            verified=self.p.verify(self.context,self.before,rows,self.supervision())
        except ValueError as error:
            self.fail(f'A single JSON fence was rejected: {error}')
        self.assertEqual(verified['verification_details']['result_format'],'json_code_fence')
        self.assertEqual(verified['handoff'],json.loads(raw))
        for bad in ('intro\n'+fenced,fenced+'\nextra',fenced+'\n'+fenced,
                    fenced.replace('```json','```python')):
            with self.subTest(result=bad), self.assertRaises(ValueError):
                rows[-1]['result']=bad
                self.p.verify(self.context,self.before,rows,self.supervision())

    def test_verifier_checks_claude_events_and_rejects_missing_or_forged_proofs(self):
        rows=self.complete_events()
        verified=self.p.verify(self.context,self.before,rows,self.supervision())
        self.assertEqual(verified['state'],'evidence_verified_pending_semantic_review')
        mutations=[rows[:-1], rows+[rows[-1]],
                   [r for r in rows if r['type']!='p06_admitted'],
                   [r for r in rows if r['type']!='p06_completed'],
                   rows+[dict(type='assistant',message={'content':[]})],
                   rows[:-1]+[dict(rows[-1],permission_denials=[{'tool_name':'Read'}])]]
        for bad in mutations:
            with self.subTest(mutation=len(bad)), self.assertRaises(ValueError):
                self.p.verify(self.context,self.before,bad,self.supervision())
        for update in ({'reason':'timeout'}, {'tree_reaped':False}, {'exit_code':1}):
            with self.assertRaises(ValueError):
                self.p.verify(self.context,self.before,rows,{**self.supervision(),**update})
        terminal=dict(rows[-1],is_error=True)
        with self.assertRaises(ValueError):
            self.p.verify(self.context,self.before,rows[:-1]+[terminal],self.supervision())
        wrong=json.loads(json.dumps(rows))
        for r in wrong:
            if r['type']=='user':
                r['message']['content'][0]['content']='not a hash result'
        with self.assertRaises(ValueError):
            self.p.verify(self.context,self.before,wrong,self.supervision())
        (self.context/'unexpected.txt').write_text('unauthorized')
        with self.assertRaises(ValueError):
            self.p.verify(self.context,self.before,rows,self.supervision())


if __name__ == '__main__':
    unittest.main()
