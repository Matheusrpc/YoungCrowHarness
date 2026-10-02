"""Bounded HTTP(S) acquisition. Docling receives the resulting local file only."""
import http.client
import ipaddress
from pathlib import Path
import queue
import re
import socket
import ssl
import threading
import time
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
import zipfile


class AcquisitionError(ValueError):
    """Safe public failure code; never includes the source URL."""


def parsed_url(url):
    if not isinstance(url, str) or len(url) > 16384 or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise AcquisitionError('invalid_source_url')
    try:
        parts = urlsplit(url)
        if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username is not None
                or parts.password is not None or '%' in parts.hostname or '\\' in parts.netloc):
            raise ValueError
        host = parts.hostname.encode('idna').decode('ascii').lower()
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, UnicodeError):
        raise AcquisitionError('invalid_source_url') from None
    return parts, host, port


def locator(url):
    parts, host, port = parsed_url(url)
    authority = f'[{host}]' if ':' in host else host
    if port != (443 if parts.scheme == 'https' else 80):
        authority += f':{port}'
    return urlunsplit((parts.scheme, authority, parts.path or '/', '', ''))


def addresses(host, port):
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        return list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))


def public_addresses(host, port):
    found = addresses(host, port)
    if not found:
        raise AcquisitionError('source_address_unavailable')
    for value in found:
        ip = ipaddress.ip_address(value)
        if isinstance(ip, ipaddress.IPv6Address):
            if (ip.ipv4_mapped or ip.sixtofour or ip.teredo
                    or ip in ipaddress.ip_network('64:ff9b::/96')
                    or ip in ipaddress.ip_network('64:ff9b:1::/48')):
                raise AcquisitionError('source_address_not_public')
        if not ip.is_global or ip.is_multicast or ip.is_reserved:
            raise AcquisitionError('source_address_not_public')
    return found


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise AcquisitionError('source_download_timeout')
    return seconds


def resolve(host, port, deadline, allowed):
    # A daemon bounds a stalled system resolver; it never opens a connection.
    result = queue.Queue(maxsize=1)
    def lookup():
        try:
            result.put((True, addresses(host, port) if host in allowed else public_addresses(host, port)))
        except (OSError, ValueError):
            result.put((False, None))
    threading.Thread(target=lookup, daemon=True).start()
    try:
        success, found = result.get(timeout=remaining(deadline))
    except queue.Empty:
        raise AcquisitionError('source_download_timeout') from None
    if not success or not found:
        raise AcquisitionError('source_address_not_allowed')
    return found


def disconnect(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def connect(host, port, approved, secure, deadline):
    for address in approved:
        sock = socket.socket(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(remaining(deadline))
            sock.connect((address, port))  # Numeric address: no second DNS resolution.
            if secure:
                sock.settimeout(remaining(deadline))
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            return sock
        except (OSError, ValueError):
            sock.close()
    raise AcquisitionError('source_connection_failed')


def observed_type(path):
    with path.open('rb') as source:
        prefix = source.read(1024 * 1024)
    if prefix.startswith(b'%PDF-'):
        return '.pdf'
    if prefix.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if prefix.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if prefix.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(path) as archive:
                if {'[Content_Types].xml', 'word/document.xml'} <= set(archive.namelist()):
                    return '.docx'
        except (OSError, zipfile.BadZipFile):
            pass
    if re.search(br'<(?:!doctype\s+html|html|head|body)(?:\s|>)', prefix.lower()):
        return '.html'
    return None


def fetch_source(url, destination, *, max_bytes, timeout_seconds=60, allowed_private_hosts=()):
    """Credentials stay in memory; failures expose codes, never access URLs."""
    original_locator = locator(url)
    destination = Path(destination)
    from document_store import safe_path
    safe_path(destination.parent, destination.name)
    if destination.exists() or max_bytes <= 0 or not 0 < timeout_seconds <= 60:
        raise AcquisitionError('invalid_download_destination_or_limit')
    deadline = time.monotonic() + timeout_seconds
    created = False
    try:
        for redirect in range(6):
            parts, host, port = parsed_url(url)
            approved = resolve(host, port, deadline, allowed_private_hosts)
            sock = connect(host, port, approved, parts.scheme == 'https', deadline)
            connection = http.client.HTTPConnection(host, port, timeout=remaining(deadline))
            connection.sock = sock
            # Socket timeouts alone allow a slow peer to drip headers forever.
            timer = threading.Timer(remaining(deadline), disconnect, args=(sock,))
            timer.daemon = True
            timer.start()
            try:
                target = quote(urlunsplit(('', '', parts.path or '/', parts.query, '')),
                               safe="/%?=&:+,;@!$'()*-._~[]")
                connection.request('GET', target, headers={'Accept-Encoding': 'identity', 'Connection': 'close'})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if redirect == 5 or not location:
                        raise AcquisitionError('source_redirect_limit')
                    next_url = urljoin(url, location)
                    next_parts, _, _ = parsed_url(next_url)
                    if parts.scheme == 'https' and next_parts.scheme != 'https':
                        raise AcquisitionError('source_insecure_redirect')
                    url = next_url
                    continue
                if response.status != 200:
                    raise AcquisitionError('source_http_error')
                lengths = response.headers.get_all('Content-Length', [])
                transfer = response.getheader('Transfer-Encoding')
                if (len(lengths) > 1 or (lengths and transfer)
                        or (transfer and transfer.lower() != 'chunked')
                        or response.getheader('Content-Encoding', 'identity').lower() != 'identity'):
                    raise AcquisitionError('source_ambiguous_encoding')
                length = int(lengths[0]) if lengths else None
                if length is not None and not 0 <= length <= max_bytes:
                    raise AcquisitionError('source_size_limit')
                total = 0
                with destination.open('xb') as output:
                    created = True
                    while not response.isclosed():
                        sock.settimeout(remaining(deadline))
                        chunk = response.read1(min(65536, max_bytes - total + 1))
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise AcquisitionError('source_size_limit')
                        output.write(chunk)
                remaining(deadline)
                if length is not None and total != length:
                    raise AcquisitionError('source_incomplete_download')
                extension = observed_type(destination)
                state, warnings = ('ready', []) if extension else ('unsupported', ['unsupported_source'])
                if extension == '.html':
                    with destination.open('rb') as source:
                        html = source.read(1024 * 1024).lower()
                    if (re.search(br'<(?:video|audio)(?:\s|>)|(?:og:video|og:audio)', html)
                            or host in ('youtu.be', 'youtube.com', 'www.youtube.com', 'vimeo.com', 'www.vimeo.com')):
                        state, warnings = 'pending', ['media_source_unavailable']
                return dict(path=str(destination), extension=extension, bytes=total, locator=original_locator,
                            state=state, warnings=warnings)
            finally:
                timer.cancel()
                connection.close()
                sock.close()
    except (OSError, ValueError, http.client.HTTPException, UnicodeError) as error:
        if created:
            destination.unlink(missing_ok=True)
        if isinstance(error, AcquisitionError):
            raise
        raise AcquisitionError('source_acquisition_failed') from None
