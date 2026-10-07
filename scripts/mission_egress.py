"""One synthetic TLS tunnel after Docker's proxy, with numeric destination checks.

Internal transport only. The controller must durably reserve the phase and run this
in an owned, bounded helper. This module does not change Docker settings or admit
provider credentials. There is no public serve command or native runtime profile.
"""
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import socket
import subprocess
import sys
import threading
import time
import uuid

HOST = 'postman-echo.com'
MAX_BYTES = 8*1024*1024
REFUSALS = {'origin_forbidden','dns_invalid','destination_forbidden','ipv6_unverified',
            'peer_mismatch','truncated_frame','socks_version','socks_method','socks_request',
            'output_limit','extra_connection'}


def validate_destination(host, port, addresses, forbidden):
    if host != HOST or type(port) is not int or port != 443:
        raise ValueError('origin_forbidden')
    if type(addresses) is not tuple or not 1 <= len(addresses) <= 64:
        raise ValueError('dns_invalid')
    values = []
    for raw in addresses:
        try:
            if type(raw) is not str or '%' in raw: raise ValueError()
            ip = ipaddress.ip_address(raw)
            if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo
                    or ip in ipaddress.ip_network('64:ff9b::/96')
                    or ip in ipaddress.ip_network('64:ff9b:1::/48')):
                raise ValueError()
            if (not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_multicast or ip.is_reserved or ip.is_unspecified or str(ip) in forbidden):
                raise ValueError()
        except ValueError:
            raise ValueError('destination_forbidden') from None
        values.append(str(ip))
    return tuple(sorted(set(values), key=lambda s: (ipaddress.ip_address(s).version, int(ipaddress.ip_address(s)))))


def left(until):
    value = until-time.monotonic()
    if value <= 0: raise TimeoutError('deadline')
    return value


def resolve_addresses(host, timeout):
    if host != HOST: raise ValueError('origin_forbidden')
    if timeout <= 0: raise TimeoutError('resolver_incomplete')
    # Fixed child, bounded output below, inheriting the controller's group/job.
    # A second supervisor would attempt to escape that already-established group.
    process = subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--resolve',HOST],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True)
    try:
        output,_ = process.communicate(timeout=min(timeout,5))
        if process.returncode or len(output) > 16384:
            raise ValueError('dns_invalid')
    except subprocess.TimeoutExpired:
        raise TimeoutError('resolver_incomplete') from None
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
    value = json.loads(output)
    if type(value) is not list or not 1 <= len(value) <= 64 or any(type(v) is not str for v in value):
        raise ValueError('dns_invalid')
    return tuple(value)


def port_available(port):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid_port')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name == 'nt': probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        else: probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:
            probe.bind(('127.0.0.1',port))
            probe.listen(1)
        except OSError:
            return False
    return True


