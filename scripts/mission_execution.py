"""Shared installation reservation. A dead process never releases a durable intent.

This module records ownership; it neither dispatches Docker nor certifies cleanup.
The fixed user scope deliberately serializes every local Docker Sandboxes install.
"""
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid

import adoption_fs as fs
from adoption import lock_guard, read_record
from document_store import safe_path
from mission_environment import _private as check_private, storage_error

RESERVATION_VERSION = 1
MAX_OPERATIONS = 1024
MAX_RECORD = 65536
MAX_LEDGER = 4*1024*1024
REQUEST_FIELDS = {'schema_version','operation_id','mission_id','project_id','project_sha256',
                  'manifest_sha256','baseline_sha256','executable_sha256','candidate_digest',
                  'authorization_sha256','deadline_ms'}
EFFECTS = {'configure_proxy','configure_exclusions','credential','policy','restart',
           'prepare','A','B','A2','restore','restart_restore'}


def user_storage():
    """Stable across GUI/SSH and environment overrides; no fallback to another lock."""
    if os.name == 'nt':
        from ctypes import wintypes
        class GUID(ctypes.Structure):
            _fields_ = [('data',ctypes.c_ubyte*16)]
        guid = GUID((ctypes.c_ubyte*16).from_buffer_copy(
            uuid.UUID('f1b32785-6fba-4fcf-9d55-7b8e7f157091').bytes_le))
        shell, ole = ctypes.WinDLL('shell32'), ctypes.WinDLL('ole32')
        shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID),wintypes.DWORD,wintypes.HANDLE,
                                              ctypes.POINTER(ctypes.c_void_p)]
        shell.SHGetKnownFolderPath.restype = ctypes.c_long
        ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        result = ctypes.c_void_p()
        try:
            if shell.SHGetKnownFolderPath(ctypes.byref(guid),0,None,ctypes.byref(result)) or not result:
                raise ValueError('execution_storage_unavailable')
            parent = Path(ctypes.wstring_at(result))
        finally:
            if result: ole.CoTaskMemFree(result)
    elif os.name == 'posix':
        import pwd
        parent = Path(pwd.getpwuid(os.getuid()).pw_dir)
    else:
        raise ValueError('execution_storage_unavailable')
    if not parent.is_absolute():
        raise ValueError('execution_storage_unavailable')
    # ponytail: one user-wide lock; split installs only after their isolation is proven.
    return fs.checked_path(parent/'YoungCrowExecution')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def identity(value):
    if type(value) is not str or str(uuid.UUID(value)) != value:
        raise ValueError('invalid_execution_reservation')
    return value


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value)


def validate_request(request):
    if (type(request) is not dict or set(request) != REQUEST_FIELDS
            or type(request['schema_version']) is not int or request['schema_version'] != 1
            or type(request['deadline_ms']) is not int
            or type(request['candidate_digest']) is not str
            or not re.fullmatch('sha256:[0-9a-f]{64}',request['candidate_digest'])
            or not all(digest(request[k]) for k in REQUEST_FIELDS if k.endswith('_sha256'))):
        raise ValueError('invalid_execution_reservation')
    for key in ('operation_id','mission_id','project_id'): identity(request[key])


