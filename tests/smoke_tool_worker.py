"""Explicit Docker proof. Never invokes a provider or an authenticated client."""
import argparse
import hashlib
import json
import os
import selectors
import shlex
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mission_worker as worker


NESTED_PROBE = '''import ctypes,errno,json,os,socket
from pathlib import Path
libc=ctypes.CDLL(None,use_errno=True)
def denied(result):
 assert result == -1 and ctypes.get_errno() in (errno.EPERM,errno.EACCES), ctypes.get_errno()
def map_user(parent):
 Path('/proc/self/setgroups').write_text('deny')
 Path('/proc/self/uid_map').write_text('0 '+str(parent)+' 1')
 Path('/proc/self/gid_map').write_text('0 '+str(parent)+' 1')
 assert os.getuid()==0 and os.getgid()==0
def protected():
 for p in ('/snapshot/nested-attack','/opt/youngcrow/check.py'):
  try: Path(p).write_bytes(b'attack')
  except OSError: pass
  else: raise AssertionError('protected file writable by nested root')
 for p in ('/control','/root','/proc/1/root','/proc/1/fd'):
  try: list(Path(p).iterdir())
  except OSError: pass
  else: raise AssertionError('private path accessible by nested root: '+p)
 try: Path('/proc/1/mem').open('rb')
 except OSError: pass
 else: raise AssertionError('guardian memory accessible')
 assert not Path('/var/run/docker.sock').exists()
def no_network():
 for address in ('1.1.1.1','169.254.169.254','172.17.0.1'):
  with socket.socket() as connection:
   connection.settimeout(.1)
   try: connection.connect((address,443))
   except OSError: pass
   else: raise AssertionError('network accessible by nested root')
assert libc.unshare(0x10000000)==0, ctypes.get_errno()
map_user(1000)
protected()
denied(libc.kill(1,9))
assert libc.setuid(2000)==-1 and ctypes.get_errno()==errno.EINVAL
denied(libc.unshare(0x20000))
with open('/proc/self/ns/user','rb') as namespace:
 denied(libc.setns(namespace.fileno(),0))
target=Path('nested-tmpfs').resolve();target.mkdir()
denied(libc.mount(b'tmpfs',os.fsencode(target),b'tmpfs',6,None))
# The parent listener must disappear from the child's new network namespace.
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
port=listener.getsockname()[1]
pid=libc.syscall(56,0x78020011,0,0,0,0)
assert pid>=0, ctypes.get_errno()
if pid==0:
 try:
  listener.close()
  map_user(0)
  protected()
  no_network()
  with socket.socket() as connection:
   connection.settimeout(.1)
   assert connection.connect_ex(('127.0.0.1',port)) != 0
  denied(libc.mount(b'none',b'/',None,0x9022,None))
  assert Path('/sys/fs/cgroup/memory.max').read_text().strip()=='1073741824'
  assert Path('/sys/fs/cgroup/pids.max').read_text().strip()=='128'
  children=[]
  try:
   for _ in range(150):
    try: child=os.fork()
    except BlockingIOError: break
    if child==0:
     import time;time.sleep(60);os._exit(0)
    children.append(child)
   else: raise AssertionError('nested PID quota absent')
  finally:
   for child in children: os.kill(child,9)
   for child in children: os.waitpid(child,0)
  assert libc.mount(b'tmpfs',os.fsencode(target),b'tmpfs',6,b'size=96m')==0, ctypes.get_errno()
  with (target/'extra').open('wb') as output:
   for _ in range(80): output.write(b'x'*1048576)
  # Nested scratch can exceed the workspace volume, within the cgroup memory cap.
  assert libc.umount2(os.fsencode(target),2)==0
  print('nested-boundary-ok',flush=True)
  os._exit(0)
 except BaseException:
  import traceback;traceback.print_exc();os._exit(1)
_,status=os.waitpid(pid,0)
assert os.waitstatus_to_exitcode(status)==0
listener.close();target.rmdir()
'''