class Guard:
    """Fixed private helper. Config is released only after its PID is persisted."""
    def __init__(self, config, persist, *, cwd):
        import mission_controller as controller
        self.config = json.loads(controller.encoded(config))
        self.persist, self.channel, self.port = persist, None, None
        self.reader, self.error, self.result = None, None, None
        self.events = []
        try:
            persist('guard_intent', dict(config=self.config))
            self.channel = controller.Channel(self.command(), cwd=cwd, deadline_ms=config['deadline_ms'])
            persist('guard_started', dict(pid=self.channel.process.pid))
            self.channel.send(config)
            event = self.receive()
            controller.require(event['event'] == 'ready' and event['pid'] == self.channel.process.pid
                and type(event['port']) is int and 1 <= event['port'] <= 65535
                and config['listen_port'] in (0,event['port'])
                and event['deadline_ms'] == config['deadline_ms'], 'guard_identity_changed')
            self.port = event['port']
            self.reader = threading.Thread(target=self.drain, daemon=True)
            self.reader.start()
        except BaseException:
            self.close()
            raise

    def command(self):
        return [sys.executable,'-I','-B',str(Path(__file__).resolve()),'--guard']

    def receive(self):
        import mission_controller as controller
        event = self.channel.receive()
        if event is None:
            return None
        controller.require(event.get('kind') == 'egress' and event.get('event') in
            ('ready','request','destination','finished','refused','closed') and
            all(event.get(k) == self.config[k] for k in ('operation_id','phase','nonce')), 'guard_identity_changed')
        self.persist('guard_'+event['event'], {k:v for k,v in event.items() if k not in ('kind','event')})
        self.events.append(event)
        self.channel.send(dict(event=event['event']))
        return event

    def drain(self):
        import mission_controller as controller
        try:
            while self.receive() is not None:
                pass
            code = self.channel.exit_code()
            controller.require(self.events[-1]['event'] == 'closed' and code in (0,125), 'guard_exit_unverified')
            result = dict(pid=self.channel.process.pid, port=self.port, exit_code=code)
            controller.require(port_available(self.port), 'guard_port_occupied')
            self.persist('guard_reaped', result)
            self.result = result
        except BaseException as error:
            self.error = error
        finally:
            self.channel.close()

    def finish(self):
        self.reader.join(self.channel.deadline.remaining())
        if self.reader.is_alive():
            self.close()
            raise ValueError('guard_exit_unverified')
        if self.error:
            raise self.error
        return dict(self.result)

    def close(self):
        if self.channel is not None:
            self.channel.close()
        if self.reader is not None and self.reader.ident is not None and self.reader is not threading.current_thread():
            self.reader.join(.3)


