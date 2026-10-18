"""Durable isolated-tool checks. No replay can create another worker or client."""
import difflib
import json
import os
from pathlib import Path
import time
import uuid

import adoption_fs as fs
import mission_execution as execution
import mission_runs as runs
import mission_store as store
import mission_process as processes
import mission_tool_clients as clients
import mission_worker as worker
from mission_backlog import project_id

ORIGINAL = b'def clamp(value, low, high):\n    return max(low, value)\n'
FIXED = b'def clamp(value, low, high):\n    return min(high, max(low, value))\n'
MANIFEST = runs.MANIFEST | {'contract','client','image_digest','source','paths','package_sha256','model','effort'}
LIMITS = dict(bytes=worker.DATA_LIMIT,files=128,event_bytes=1048576,output_bytes=worker.DATA_LIMIT,
              cpus=2,memory=1073741824,pids=128,client_invocations=1)
REQUEST = {'operation_id','run_id','mission_id','project_id','manifest_sha256','authorization_sha256',
           'package_sha256','source_sha256','executable_sha256','code_sha256','project_sha256',
           'client','version','model','effort','created_ms','deadline_ms','engine','image_digest','limits','manifest','config'}
EVENTS = {'linked','create_intent','created','start_intent','ready','client_intent','client_started',
          'client_finished','stop_intent','stopped','collected','closed','recovered'}
ADMISSION_ERRORS={'limit_exceeded','revision_conflict','unresolved_run'}


def require(value,reason='invalid_worker_record'):worker.require(value,reason)


def validate_manifest(manifest):
    require(type(manifest) is dict and set(manifest)==MANIFEST and len(fs.canonical(manifest))<=16384,'invalid_manifest')
    require(manifest['contract']=='isolated-tools' and manifest['fixture_id']=='clamp-v1','invalid_manifest')
    legacy={k:manifest[k] for k in runs.MANIFEST};legacy['fixture_id']='echo-v1'
    runs.manifest_valid(legacy)
    require(manifest['max_runs']==1 and manifest['api_budget_usd'] is None and 3<=manifest['agent_seconds']<=120,'invalid_manifest')
    require(manifest['client'] in clients.VERSIONS and manifest['paths']==['clamp.py'],'invalid_manifest')
    worker.relative(manifest['source'])
    require(execution.digest(manifest['package_sha256']),'invalid_manifest')
    import re
    require(type(manifest['image_digest']) is str and re.fullmatch('sha256:[a-f0-9]{64}',manifest['image_digest']),'invalid_manifest')
    for key in ('model','effort'):
        require(type(manifest[key]) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,128}',manifest[key]),'invalid_manifest')


def runtime_plan(plan):
    return dict(contract='isolated-tools',schema_version=1,**{k:plan[k] for k in
                ('operation_id','deadline_ms','image_digest','package_sha256','engine')})