def run(docker, image, seconds=30):
    observations = []
    with tempfile.TemporaryDirectory(prefix='yc-worker-') as directory:
        root = Path(directory)
        source = root / 'source'
        source.mkdir()
        original = b'def clamp(value, low, high):\n    return max(low, value)\n'
        (source / 'clamp.py').write_bytes(original)
        package = root / 'package.tar'
        packed = worker.pack(source, ['clamp.py'], package)
        plan = dict(contract='isolated-tools', schema_version=1, operation_id=str(uuid.uuid4()),
                    deadline_ms=int(time.time() * 1000) + seconds * 1000,
                    image_digest=image, package_sha256=packed['sha256'], engine=worker.engine(docker))
        def persist(kind, payload):
            observations.append(dict(kind=kind, payload=payload))
        handle = None
        try:
            handle = worker.start(plan, package, docker, persist)
            current = worker.observe(handle)
            assert current['network_mode'] == 'none' and current['tool_uid'] == 1000
            assert current['host_bind_mounts'] == []
            probe = '''import json,os,socket,sys
from pathlib import Path
assert os.getuid()==1000
cwd=Path.cwd()
assert cwd == Path(os.environ['HOME']) and cwd.resolve() == cwd
assert cwd.parent.stat().st_uid == 0 and cwd.parent.stat().st_mode & 0o022 == 0
assert cwd.stat().st_dev != Path('/tmp').stat().st_dev
capacity=os.statvfs(cwd)
assert capacity.f_blocks * capacity.f_frsize == 64 * 1024 * 1024
sys.path.insert(0,'/opt/youngcrow')
import mcp
assert json.loads(mcp.run('pwd')) == dict(exit_code=0,output=str(cwd)+'\\n')
assert 'YC_PRIVATE_SENTINEL' not in os.environ
assert not any(v for k,v in os.environ.items() if 'proxy' in k.lower())
for path in ['/snapshot/attack','/opt/youngcrow/check.py']:
 try: Path(path).write_text('attack')
 except (PermissionError,OSError):pass
 else:raise AssertionError('protected snapshot/image writable')
for path in ['/control','/root','/var/run/docker.sock']:
 try:
  list(Path(path).iterdir()) if Path(path).is_dir() else Path(path).read_bytes()
 except (PermissionError,FileNotFoundError,NotADirectoryError): pass
 else: raise AssertionError('private path accessible')
try: os.kill(1,9)
except PermissionError: pass
else: raise AssertionError('guardian kill allowed')
for address in ['1.1.1.1','169.254.169.254','172.17.0.1']:
 s=socket.socket();s.settimeout(.1)
 try: s.connect((address,443))
 except OSError: pass
 else: raise AssertionError('network accessible')
 finally:s.close()
children=[]
try:
 for _ in range(150):
  try:pid=os.fork()
  except BlockingIOError:break
  if pid==0:
   import time;time.sleep(60);os._exit(0)
  children.append(pid)
 else:raise AssertionError('PID quota absent')
finally:
 for pid in children:os.kill(pid,9)
 for pid in children:os.waitpid(pid,0)
quota=Path('quota')
written=0
try:
 with quota.open('wb') as stream:
  for _ in range(66):
   stream.write(b'x'*1048576)
   written+=1048576
except OSError as e:
 assert e.errno==28 and written > 16 * 1024 * 1024
else:raise AssertionError('tmpfs quota absent')
finally:quota.unlink()
Path('clamp.py').write_text('def clamp(value, low, high):\\n    return min(high, max(low, value))\\n')
print('boundary-ok')
'''
            output = worker.execute(handle, ['/usr/local/bin/python3', '-I', '-c', probe])
            assert output == b'boundary-ok\n'
            output = worker.execute(handle, ['/usr/local/bin/python3', '-I', '-c', NESTED_PROBE])
            assert output == b'nested-boundary-ok\n'
            result = worker.collect(handle, root / 'result', persist)
            assert result['worker_stopped_before_publish'] and result['test']['exit_code'] == 0
            assert (source / 'clamp.py').read_bytes() == original
            assert (root / 'result' / 'clamp.py').read_bytes() != original
            result['original_changed'] = False
            result['boundary'] = 'passed'
            result['nested_user_mount_pid_network_boundaries'] = 'passed'
            result['nested_scratch_exceeds_workspace_volume'] = True
            result['seccomp_sha256'] = worker.SECCOMP_SHA256
        finally:
            if handle is None:
                handle = next((e['payload'] for e in reversed(observations) if e['kind'] in ('ready','start_intent','created')), None)
            if handle:
                worker.stop(handle, persist)
                worker.remove(handle, persist)
        # Kill a real controller after it starts a detached worker descendant.
        plan.update(operation_id=str(uuid.uuid4()), deadline_ms=int(time.time()*1000)+10000)
        child = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--crash-child'],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        handle = None
        journal = root/'child.json'
        try:
            child.stdin.write(json.dumps(dict(plan=plan,package=str(package),docker=str(docker),journal=str(journal))).encode()+b'\n')
            child.stdin.close()
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout,selectors.EVENT_READ)
                assert selector.select(8),'child did not become ready'
                handle=json.loads(child.stdout.readline(8192))
            os.kill(child.pid,signal.SIGKILL);child.wait(timeout=3)
            assert child.returncode==-signal.SIGKILL
            while worker.observe(handle)['running'] and time.time()*1000 < plan['deadline_ms']+1000:
                time.sleep(.1)
            stopped=worker.observe(handle)
            assert not stopped['running'] and stopped['pid']==0 and stopped['finished_ms']<=plan['deadline_ms']
            result['deadline_without_controller']='passed'
            result['nested_process_deadline']='passed'
            result['controller_killed']=True
            result['remaining_worker_processes']=0
        finally:
            if child.poll() is None:child.kill()
            child.wait()
            child.stdout.close();child.stderr.close()
            if handle is None and journal.exists():
                rows=json.loads(journal.read_text())
                handle=next((e['payload'] for e in reversed(rows) if e['kind'] in ('ready','start_intent','created')),None)
            if handle:
                worker.stop(handle,persist);worker.remove(handle,persist)
        result.update(kind='native-docker-no-model', engine=plan['engine'], image_digest=image,
                      model_calls=0, events=len(observations))
        # An edited module cannot manufacture the checker's success receipt.
        plan.update(operation_id=str(uuid.uuid4()), deadline_ms=int(time.time()*1000)+15000)
        handle = None
        try:
            handle = worker.start(plan, package, docker, persist)
            forged = 'import os\nprint(\'{"cases": 3, "exit_code": 0}\', flush=True)\nos._exit(0)\n'
            worker.execute(handle, ['/usr/local/bin/python3', '-I', '-c',
                'from pathlib import Path; Path("clamp.py").write_text(' + repr(forged) + ')'])
            try:
                worker.collect(handle, root/'forged-result', persist)
            except ValueError:
                assert not (root/'forged-result').exists()
                result['forged_checker_receipt']='refused'
            else:
                raise AssertionError('candidate forged a passing test receipt')
        finally:
            if handle:
                worker.stop(handle,persist);worker.remove(handle,persist)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', type=Path, required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.docker, args.image)
    with args.report.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


