"""The record of what the installer wrote, and the one check every write goes through.

`.youngcrow/manifest.json` lists each file the installer wrote with the SHA-256 it had then,
so `upgrade` and `undo` can tell a file that is still the installer's from one the user changed.
`safe_target` is the gate for every destination: call it for all of them before the first write.
"""
from dataclasses import dataclass, field
from pathlib import Path, PurePath
import hashlib
import json
import os
import stat

SCHEMA_VERSION = 1
MANIFEST_PATH = '.youngcrow/manifest.json'

# FILE_ATTRIBUTE_REPARSE_POINT works on Python 3.11 too (Path.is_junction is 3.12+).
_REPARSE_POINT = 0x400


class UnsafePathError(ValueError):
    """A destination that leaves the project, runs through a link, or has the wrong type."""


@dataclass
class Manifest:
    version: str
    client: str
    lang: str
    rigor: str
    files: dict[str, str]  # relative path -> SHA-256 of what was written
    created: list[str]     # files that did not exist before
    edits: list[str]       # files that received a line or a block
    # JSON file that received keys (.claude/settings.json) -> the [top, sub] pairs init added there (R49)
    json_edits: dict[str, list[list[str]]] = field(default_factory=dict)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _is_link(metadata: os.stat_result) -> bool:
    """A symbolic link or a Windows junction (reparse point)."""
    return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, 'st_file_attributes', 0) & _REPARSE_POINT)


def is_real_dir(path: Path) -> bool:
    """True when `path` is a directory itself: not a symbolic link, not a junction, not a file.

    A missing path gives False. Check this (it uses `lstat`) before creating something inside a
    directory or removing the directory.
    """
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISDIR(metadata.st_mode) and not _is_link(metadata)


def safe_target(root: Path, relative: str) -> Path:
    """`root / relative`, or UnsafePathError when writing there could land somewhere else.

    Refuses an absolute path, any `..`, a symbolic link or Windows junction on the way, and a
    path whose type is wrong (a file where a directory is needed, or the reverse). Components
    that do not exist yet are fine. Nothing is created.
    """
    path = PurePath(relative)
    if path.anchor or '..' in path.parts or not path.parts:
        raise UnsafePathError('path outside the project: ' + relative)
    current = root
    for i, part in enumerate(path.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if _is_link(metadata):
            raise UnsafePathError('linked managed path: ' + relative)
        if stat.S_ISDIR(metadata.st_mode) != (i < len(path.parts) - 1):
            raise UnsafePathError('wrong path type: ' + relative)
    return root / path


def load(root: Path) -> Manifest | None:
    """The saved manifest, None when there is none; ValueError when the file cannot be trusted."""
    path = safe_target(root, MANIFEST_PATH)
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ValueError(f'{MANIFEST_PATH} is not valid JSON: {error}') from error
    if not isinstance(data, dict):
        raise ValueError(f'{MANIFEST_PATH} must hold a JSON object.')
    if data.get('schema_version') != SCHEMA_VERSION:
        raise ValueError(f'{MANIFEST_PATH} has schema_version {data.get("schema_version")!r}; expected {SCHEMA_VERSION}.')
    data.setdefault('json_edits', {})  # manifests written before it existed have none
    try:
        manifest = Manifest(*(data[name] for name in Manifest.__dataclass_fields__))
    except KeyError as error:
        raise ValueError(f'{MANIFEST_PATH} lacks the field {error}.') from error
    texts = (manifest.version, manifest.client, manifest.lang, manifest.rigor)
    if not (all(isinstance(value, str) for value in texts)
            and isinstance(manifest.files, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in manifest.files.items())
            and all(isinstance(names, list) and all(isinstance(n, str) for n in names)
                    for names in (manifest.created, manifest.edits))
            and isinstance(manifest.json_edits, dict)
            and all(isinstance(rel, str) and isinstance(pairs, list)
                    and all(isinstance(pair, list) and len(pair) == 2 and all(isinstance(k, str) for k in pair)
                            for pair in pairs)
                    for rel, pairs in manifest.json_edits.items())):
        raise ValueError(f'{MANIFEST_PATH} has a field of the wrong type.')
    return manifest


def save(root: Path, manifest: Manifest) -> None:
    """Write the manifest atomically: a temp file next to it, flushed, then renamed over it."""
    target = safe_target(root, MANIFEST_PATH)
    target.parent.mkdir(exist_ok=True)
    data = {'schema_version': SCHEMA_VERSION, **vars(manifest)}
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    temp = target.with_name(f'{target.name}.{os.getpid()}.tmp')
    try:
        with open(temp, 'x', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
