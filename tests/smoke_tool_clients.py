"""Native tool transports without a model. These observations do not qualify agent routing."""
import argparse
import base64
import json
from pathlib import Path
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mission_worker as worker
import mission_tool_clients as clients
import mission_process as processes

FIXED=b'def clamp(value, low, high):\n    return min(high, max(low, value))\n'


def run(client, executable, docker, image):
    binary=clients.verify_binary(client,executable)
    events=[]
    with tempfile.TemporaryDirectory(prefix='yc-tool-transport-') as directory:
        root=Path(directory);source=root/'source';source.mkdir()
        (source/'clamp.py').write_bytes(b'def clamp(value, low, high):\n    return max(low, value)\n')
        package=root/'input.tar';packed=worker.pack(source,['clamp.py'],package)
        plan=dict(contract='isolated-tools',schema_version=1,operation_id=str(uuid.uuid4()),
                  deadline_ms=int(time.time()*1000)+30000,image_digest=image,package_sha256=packed['sha256'],engine=worker.engine(docker))
        def persist(kind,payload):events.append(dict(kind=kind,payload=payload))
        handle=None
        try:
            handle=worker.start(plan,package,docker,persist)
            cwd = Path(worker.workspace(plan['operation_id']))
            if client=='codex':
                requests=[({'id':1,'method':'initialize','params':{'clientName':'youngcrow-smoke'}},1),
                          ({'method':'initialized','params':{}},None),
                          ({'id':2,'method':'fs/writeFile','params':{'path':(cwd/'clamp.py').as_uri(),'dataBase64':base64.b64encode(FIXED).decode(),'followSymlinks':False,'sandbox':None}},2),
                          ({'id':3,'method':'fs/readFile','params':{'path':(cwd/'clamp.py').as_uri(),'followSymlinks':False,'sandbox':None}},3),
                          ({'id':4,'method':'process/start','params':{'processId':'probe','argv':['/usr/local/bin/python3','-c','import os;assert os.getuid()==1000;print("worker-ok")'],'cwd':cwd.as_uri(),'env':{'PATH':'/usr/local/bin:/usr/bin:/bin'},'tty':False,'pipeStdin':False,'arg0':None,'sandbox':None}},4),
                          ({'id':5,'method':'process/read','params':{'processId':'probe','afterSeq':None,'maxBytes':65536,'waitMs':1000}},5)]
                command=worker.exec_argv(handle,['/usr/local/bin/codex','exec-server','--listen','stdio'])
            else:
                command=worker.exec_argv(handle,['/usr/local/bin/python3','-I','-B','/opt/youngcrow/mcp.py'])
                correction="python3 -c \"from pathlib import Path;Path('clamp.py').write_bytes("+repr(FIXED)+")\""
                requests=[({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'youngcrow','version':'1'}}},1),
                          ({'jsonrpc':'2.0','method':'notifications/initialized'},None),
                          ({'jsonrpc':'2.0','id':2,'method':'tools/list'},2),
                          ({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'run','arguments':{'command':correction}}},3)]
            result=processes.supervise(dict(argv=command,cwd=str(root),stdin=b'',exchange_requests=requests,
                        timeout_seconds=12,output_limit_bytes=worker.DATA_LIMIT,connection='authenticated',
                        client=client,execution_contract='isolated-tools',environment_overrides={}),
                        on_started=lambda owner:persist('bridge_started',owner),stop_requested=lambda:False)
            assert result['tree_reaped'] and result['exit_code']==0, result['stderr'].decode(errors='replace')
            messages=[json.loads(line) for line in result['stdout'].splitlines()]
            responses={v['id']:v for v in messages if 'id' in v}
            assert not any('error' in v for v in responses.values()), responses
            if client=='codex':
                assert base64.b64decode(responses[3]['result']['dataBase64'])==FIXED
            else:
                assert [t['name'] for t in responses[2]['result']['tools']]==['run']
                assert not responses[3]['result']['isError']
            artifact=worker.collect(handle,root/'result',persist)
            assert (root/'result/clamp.py').read_bytes()==FIXED
            return dict(kind='native-transport-no-model',client=client,**binary,image_digest=image,
                        state='partial',transport='passed',model_calls=0,artifact=artifact,
                        agent_routes='unverified',qualified=False,
                        gaps=clients.managed_gaps(client)+['agent_tool_catalog_unqualified','subscription_acceptance_pending'])
        finally:
            if handle is None:
                handle=next((r['payload'] for r in reversed(events) if r['kind'] in ('ready','start_intent','created')),None)
            if handle:
                worker.stop(handle,persist);worker.remove(handle,persist)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client',choices=('codex','claude'),required=True)
    parser.add_argument('--executable',type=Path,required=True)
    parser.add_argument('--docker',type=Path,required=True)
    parser.add_argument('--image',required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--native-manifest',type=Path)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    if args.native_manifest:
        import mission_worker_runs
        result=mission_worker_runs.check_worker(args.root,json.loads(args.native_manifest.read_text()),args.executable,args.docker)
    else:result=run(args.client,args.executable,args.docker,args.image)
    with args.report.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))
    return 0 if result.get('transport')=='passed' else 1


if __name__=='__main__':sys.exit(main())