class Registry:
    def __init__(self, base=None):
        # A base override is an internal fixture seam; the CLI has no store option.
        self.base = fs.checked_path(user_storage() if base is None else base)

    def check(self):
        try:
            fs.outside_git(self.base)
        except subprocess.TimeoutExpired as error:
            raise storage_error(error,'git_boundary') from None
        if self.base.exists(): check_private(self.base)

    def create_empty(self, name):
        path = safe_path(self.base,name)
        try:
            # POSIX protection inspects existing modes; create privately even under umask 022.
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
                fs.protect_for_storage(path)  # Only this newly created, still empty file.
                check_private(path)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            check_private(path)

    @contextmanager
    def locked(self):
        self.check()
        created = False
        if not self.base.exists():
            try:
                fs.private_dir(self.base)
                created = True
            except (FileExistsError, ValueError):
                if not self.base.is_dir(): raise
        self.check()
        self.create_empty('reclaim.lock')
        with lock_guard(self.base):
            if created and not (self.base/'registry.json').exists():
                if {p.name for p in self.base.iterdir()} != {'reclaim.lock'}:
                    raise ValueError('execution_reservation_invalid')
                self.persist([])
            check_private(self.base)
            yield

    def records(self):
        self.check()
        if not self.base.exists(): return []
        # An existing store with no ledger is interrupted/corrupt, never a first use.
        if {p.name for p in self.base.iterdir()} != {'registry.json','reclaim.lock'}:
            raise ValueError('execution_reservation_invalid')
        path = fs.checked_path(self.base/'registry.json')
        if path.stat().st_size > MAX_LEDGER: raise ValueError('execution_history_limit')
        try:
            rows = read_record(self.base,'registry.json')
        except (ValueError, RecursionError):
            raise ValueError('execution_reservation_invalid') from None
        self.validate_rows(rows)
        return rows

    def validate_rows(self, rows):
        if type(rows) is not list or len(rows) > MAX_OPERATIONS:
            raise ValueError('execution_reservation_invalid')
        for row in rows:
            if type(row) is not dict or type(row.get('request')) is not dict:
                raise ValueError('execution_reservation_invalid')
            self.validate_record(row,row['request'].get('operation_id'))
        if len({r['request']['operation_id'] for r in rows}) != len(rows):
            raise ValueError('execution_reservation_invalid')
        if sum(r['state'] != 'abandoned' for r in rows) > 1:
            raise ValueError('execution_reservation_invalid')

    def validate_record(self, record, operation_id):
        keys = {'request','state','revision','created_at','updated_at','intents'}
        if (type(record) is not dict or set(record) != keys or record['state'] not in ('reserved','consumed','abandoned')
                or type(record['revision']) is not int or record['revision'] < 1
                or type(record['intents']) is not list or len(record['intents']) > len(EFFECTS)
                or any(type(record[k]) is not str for k in ('created_at','updated_at'))):
            raise ValueError('execution_reservation_invalid')
        validate_request(record['request'])
        if len(fs.canonical(record)) > MAX_RECORD: raise ValueError('execution_record_limit')
        if record['request']['operation_id'] != operation_id: raise ValueError('execution_reservation_invalid')
        labels = []
        for intent in record['intents']:
            if (type(intent) is not dict or set(intent) != {'effect','before_sha256','after_sha256','at'}
                    or intent['effect'] not in EFFECTS or type(intent['at']) is not str
                    or not digest(intent['before_sha256']) or not digest(intent['after_sha256'])):
                raise ValueError('execution_reservation_invalid')
            labels.append(intent['effect'])
        if len(set(labels)) != len(labels) or bool(labels) != (record['state'] == 'consumed'):
            raise ValueError('execution_reservation_invalid')

    def save(self, record):
        identity(record['request']['operation_id'])
        record['revision'] += 1
        record['updated_at'] = stamp()
        self.validate_record(record,record['request']['operation_id'])
        rows = self.records()
        rows = [r for r in rows if r['request']['operation_id'] != record['request']['operation_id']]+[record]
        self.persist(rows)

    def persist(self, rows):
        self.validate_rows(rows)
        data = fs.canonical(dict(payload=rows,sha256=fs.tree_digest(rows)))
        if len(data) > MAX_LEDGER: raise ValueError('execution_history_limit')
        # Protect the new empty temp before bytes, never repair an existing receipt.
        from document_store import atomic_write
        parent_identity = fs.identity(self.base)
        def before_write(name):
            path=safe_path(self.base,name)
            entry = path.lstat()
            file_identity = fs.identity(path)
            if (path.parent != self.base or not stat.S_ISREG(entry.st_mode) or entry.st_size
                    or not re.fullmatch(r'\.yc-[A-Za-z0-9_-]+\.tmp',path.name)
                    or parent_identity is None or fs.identity(self.base) != parent_identity or file_identity is None):
                raise ValueError('execution_storage_unprotected')
            fs.protect_for_storage(path)
            check_private(path)
            if fs.identity(path) != file_identity or path.stat().st_size or fs.identity(self.base) != parent_identity:
                raise ValueError('execution_storage_unprotected')
        atomic_write(self.base,'registry.json',data,before_write)
        if os.name == 'posix':
            descriptor=os.open(self.base,os.O_RDONLY|os.O_DIRECTORY)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        check_private(self.base)

    def status(self):
        active=next((r for r in self.records() if r['state'] != 'abandoned'),None)
        return dict(state=active['state'] if active else 'available',
                    operation_id=active['request']['operation_id'] if active else None,
                    effects_allowed=False)

    def reserve(self, request):
        """deadline_ms bounds the whole transaction, including its initial cleanup.

        It never releases ownership. Late recovery requires a separate bounded
        observer/restorer and may not extend this transaction or replay its work.
        """
        validate_request(request)
        with self.locked():
            records=self.records()
            old=next((r for r in records if r['request']['operation_id']==request['operation_id']),None)
            if old:
                if old['request'] != request: raise ValueError('operation_conflict')
                return dict(new=False,record=old)
            if any(r['state'] != 'abandoned' for r in records): raise ValueError('execution_reserved')
            if len(records) >= MAX_OPERATIONS: raise ValueError('execution_history_limit')
            if not 0 < request['deadline_ms']-time.time()*1000 <= 600000: raise ValueError('execution_deadline')
            record=dict(request=request,state='reserved',revision=0,created_at=stamp(),updated_at=stamp(),intents=[])
            self.save(record)
            return dict(new=True,record=record)

    def intent(self, operation_id, effect, change):
        identity(operation_id)
        if (effect not in EFFECTS or type(change) is not dict or set(change) != {'before_sha256','after_sha256'}
                or not all(digest(v) for v in change.values())): raise ValueError('invalid_execution_intent')
        with self.locked():
            record=next((r for r in self.records() if r['request']['operation_id']==operation_id),None)
            if not record or record['state']=='abandoned': raise ValueError('execution_reservation_missing')
            if any(i['effect']==effect for i in record['intents']): raise ValueError('effect_consumed')
            if record['request']['deadline_ms'] <= time.time()*1000: raise ValueError('execution_deadline')
            record['intents'].append(dict(effect=effect,**change,at=stamp()))
            record['state']='consumed'
            self.save(record)
            return record

    def abandon_unused(self, operation_id, observe_baseline):
        """Internal read-only observer, never a caller-supplied approval/cleanup flag.

        Once an effect was intended, this narrow path cannot release the reservation.
        Native recovery must establish its own stop and restoration evidence.
        """
        identity(operation_id)
        with self.locked():
            record=next((r for r in self.records() if r['request']['operation_id']==operation_id),None)
            if not record: raise ValueError('execution_reservation_missing')
            if record['state']=='abandoned': return record
            if record['intents']: raise ValueError('execution_reconciliation_required')
            if observe_baseline() != record['request']['baseline_sha256']: raise ValueError('configuration_changed')
            record['state']='abandoned'
            self.save(record)
            return record


def status():
    try:
        return Registry().status()
    except (OSError, ValueError, TypeError, KeyError, RecursionError, subprocess.SubprocessError) as error:
        known = {'execution_reservation_invalid','execution_history_limit','execution_storage_unavailable',
                 'storage_in_git','git_boundary_unknown'}
        reason = str(error) if str(error) in known else storage_error(error,'existing_storage').diagnostic['reason']
        return dict(state='unknown',operation_id=None,effects_allowed=False,reason=reason,
                    guidance='Preserve the shared reservation ledger; inspect its storage and recorded operation before retrying. Do not delete receipts or repair existing permissions automatically.')