def connect_checked(host, port, deadline_ms, forbidden, *, resolve=resolve_addresses,
                    socket_factory=socket.socket):
    until = time.monotonic()+min(10,(deadline_ms-time.time()*1000)/1000)
    left(until)
    if host != HOST or type(port) is not int or port != 443: raise ValueError('origin_forbidden')
    addresses = validate_destination(host,port,resolve(host,left(until)),forbidden)
    ipv4 = [a for a in addresses if ipaddress.ip_address(a).version == 4]
    if not ipv4: raise ValueError('ipv6_unverified')
    # ponytail: one deterministic IPv4, no retry/fallback until separately proven.
    address = ipv4[0]
    sock = socket_factory(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.settimeout(left(until))
        sock.connect((address,port))
        peer,peer_port = sock.getpeername()[:2]
        if peer != address or peer_port != port: raise ValueError('peer_mismatch')
        left(until)
        return sock,dict(host=host,port=port,resolved=list(addresses),selected_ip=address,
                         peer=peer,peer_port=peer_port,family='IPv4',decision='connected')
    except BaseException:
        sock.close()
        raise


def read_exact(sock, size, until):
    data = bytearray()
    while len(data) < size:
        sock.settimeout(left(until))
        part = sock.recv(size-len(data))
        if not part: raise ValueError('truncated_frame')
        data.extend(part)
    return bytes(data)


def request(sock, until):
    version,count = read_exact(sock,2,until)
    if version != 5 or count == 0: raise ValueError('socks_version')
    if 0 not in read_exact(sock,count,until): raise ValueError('socks_method')
    sock.sendall(b'\x05\x00')
    if read_exact(sock,4,until) != b'\x05\x01\x00\x03': raise ValueError('socks_request')
    length = read_exact(sock,1,until)[0]
    host = read_exact(sock,length,until).decode('ascii')
    port = int.from_bytes(read_exact(sock,2,until),'big')
    if host != HOST or port != 443: raise ValueError('origin_forbidden')
    return host,port


def transfer(client, upstream, until):
    reading = [client,upstream]
    counts = dict(client_to_upstream_bytes=0,upstream_to_client_bytes=0)
    while reading:
        ready,_,_ = select.select(reading,[],[],min(left(until),.2))
        for source in ready:
            target = upstream if source is client else client
            source.settimeout(left(until))
            chunk = source.recv(65536)
            if not chunk:
                reading.remove(source)
                target.shutdown(socket.SHUT_WR)
                continue
            if sum(counts.values())+len(chunk) > MAX_BYTES: raise ValueError('output_limit')
            target.settimeout(left(until))
            target.sendall(chunk)
            counts['client_to_upstream_bytes' if source is client else 'upstream_to_client_bytes'] += len(chunk)
    return dict(transferred_bytes=sum(counts.values()),**counts)


def serve(config, emit):
    """Emit metadata through a trusted durable writer; never record tunneled bytes."""
    keys = {'schema_version','operation_id','phase','nonce','deadline_ms','host','port',
            'listen_port','forbidden_ips','max_connections'}
    if (type(config) is not dict or set(config) != keys
            or type(config['schema_version']) is not int or config['schema_version'] != 1
            or config['host'] != HOST or type(config['port']) is not int or config['port'] != 443
            or type(config['max_connections']) is not int or config['max_connections'] != 1
            or type(config['listen_port']) is not int or not 0 <= config['listen_port'] <= 65535
            or type(config['deadline_ms']) is not int or not 0 < config['deadline_ms']-time.time()*1000 <= 120000
            or config['phase'] not in ('A','A2') or type(config['operation_id']) is not str
            or str(uuid.UUID(config['operation_id'])) != config['operation_id']
            or type(config['nonce']) is not str or not re.fullmatch('[0-9a-f]{32}',config['nonce'])
            or type(config['forbidden_ips']) is not list or len(config['forbidden_ips']) > 256
            or any(type(s) is not str or '%' in s for s in config['forbidden_ips'])):
        raise ValueError('invalid_config')
    forbidden = frozenset(str(ipaddress.ip_address(s)) for s in config['forbidden_ips'])
    until = time.monotonic()+(config['deadline_ms']-time.time()*1000)/1000
    listener = client = upstream = None
    def event(kind, **fields):
        emit(kind,operation_id=config['operation_id'],phase=config['phase'],nonce=config['nonce'],
             at_ms=int(time.time()*1000),**fields)
    try:
        listener = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        if os.name == 'nt': listener.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        else: listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('127.0.0.1',config['listen_port']));listener.listen(1)
        listener.settimeout(left(until))
        event('ready',port=listener.getsockname()[1],pid=os.getpid(),deadline_ms=config['deadline_ms'])
        client,_ = listener.accept()
        attempt_until = min(until,time.monotonic()+10)
        host,port = request(client,attempt_until)
        event('request',host=host,port=port)
        deadline = min(config['deadline_ms'],int(time.time()*1000+left(attempt_until)*1000))
        upstream,row = connect_checked(host,port,deadline,forbidden)
        event('destination',**row)
        client.settimeout(left(attempt_until))
        client.sendall(b'\x05\x00\x00\x01'+b'\x00'*6)
        counts = transfer(client,upstream,attempt_until)
        listener.setblocking(False)
        try:
            extra,_ = listener.accept();extra.close()
        except BlockingIOError:
            pass
        else:
            raise ValueError('extra_connection')
        event('finished',**counts)
        return 0
    except (ValueError,OSError) as error:
        reason = str(error) if type(error) is ValueError and str(error) in REFUSALS else type(error).__name__
        event('refused',reason=reason)
        return 125
    finally:
        for sock in (client,upstream,listener):
            if sock is not None: sock.close()
        event('closed')


if __name__ == '__main__':
    if sys.argv[1:] == ['--resolve',HOST]:
        rows = socket.getaddrinfo(HOST,443,socket.AF_UNSPEC,socket.SOCK_STREAM)
        values = list(dict.fromkeys(r[4][0] for r in rows))
        if not 1 <= len(values) <= 64 or any(len(value) > 128 for value in values):
            raise SystemExit(125)
        print(json.dumps(values))
    elif sys.argv[1:] == ['--guard']:
        config = json.loads(sys.stdin.buffer.readline(16385))
        def emit(kind, **row):
            print(json.dumps(dict(kind='egress',event=kind,**row)),flush=True)
            if json.loads(sys.stdin.buffer.readline(1025)) != dict(event=kind):
                raise ValueError('guard_ack_invalid')
        raise SystemExit(serve(config,emit))
    else:
        raise SystemExit('private guard or resolver invocation required')
