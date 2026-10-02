"""Local document commands. The harness itself needs only the standard library."""
import argparse
import hashlib
import json
import os
import math
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid

# Diagnostics must remain read-only even on a freshly installed consumer repo.
sys.dont_write_bytecode = True
from document_store import prepare_storage, safe_path
import document_store as store
import source_fetch

VERSION = '2.132.0'
BASE = '.operacao-local/docling'
WORKER = Path(__file__).with_name('docling_worker.py')
MEDIA_FORMATS = {'.wav': 'wav', '.mp3': 'mp3', '.m4a': 'mov', '.aac': 'aac', '.ogg': 'ogg',
                 '.flac': 'flac', '.mp4': 'mov', '.mov': 'mov', '.avi': 'avi', '.mkv': 'matroska', '.webm': 'matroska'}


def profile_base(root, profile='documents'):
    if profile not in ('documents', 'media'):
        raise ValueError('Unsupported profile.')
    return Path(root) / BASE / ('media' if profile == 'media' else '')


def executable_path(base):
    private_bin = (base.parent if base.name == 'media' else base) / 'bin'
    return str(private_bin.absolute()) + os.pathsep + os.environ.get('PATH', '')


def media_tools(env=None):
    found = {name: shutil.which(name, path=(env or os.environ).get('PATH', '')) for name in ('ffmpeg', 'ffprobe')}
    return found if all(found.values()) else {}


def probe_media(source, env):
    if source.stat().st_size > 500 * 1024 * 1024:
        raise ValueError('media_size_limit')
    tools = media_tools(env)
    if not tools:
        raise ValueError('ffmpeg_missing')
    demuxer = MEDIA_FORMATS.get(source.suffix.lower())
    if not demuxer:
        raise ValueError('unsupported_media_format')
    result = run_process([tools['ffprobe'], '-v', 'error', '-protocol_whitelist', 'file', '-f', demuxer,
                          '-i', 'file:' + str(source.absolute()), '-show_entries', 'format=duration:stream=codec_type',
                          '-of', 'json'], timeout=30, env=env)
    if result.returncode:
        raise ValueError('media_probe_failed')
    data = json.loads(result.stdout)
    duration = float(data.get('format', {}).get('duration', 'nan'))
    if not math.isfinite(duration) or duration <= 0 or duration > 3600:
        raise ValueError('media_duration_limit')
    kinds = {stream.get('codec_type') for stream in data.get('streams', [])}
    return dict(duration_seconds=duration, has_audio='audio' in kinds, has_video='video' in kinds)


def runtime_python(runtime):
    return Path(runtime) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def worker_environment(base, *, offline=True):
    base = Path(base).absolute()
    env = {k: v for k, v in os.environ.items()
           if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'PATHEXT')}
    env['PATH'] = executable_path(base)
    for folder in ('cache', 'temp', 'home'):
        safe_path(base, Path(folder) / '.probe')
        (base / folder).mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(base / 'home'), USERPROFILE=str(base / 'home'),
               LOCALAPPDATA=str(base / 'home'), APPDATA=str(base / 'home'),
               TEMP=str(base / 'temp'), TMP=str(base / 'temp'),
               PIP_CACHE_DIR=str(base / 'cache/pip'),
               HF_HOME=str(base / 'cache/huggingface'), TORCH_HOME=str(base / 'cache/torch'),
               XDG_CACHE_HOME=str(base / 'cache'), DOCLING_CACHE_DIR=str(base / 'cache/docling'),
               PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1',
               HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', PYTHONUTF8='1')
    if offline:
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    return env