def crash_child():
    request=json.loads(sys.stdin.buffer.readline(16384));rows=[]
    def persist(kind,payload):
        rows.append(dict(kind=kind,payload=payload))
        with Path(request['journal']).open('w') as stream:
            json.dump(rows,stream);stream.flush();os.fsync(stream.fileno())
    handle=worker.start(request['plan'],Path(request['package']),Path(request['docker']),persist)
    code = "from pathlib import Path; import time; Path('nested-ready').write_text('ready'); time.sleep(60)"
    command = ['/usr/local/bin/codex-resources/bwrap', '--unshare-user', '--unshare-pid',
               '--unshare-net', '--unshare-ipc', '--bind', '/', '/', '--',
               '/usr/local/bin/python3', '-I', '-c', code]
    worker.execute(handle,['/bin/sh','-c',shlex.join(command)+' >/dev/null 2>&1 &'])
    worker.execute(handle, ['/usr/local/bin/python3', '-I', '-c',
        "from pathlib import Path; import time; "
        "exec(\"for _ in range(30):\\n if Path('nested-ready').exists(): break\\n time.sleep(.05)\"); "
        "assert Path('nested-ready').read_text() == 'ready'"])
    print(json.dumps(handle),flush=True)
    while True:time.sleep(.1)


if __name__ == '__main__':
    if sys.argv[1:]==['--crash-child']:crash_child()
    else:main()
