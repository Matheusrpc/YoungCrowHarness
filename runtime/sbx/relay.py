"""Trusted single-exchange HTTP relay. Never a general forward proxy.

Only guardian may construct the policy. This module neither authenticates a user
nor qualifies an execution profile. The post-Docker destination guard is separate.
"""
from dataclasses import dataclass
import http.client
import hashlib
import os
import re
import select
import socket
import ssl
import stat
import threading
import time

PORT = 62143
HEADER_LIMIT = 16384
REQUEST_LIMIT = 65536
RESPONSE_LIMIT = 8 * 1024 * 1024
WIRE_LIMIT = 2 * RESPONSE_LIMIT
SHUTDOWN_RESERVE = 1
CA_LIMIT = 1024 * 1024


class Refused(Exception):
    pass


@dataclass(frozen=True)
class Policy:
    host: str
    method: str
    target: str
    headers: tuple


def echo_policy(nonce, phase, placeholder):
    if (not re.fullmatch('[0-9a-f]{32}', nonce) or phase not in ('A', 'B', 'A2')
            or not re.fullmatch('youngcrow-probe-[0-9a-f]{32}', placeholder)):
        raise Refused('invalid_echo_policy')
    return Policy('postman-echo.com', 'GET', '/get?youngcrow='+nonce+'-'+phase,
                  (('X-Youngcrow-Probe', placeholder),))


def header_block(connection):
    raw = bytearray()
    while not raw.endswith(b'\r\n\r\n'):
        byte = connection.recv(1)
        if not byte:
            raise Refused('incomplete_headers')
        raw.extend(byte)
        if len(raw) > HEADER_LIMIT:
            raise Refused('header_limit')
    try:
        lines = bytes(raw).decode('ascii').split('\r\n')
    except UnicodeError:
        raise Refused('invalid_headers') from None
    fields = {}
    for line in lines[1:-2]:
        name, separator, value = line.partition(':')
        if (not separator or not re.fullmatch('[!#$%&\'*+.^_`|~0-9A-Za-z-]+', name)
                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise Refused('invalid_headers')
        name = name.lower()
        if name in fields:
            raise Refused('duplicate_header')
        fields[name] = value.strip()
    return lines[0], fields


def read_ca(path, digest, *, snapshot=True):
    """Read only root-controlled regular bytes; no trust-store fallback."""
    def check(info):
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                or info.st_mode & 0o022 or (snapshot and stat.S_IMODE(info.st_mode) != 0o600)):
            raise Refused('unprotected_ca')
    check(path.lstat())
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        check(os.fstat(stream.fileno()))
        raw = stream.read(CA_LIMIT+1)
    if not raw or len(raw) > CA_LIMIT or hashlib.sha256(raw).hexdigest() != digest:
        raise Refused('ca_changed')
    # Parse these same bytes, never reopen the path between hash and TLS use.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=raw.decode('ascii'))
    return raw, context


def open_upstream(proxy_ipv4, host, timeout, register, context):
    """One numeric proxy connection; fixed CONNECT authority and verified TLS/SNI."""
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    register(raw)
    raw.settimeout(timeout)
    raw.connect((proxy_ipv4, 3128))
    raw.sendall(f'CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n'.encode('ascii'))
    status, headers = header_block(raw)
    if (status != 'HTTP/1.1 200 OK' or headers.get('content-length', '0') != '0'
            or 'transfer-encoding' in headers):
        raise Refused('proxy_connect_refused')
    tls = context.wrap_socket(raw, server_hostname=host, do_handshake_on_connect=False)
    register(tls)
    tls.do_handshake()
    return tls


class LimitedReader:
    """Bound HTTPResponse's status, headers, chunk framing and body allocations."""
    def __init__(self, stream):
        self.stream, self.remaining = stream, HEADER_LIMIT

    def take(self, method, size=-1):
        size = self.remaining+1 if size < 0 else min(size, self.remaining+1)
        data = getattr(self.stream, method)(size)
        self.remaining -= len(data)
        if self.remaining < 0:
            raise Refused('upstream_wire_limit')
        return data

    def readline(self, size=-1): return self.take('readline', size)
    def read(self, size=-1): return self.take('read', size)
    def read1(self, size=-1): return self.take('read1', size)
    def flush(self): pass  # Read-only wrapper; HTTPResponse.close still calls flush.
    def close(self): self.stream.close()


