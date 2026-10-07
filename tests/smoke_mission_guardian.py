"""Unpaid protocol proof inside the owned microVM, using a prepared image digest.

Does not create/approve an sbx runtime profile. Never run against the host Docker
daemon. The VM must have YC_PROBE_NONCE set by its recorded creation intent.
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


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, timeout=10)


def require(*args):
    result = docker(*args)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:1000])
    return result.stdout


def case(image, mode, root):
    nonce = uuid.uuid4().hex
    directory = root / nonce
    directory.mkdir(mode=0o700)
    control = directory / 'control'
    control.mkdir(mode=0o700)
    argv = ['/usr/bin/python3.14', '-I', '-B', '/opt/youngcrow/attack.py']
    # Give the output cap time to win over the independent deadline control.
    budget_seconds = 10 if mode == 'output-limit' else 5
    config = dict(schema_version=1, operation_id=str(uuid.uuid4()), nonce=nonce,
                  deadline_ms=int(time.time() * 1000) + budget_seconds * 1000,
                  init_argv=argv + ['discover-fails' if mode == 'discovery-fails' else 'discover'],
                  dispatch_prefix=argv)
    manifest = control / 'launch.json'
    manifest.write_text(json.dumps(config))
    manifest.chmod(0o600)
    journal = directory / 'receipt.json'
    record = dict(mode=mode, nonce=nonce, image=image, state='create_intent', deadline_ms=config['deadline_ms'])
    def save():
        journal.write_text(json.dumps(record, indent=2) + '\n')
    save()
    cid = require('create', '-i', '--name', 'yc-protocol-' + nonce[:12], '--label', 'yc.protocol=' + nonce,
                  '--restart', 'no', '--read-only', '--network', 'none', '--cpus', '2',
                  '--memory', '4g', '--memory-swap', '4g', '--pids-limit', '64',
                  '--cap-drop', 'ALL', '--cap-add', 'SETUID', '--cap-add', 'SETGID', '--cap-add', 'SETPCAP',
                  '--security-opt', 'no-new-privileges=true', '--user', '0:0',
                  '--mount', 'type=bind,src=' + str(control) + ',dst=/control',
                  '--tmpfs', '/home/client:rw,noexec,nosuid,nodev,size=16m,uid=1000,gid=1000,mode=0700',
                  '--log-driver', 'none', image, '/usr/bin/python3.14', '-I', '-B',
                  '/opt/youngcrow/guardian.py').decode().strip()
    record.update(container_id=cid, state='created')
    save()
    inspection = json.loads(require('inspect', cid))[0]
    host = inspection['HostConfig']
    assert inspection['Image'] == image and inspection['Config']['Labels']['yc.protocol'] == nonce
    assert host['NetworkMode'] == 'none' and host['ReadonlyRootfs'] and not host['Privileged']
    assert host['NanoCpus'] == 2000000000 and host['Memory'] == 4294967296 and host['PidsLimit'] == 64
    assert host['RestartPolicy']['Name'] == 'no' and not host['PortBindings']
    assert len(inspection['Mounts']) == 1 and inspection['Mounts'][0]['Source'] == str(control)
    record.update(state='start_intent', host_config=host)
    save()
    started = time.monotonic()
    transport = subprocess.Popen(['docker', 'start', '-ai', cid], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(transport.stdout, selectors.EVENT_READ)
    events, pending = [], b''
    worker_count = 0
    replay_sent = False
    streams = {'stdout': b'', 'stderr': b''}
    def send(action, **extra):
        message = dict(schema_version=1, operation_id=config['operation_id'], nonce=nonce, action=action)
        message.update(extra)
        transport.stdin.write(json.dumps(message).encode() + b'\n')
        transport.stdin.flush()
    try:
        while time.monotonic() - started < budget_seconds + 5:
            for key, _ in selector.select(.05):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fd)
                    continue
                pending += chunk
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    event = json.loads(line)
                    events.append({k:v for k,v in event.items() if k != 'data'})
                    if event['kind'] == 'listening':
                        send('initialize')
                    if event['kind'] == 'ready':
                        if mode == 'bad-identity':
                            send('dispatch', argv=argv + ['complete'], nonce='0' * 32)
                        else:
                            worker_mode = 'wait' if mode in {'replay', 'deadline'} else mode
                            send('dispatch', argv=argv + [worker_mode])
                    if event['kind'] == 'output' and event['phase'] == 'dispatch':
                        stream = event['stream']
                        streams[stream] += base64.b64decode(event['data'])
                        if stream == 'stdout' and b'\n' in streams[stream] and not worker_count:
                            worker = json.loads(streams[stream].split(b'\n', 1)[0])
                            assert worker['kind'] == 'synthetic_worker'
                            record['worker'] = worker
                            worker_count = 1
                            if mode == 'replay' and not replay_sent:
                                send('dispatch', argv=argv + ['wait'])
                                replay_sent = True
            if transport.poll() is not None and not selector.get_map():
                break
        transport.wait(timeout=1)
    finally:
        # Only the exact container created above is eligible for this cleanup.
        if json.loads(require('inspect', cid))[0]['State']['Running']:
            require('kill', cid)
        if transport.poll() is None:
            transport.kill()
        transport.wait(timeout=3)
        transport.stdin.close()
        transport.stdout.close()
        stderr = transport.stderr.read().decode(errors='replace')
        transport.stderr.close()
        selector.close()
    final = json.loads(require('inspect', cid))[0]['State']
    record.update(elapsed_seconds=time.monotonic()-started, events=events, final_state=final,
                  transport_stderr=stderr, markers=sorted(p.name for p in control.glob('*.json')),
                  worker_count=worker_count, state='observed_stopped')
    save()
    expected = {'complete':0, 'replay':125, 'bad-identity':125, 'deadline':124,
                'discovery-fails':126, 'output-limit':122}[mode]
    assert final['ExitCode'] == expected, record
    assert not final['Running'] and final['Pid'] == 0
    stamp = final['FinishedAt']
    whole = int(datetime.datetime.fromisoformat(stamp[:19]+'+00:00').timestamp())
    finished_ms = (Decimal(whole) + Decimal('0.'+(stamp[19:-1].lstrip('.') or '0'))) * 1000
    record['deadline_margin_ms'] = str(Decimal(config['deadline_ms'])-finished_ms)
    save()
    assert finished_ms <= config['deadline_ms'], 'Original deadline exceeded'
    assert record['elapsed_seconds'] < budget_seconds + 5
    assert len([e for e in events if e['kind'] == 'started' and e['phase'] == 'dispatch']) == worker_count
    if mode in {'bad-identity', 'discovery-fails'}:
        assert worker_count == 0 and not (control/'dispatch.json').exists()
    else:
        w = record['worker']
        assert w['uid'] == w['gid'] == 1000 and w['no_new_privs'] == '1'
        assert all(v == '0000000000000000' for v in w['caps'].values())
        assert all(w[k] for k in ('stdin_closed', 'control_read_denied', 'control_write_denied',
                                  'signal_denied', 'parent_fds_denied', 'sockets_absent', 'home_writable'))
        assert w['cpu_max'] == '200000 100000' and w['pids_max'] == '64' and w['memory_max'] == '4294967296'
        assert w['env_keys'] == ['HOME', 'LANG', 'PATH', 'PYTHONDONTWRITEBYTECODE']
    # Same container and persisted control: starting it again cannot obtain a lease.
    restarted = docker('start', '-ai', cid)
    again = json.loads(require('inspect', cid))[0]['State']
    restart_events = [json.loads(line) for line in restarted.stdout.splitlines()]
    assert all(e['kind'] == 'refused' for e in restart_events)
    assert again['ExitCode'] == 125 and not again['Running'] and again['Pid'] == 0
    record.update(restart_exit=again['ExitCode'], restart_output_bytes=len(restarted.stdout), assertions_passed=True)
    save()
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    assert os.name == 'posix' and os.getuid() == 0 and os.environ.get('YC_PROBE_NONCE')
    assert args.image.startswith('sha256:') and len(args.image) == 71
    args.root.mkdir(mode=0o700)
    for mode in ('complete', 'replay', 'bad-identity', 'discovery-fails', 'deadline', 'output-limit'):
        result = case(args.image, mode, args.root)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
