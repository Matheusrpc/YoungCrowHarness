"""One fixed, unpaid echo through guardian's loopback relay. No client credentials."""
import hashlib
import json
import re
import socket
import sys
import time

FIXTURE_ID = 'isolated-egress-v1'
HEADER_LIMIT = 16384
BODY_LIMIT = 65536


def initialize():
    return dict(schema_version=1, fixture_id=FIXTURE_ID, stage='initialize',
                network_requests=0, model_calls=0)


def request(nonce, phase, placeholder, deadline_ms):
    if (type(nonce) is not str or not re.fullmatch('[0-9a-f]{32}', nonce)
            or phase not in ('A', 'B', 'A2') or type(placeholder) is not str
            or not re.fullmatch('youngcrow-probe-[0-9a-f]{32}', placeholder)
            or type(deadline_ms) is not int or not 1000 < deadline_ms-time.time()*1000 <= 120000):
        raise ValueError('invalid_fixture_request')
    until = time.monotonic() + (deadline_ms/1000-time.time()) - 1
    def remaining():
        value = min(until-time.monotonic(), deadline_ms/1000-time.time()-1)
        if value <= 0:
            raise ValueError('fixture_deadline')
        return value
    target = '/get?youngcrow='+nonce+'-'+phase
    raw = bytearray()
    # The numeric loopback destination and relay route cannot be supplied by a caller.
    with socket.create_connection(('127.0.0.1', 62143), timeout=remaining()) as connection:
        connection.settimeout(remaining())
        connection.sendall(('GET '+target+' HTTP/1.1\r\nHost: 127.0.0.1:62143\r\n'
                            'Connection: close\r\n\r\n').encode('ascii'))
        # Do not half-close: guardian treats client EOF as cancellation.
        while True:
            connection.settimeout(remaining())
            chunk = connection.recv(4096)
            if not chunk:
                break
            raw.extend(chunk)
            split = raw.find(b'\r\n\r\n')
            if ((split < 0 and len(raw) > HEADER_LIMIT) or split > HEADER_LIMIT
                    or len(raw) > HEADER_LIMIT + BODY_LIMIT):
                raise ValueError('fixture_output_limit')
    remaining()
    header, separator, body = bytes(raw).partition(b'\r\n\r\n')
    # The trusted relay emits this closed framing, with EOF delimiting its body.
    if (not separator or header != b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close'
            or len(body) > BODY_LIMIT):
        raise ValueError('fixture_response_refused')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('fixture_response_refused')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('fixture_response_refused')
    try:
        value = json.loads(body, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('fixture_response_refused') from None
    headers = value.get('headers') if type(value) is dict else None
    if (type(headers) is not dict or
            [v for k, v in headers.items() if k.lower() == 'x-youngcrow-probe'] != [placeholder]
            or value.get('args') != {'youngcrow': nonce+'-'+phase}
            or value.get('url') != 'https://postman-echo.com'+target):
        raise ValueError('echo_mismatch')
    return dict(schema_version=1, fixture_id=FIXTURE_ID, stage='dispatch', nonce=nonce, phase=phase,
                http_status=200, echo_matches=True, response_sha256=hashlib.sha256(body).hexdigest(),
                network_requests=1, model_calls=0)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ['initialize']:
            result = initialize()
        elif len(args) == 5 and args[0] == 'request' and re.fullmatch('[0-9]{1,16}', args[4]):
            result = request(args[1], args[2], args[3], int(args[4]))
        else:
            raise ValueError('invalid_fixture_request')
        print(json.dumps(result, separators=(',', ':'), allow_nan=False), flush=True)
        return 0
    except (ValueError, OSError) as error:
        allowed = {'invalid_fixture_request', 'fixture_deadline', 'fixture_output_limit',
                   'fixture_response_refused', 'echo_mismatch'}
        reason = str(error) if type(error) is ValueError and str(error) in allowed else 'request_failed'
        print(json.dumps(dict(kind='fixture_refused', reason=reason)), flush=True)
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
