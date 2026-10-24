"""`youngcrow init`: put the harness into a project and record what was written.

Everything is planned before the first write: every destination goes through `safe_target`,
every source and user file is read, every managed edit is computed. A refusal at that stage
leaves the project untouched. If a write fails later, the files and folders this run created
are removed and the files it edited get their original bytes back. The manifest is saved last,
so a project has one only when the install finished.
"""
from dataclasses import asdict, dataclass, field
from importlib.resources import files
from pathlib import Path, PurePath
from typing import Callable
import hashlib
import os
import shutil

from youngcrow import __version__
from youngcrow.blocks import (
    GITIGNORE_END, GITIGNORE_START, IMPORT_LINE, MD_END, MD_START,
    ensure_line, remove_block, upsert_block,
)
from youngcrow.manifest import MANIFEST_PATH, Manifest, UnsafePathError, is_real_dir, safe_target, save
from youngcrow.payload import PAYLOAD, payload_root

CLIENTS = ('claude', 'codex', 'both')
GITIGNORE_BODY = '\n'.join(('.env', '.env.*', '!.env.example', '.operacao-local/', 'vault/local/'))
# Indexes created when missing, from the package templates of the same path.
VAULT_INDEXES = ('vault/index.md', 'vault/integrations/index.md', 'vault/capabilities/index.md')


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
    old: bytes | None = None  # bytes the file had before; None when it did not exist
    managed: bool = False     # it carries text the installer added: the import line or a block

    @property
    def created(self) -> bool:
        return self.old is None


def _check_options(client: str, lang: str, rigor: str) -> None:
    if client not in CLIENTS:
        raise ValueError(f'client {client!r} is not supported; use claude, codex or both.')
    if lang != 'en':
        raise ValueError(f"lang {lang!r} is not available yet; use 'en'.")
    if rigor != 'light':
        raise ValueError(f"rigor {rigor!r} is not available yet; use 'light'.")


def _template(*parts: str) -> str:
    """Text of a file under the package's `templates/` folder, with LF line endings."""
    raw = files('youngcrow').joinpath('templates', *parts).read_bytes()
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
    return _Step(rel, new.encode('utf-8'), None if old is None else old.encode('utf-8'), managed=True)


def _make_dirs(root: Path, parent: PurePath, made: list[Path]) -> None:
    """Create the missing directories one at a time, each checked as a real directory (no link).

    Every directory created is appended to `made` at once, so a failure still leaves the list true.
    """
    current = root
    for part in parent.parts:
        current = current / part
        try:
            os.mkdir(current)
            made.append(current)
        except FileExistsError:
            pass
        if not is_real_dir(current):
            raise UnsafePathError('linked managed path: ' + current.relative_to(root).as_posix())


def _replace_file(target: Path, data: bytes) -> None:
    """Write through a temp file and a rename, so a user's file is never left half written."""
    temp = target.with_name(f'{target.name}.{os.getpid()}.tmp')
    try:
        with open(temp, 'xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            shutil.copymode(target, temp)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _roll_back(root: Path, written: list[_Step], made: list[Path]) -> list[str]:
    """Undo this run's writes: delete what it created, restore what it edited, remove its folders.

    Returns what could not be undone. Folders are removed only when `is_real_dir` still says so
    and they are empty.
    """
    left = []
    for step in reversed(written):
        try:
            target = safe_target(root, step.rel)
            if step.old is None:
                target.unlink(missing_ok=True)
            else:
                _replace_file(target, step.old)
        except OSError as error:
            left.append(f'{step.rel} ({error})')
    for directory in reversed(made):
        try:
            if is_real_dir(directory):
                directory.rmdir()
        except OSError as error:
            left.append(f'{directory.relative_to(root).as_posix()}/ ({error})')
    return left


def init(root: Path, *, client: str = 'both', lang: str = 'en', rigor: str = 'light') -> Report:
    """Install the harness into `root`.

    Copies the scripts into `.youngcrow/`, creates the vault indexes that are missing, links the
    rules into CLAUDE.md (import line) and AGENTS.md (block), adds the .gitignore block, and saves
    the manifest. Raises ValueError for an unsupported option, UnsafePathError for a linked or
    mistyped destination, ManagedBlockError for broken markers, AlreadyInitialized when the
    project has a manifest or install leftovers. None of these writes anything. A write that fails
    is rolled back before the error is raised again.
    """
    _check_options(client, lang, rigor)
    root = Path(root)
    if safe_target(root, MANIFEST_PATH).exists():
        raise AlreadyInitialized(f'{MANIFEST_PATH} already exists: this project is already set up.')

    harness = _template(f'HARNESS.{lang}.{rigor}.md')
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
    for rel in VAULT_INDEXES:
        if os.path.lexists(safe_target(root, rel)):
            report.skipped.append(rel)
        else:
            steps.append(_Step(rel, _template(*rel.split('/')).encode('utf-8')))

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

    written: list[_Step] = []
    made: list[Path] = []
    try:
        for step in steps:
            target = safe_target(root, step.rel)
            _make_dirs(root, PurePath(step.rel).parent, made)
            _replace_file(target, step.data)
            written.append(step)
        save(root, Manifest(
            version=__version__, client=client, lang=lang, rigor=rigor,
            files={step.rel: hashlib.sha256(step.data).hexdigest() for step in steps},
            created=[step.rel for step in steps if step.created],
            edits=[step.rel for step in steps if step.managed],
        ))
    except BaseException as error:
        left = _roll_back(root, written, made)
        if left:
            error.add_note('Could not undo these changes: ' + '; '.join(left))
        raise
    report.written = [step.rel for step in steps]
    return report
