"""Local protocol peer, no network, credentials or model. Not a Claude substitute."""
import json
import hashlib
from pathlib import Path
import sys
import time

mode=sys.argv[1]
def emit(value):
    print(json.dumps(value),flush=True)

if '--version' in sys.argv:
    print('2.1.220 (Claude Code)')
elif 'auth' in sys.argv:
    emit(dict(loggedIn=mode!='unauthenticated',authMethod='claude.ai',apiProvider='firstParty'))
else:
    assert '--setting-sources=' in sys.argv
    init=json.loads(sys.stdin.readline())
    assert set(init['request']['hooks'])=={'PreToolUse','PostToolUse'}
    emit(dict(type='control_response',response=dict(subtype='success',request_id='init',response=dict(commands=[{'name':s} for s in ('retrieve-memory','karpathy','ponytail')]))))
    prompt=sys.stdin.readline()
    if not prompt:
        sys.exit(0)
    if mode=='hang':
        time.sleep(60)
    evidence_paths=['vault/features/delivery-board/index.md','vault/decisions/static-site.md',
        'vault/features/delivery-board/runs/implementation.md','vault/features/delivery-board/runs/native-memory.md','vault/operations/index.md']
    if mode=='success':
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
        import vault
        paths=['vault/index.md','vault/project.json']+[f'skills/{s}/SKILL.md' for s in ('retrieve-memory','karpathy','ponytail')]+evidence_paths
        calls=[('Read',{'file_path':p}) for p in paths]+[('Bash',{'command':'sha256sum -- '+' '.join(evidence_paths)})]
        emit(dict(type='system',subtype='init',session_id='fixture-session',model='local-fixture'))
    else:
        calls=[('Read',{'file_path':'vault/index.md'})]*25
    for i,(tool,args) in enumerate(calls):
        emit(dict(type='assistant',session_id='fixture-session',message={'content':[dict(type='tool_use',id=str(i),name=tool,input=args)]}))
        emit(dict(type='control_request',request_id=f'pre-{i}',request=dict(subtype='hook_callback',callback_id='p06-pre',tool_use_id=str(i),input=dict(hook_event_name='PreToolUse',tool_use_id=str(i),tool_name=tool,tool_input=args))))
        line=sys.stdin.readline()
        if not line:
            sys.exit(3)
        response=json.loads(line)['response']['response']
        if response['hookSpecificOutput']['permissionDecision']!='allow':
            sys.exit(4)
        if i==24:
            Path('twenty-fifth-executed').write_text('ERROR')
        content=Path(args['file_path']).read_text(encoding='utf-8') if tool=='Read' else '\n'.join(hashlib.sha256(Path(p).read_bytes()).hexdigest()+'  '+p for p in evidence_paths)
        emit(dict(type='control_request',request_id=f'post-{i}',request=dict(subtype='hook_callback',callback_id='p06-post',tool_use_id=str(i),input=dict(hook_event_name='PostToolUse',tool_use_id=str(i),tool_name=tool,tool_input=args,tool_response=content))))
        if not sys.stdin.readline():
            sys.exit(3)
        emit(dict(type='user',session_id='fixture-session',message={'content':[dict(type='tool_result',tool_use_id=str(i),content=content)]}))
    if mode=='success':
        evidence=[dict(path=p,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest(),note_id=vault.metadata(Path(p).read_text(encoding='utf-8'))[0]['id']) for p in evidence_paths]
        result=dict(project_id=json.loads(Path('vault/project.json').read_text())['project_id'],feature_id=evidence[0]['note_id'],decision='fixture',development='fixture',production='fixture',next_action='semantic review',capabilities_used=['retrieve-memory','karpathy','ponytail'],warnings=[],evidence=evidence)
        emit(dict(type='result',subtype='success',is_error=False,session_id='fixture-session',result=json.dumps(result)))
