"""Frozen pre-phase environment helper; host queries are supplied by the test."""
from datetime import datetime, timezone
from pathlib import Path
import os
import re
from mission_clients import hash_executable


def inspect_environment(root: Path, executable: Path) -> dict:
    root, executable = Path(root).resolve(strict=True), Path(executable).absolute()
    facts = _host_facts(root)
    gaps = []
    if str(facts['machine']).lower() not in ('amd64', 'x86_64'):
        gaps.append('unsupported_platform')
    if facts['system'] == 'Windows':
        build = facts['build']
        if not isinstance(build, str) or not build.isdecimal() or int(build) < 22000:
            gaps.append('unsupported_platform')
        if facts['whp_state'] != 1:
            gaps.append('whp_disabled' if facts['whp_state'] in (2, 3) else 'whp_unknown')
    elif facts['system'] == 'Linux':
        if facts['distribution'] != 'ubuntu:24.04':
            gaps.append('unsupported_platform')
        if facts['kvm_access'] is not True:
            gaps.append('kvm_unavailable')
    else:
        gaps.append('unsupported_platform')

    digest, version = None, None
    try:
        if not executable.exists():
            gaps.append('runtime_missing')
        else:
            digest = hash_executable(executable)
            if os.name == 'nt' and executable.suffix.lower() != '.exe':
                raise ValueError('invalid_executable')
    except (OSError, ValueError):
        gaps.append('runtime_invalid')
        digest = None
    if digest:
        try:
            output = _exchange(executable, ['version'], root)
            match = re.fullmatch(r'sbx version: v?(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?) [0-9a-f]{6,64}',
                                 output.strip()) if isinstance(output, str) and len(output) <= 256 else None
            if hash_executable(executable) != digest:
                gaps.append('stale_observation')
            elif match:
                version = match[1]
            else:
                gaps.append('runtime_metadata_invalid')
        except (OSError, ValueError, UnicodeError):
            gaps.append('runtime_metadata_failed')
    # No runtime profile is certified yet. Metadata alone never changes this gate.
    gaps.append('runtime_profile_unverified')
    return dict(schema_version=1, kind='sbx', executable=str(executable),
                executable_sha256=digest, version=version,
                platform={k: facts[k] for k in ('system', 'machine', 'build', 'distribution')},
                prerequisites={k: facts[k] for k in ('whp_state', 'kvm_access')},
                gaps=sorted(set(gaps)), profile_ids=[],
                checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