def validate_record(record):
    require(type(record) is dict and set(record)=={'contract','schema_version','request','state','revision',
                'created_at','updated_at','events','handle','client_owner','coordinator_pid','outcome'})
    require(record['contract']=='isolated-tools' and type(record['schema_version']) is int and record['schema_version']==1)
    plan=record['request'];require(type(plan) is dict and set(plan)==REQUEST)
    for key in ('operation_id','run_id','mission_id','project_id'):execution.identity(plan[key])
    for key in REQUEST:
        if key.endswith('_sha256'):require(execution.digest(plan[key]))
    require(type(plan['created_ms']) is int and type(plan['deadline_ms']) is int
            and 3000<=plan['deadline_ms']-plan['created_ms']<=120000 and fs.canonical(plan['limits'])==fs.canonical(LIMITS))
    validate_manifest(plan['manifest'])
    require(runs.digest_manifest(plan['manifest'])==plan['manifest_sha256'] and type(plan['config']) is dict)
    require(all(plan[k]==plan['manifest'][k] for k in ('operation_id','mission_id','client','model','effort','image_digest','package_sha256')))
    require(plan['client'] in clients.VERSIONS and plan['version']==clients.VERSIONS[plan['client']])
    require(type(plan['engine']) is dict and set(plan['engine'])=={'id','version','boot_id'}
            and all(type(v) is str and v for v in plan['engine'].values()))
    require(type(record['revision']) is int and record['revision']>=0 and record['state'] in ('reserved','consumed','recovered'))
    require(type(record['coordinator_pid']) is int and record['coordinator_pid']>1)
    require(all(type(record[k]) is str for k in ('created_at','updated_at')))
    require(type(record['events']) is list and len(record['events'])<=64 and all(type(e) is dict
            and set(e)=={'kind','payload'} and e['kind'] in EVENTS and type(e['payload']) is dict for e in record['events']))
    kinds=[e['kind'] for e in record['events']]
    require(all(kinds.count(k)<=1 for k in ('create_intent','created','start_intent','ready','client_intent','client_started','client_finished','collected','closed')))
    if record['handle'] is not None:
        handle=record['handle']
        require(type(handle) is dict and set(handle) in (
            {'container_id','docker','engine','image_digest','operation_id','plan_sha256','deadline_ms'},
            {'container_id','docker','engine','image_digest','operation_id','plan_sha256','deadline_ms','config_sha256'}))
        require(execution.digest(handle['container_id']) and Path(handle['docker']).is_absolute())
        require(all(handle[k]==plan[k] for k in ('engine','image_digest','operation_id','deadline_ms')))
        require(handle['plan_sha256']==worker.sha(fs.canonical(runtime_plan(plan))))
        if 'config_sha256' in handle:require(execution.digest(handle['config_sha256']))
        require('created' in kinds)
    if record['client_owner'] is not None:
        owner=record['client_owner'];require(type(owner) is dict and set(owner)=={'kind','name','pid'})
        require(owner['kind'] in ('linux-group','linux-pidns-group') and type(owner['pid']) is int and owner['pid']>1)
        execution.identity(owner['name']);require('client_started' in kinds)
    require(record['outcome'] is None or type(record['outcome']) is dict)
    if record['state']=='recovered':require(record['outcome'] is not None and any(k in kinds for k in ('closed','recovered')))
    require(len(fs.canonical(record))<=execution.MAX_RECORD,'execution_record_limit')


def save_observation(registry,record,kind,payload):
    require(kind in EVENTS and type(payload) is dict)
    record['events'].append(dict(kind=kind,payload=payload))
    if kind in ('create_intent','client_intent'):record['state']='consumed'
    if kind in ('created','start_intent','ready'):record['handle']=payload.copy()
    if kind=='client_started':record['client_owner']=payload.copy()
    with registry.locked():
        current=_find(registry,record['request']['operation_id'])
        require(current is not None and current['revision']==record['revision'],'revision_conflict')
        registry.save(record)


def storage_root():return execution.user_storage().with_name('YoungCrowToolRuns')


def inspect_worker(root,client,executable,docker):
    binary=clients.verify_binary(client,executable)
    observed=worker.engine(docker)
    registry=execution.Registry()
    gaps=clients.managed_gaps(client)
    if not clients.QUALIFIED:gaps.append('tool_profile_unqualified')
    account=storage_root()/client/'account'
    # Presence is not authentication; inspection never launches a client or reads token bytes.
    gaps.append('subscription_acceptance_pending')
    return dict(contract='isolated-tools',schema_version=1,client=client,**binary,engine=observed,
                reservation=registry.status(),account_directory=str(account),auth_status='not_checked',
                gaps=sorted(set(gaps)),runtime_available=False,runnable=False)


def preflight(root,manifest,executable,docker):
    agent,config=runs.mission_agent(root,manifest)
    require(agent['client']==manifest['client'] and agent['connection']=='authenticated','connection_conflict')
    info=inspect_worker(root,manifest['client'],executable,docker)
    require(not clients.managed_gaps(manifest['client']),'managed_policy_conflict')
    require(bool(clients.QUALIFIED),'tool_profile_unqualified')
    # Selection must already be explicit in the mission. Never silently resolve latest differently.
    require(agent['model']==manifest['model'],'unresolved_model_selection')
    effort=agent['effort']['native_value'] if agent['effort']['level']=='native' else agent['effort']['level']
    require(effort==manifest['effort'],'unresolved_model_selection')
    return dict(agent=agent,config=config,engine=info['engine'],version=info['version'],executable_sha256=info['sha256'])