def windows_job(process):
    """Own the suspended worker and descendants before allowing it to run."""
    import ctypes
    from ctypes import wintypes as w
    class Limits(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong), ('flags', w.DWORD),
                    ('min_working_set', ctypes.c_size_t), ('max_working_set', ctypes.c_size_t),
                    ('active_processes', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Limits), ('io', ctypes.c_ulonglong * 6),
                    ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                    ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes, kernel.CreateJobObjectW.restype = [ctypes.c_void_p, w.LPCWSTR], w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    close = lambda: kernel.CloseHandle(job)
    try:
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.AssignProcessToJobObject(job, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Popen closes the initial thread handle; resume the process only after
        # assignment. This avoids the race in assigning an already running worker.
        native = ctypes.WinDLL('ntdll')
        native.NtResumeProcess.argtypes, native.NtResumeProcess.restype = [w.HANDLE], w.LONG
        if native.NtResumeProcess(int(process._handle)) != 0:
            raise OSError('Cannot resume worker.')
        return close
    except BaseException:
        close()
        raise


def run_process(arguments, *, timeout, env):
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | 0x4} if os.name == 'nt' else {'start_new_session': True}
    with subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **options) as process:
        close_job = None
        try:
            if os.name == 'nt':
                try:
                    close_job = windows_job(process)
                except BaseException:
                    process.kill()
                    process.communicate()
                    raise
            stdout, stderr = process.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as interrupted:
            if os.name == 'nt':
                if close_job:
                    close_job()
                    close_job = None
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            if isinstance(interrupted, KeyboardInterrupt):
                raise
            raise subprocess.TimeoutExpired(['docling-worker'], timeout) from None
        finally:
            if close_job:
                close_job()
        return subprocess.CompletedProcess(['docling-worker'], process.returncode, stdout, stderr)


def failed(code, state='failed'):
    return dict(state=state, warnings=[code], coverage={}, note_path=None)


def run_worker(source, output, runtime, profile='documents'):
    """Only local paths cross the worker boundary; never relay its stderr."""
    source, output, runtime = Path(source), Path(output), Path(runtime)
    executable = runtime_python(runtime)
    if not executable.is_file():
        return failed('runtime_missing', 'pending')
    output.mkdir(parents=True, exist_ok=False)
    request = output / 'request.json'
    try:
        env = worker_environment(runtime.parent)
        media = probe_media(source, env) if profile == 'media' else None
        request.write_text(json.dumps(dict(source=str(source.absolute()), output=str(output.absolute()),
                                           models=str((runtime.parent / 'models').absolute()), profile=profile,
                                           media=media)), encoding='utf-8')
        result = run_process([str(executable), str(WORKER), 'convert', str(request)], timeout=1800,
                             env=env)
        if result.returncode:
            (output / 'error.log').write_bytes(result.stderr)
            return failed('conversion_failed')
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or data.get('state') not in ('ready', 'partial', 'failed', 'unsupported'):
            return failed('invalid_worker_result')
        for current, directories, files in os.walk(output, followlinks=False):
            relative = Path(current).relative_to(output)
            for directory in directories:
                safe_path(output, relative / directory / '.probe')
            for name in files:
                safe_path(output, relative / name)
        if data['state'] in ('ready', 'partial') and not all((output / p).is_file() for p in ('content.md', 'document.json')):
            return failed('invalid_worker_result')
        # Trust only the protocol generated by our worker, not diagnostic text.
        return {key: data[key] for key in ('state', 'warnings', 'coverage', 'converter') if key in data}
    except subprocess.TimeoutExpired:
        return failed('conversion_timeout')
    except ValueError as error:
        code = str(error)
        return failed(code if code in ('media_size_limit', 'media_duration_limit', 'media_probe_failed',
                                       'unsupported_media_format', 'ffmpeg_missing') else 'invalid_worker_result')
    except OSError:
        return failed('invalid_worker_result')
    finally:
        request.unlink(missing_ok=True)


