"""`youngcrow init`: put the harness into a project and record what was written.

Everything is planned before the first write: every destination goes through `safe_target`,
every source and user file is read, every managed edit is computed. A refusal at that stage
leaves the project untouched. The manifest is saved last, so a project has one only when the
install finished.
"""
from dataclasses import asdict, dataclass, field
from importlib.resources import files
from pathlib import Path, PurePath
from typing import Callable
import os
import shutil
import stat

from youngcrow import __version__
from youngcrow.blocks import (
    GITIGNORE_END, GITIGNORE_START, IMPORT_LINE, MD_END, MD_START,
    ensure_line, remove_block, upsert_block,
)
from youngcrow.manifest import (
    MANIFEST_PATH, _REPARSE_POINT, Manifest, UnsafePathError, safe_target, save, sha256_file,
)
from youngcrow.payload import PAYLOAD, VAULT_TEMPLATES, payload_root

CLIENTS = ('claude', 'codex', 'both')
GITIGNORE_BODY = '\n'.join(('.env', '.env.*', '!.env.example', '.operacao-local/', 'vault/local/'))


class AlreadyInitialized(RuntimeError):
    """The project already has a manifest, or leftovers an earlier install did not finish."""


@dataclass
class Report:
    written: list[str] = field(default_factory=list)
    kept_modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class _Step:
    rel: str
    data: bytes
    created: bool = True    # the file did not exist before
    managed: bool = False   # it carries text the installer added: the import line or a block


def _check_options(client: str, lang: str, rigor: str) -> None:
    if client not in CLIENTS:
        raise ValueError(f'client {client!r} is not supported; use claude, codex or both.')
    if lang != 'en':
        raise ValueError(f"lang {lang!r} is not available yet; use 'en'.")
    if rigor != 'light':
        raise ValueError(f"rigor {rigor!r} is not available yet; use 'light'.")


def _harness_text(lang: str, rigor: str) -> str:
    raw = (files('youngcrow') / 'templates' / f'HARNESS.{lang}.{rigor}.md').read_bytes()
    return raw.decode('utf-8').replace('\r\n', '\n')


def _read(root: Path, rel: str) -> str | None:
    """Text of an existing project file, None when it is missing. Line endings stay as they are."""
    try:
        return safe_target(root, rel).read_bytes().decode('utf-8')
    except FileNotFoundError:
        return None
    except UnicodeDecodeError as error:
        raise ValueError(f'{rel} is not UTF-8 text; init does not edit it.') from error


def _add_block(body: str, start: str, end: str) -> Callable[[str], str]:
    """Adds the block, or returns the text as it is when markers are already there.

    A block found without a manifest is the user's, so init neither rewrites nor records it.
    Broken markers raise ManagedBlockError.
    """
    def add(text: str) -> str:
        has_block = remove_block(text, start, end) != text
        return text if has_block else upsert_block(text, body, start, end)
    return add


def _plan_managed(root: Path, rel: str, fresh: str, add: Callable[[str], str]) -> _Step | None:
    """The step that adds managed text to `rel`; None when `add` leaves the text unchanged."""
    old = _read(root, rel)
    new = add(fresh if old is None else old)
    if old is not None and new == old:
        return None
    return _Step(rel, new.encode('utf-8'), created=old is None, managed=True)


def _make_dirs(root: Path, parent: PurePath) -> None:
    """Create the missing directories one at a time; each must end up a real directory, not a link."""
    current = root
    for part in parent.parts:
        current = current / part
        try:
            os.mkdir(current)
        except FileExistsError:
            pass
        metadata = os.lstat(current)
        if not stat.S_ISDIR(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & _REPARSE_POINT:
            raise UnsafePathError('linked managed path: ' + current.relative_to(root).as_posix())


def _write(root: Path, step: _Step) -> None:
    """Write through a temp file and a rename, so a user's file is never left half written."""
    target = safe_target(root, step.rel)
    _make_dirs(root, PurePath(step.rel).parent)
    temp = target.with_name(f'{target.name}.{os.getpid()}.tmp')
    try:
        with open(temp, 'xb') as handle:
            handle.write(step.data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            shutil.copymode(target, temp)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def init(root: Path, *, client: str = 'both', lang: str = 'en', rigor: str = 'light') -> Report:
    """Install the harness into `root`.

    Copies the scripts into `.youngcrow/`, creates the vault indexes that are missing, links the
    rules into CLAUDE.md (import line) and AGENTS.md (block), adds the .gitignore block, and saves
    the manifest. Raises ValueError for an unsupported option, UnsafePathError for a linked or
    mistyped destination, ManagedBlockError for broken markers, AlreadyInitialized when the
    project has a manifest or install leftovers. None of these writes anything.
    """
    _check_options(client, lang, rigor)
    root = Path(root)
    if safe_target(root, MANIFEST_PATH).exists():
        raise AlreadyInitialized(f'{MANIFEST_PATH} already exists: this project is already set up.')

    harness = _harness_text(lang, rigor)
    source = payload_root()
    steps = [
        _Step('.youngcrow/VERSION', (__version__ + '\n').encode('utf-8')),
        _Step('.youngcrow/HARNESS.md', harness.encode('utf-8')),
        *(_Step(f'.youngcrow/{rel}', (source / rel).read_bytes()) for rel in PAYLOAD),
    ]
    for step in steps:
        if os.path.lexists(safe_target(root, step.rel)):
            raise AlreadyInitialized(
                f'{step.rel} exists but {MANIFEST_PATH} does not; remove it (or the whole .youngcrow '
                'folder) and run init again.')

    report = Report()
    for rel in VAULT_TEMPLATES:
        if os.path.lexists(safe_target(root, rel)):
            report.skipped.append(rel)
        else:
            steps.append(_Step(rel, (source / rel).read_bytes()))

    plans = []
    if client != 'codex':
        plans.append(('CLAUDE.md', '# Project rules\n', lambda text: ensure_line(text, IMPORT_LINE)))
    if client != 'claude':
        plans.append(('AGENTS.md', '', _add_block(harness, MD_START, MD_END)))
    plans.append(('.gitignore', '', _add_block(GITIGNORE_BODY, GITIGNORE_START, GITIGNORE_END)))
    for rel, fresh, add in plans:
        step = _plan_managed(root, rel, fresh, add)
        if step is None:
            report.skipped.append(rel)
        else:
            steps.append(step)

    for step in steps:
        _write(root, step)
        report.written.append(step.rel)
    save(root, Manifest(
        version=__version__, client=client, lang=lang, rigor=rigor,
        files={step.rel: sha256_file(root / step.rel) for step in steps},
        created=[step.rel for step in steps if step.created],
        edits=[step.rel for step in steps if step.managed],
    ))
    return report
