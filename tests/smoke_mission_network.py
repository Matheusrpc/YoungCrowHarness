"""Unpaid Linux proof. Requires an owned VM, prepared image and root launcher.

Does not change sbx policy, call a provider, restart a daemon or enable a profile.
"""
import argparse
import base64
import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
import uuid


def case(image, launcher_path, root, mode):
    operation_id, nonce = str(uuid.uuid4()), uuid.uuid4().hex
    argv = ['/usr/bin/python3.14','-I','-B','/opt/youngcrow/network_attack.py']
    manifest = dict(schema_version=2,operation_id=operation_id,nonce=nonce,deadline_ms=int(time.time()*1000)+15000,
                    network={'host':'api.openai.com','ipv4':'1.1.1.1'},init_argv=argv+['discover'],dispatch_prefix=argv)
    launcher = ['/usr/bin/python3.14','-I','-B',str(launcher_path)]
    receipt = root/(operation_id+'.json')
    record = dict(mode=mode,operation_id=operation_id,nonce=nonce,image=image,deadline_ms=manifest['deadline_ms'],state='prepare_intent')
    def save():
        with receipt.open('w') as output:json.dump(record,output,indent=2);output.flush();os.fsync(output.fileno())
    with receipt.open('x') as output:json.dump(record,output);output.flush();os.fsync(output.fileno())
    result = subprocess.run(launcher+['prepare',image],input=json.dumps(manifest).encode(),capture_output=True,timeout=8)
    assert result.returncode == 0,result.stdout.decode()+result.stderr.decode()
    created = json.loads(result.stdout);cid=created['container_id'];record.update(created=created,state='start_intent');save()
    def inspect():return json.loads(subprocess.check_output(['/usr/bin/docker','inspect',cid],timeout=3))[0]
    def network(phase):
        r = subprocess.run(launcher+['network',operation_id,nonce,phase],capture_output=True,timeout=8)
        record.setdefault('network_results',[]).append({'phase':phase,'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()})
        save();return r
    transport = subprocess.Popen(launcher+['run',operation_id,nonce],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    selector=selectors.DefaultSelector();selector.register(transport.stdout,selectors.EVENT_READ)
    events=[];pending=b'';output=b'';started=time.monotonic()
    try:
        while time.monotonic()-started<18:
            for key,_ in selector.select(.05):
                chunk=os.read(key.fd,65536)
                if not chunk:selector.unregister(key.fd);continue
                pending+=chunk
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1);event=json.loads(line)
                    events.append({k:v for k,v in event.items() if k!='data'})
                    if event['kind']=='output':output+=base64.b64decode(event['data'])
                    if mode=='transport-loss' and event['kind']=='started' and event['phase']=='dispatch':
                        transport.kill();continue
                    action='initialize' if event['kind']=='listening' else 'dispatch' if event['kind']=='ready' else None
                    if not action:continue
                    if mode=='setup-crash' and action=='initialize':
                        code=("import sys,os;sys.path.insert(0,"+repr(str(launcher_path.parent))+");import launcher;"
                              "original=launcher.net_command\ndef cut(*a,**kw):\n original(*a,**kw)\n os._exit(99)\n"
                              "launcher.net_command=cut\nlauncher.configure_network(launcher.STATE,"+repr(operation_id)+","+repr(nonce)+",'initialize')")
                        cut=subprocess.run(['/usr/bin/python3.14','-I','-B','-c',code],capture_output=True,timeout=8)
                        assert cut.returncode==99,cut.stderr.decode()
                        assert network(action).returncode==125
                    elif mode=='tamper' and action=='dispatch':
                        pid=inspect()['State']['Pid']
                        subprocess.run(['/usr/bin/nsenter','-t',str(pid),'-n','/usr/sbin/iptables','-A','OUTPUT','-j','ACCEPT'],check=True,timeout=3)
                        assert network(action).returncode==125
                        assert network(action).returncode==125
                    elif (mode=='missing-initialize' and action=='initialize') or (mode=='missing-dispatch' and action=='dispatch'):
                        pass
                    else:
                        r=network(action);assert r.returncode==0,r.stdout.decode()+r.stderr.decode()
                        if mode=='replay':assert network(action).returncode==125
                    message=dict(schema_version=1,operation_id=operation_id,nonce=nonce,action=action)
                    if action=='dispatch':message['argv']=argv+['wait' if mode in ('transport-loss','deadline') else 'complete']
                    transport.stdin.write(json.dumps(message).encode()+b'\n');transport.stdin.flush()
            if transport.poll() is not None and not selector.get_map():break
        transport.wait(timeout=1)
        while inspect()['State']['Running'] and time.monotonic()-started<18:time.sleep(.05)
        final=inspect()['State'];record.update(events=events,final_container=final,client_output=output.decode(errors='replace'))
        stamp=final['FinishedAt'];whole=int(datetime.datetime.fromisoformat(stamp[:19]+'+00:00').timestamp())
        finished=(Decimal(whole)+Decimal('0.'+stamp[20:-1]))*1000
        record['deadline_margin_ms']=str(Decimal(manifest['deadline_ms'])-finished)
        assert not final['Running'] and final['Pid']==0 and finished<=manifest['deadline_ms']
        refused=mode in ('missing-initialize','missing-dispatch','tamper','setup-crash')
        dispatches=[e for e in events if e['kind']=='started' and e['phase']=='dispatch']
        assert len(dispatches)==(0 if refused else 1),events
        assert final['ExitCode'] in ({125} if refused else {124,125} if mode=='transport-loss' else {124} if mode=='deadline' else {0}),final
        replay=subprocess.run(launcher+['run',operation_id,nonce],capture_output=True,timeout=3)
        assert replay.returncode==125 and inspect()['State']==final
        record.update(state='observed',assertions_passed=True);save();return record
    finally:
        final=inspect();assert final['Image']==image and final['Config']['Labels']['youngcrow.nonce']==nonce
        if final['State']['Running']:subprocess.run(['/usr/bin/docker','kill',cid],check=True,capture_output=True,timeout=3)
        if transport.poll() is None:transport.kill()
        transport.wait(timeout=3)
        for stream in (transport.stdin,transport.stdout,transport.stderr):stream.close()
        selector.close();record['final_container']=inspect()['State'];save()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True)
    parser.add_argument('--launcher',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    assert os.name=='posix' and os.getuid()==0 and os.environ.get('YC_PROBE_NONCE')
    args.root.mkdir(mode=0o700)
    for mode in ('complete','missing-initialize','missing-dispatch','setup-crash','tamper','replay','transport-loss','deadline'):
        print(json.dumps(case(args.image,args.launcher,args.root,mode)),flush=True)


if __name__=='__main__':main()
