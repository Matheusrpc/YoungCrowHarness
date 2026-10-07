"""Private host preference. Does not dispatch, authenticate or authorize execution."""
import sys
sys.dont_write_bytecode = True

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

import adoption_fs as fs
from adoption import lock_guard
from capabilities import parse_json
from document_store import atomic_write, safe_path

SELECTION_VERSION = 1
AREA = '.operacao-local/execution'
SELECTION = AREA + '/selection.json'
LIMIT = 64 * 1024
ERRORS = {'invalid_execution_selection', 'execution_selection_conflict', 'execution_location_conflict',
          'execution_selection_busy', 'execution_storage_unprotected'}


class StorageError(ValueError):
    """Public enums only; never expose native exceptions, paths or ACL identities."""
    def __init__(self, phase, reason):
        super().__init__('execution_storage_unprotected')
        phases = ('git_boundary', 'git_exclusion', 'existing_storage', 'storage_creation',
                  'evidence_destination', 'temporary_evidence')
        reasons = ('owner_mismatch', 'acl_not_private', 'acl_empty', 'acl_custom', 'acl_unexpected',
                   'unsupported_entry', 'unsupported_attributes', 'unsupported_volume', 'inventory_limit',
                   'git_query_failed', 'git_query_timeout', 'git_tracked', 'git_exclusion_missing',
                   'permission_query_timeout', 'inspection_failed')
        self.diagnostic = dict(phase=phase if phase in phases else 'existing_storage',
                               reason=reason if reason in reasons else 'inspection_failed')
        if reason == 'owner_mismatch':
            self.guidance = ('The file owner differs from the current user. Preserve existing evidence; '
                             'check the session default owner before retrying. Do not change existing ACLs automatically.')
        elif reason.startswith('git_'):
            self.guidance = ('Check Git access and the exclusion of .operacao-local/execution/, including '
                             'temporary files. Preserve evidence; do not force-add it to Git.')
        else:
            self.guidance = ('Check private storage permissions and the reported phase. Preserve existing '
                             'evidence; do not broaden access or repeat Docker proofs.')


def storage_error(error, phase):
    if isinstance(error, StorageError):
        return error
    if isinstance(error, subprocess.TimeoutExpired):
        reason = 'git_query_timeout' if phase.startswith('git_') else 'permission_query_timeout'
    else:
        reason = getattr(error, 'reason', str(error))
    return StorageError(phase, reason)


def _private(path):
    fs.checked_path(path)
    fs.inspect_permissions(path, role='snapshot')
    if os.name != 'nt':
        # snapshot inspection checks ownership/ACL support; selection also forbids group/other access.
        for item in (path, *path.rglob('*')) if path.is_dir() else (path,):
            if stat.S_IMODE(item.stat().st_mode) & 0o077:
                raise ValueError('execution_storage_unprotected')


def _git_boundary(root):
    detected = fs.git_read(root, 'rev-parse', '--show-toplevel')
    if detected.returncode:
        if b'not a git repository' not in detected.stderr.lower():
            raise StorageError('git_boundary', 'git_query_failed')
        return False
    tracked = fs.git_read(root, 'ls-files', '-z', '--', AREA)
    if tracked.returncode or tracked.stdout:
        raise StorageError('git_boundary', 'git_query_failed' if tracked.returncode else 'git_tracked')
    return True


def _storage(root):
    phase = 'git_boundary'
    try:
        ignore = fs.checked_path(safe_path(root, '.gitignore'))
        in_git = _git_boundary(root)
        phase = 'git_exclusion'
        if not in_git:
            if not ignore.exists() or ('/' + AREA + '/').encode() not in ignore.read_bytes().splitlines():
                raise StorageError(phase, 'git_exclusion_missing')
        else:
            for relative in (SELECTION, AREA + '/reclaim.lock', AREA + '/.youngcrow-ignore-check'):
                code = fs.git_read(root, 'check-ignore', '--quiet', '--', relative).returncode
                if code:
                    raise StorageError(phase, 'git_exclusion_missing' if code == 1 else 'git_query_failed')
        phase = 'existing_storage'
        directory = fs.checked_path(root / AREA)
        if directory.exists():
            _private(directory)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise storage_error(error, phase) from None