def check_auth(profile):
    argv=[profile['argv'][0],*(['login','status'] if profile['client']=='codex' else ['auth','status'])]
    result=processes.supervise(dict(argv=argv,cwd=profile['cwd'],stdin=b'',timeout_seconds=10,output_limit_bytes=1048576,
                connection='authenticated',execution_contract='isolated-tools',environment_overrides=profile['environment_overrides']),
                on_started=lambda _:None,stop_requested=lambda:False)
    require(result['tree_reaped'] and result['exit_code']==0,'subscription_login_required')
    if profile['client']=='codex':
        require(b'logged in using chatgpt' in (result['stdout']+result['stderr']).lower(),'subscription_login_required')
    else:
        status=json.loads(result['stdout'])
        require(status.get('loggedIn') is True and status.get('authMethod')=='claude.ai','subscription_login_required')


def _find(registry,operation_id):
    return next((r for r in registry.records() if r['request']['operation_id']==operation_id),None)


def _receipt(root,record):
    require(project_id(root)==record['request']['project_id'] and
            worker.sha(str(Path(root).resolve()).encode())==record['request']['project_sha256'],'foreign_project')
    with store.reader(root) as conn:
        require(runs.has_runs(conn),'worker_receipt_unlinked')
        run=runs.find_run(conn,record['request']['run_id'])
        require(run.get('execution_contract')=='isolated-tools' and
                run.get('execution_plan_sha256')==worker.sha(fs.canonical(record['request'])),'worker_receipt_conflict')
    return run


def _finish_receipt(root,record):
    with store.transaction(root) as conn:
        run=runs.find_run(conn,record['request']['run_id'])
        require(run.get('execution_plan_sha256')==worker.sha(fs.canonical(record['request'])),'worker_receipt_conflict')
        if run['state'] in runs.UNRESOLVED:
            revision=run['revision']
            if record['state']=='recovered':
                run.update(record['outcome'],ended_at=runs.now())
            else:run.update(state='uncertain',reason='worker_reconciliation_required')
            runs.save_event(conn,run,dict(kind='worker_observed',state=run['state']),revision,str(uuid.uuid4()))
    return runs.project(root,run)



def receipt_details(request):
    manifest=request['manifest']
    details=dict(purpose='isolated_tool_check',execution_contract='isolated-tools',execution_plan_sha256=worker.sha(fs.canonical(request)),
                 client=manifest['client'],connection='authenticated',version=request['version'],state='reserved',reason=None,
                 requested_model=manifest['model'],resolved_model=manifest['model'],requested_effort=manifest['effort'],
                 observed_model=None,observed_effort=None,policy_digest=request['code_sha256'],executable_sha256=request['executable_sha256'],
                 capabilities_requested=['isolated-tools'],tools_observed=[],runtime_available=False,runnable=False)
    return details


def ensure_receipt(root,record):
    with store.reader(root) as conn:
        exists=runs.has_runs(conn) and conn.execute('SELECT 1 FROM agent_runs WHERE id=?',(record['request']['run_id'],)).fetchone()
    if exists:return _receipt(root,record)
    require(not any(e['kind']=='create_intent' for e in record['events']),'worker_receipt_conflict')
    request=record['request']
    return runs._record_check(root,request['manifest'],request['config'],receipt_details(request),run_id=request['run_id'])


def link_receipt(root,registry,record):
    if record['state']=='recovered' and record['outcome'].get('reason') in ADMISSION_ERRORS:
        raise ValueError(record['outcome']['reason'])
    try:
        return ensure_receipt(root,record)
    except ValueError as error:
        # These errors precede SQLite insertion. No effect intent may have been written.
        if str(error) in ADMISSION_ERRORS and not record['events'] and record['handle'] is None:
            record['outcome']=dict(state='blocked',reason=str(error))
            record['state']='recovered'
            save_observation(registry,record,'closed',dict(admission='rejected'))
        raise