def doctor(root, profile='documents'):
    base = profile_base(root, profile)
    relative_base = base.relative_to(root)
    executable = runtime_python(base / 'venv')
    if not executable.is_file():
        return failed('runtime_missing', 'pending')
    try:
        safe_path(Path(root), relative_base / 'venv/pyvenv.cfg')
        manifest = json.loads((base / 'environment.json').read_text(encoding='utf-8'))
        if manifest['docling'] != VERSION:
            return failed('runtime_version_mismatch')
        if not manifest['packages'].get('onnxruntime'):
            return failed('runtime_dependencies_missing', 'pending')
        if profile == 'media':
            if not manifest['packages'].get('openai-whisper'):
                return failed('runtime_dependencies_missing', 'pending')
            tools = media_tools({'PATH': executable_path(base)})
            if not tools:
                return failed('ffmpeg_missing', 'pending')
            if any(store.file_digest(Path(path)) != manifest.get('media_tools', {}).get(name, {}).get('sha256')
                   for name, path in tools.items()):
                return failed('ffmpeg_changed', 'pending')
        for item in manifest['models']:
            path = safe_path(Path(root), relative_base / 'models' / item['path'])
            if path.stat().st_size != item['size']:
                return failed('models_incomplete', 'pending')
        if not manifest['models']:
            return failed('models_incomplete', 'pending')
        result = subprocess.run([str(executable), str(WORKER), 'versions'],
                                capture_output=True, timeout=30)
        actual = json.loads(result.stdout)
        if result.returncode or actual['docling'] != VERSION or actual['packages'] != manifest['packages']:
            return failed('runtime_version_mismatch')
        return dict(state='ready', warnings=[], profile=manifest['profile'], docling=VERSION,
                    python=actual['python'], models=len(manifest['models']))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return failed('runtime_incomplete', 'pending')


def setup(root, profile='documents'):
    profile_base(root, profile)
    root = Path(root).resolve(strict=True)
    prepare_storage(root)
    with store.project_lock(root):
        return setup_runtime(root, profile)