def read_selection(root: Path) -> dict:
    try:
        root = fs.checked_path(root)
        path = fs.checked_path(safe_path(root, SELECTION))
        default = dict(schema_version=1, location='local', origin='default', selected_at=None, digest=None)
        if not path.exists():
            if (root / AREA).exists():
                _storage(root)
            elif root.exists():
                try:
                    _git_boundary(root)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    raise storage_error(error, 'git_boundary') from None
            return default
        _storage(root)
        if path.stat().st_size > LIMIT:
            raise ValueError('invalid_execution_selection')
        with path.open('rb') as stream:
            data = stream.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('invalid_execution_selection')
        value = parse_json(data)
        if (not isinstance(value, dict) or set(value) != {'schema_version', 'location', 'selected_at'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1
                or value['location'] not in ('local', 'dedicated') or not isinstance(value['selected_at'], str)
                or 'T' not in value['selected_at']):
            raise ValueError('invalid_execution_selection')
        stamp = datetime.fromisoformat(value['selected_at'])
        if stamp.utcoffset() != timedelta(0):
            raise ValueError('invalid_execution_selection')
        return dict(value, origin='configured', digest=hashlib.sha256(data).hexdigest())
    except (ValueError, OSError, TypeError, KeyError) as error:
        if str(error) == 'execution_storage_unprotected':
            raise
        raise ValueError('invalid_execution_selection') from None


def configure_selection(root: Path, location: str, expected_digest: str | None) -> dict:
    if (location not in ('local', 'dedicated') or
            (expected_digest is not None and (not isinstance(expected_digest, str)
                                              or not re.fullmatch('[0-9a-f]{64}', expected_digest)))):
        raise ValueError('invalid_execution_selection')
    current = read_selection(root)
    if current['digest'] != expected_digest:
        raise ValueError('execution_selection_conflict')
    root = fs.checked_path(root)
    _storage(root)
    for relative in ('.operacao-local', AREA):
        directory = fs.checked_path(root / relative)
        if not directory.exists():
            try:
                if relative == AREA:
                    fs.private_dir(directory)
                else:
                    # Python 3.13+ treats Windows 0700 as a custom ACL. This parent stores no preference bytes.
                    directory.mkdir(mode=0o777 if os.name == 'nt' else 0o700)
            except (ValueError, FileExistsError):
                if not directory.exists():
                    raise
        if relative == AREA:
            _private(directory)
    try:
        with lock_guard(root / AREA):
            current = read_selection(root)
            if current['digest'] != expected_digest:
                raise ValueError('execution_selection_conflict')
            _storage(root)
            if current['origin'] == 'configured' and current['location'] == location:
                return current
            value = dict(schema_version=1, location=location, selected_at=datetime.now(timezone.utc).isoformat())
            atomic_write(root, SELECTION, json.dumps(value, indent=2) + '\n',
                         before_write=lambda relative: _private(root / relative))
            return read_selection(root)
    except ValueError as error:
        if str(error) == 'locked':
            raise ValueError('execution_selection_busy') from None
        raise


def setup_selection(root: Path, requested: str | None, *, apply: bool) -> dict:
    if requested is not None and requested not in ('local', 'dedicated'):
        raise ValueError('invalid_execution_selection')
    current = read_selection(root)
    if current['origin'] == 'configured':
        if requested is not None and current['location'] != requested:
            raise ValueError('execution_location_conflict')
        return current
    # Check existing storage before installation can overwrite its ignore rules.
    area = fs.checked_path(Path(root) / AREA)
    if area.exists():
        _storage(Path(root))
    if apply:
        return configure_selection(root, requested or 'local', None)
    return current


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('setup-check', 'setup-apply'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--location', choices=('local', 'dedicated'))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(setup_selection(args.root, args.location, apply=args.command == 'setup-apply')))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error) if str(error) in ERRORS else 'execution_storage_unprotected'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