def check_worker(root,manifest,executable,docker,*,_registry=None,_storage=None):
    validate_manifest(manifest)
    registry=_registry or execution.Registry()
    # Read UUID before preflight, allocating a run, or calculating any new deadline.
    old=_find(registry,manifest['operation_id'])
    if old:
        require(old.get('contract')=='isolated-tools' and old['request']['manifest_sha256']==runs.digest_manifest(manifest),'operation_conflict')
        link_receipt(root,registry,old)
        return _finish_receipt(root,old) if old['state']=='recovered' else runs.project(root,_receipt(root,old))
    prepared=preflight(root,manifest,executable,docker)
    base=fs.checked_path(_storage or storage_root());fs.outside_git(base)
    if not base.exists():fs.private_dir(base)
    private=base/manifest['operation_id'];fs.private_dir(private)
    packed=worker.pack(fs.checked_path(root/manifest['source']),manifest['paths'],private/'input.tar')
    require(packed['sha256']==manifest['package_sha256'],'worker_input_changed')
    require(worker.archive_files((private/'input.tar').read_bytes())=={'clamp.py':ORIGINAL},'invalid_worker_fixture')
    created=int(time.time()*1000)
    request=dict(operation_id=manifest['operation_id'],run_id=str(uuid.uuid4()),mission_id=manifest['mission_id'],
                 project_id=project_id(root),project_sha256=worker.sha(str(Path(root).resolve()).encode()),
                 manifest_sha256=runs.digest_manifest(manifest),authorization_sha256=worker.sha(manifest['authorization_ref'].encode()),
                 package_sha256=packed['sha256'],source_sha256=worker.sha(ORIGINAL),executable_sha256=prepared['executable_sha256'],
                 code_sha256=worker.sha(Path(__file__).read_bytes()+Path(clients.__file__).read_bytes()+Path(worker.__file__).read_bytes()+Path(processes.__file__).read_bytes()),
                 client=manifest['client'],version=prepared['version'],model=manifest['model'],effort=manifest['effort'],
                 created_ms=created,deadline_ms=created+manifest['agent_seconds']*1000,engine=prepared['engine'],
                 image_digest=manifest['image_digest'],limits=LIMITS.copy(),manifest=manifest,config=prepared['config'])
    record=dict(contract='isolated-tools',schema_version=1,request=request,state='reserved',revision=0,
                created_at=runs.now(),updated_at=runs.now(),events=[],handle=None,client_owner=None,
                coordinator_pid=os.getpid(),outcome=None)
    with registry.locked():
        require(_find(registry,manifest['operation_id']) is None,'operation_conflict')
        require(registry.status()['state']=='available','execution_reserved')
        registry.save(record)
    run=link_receipt(root,registry,record)
    persist=lambda kind,payload:save_observation(registry,record,kind,payload)
    persist('linked',dict(run_id=run['id'],revision=run['revision']))
    handle=None
    observed=dict(observed_model=None,observed_effort=None,tools_observed=[])
    try:
        handle=worker.start(runtime_plan(request),private/'input.tar',docker,persist)
        account=base/manifest['client']
        profile=clients.build_profile(manifest['client'],executable,handle,account,dict(model=manifest['model'],effort=manifest['effort']))
        clients.validate_qualification(profile,dict(profile_sha256=profile['profile_sha256']))
        check_auth(profile)
        remaining=(request['deadline_ms']/1000-time.time())-1
        require(remaining>0,'invalid_worker_deadline')
        persist('client_intent',dict(profile_sha256=profile['profile_sha256']))
        result=processes.supervise(dict(argv=profile['argv'],cwd=profile['cwd'],
                    stdin=b'Fix clamp.py so clamp(value, low, high) handles values below, within, and above the interval. Use only worker tools.\n',
                    timeout_seconds=remaining,output_limit_bytes=worker.DATA_LIMIT,connection='authenticated',
                    execution_contract='isolated-tools',environment_overrides=profile['environment_overrides']),
                    on_started=lambda owner:persist('client_started',owner),stop_requested=lambda:False)
        persist('client_finished',{k:result[k] for k in ('tree_reaped','reason','exit_code','elapsed_seconds')})
        require(result['tree_reaped'],'worker_client_uncertain')
        require(result['reason']=='completed' and result['exit_code']==0,'worker_client_failed')
        observed=clients.observe_result(manifest['client'],result['stdout'])
        for field in ('model','effort'):
            require(observed['observed_'+field] is not None,'worker_selection_unobservable')
            require(observed['observed_'+field]==manifest[field],'worker_selection_mismatch')
        require(observed['tools_observed'],'unexpected_tool')
        artifact=worker.collect(handle,private/'result',persist)
        # Snapshot bytes are data only; never import/execute them in the controller.
        candidate=(private/'result/clamp.py').read_bytes()
        diff=''.join(difflib.unified_diff(ORIGINAL.decode().splitlines(True),candidate.decode(errors='replace').splitlines(True),
                                        fromfile='before/clamp.py',tofile='after/clamp.py'))
        (private/'change.diff').write_text(diff)
        require(worker.read_source(fs.checked_path(root/manifest['source']/'clamp.py'))==ORIGINAL,'worker_original_changed')
        record['outcome']=dict(state='succeeded',reason='completed',**observed,artifact=artifact,diff_sha256=worker.sha(diff.encode()),
                               artifacts_directory=str(private),original_changed=False,baseline_test='upper_bound_failed',
                               test_sha256=worker.sha((Path(__file__).resolve().parents[1]/'runtime/worker/check.py').read_bytes()))
        record['state']='recovered';persist('closed',dict(snapshot_sha256=artifact['snapshot_sha256']))
    except (ValueError,OSError,KeyError,TypeError) as error:
        # Lost responses preserve reservation. A deadline alone is never cleanup evidence.
        if handle is None:handle=record['handle']
        if handle is not None:
            try:
                worker.stop(handle,persist)
                owner=record['client_owner']
                if owner is None or processes.owner_gone(owner):
                    reason=str(error) if str(error) in ('worker_selection_unobservable','worker_selection_mismatch',
                            'client_protocol_error','unexpected_tool') else 'worker_check_failed'
                    record['outcome']=dict(state='failed',reason=reason,**observed)
                    record['state']='recovered';persist('closed',{})
            except (ValueError,OSError):pass
    # Only durable closure can finish the local projection.
    return _finish_receipt(root,_find(registry,manifest['operation_id']))


