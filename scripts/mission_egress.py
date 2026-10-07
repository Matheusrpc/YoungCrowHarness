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
import sys
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
    import mission_process
    if host != HOST: raise ValueError('origin_forbidden')
    # Stdlib DNS can block; the existing process supervisor owns and bounds it.
    result = mission_process.supervise(dict(
        argv=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--resolve',HOST],
        cwd=str(Path(__file__).resolve().parent),stdin=b'',connection='native',
        timeout_seconds=min(timeout,5),output_limit_bytes=16384),
        on_started=lambda _:None,stop_requested=lambda:False)
    if not result['tree_reaped'] or result['reason'] != 'completed' or result['exit_code'] != 0:
        raise TimeoutError('resolver_incomplete')
    value = json.loads(result['stdout'])
    if type(value) is not list or not 1 <= len(value) <= 64 or any(type(v) is not str for v in value):
        raise ValueError('dns_invalid')
    return tuple(value)


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
    if sys.argv[1:] != ['--resolve',HOST]: raise SystemExit('resolver invocation required')
    rows = socket.getaddrinfo(HOST,443,socket.AF_UNSPEC,socket.SOCK_STREAM)
    print(json.dumps(list(dict.fromkeys(r[4][0] for r in rows))))