def setup_runtime(root, profile):
    base = profile_base(root, profile)
    for relative in ('venv/pyvenv.cfg', 'models/.probe', 'cache/.probe', 'temp/.probe', 'home/.probe',
                     'environment.json', 'setup.log'):
        safe_path(root, base.relative_to(root) / relative)
    if (base / 'environment.json').exists():
        result = doctor(root, profile)
        if result['state'] != 'ready':
            raise ValueError('Existing runtime differs or is incomplete; inspect doctor before replacing it.')
        return result
    env = worker_environment(base, offline=False)
    tool_records = {}
    if profile == 'media':
        tools = media_tools(env)
        if not tools:
            return failed('ffmpeg_missing', 'pending')
        for name, path in tools.items():
            result = run_process([path, '-version'], timeout=30, env=env)
            if result.returncode:
                return failed('setup_failed')
            tool_records[name] = dict(sha256=store.file_digest(Path(path)),
                                      version=result.stdout.decode(errors='replace').splitlines()[0])
    executable = runtime_python(base / 'venv')
    commands = []
    installed = None
    packages = {}
    if executable.exists():
        probe = run_process([str(executable), str(WORKER), 'versions'], timeout=30, env=env)
        if probe.returncode:
            return failed('runtime_incomplete')
        existing = json.loads(probe.stdout)
        installed = existing['docling']
        packages = existing.get('packages', {})
        if installed not in (None, VERSION):
            return failed('runtime_version_mismatch')
    if not executable.exists():
        commands.append([sys.executable, '-m', 'venv', str(base / 'venv')])
    requirements = Path(__file__).resolve().parents[1] / 'requirements' / ('docling-media.txt' if profile == 'media' else 'docling.txt')
    if installed is None or not packages.get('onnxruntime') or (profile == 'media' and not packages.get('openai-whisper')):
        commands.append([str(executable), '-m', 'pip', 'install', '-r', str(requirements)])
    commands.append([str(executable), str(WORKER), 'prepare', str(base / 'models'), profile])
    for command in commands:
        result = run_process(command, timeout=1800, env=env)
        with (base / 'setup.log').open('ab') as log:
            log.write(result.stdout + result.stderr)
        if result.returncode:
            return failed('setup_failed')
    result = run_process([str(executable), str(WORKER), 'versions'], timeout=30, env=env)
    manifest = json.loads(result.stdout)
    if result.returncode or manifest['docling'] != VERSION:
        return failed('runtime_version_mismatch')
    manifest.update(profile=profile, models=[dict(path=p.relative_to(base / 'models').as_posix(), size=p.stat().st_size)
                                            for p in sorted((base / 'models').rglob('*')) if p.is_file()])
    if profile == 'media':
        manifest['media_tools'] = tool_records
    (base / 'environment.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return doctor(root, profile)


def converter_info(root, profile):
    manifest = safe_path(root, profile_base(root, profile).relative_to(root) / 'environment.json')
    return dict(package='docling', version=VERSION, profile=profile,
                models=['whisper-base-native'] if profile == 'media' else ['layout', 'tableformer', 'rapidocr-onnxruntime-latin'],
                options=dict(max_pages=500, max_bytes=(500 if profile == 'media' else 100) * 1024 * 1024, timeout=1800,
                             remote_fetch=False, local_fetch=False, device='cpu',
                             **(dict(max_duration=3600, max_frames=200, frame_interval=10, diarization=False) if profile == 'media' else {}),
                             adapter_sha256=store.file_digest(WORKER),
                             runtime_manifest_sha256=store.file_digest(manifest) if manifest.exists() else None))


def new_receipt(record, reason='conversion_not_started'):
    return dict(schema_version=1, project_id=record['project_id'], source_id=record['source_id'],
                revision=None, attempt_id=str(uuid.uuid4()), state='pending', note_path=None,
                converter=None, coverage={}, warnings=[reason], next_action='ingest_source')


def record_pending(root, reason):
    if reason not in ('source_unavailable', 'runtime_missing', 'unsupported_source', 'reference_needs_review'):
        raise ValueError('Unknown pending reason.')
    root = Path(root).resolve(strict=True)
    project = prepare_storage(root)
    with store.project_lock(root):
        record = store.source_record(root, project, None)
        receipt = new_receipt(record, reason)
        store.save_attempt(root, record, receipt)
        return receipt


def status(root, source_id=None):
    root = Path(root).resolve(strict=True)
    if source_id is not None:
        source_id = str(uuid.UUID(source_id))
    results = []
    for record in store.source_records(root):
        if source_id is not None and record['source_id'] != source_id:
            continue
        receipt = store.read_json(root, Path(BASE) / record['source_id'] / 'attempts' / (record['latest_attempt'] + '.json'))
        results.append(dict(source_id=record['source_id'], current_revision=record['current_revision'],
                            current_note=record['current_note'], latest_attempt=receipt))
    return results


def ingest(root, source, *, source_id=None, convert=run_worker):
    root = Path(root).resolve(strict=True)
    remote = isinstance(source, str) and '://' in source
    if remote:
        try:
            locator = source_fetch.locator(source)
        except ValueError:
            return record_pending(root, 'source_unavailable')
        origin_key = hashlib.sha256(source.encode()).hexdigest()
    else:
        source = Path(source).absolute()
        locator, origin_key = source.as_uri(), None
    project = prepare_storage(root)
    with store.project_lock(root):
        record = store.source_record(root, project, locator, source_id, origin_key=origin_key)
        receipt = new_receipt(record)
        store.save_attempt(root, record, receipt)
        attempt = Path(BASE) / record['source_id'] / 'attempts' / receipt['attempt_id']
        try:
            if remote:
                policy_path = safe_path(root, Path(BASE) / 'acquisition.json')
                policy = json.loads(policy_path.read_text(encoding='utf-8')) if policy_path.exists() else {}
                allowed = policy.get('allowed_private_hosts', [])
                if not isinstance(allowed, list) or any(not isinstance(host, str) or not host for host in allowed):
                    raise ValueError('Invalid acquisition policy.')
                destination = safe_path(root, attempt / 'download')
                destination.parent.mkdir(parents=True, exist_ok=True)
                acquired = source_fetch.fetch_source(source, destination, max_bytes=500 * 1024 * 1024,
                                                       allowed_private_hosts=tuple(allowed))
                if acquired['state'] != 'ready':
                    receipt.update(state=acquired['state'], warnings=acquired['warnings'], next_action='provide_direct_source')
                    return receipt
                source = Path(acquired['path'])
                extension = acquired['extension']
            else:
                extension = source.suffix.lower()
            if not source.is_file():
                receipt['warnings'] = ['source_unavailable']
                return receipt
            profile = 'media' if extension in MEDIA_FORMATS else 'documents'
            if profile == 'documents' and extension not in ('.html', '.htm', '.pdf', '.docx', '.png', '.jpg', '.jpeg'):
                receipt.update(state='unsupported', warnings=['unsupported_source'], next_action='provide_supported_source')
                return receipt
            if convert is run_worker:
                diagnostic = doctor(root, profile)
                if diagnostic['state'] != 'ready':
                    receipt.update(warnings=diagnostic['warnings'], next_action='setup_or_repair_runtime')
                    return receipt
            configuration = converter_info(root, profile)
            # A suffix-sensitive parser is part of the conversion configuration.
            configuration = {**configuration, 'input_format': {'.htm': '.html', '.jpeg': '.jpg'}.get(extension, extension)}
            snapshot = attempt / ('original' + extension)
            copied_hash = store.copy_source(root, source, snapshot, (500 if profile == 'media' else 100) * 1024 * 1024)
            payload = json.dumps(dict(bytes_sha256=copied_hash, converter=configuration), sort_keys=True, separators=(',', ':')).encode()
            revision = hashlib.sha256(payload).hexdigest()
            receipt.update(revision=revision, converter=configuration, state='running', warnings=[], next_action='wait_for_conversion')
            store.save_attempt(root, record, receipt)
            revision_base = Path(BASE) / record['source_id'] / revision
            original = safe_path(root, revision_base / ('original' + extension))
            original.parent.mkdir(parents=True, exist_ok=True)
            if original.exists():
                if store.file_digest(original) != copied_hash:
                    raise ValueError('Stored original changed; preserve it for inspection.')
                (root / snapshot).unlink()
            else:
                os.replace(root / snapshot, original)
            cache = Path(BASE) / 'extractions' / revision
            cache_manifest = Path(BASE) / 'extractions' / (revision + '.json')
            safe_path(root, cache / '.probe')
            if safe_path(root, cache_manifest).exists():
                cached = store.read_json(root, cache_manifest)
                if store.tree_digest(root / cache) != cached['digest']:
                    raise ValueError('Extraction cache changed; preserve it for inspection.')
                result, output = cached['result'], root / cache
            else:
                output = root / BASE / 'work' / receipt['attempt_id']
                safe_path(root, output.relative_to(root) / '.probe')
                result = convert(original, output, profile_base(root, profile) / 'venv', profile)
                if result.get('state') in ('ready', 'partial'):
                    store.normalize_assets(output)
                if result.get('state') == 'ready':
                    digest = store.tree_digest(output)
                    safe_path(root, cache / '.probe')
                    (root / cache).parent.mkdir(parents=True, exist_ok=True)
                    os.replace(output, root / cache)
                    output = root / cache
                    store.write_json(root, cache_manifest, dict(digest=digest, result=result))
            state = result.get('state', 'failed')
            if state not in ('ready', 'partial', 'failed', 'unsupported', 'pending'):
                state = 'failed'
            warnings = [code for code in result.get('warnings', []) if isinstance(code, str) and code.replace('_', '').isalnum()]
            receipt.update(state=state, warnings=warnings, coverage=result.get('coverage', {}),
                           next_action='review_extraction' if state == 'ready' else 'inspect_and_retry')
            if state in ('ready', 'partial'):
                if state == 'partial' and not warnings:
                    receipt['warnings'] = ['incomplete_conversion']
                receipt['note_path'] = store.persist_note(root, record, receipt, output)
                if state == 'ready' or record['current_revision'] is None:
                    record.update(current_revision=revision, current_note=receipt['note_path'])
            return receipt
        except KeyboardInterrupt:
            receipt.update(state='pending', warnings=['conversion_interrupted'], next_action='retry_same_source')
            raise
        except source_fetch.AcquisitionError as error:
            receipt.update(state='pending', warnings=[str(error)], next_action='provide_direct_source_or_retry')
            return receipt
        except (OSError, ValueError, KeyError, TypeError) as error:
            code = 'source_size_limit' if str(error) == 'source_size_limit' else 'ingestion_failed'
            receipt.update(state='failed', warnings=[code], next_action='inspect_and_retry')
            return receipt
        finally:
            store.save_attempt(root, record, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    install = sub.add_parser('setup')
    install.add_argument('--profile', choices=['documents', 'media'], default='documents')
    install.add_argument('--json', action='store_true')
    diagnostic = sub.add_parser('doctor')
    diagnostic.add_argument('--json', action='store_true')
    diagnostic.add_argument('--profile', choices=['documents', 'media'], default='documents')
    ingest_parser = sub.add_parser('ingest')
    ingest_parser.add_argument('source')
    ingest_parser.add_argument('--source-id')
    ingest_parser.add_argument('--json', action='store_true')
    status_parser = sub.add_parser('status')
    status_parser.add_argument('--source-id')
    status_parser.add_argument('--json', action='store_true')
    sub.add_parser('lock-status').add_argument('--json', action='store_true')
    recover = sub.add_parser('recover-lock')
    recover.add_argument('--token', required=True)
    recover.add_argument('--json', action='store_true')
    relation = sub.add_parser('relate')
    relation.add_argument('--source-id', required=True)
    relation.add_argument('--revision', required=True)
    relation.add_argument('--target-id', required=True)
    relation.add_argument('--relation', required=True, choices=['supports', 'complements', 'contradicts', 'supersedes', 'used-in'])
    relation.add_argument('--evidence', required=True)
    relation.add_argument('--json', action='store_true')
    review = sub.add_parser('prepare-review')
    review.add_argument('--source-id', required=True)
    review.add_argument('--revision', required=True)
    review.add_argument('--json', action='store_true')
    inspect = sub.add_parser('review-status')
    inspect.add_argument('--review-id', required=True)
    inspect.add_argument('--json', action='store_true')
    publish = sub.add_parser('promote')
    publish.add_argument('--review-id', required=True)
    publish.add_argument('--approved-digest', required=True)
    publish.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            print('Installing project-local Docling 2.132.0 with ' +
                  ('Whisper Base and media dependencies.' if args.profile == 'media' else 'layout, tables and Latin OCR models.'), file=sys.stderr)
            result = setup(args.root, args.profile)
        elif args.command == 'doctor':
            result = doctor(args.root, args.profile)
        elif args.command == 'ingest':
            result = ingest(args.root, args.source, source_id=args.source_id)
        elif args.command == 'lock-status':
            result = store.lock_status(args.root.resolve(strict=True))
        elif args.command == 'recover-lock':
            result = store.recover_lock(args.root.resolve(strict=True), args.token)
        elif args.command == 'relate':
            result = store.relate(args.root, args.source_id, args.revision, args.target_id, args.relation, args.evidence)
        elif args.command == 'prepare-review':
            result = store.prepare_review(args.root, args.source_id, args.revision)
        elif args.command == 'review-status':
            result = store.review_status(args.root, args.review_id)
        elif args.command == 'promote':
            result = store.promote(args.root, args.review_id, args.approved_digest)
        else:
            result = status(args.root, args.source_id)
    except (OSError, ValueError, subprocess.SubprocessError):
        result = failed('storage_or_runtime_check_failed')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if isinstance(result, list) or result.get('state') in (None, 'ready', 'locked', 'unlocked') else 1


if __name__ == '__main__':
    raise SystemExit(main())
