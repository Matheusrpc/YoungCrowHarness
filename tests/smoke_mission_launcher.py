"""Partial unpaid launcher proof. Run only inside the recorded synthetic sbx VM.

Requires the guardian/attack image from smoke_mission_guardian and the launcher
installed at /opt/youngcrow. No inference, network allowance or profile approval.
"""
import argparse
import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
import uuid


def case(image, mode, root):
    operation_id, nonce = str(uuid.uuid4()), uuid.uuid4().hex
    argv = ['/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/attack.py']
    manifest = dict(schema_version=1, operation_id=operation_id, nonce=nonce,
                    deadline_ms=int(time.time()*1000)+5000, init_argv=argv+['discover'], dispatch_prefix=argv)
    launcher = ['/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/launcher.py']
    # Persist outside the launcher too, before any external resource creation.
    receipt = root/(operation_id+'.json')
    record = dict(operation_id=operation_id, nonce=nonce, image=image, mode=mode,
                  deadline_ms=manifest['deadline_ms'], state='prepare_intent')
    def save():
        receipt.write_text(json.dumps(record, indent=2)+'\n')
    save()
    prepared = subprocess.run(launcher+['prepare',image], input=json.dumps(manifest).encode(),
                              capture_output=True, timeout=10)
    assert prepared.returncode == 0, prepared.stdout.decode()+prepared.stderr.decode()
    created = json.loads(prepared.stdout)
    cid = created['container_id']
    record.update(container_id=cid, state='start_intent')
    save()
    transport = subprocess.Popen(launcher+['run',operation_id,nonce], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(transport.stdout, selectors.EVENT_READ)
    events, pending = [], b''
    started = time.monotonic()
    def inspect():
        return json.loads(subprocess.check_output(['/usr/bin/docker','inspect',cid],timeout=5))[0]
    try:
        while time.monotonic()-started < 10:
            for key,_ in selector.select(.05):
                chunk = os.read(key.fd,65536)
                if not chunk:
                    selector.unregister(key.fd)
                    continue
                pending += chunk
                while b'\n' in pending:
                    line,pending = pending.split(b'\n',1)
                    event = json.loads(line)
                    events.append({k:v for k,v in event.items() if k!='data'})
                    action = 'initialize' if event['kind']=='listening' else 'dispatch' if event['kind']=='ready' else None
                    if action:
                        message = dict(schema_version=1,operation_id=operation_id,nonce=nonce,action=action)
                        if action=='dispatch':
                            message['argv'] = argv+['complete' if mode=='complete' else 'wait']
                        transport.stdin.write(json.dumps(message).encode()+b'\n')
                        transport.stdin.flush()
                    if mode=='transport-loss' and event.get('phase')=='dispatch' and event['kind']=='started':
                        transport.kill()
            if transport.poll() is not None and not selector.get_map():
                break
        transport.wait(timeout=1)
        while inspect()['State']['Running'] and time.monotonic()-started < 10:
            time.sleep(.05)
        final = inspect()
        record.update(state='observed',events=events,elapsed_seconds=time.monotonic()-started,
                      final_state=final['State'])
        save()
        assert not final['State']['Running'] and final['State']['Pid']==0
        stamp = final['State']['FinishedAt']
        whole = int(datetime.datetime.fromisoformat(stamp[:19]+'+00:00').timestamp())
        finished_ms = (Decimal(whole) + Decimal('0.'+(stamp[19:-1].lstrip('.') or '0'))) * 1000
        record['deadline_margin_ms'] = str(Decimal(manifest['deadline_ms'])-finished_ms)
        save()
        assert finished_ms <= manifest['deadline_ms'], 'Original deadline exceeded'
        expected = {'complete':{0},'deadline':{124},'transport-loss':{124,125}}
        assert final['State']['ExitCode'] in expected[mode], record
        assert len([e for e in events if e['kind']=='started' and e['phase']=='dispatch'])==1
        repeated = subprocess.run(launcher+['run',operation_id,nonce],capture_output=True,timeout=5)
        assert repeated.returncode==125 and json.loads(repeated.stdout)['reason']=='start_consumed'
        assert inspect()['State']==final['State']
        record.update(assertions_passed=True,repeated_start='refused_without_start')
        save()
        return record
    finally:
        if inspect()['State']['Running']:
            subprocess.run(['/usr/bin/docker','kill',cid],capture_output=True,check=True,timeout=5)
        if transport.poll() is None:
            transport.kill()
        transport.wait(timeout=3)
        for stream in (transport.stdin,transport.stdout,transport.stderr):
            stream.close()
        selector.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    assert os.name=='posix' and os.getuid()==0 and os.environ.get('YC_PROBE_NONCE')
    args.root.mkdir(mode=0o700)
    for mode in ('complete','deadline','transport-loss'):
        print(json.dumps(case(args.image,mode,args.root)),flush=True)


if __name__=='__main__':
    main()
