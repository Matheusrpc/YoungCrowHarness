"""P06 regressions use local fixtures only; never launch Claude or a model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
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
        source.write_text('synthetic-credential')
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
        self.assertEqual(source.read_text(),'synthetic-credential')

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
        self.assertEqual(self.p.package_hashes(ROOT).get('scripts/adoption_acl.ps1'),
                         self.p.digest(ROOT/'scripts/adoption_acl.ps1'))

    def evidence(self):
        output=[]
        for relative in sorted(self.p.REQUIRED_EVIDENCE):
            raw=(self.context/relative).read_bytes()
            output.append(dict(path=relative, note_id=self.p.vault.metadata(raw.decode())[0]['id'],
                               sha256=hashlib.sha256(raw).hexdigest()))
        return output

    def complete_events(self):
        evidence=self.evidence()
        result=dict(project_id=json.loads((self.context/'vault/project.json').read_text())['project_id'],
                    feature_id=next(e['note_id'] for e in evidence if e['path'].endswith('delivery-board/index.md')),
                    decision='Static site', development='Verified development',
                    production='Observed production; semantic review still required',
                    evidence=evidence, next_action='Review this new proof',
                    capabilities_used=['retrieve-memory','karpathy','ponytail'], warnings=[])
        rows=[dict(type='p06_prompt_sent'), dict(type='system', subtype='init', session_id='session-1', model='fixture')]
        reads=set(self.p.REQUIRED_READS)|{e['path'] for e in evidence}
        calls=[('Read',{'file_path':p}) for p in sorted(reads)]
        calls.append(('Bash',{'command':'sha256sum -- '+' '.join(sorted(e['path'] for e in evidence))}))
        for number,(tool,args) in enumerate(calls):
            hook=self.hook(number,tool,args)
            admitted=self.gate.admit(hook)
            rows.append(dict(type='p06_admitted', **admitted))
            rows.append(dict(type='assistant', session_id='session-1', message={'content':[dict(type='tool_use',id=hook['tool_use_id'],name=tool,input=args)]}))
            rows.append(dict(type='p06_completed', **self.gate.complete({**hook,'hook_event_name':'PostToolUse'})))
            content='\n'.join(self.before[p]+'  '+p for p in admitted['paths']) if tool=='Bash' else (self.context/admitted['paths'][0]).read_text()
            rows.append(dict(type='user', session_id='session-1', message={'content':[dict(type='tool_result',tool_use_id=hook['tool_use_id'],content=content)]}))
        rows.append(dict(type='result',subtype='success',is_error=False,session_id='session-1',result=json.dumps(result)))
        return rows

    def supervision(self):
        return dict(reason='completed',exit_code=0,tree_reaped=True,elapsed_seconds=1)

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