def recover_record(registry,operation_id,docker,*,recovery_request=None):
    """Recovery works without a checkout. It observes/stops; it never starts resources."""
    record=_find(registry,operation_id);require(record is not None,'unknown_worker_operation')
    require(record.get('contract')=='isolated-tools')
    if record['state']=='recovered':
        if recovery_request is not None:save_observation(registry,record,'recovered',dict(recovery_request=recovery_request))
        return record
    require(processes.process_missing(record['coordinator_pid']),'worker_coordinator_alive')
    owner=record['client_owner']
    require(owner is None or processes.owner_gone(owner),'worker_client_alive')
    kinds=[e['kind'] for e in record['events']]
    if 'create_intent' in kinds:
        require(record['handle'] is not None,'worker_identity_unknown')
        require(str(docker)==record['handle']['docker'],'worker_identity_changed')
        worker.stop(record['handle'],lambda k,p:save_observation(registry,record,k,p))
    record['state']='recovered';record['outcome']=dict(state='interrupted',reason='worker_recovered')
    save_observation(registry,record,'recovered',dict(recovery_request=recovery_request) if recovery_request else {})
    return record


def reconcile_worker(root,run_id,expected_revision,operation_id,docker,*,_registry=None):
    execution.identity(run_id);execution.identity(operation_id)
    require(type(expected_revision) is int and expected_revision>0,'invalid_revision')
    registry=_registry or execution.Registry()
    request=dict(operation_id=operation_id,run_id=run_id,expected_revision=expected_revision)
    for row in registry.records():
        if row.get('contract')!='isolated-tools':continue
        for event in row['events']:
            previous=event['payload'].get('recovery_request')
            if previous and previous['operation_id']==operation_id:
                require(previous==request,'operation_conflict')
                _receipt(root,row)
                return _finish_receipt(root,row)
    with store.reader(root) as conn:
        run=runs.find_run(conn,run_id)
        require(run.get('execution_contract')=='isolated-tools','invalid_contract')
        require(run['revision']==expected_revision,'revision_conflict')
    record=recover_record(registry,run['operation_id'],docker,recovery_request=request)
    _receipt(root,record)
    return _finish_receipt(root,record)