class Relay:
    def __init__(self, *, deadline_ms, proxy_ipv4, policy, claim, context):
        remaining = deadline_ms/1000-time.time()-SHUTDOWN_RESERVE
        if not 0 < remaining <= 120-SHUTDOWN_RESERVE:
            raise Refused('invalid_deadline')
        self.deadline_ms, self.monotonic_deadline = deadline_ms, time.monotonic()+remaining
        self.proxy_ipv4, self.policy, self.claim = proxy_ipv4, policy, claim
        self.context = context
        self.lock = threading.Lock()
        self.halt, self.done, self.upstream_started = (threading.Event() for _ in range(3))
        self.sockets, self.threads, self.client = [], [], None
        self.watch_client = False
        self.state, self.reason, self.bytes_forwarded = 'idle', None, 0
        self.requests = 0
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.listener.set_inheritable(False)
            self.listener.bind(('127.0.0.1', PORT))
            self.listener.listen(1)
            self.listener.settimeout(self.remaining())
            self.port = self.listener.getsockname()[1]
            self.register(self.listener)
        except BaseException:
            self.listener.close()
            raise

    def remaining(self):
        value = min(self.deadline_ms/1000-time.time()-SHUTDOWN_RESERVE,
                    self.monotonic_deadline-time.monotonic())
        if value <= 0 or self.halt.is_set():
            raise Refused('deadline_or_cancelled')
        return value

    def register(self, connection):
        with self.lock:
            if self.halt.is_set():
                connection.close()
                raise Refused('cancelled')
            self.sockets.append(connection)
        connection.settimeout(self.remaining())

    def start(self):
        if self.threads or self.halt.is_set():
            raise Refused('relay_consumed')
        self.state = 'serving'
        # Guardian calls this only AFTER its last Popen, never before preexec_fn.
        try:
            for fn in (self.serve, self.watch):
                thread = threading.Thread(target=fn, daemon=True)
                thread.start()
                self.threads.append(thread)
        except (RuntimeError, OSError):
            self.stop()
            raise Refused('relay_start_failed') from None

    def abort(self, state, reason):
        with self.lock:
            if self.state in ('idle', 'serving'):
                self.state, self.reason = state, reason
            self.halt.set()
            sockets = list(self.sockets)
        for connection in sockets:
            try: connection.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            connection.close()

    def stop(self):
        self.abort('cancelled', 'coordinator_stopped')
        until = time.monotonic()+.5
        for thread in self.threads:
            thread.join(max(0, until-time.monotonic()))
        return not any(thread.is_alive() for thread in self.threads)

    def result(self):
        return dict(state=self.state, reason=self.reason, requests=self.requests,
                    bytes_forwarded=self.bytes_forwarded)

    def succeed(self):
        with self.lock:
            self.remaining()
            if self.state != 'serving':
                raise Refused('exchange_cancelled')
            self.state, self.reason = 'succeeded', None

    def body_parts(self, response, headers):
        """Strict framing: stdlib accepts missing chunk terminators and trailers."""
        stream = response.fp
        if headers.get('transfer-encoding', '').lower() == 'chunked':
            while True:
                self.remaining()
                line = stream.readline(32)
                if not re.fullmatch(b'[0-9a-fA-F]{1,8}\r\n', line):
                    raise Refused('upstream_chunk_framing')
                size = int(line[:-2], 16)
                if size == 0:
                    if stream.read(2) != b'\r\n':
                        raise Refused('upstream_chunk_framing')
                    return  # Trailers and chunk extensions are deliberately unsupported.
                if size > RESPONSE_LIMIT-self.bytes_forwarded:
                    raise Refused('response_body_limit')
                while size:
                    part = stream.read1(min(8192, size))
                    if not part:
                        raise Refused('upstream_incomplete')
                    size -= len(part)
                    yield part
                if stream.read(2) != b'\r\n':
                    raise Refused('upstream_chunk_framing')
        else:
            size = int(headers['content-length']) if 'content-length' in headers else None
            while size is None or size > 0:
                part = stream.read1(8192 if size is None else min(8192, size))
                if not part:
                    if size is not None and size > 0:
                        raise Refused('upstream_incomplete')
                    return
                if size is not None:
                    size -= len(part)
                yield part

    def watch(self):
        while not self.done.wait(.025):
            try:
                self.remaining()
                # No worker reads the client after the bounded request body. A new
                # byte is pipelining, EOF is cancellation; neither causes a retry.
                if self.watch_client and select.select([self.client], [], [], 0)[0]:
                    self.abort('cancelled', 'client_closed_or_pipelined')
                    return
            except Refused:
                self.abort('deadline', 'deadline')
                return
            except (OSError, ValueError):
                self.abort('cancelled', 'client_closed')
                return

    def request(self, client):
        start, headers = header_block(client)
        if start != f'{self.policy.method} {self.policy.target} HTTP/1.1':
            raise Refused('route_not_allowed')
        if headers.get('host') != '127.0.0.1:'+str(self.port):
            raise Refused('host_not_allowed')
        if any(k in headers for k in ('transfer-encoding', 'upgrade', 'expect', 'content-encoding')):
            raise Refused('unsupported_framing')
        if headers.get('connection', '').lower() not in ('', 'close', 'keep-alive'):
            raise Refused('unsupported_connection')
        size = headers.get('content-length', '0')
        if not re.fullmatch('[0-9]{1,6}', size) or int(size) > REQUEST_LIMIT:
            raise Refused('request_body_limit')
        if self.policy.method == 'GET' and int(size) != 0:
            raise Refused('unexpected_body')
        if self.policy.method == 'POST' and (not int(size) or headers.get('content-type') != 'application/json'):
            raise Refused('unsupported_body')
        body = bytearray()
        while len(body) < int(size):
            part = client.recv(min(8192, int(size)-len(body)))
            if not part:
                raise Refused('incomplete_body')
            body.extend(part)
        self.watch_client = True
        return bytes(body)

    def serve(self):
        response = None
        try:
            self.client, _ = self.listener.accept()
            self.register(self.client)
            self.listener.close()  # One connection, including a failed request.
            body = self.request(self.client)
            self.remaining()
            self.claim()  # Durable, consumed before the first upstream connection.
            self.requests = 1
            upstream = open_upstream(self.proxy_ipv4, self.policy.host, self.remaining(), self.register, self.context)
            self.upstream_started.set()
            fields = [('Host', self.policy.host), ('Connection', 'close'), ('Accept-Encoding', 'identity'),
                      ('Accept', 'application/json, text/event-stream'), ('Content-Length', str(len(body)))]
            if self.policy.method == 'POST': fields.append(('Content-Type', 'application/json'))
            fields.extend(self.policy.headers)
            header = self.policy.method+' '+self.policy.target+' HTTP/1.1\r\n'
            header += ''.join(key+': '+value+'\r\n' for key, value in fields)+'\r\n'
            upstream.sendall(header.encode('ascii')+body)
            response = http.client.HTTPResponse(upstream)
            response.fp = LimitedReader(response.fp)
            response.begin()
            pairs = response.getheaders()
            headers = {key.lower(): value for key, value in pairs}
            if (len(headers) != len(pairs) or response.status != 200
                    or ('content-length' in headers and 'transfer-encoding' in headers)
                    or headers.get('transfer-encoding', '').lower() not in ('', 'chunked')
                    or 'content-encoding' in headers or 'upgrade' in headers):
                raise Refused('upstream_response_refused')
            length = headers.get('content-length')
            if length is not None and (not re.fullmatch('[0-9]+', length) or int(length) > RESPONSE_LIMIT):
                raise Refused('response_body_limit')
            content_type = headers.get('content-type', '').split(';', 1)[0].strip().lower()
            if content_type not in ('application/json', 'text/event-stream'):
                raise Refused('upstream_content_type')
            response.fp.remaining = WIRE_LIMIT
            self.client.sendall(('HTTP/1.1 200 OK\r\nContent-Type: '+content_type+
                                 '\r\nConnection: close\r\n\r\n').encode('ascii'))
            for part in self.body_parts(response, headers):
                self.remaining()
                self.bytes_forwarded += len(part)
                if self.bytes_forwarded > RESPONSE_LIMIT:
                    raise Refused('response_body_limit')
                self.client.sendall(part)
            self.succeed()
        except (Refused, OSError, ValueError, http.client.HTTPException) as error:
            # No request, response, traceback or exception text leaves the relay.
            reason = str(error) if isinstance(error, Refused) else 'transport_failed'
            try:
                self.remaining()
            except Refused:
                self.abort('deadline', 'deadline')
            else:
                self.abort('refused', reason)
        except Exception:
            self.abort('refused', 'claim_or_internal_failure')
        finally:
            try:
                if response is not None: response.close()
            finally:
                self.done.set()
                self.abort('refused', 'unfinished_exchange')
