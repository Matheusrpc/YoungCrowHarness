"""One MCP tool inside the networkless UID1000 worker. No host-side command parser."""
import json
import os
import selectors
import subprocess
import time

FRAME = 1024 * 1024
OUTPUT = 8 * FRAME
TOOL = dict(name='run', description='Run a shell command in the isolated, networkless workspace.',
            inputSchema=dict(type='object', properties=dict(command=dict(type='string', maxLength=65536)),
                             required=['command'], additionalProperties=False))


def run(command):
    process = subprocess.Popen(['/bin/sh', '-c', command], cwd=os.environ['HOME'], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    data = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic()+30
            while selector.get_map():
                if time.monotonic() >= deadline: raise ValueError('command_timeout')
                for key, _ in selector.select(.1):
                    chunk = os.read(key.fd, 65536)
                    if not chunk: selector.unregister(key.fileobj)
                    data.extend(chunk)
                    if len(data) > FRAME//2: raise ValueError('command_output_limit')
        code = process.wait(timeout=max(.01, deadline-time.monotonic()))
        return json.dumps(dict(exit_code=code, output=data.decode('utf-8', errors='replace')))
    finally:
        if process.poll() is None: process.kill()
        process.wait()
        process.stdout.close()


def serve(stdin, stdout):
    if os.getuid() != 1000: return 125
    seen, initialized, total, frames = set(), False, 0, 0
    while True:
        line = stdin.readline(FRAME+1)
        if not line: return 0
        frames += 1
        if len(line) > FRAME or frames > 1024: return 125
        try:
            request = json.loads(line)
            if type(request) is not dict or request.get('jsonrpc') != '2.0': return 125
            method, request_id = request.get('method'), request.get('id')
            if method == 'notifications/initialized' and 'id' not in request: continue
            if type(request_id) not in (str, int) or len(str(request_id)) > 128: return 125
            response = dict(jsonrpc='2.0', id=request_id)
            if request_id in seen or len(seen) >= 256:
                response['error'] = dict(code=-32600, message='Duplicate or excessive request ID')
            else:
                seen.add(request_id)
                params = request.get('params', {})
                if type(params) is not dict: raise ValueError('invalid_params')
                if method == 'initialize' and not initialized and params.get('protocolVersion') == '2025-06-18':
                    initialized = True
                    result = dict(protocolVersion='2025-06-18', capabilities=dict(tools={}),
                                  serverInfo=dict(name='youngcrow-worker', version='1'))
                elif initialized and method == 'ping': result = {}
                elif initialized and method == 'tools/list': result = dict(tools=[TOOL])
                elif initialized and method == 'tools/call':
                    arguments = params.get('arguments')
                    if (params.get('name') != 'run' or type(arguments) is not dict or set(arguments) != {'command'}
                            or type(arguments['command']) is not str or not 0 < len(arguments['command']) <= 65536
                            or '\0' in arguments['command']): raise ValueError('invalid_tool')
                    try:
                        result = dict(content=[dict(type='text', text=run(arguments['command']))], isError=False)
                    except (ValueError, OSError, subprocess.TimeoutExpired):
                        result = dict(content=[dict(type='text', text='Worker command failed or exceeded its limit')], isError=True)
                else: raise ValueError('unsupported_method')
                response['result'] = result
        except (ValueError, TypeError, RecursionError):
            return 125
        data = json.dumps(response).encode()+b'\n'
        total += len(data)
        if len(data) > FRAME or total > OUTPUT: return 125
        stdout.write(data);stdout.flush()


if __name__ == '__main__':
    import sys
    sys.exit(serve(sys.stdin.buffer, sys.stdout.buffer))
