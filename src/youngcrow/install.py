"""`youngcrow init`, `upgrade` and `undo`: put the harness into a project, keep it current, take it out.

Each operation is planned before the first write: every path goes through `safe_target`, every
source and user file is read, every managed edit is computed. A refusal at that stage leaves the
project untouched. If a write fails later, the run is rolled back: files it created are removed,
files it edited or deleted get their original bytes back, and its folders are removed or put back.
The manifest is saved (or, by `undo`, deleted) last, so it always describes a finished operation.
"""
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path, PurePath
from typing import Callable, Sequence
from urllib.parse import unquote, urlsplit
import hashlib
import os
import posixpath
import re
import shutil
import stat

from youngcrow import __version__
from youngcrow.blocks import (
    GITIGNORE_END, GITIGNORE_START, IMPORT_LINE, MD_END, MD_START,
    ManagedBlockError, ensure_line, remove_block, remove_line, upsert_block,
)
from youngcrow.manifest import (
    MANIFEST_PATH, Manifest, UnsafePathError, is_real_dir, load, safe_target, save,
)
from youngcrow.payload import PAYLOAD, payload_root
from youngcrow.settings import (
    CLAUDE_MANUAL_STEP, CLAUDE_SETTINGS, CLAUDE_STEP, CODEX_AGENT, CODEX_STEP, HOOK_FILES, ORIGINALS, SettingsSkipped,
    add_wiring, added_pairs, codex_agent, remove_hooks, same_value, unwire,
)

CLIENTS = ('claude', 'codex', 'both')
GITIGNORE_BODY = '\n'.join(('.env', '.env.*', '!.env.example', '.operacao-local/', 'vault/local/'))
# Indexes created when missing, from the package templates of the same path. The first is the
# parent of the other two.
VAULT_INDEXES = ('vault/index.md', 'vault/integrations/index.md', 'vault/capabilities/index.md')
_INLINE_LINK = re.compile(r'\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^()\s]+)[^)]*\)')
# The markers of each file that gets a managed block; CLAUDE.md gets the import line instead.
_BLOCKS = {'AGENTS.md': (MD_START, MD_END), '.gitignore': (GITIGNORE_START, GITIGNORE_END)}


class AlreadyInitialized(RuntimeError):
    """The project already has a manifest, or leftovers an earlier install did not finish."""


class NotInitialized(RuntimeError):
    """The project has no manifest, so there is no install to upgrade or undo."""


@dataclass
class Report:
    written: list[str] = field(default_factory=list)
    kept_modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # for the person; not in `to_json`
    next_steps: list[str] = field(default_factory=list)  # what the person does after init, one client each
    hooks: dict[str, int] = field(default_factory=dict)  # entries `strip_hooks` took out, per file; not in `to_json`

    def to_json(self) -> dict:
        """The four lists `written`, `kept_modified`, `removed` and `skipped`, then `next_steps`."""
        return {name: getattr(self, name) for name in ('written', 'kept_modified', 'removed', 'skipped', 'next_steps')}


@dataclass
class _Step:
    rel: str
    data: bytes | None        # what to write; None deletes the file
    old: bytes | None = None  # bytes the file had before; None when it did not exist
    managed: bool = False     # it carries text the installer added: the import line or a block
    mode: int | None = None   # st_mode of a file the step deleted, put back by a roll back

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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(root: Path, rel: str) -> bytes | None:
    """Bytes of a project file, None when it is missing. The path goes through `safe_target`."""
    try:
        return safe_target(root, rel).read_bytes()
    except FileNotFoundError:
        return None


def _decode(rel: str, data: bytes) -> str:
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'{rel} is not UTF-8 text; youngcrow does not edit it.') from error


def _read(root: Path, rel: str) -> str | None:
    """Text of an existing project file, None when it is missing. Line endings stay as they are."""
    data = _read_bytes(root, rel)
    return None if data is None else _decode(rel, data)


def _managed(rel: str, edit: Callable[[str], str], text: str) -> str:
    """`edit(text)`, with a ManagedBlockError that names the file."""
    try:
        return edit(text)
    except ManagedBlockError as error:
        raise ManagedBlockError(f'{rel}: {error}') from error


def _put_block(rel: str, text: str, body: str) -> str:
    """The text of `rel` with `body` in its managed block (appended when there is none)."""
    start, end = _BLOCKS[rel]
    return _managed(rel, lambda t: upsert_block(t, body, start, end), text)


def _owns_block(rel: str, text: str, body: str | None, whole: bool) -> bool:
    """Whether the block in `rel` is still the installer's (R21): its body is `body`, the text the
    installer wrote there, or the whole file still has the hash in the manifest (`whole`)."""
    return whole or (body is not None and _put_block(rel, text, body) == text)


def _strip(rel: str, text: str, body: str | None, whole: bool) -> str | None:
    """The text of `rel` without the managed text init put there.

    None when the block is no longer the installer's (see `_owns_block`): the user typed inside
    the markers, so the file is left as it is (R20). A broken block raises.
    """
    if rel == 'CLAUDE.md':
        return _managed(rel, lambda t: remove_line(t, IMPORT_LINE), text)
    start, end = _BLOCKS[rel]
    stripped = _managed(rel, lambda t: remove_block(t, start, end), text)
    if stripped != text and not _owns_block(rel, text, body, whole):
        return None
    return stripped


def _installed_harness(root: Path, manifest: Manifest) -> str | None:
    """The HARNESS text init or upgrade put in the AGENTS.md block, when it can still be known:
    `.youngcrow/HARNESS.md` as long as its hash matches the manifest. None otherwise."""
    rel = '.youngcrow/HARNESS.md'
    data = _read_bytes(root, rel)
    if data is None or _sha(data) != manifest.files.get(rel):
        return None
    return _decode(rel, data)


def _refuse_leftover(root: Path, rel: str) -> None:
    """AlreadyInitialized when a `.youngcrow/` file init is about to write is there without a manifest."""
    if os.path.lexists(safe_target(root, rel)):
        raise AlreadyInitialized(
            f'{rel} exists but {MANIFEST_PATH} does not; remove it (or the whole .youngcrow '
            'folder) and run init again.')


def _load(root: Path) -> Manifest:
    manifest = load(root)
    if manifest is None:
        raise NotInitialized(f'{MANIFEST_PATH} not found: this project was not set up by youngcrow init.')
    return manifest


def _harness_files(harness: str) -> dict[str, bytes]:
    """The `.youngcrow/` files this package installs: VERSION, HARNESS.md, the catalog and the payload."""
    source = payload_root()
    return {
        '.youngcrow/VERSION': (__version__ + '\n').encode('utf-8'),
        '.youngcrow/HARNESS.md': harness.encode('utf-8'),
        '.youngcrow/capabilities.json': _template('capabilities.json').encode('utf-8'),
        **{f'.youngcrow/{rel}': (source / rel).read_bytes() for rel in PAYLOAD},
    }


def _prose(text: str) -> str:
    """The text without HTML comments, fenced code and inline code, where a link is not a link."""
    kept, fence = [], None
    for line in re.sub(r'<!--.*?-->', '', text, flags=re.S).splitlines():
        match = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
        elif match:
            fence = match[1]
        else:
            kept.append(line)
    return re.sub(r'(`+).*?\1', '', '\n'.join(kept), flags=re.S)


def _links_to(root: Path, note: str, target: str) -> bool:
    """Whether the existing Markdown `note` has an inline link that resolves to `target`.

    Both are project-relative. Only inline links count; a reference-style or wiki link reads as no
    link, which errs towards creating less. The note is only read, never edited, and bytes that
    are not UTF-8 do not stop the read.
    """
    text = safe_target(root, note).read_bytes().decode('utf-8', errors='replace')
    for match in _INLINE_LINK.finditer(_prose(text)):
        parts = urlsplit(match[1].strip('<>'))
        if not parts.scheme and posixpath.normpath(
                posixpath.join(posixpath.dirname(note), unquote(parts.path))) == target:
            return True
    return False


def _add_block(body: str, start: str, end: str) -> Callable[[str], str]:
    """Adds the block, or returns the text as it is when markers are already there.

    A block found without a manifest is the user's, so init neither rewrites nor records it.
    Broken markers raise ManagedBlockError.
    """
    def add(text: str) -> str:
        has_block = remove_block(text, start, end) != text
        return text if has_block else upsert_block(text, body, start, end)
    return add


def _plan_managed(root: Path, rel: str, fresh: str, add: Callable[[str], str],
                  gone: frozenset[str] = frozenset()) -> _Step | None:
    """The step that adds managed text to `rel`; None when `add` leaves the text unchanged.

    A file in `gone` is about to be removed by the same run, so it counts as missing.
    """
    old = None if rel in gone else _read(root, rel)
    new = _managed(rel, add, fresh if old is None else old)
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
    """Write through a temp file and a rename, so a user's file is never left half written.

    The temp file is created exclusively; when its name is already taken, the write fails and the
    file that holds the name is left alone.
    """
    temp = target.with_name(f'{target.name}.{os.getpid()}.tmp')
    handle = open(temp, 'xb')
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            shutil.copymode(target, temp)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _roll_back(root: Path, written: list[_Step], made: list[Path], removed: list[Path] = ()) -> list[str]:
    """Undo this run's changes: put back the folders it removed, delete what it created, restore
    what it edited or deleted (bytes and permission bits), remove the folders it made.

    Returns what could not be undone. Folders are removed only when `is_real_dir` still says so
    and they are empty.
    """
    left = []
    for directory in reversed(removed):
        try:
            os.mkdir(directory)
        except FileExistsError:
            pass
        except OSError as error:
            left.append(f'{directory.relative_to(root).as_posix()}/ ({error})')
    for step in reversed(written):
        try:
            target = safe_target(root, step.rel)
            if step.old is None:
                target.unlink(missing_ok=True)
            else:
                _replace_file(target, step.old)
                if step.mode is not None:
                    os.chmod(target, stat.S_IMODE(step.mode))
        except OSError as error:
            left.append(f'{step.rel} ({error})')
    for directory in reversed(made):
        try:
            if is_real_dir(directory):
                directory.rmdir()
        except OSError as error:
            left.append(f'{directory.relative_to(root).as_posix()}/ ({error})')
    return left


def _apply(root: Path, steps: list[_Step], *, manifest: Manifest | None = None,
           dirs: list[Path] = ()) -> None:
    """Carry out the steps in order, then remove the empty `dirs`, then save `manifest`.

    All or nothing: when anything fails, what was already done is rolled back and the error is
    raised again, with a note naming whatever the roll back could not restore.
    """
    written: list[_Step] = []
    made: list[Path] = []
    removed: list[Path] = []
    try:
        for step in steps:
            target = safe_target(root, step.rel)
            if step.data is None:
                step.mode = target.lstat().st_mode
                target.unlink()
            else:
                _make_dirs(root, PurePath(step.rel).parent, made)
                _replace_file(target, step.data)
            written.append(step)
        for directory in dirs:
            if not is_real_dir(directory):
                raise UnsafePathError('linked managed path: ' + directory.relative_to(root).as_posix())
            directory.rmdir()
            removed.append(directory)
        if manifest is not None:
            save(root, manifest)
    except BaseException as error:
        left = _roll_back(root, written, made, removed)
        if left:
            error.add_note('Could not undo these changes: ' + '; '.join(left))
        raise


def _plan_hooks(root: Path, published: Sequence[dict], gone: frozenset[str], report: Report) -> list[_Step]:
    """The steps that take the old setup.sh hook entries out of the hook files (R41, R43).

    In each of HOOK_FILES that is there and not in `gone`, the entries equal to one in `published`
    come out (`settings.remove_hooks`), and how many goes into `report.hooks`. A look-alike entry
    stays and gets a line in `warnings`, as does a file that is not a JSON object in UTF-8, which is
    left as it is. So is a link (or a path behind one), a folder or any other file that is not a
    regular one, and a file that cannot be read (R51): migrate never reads those (R9), and its scan
    does not count them either.
    """
    steps = []
    for rel in HOOK_FILES if published else ():
        if rel in gone:
            continue
        try:
            target = safe_target(root, rel)
            if not stat.S_ISREG(target.lstat().st_mode):
                raise UnsafePathError('not a regular file: ' + rel)
            old = target.read_bytes()
        except FileNotFoundError:
            continue
        except (UnsafePathError, OSError):
            report.warnings.append(f'{rel} is a link (or unreadable), so youngcrow did not look for the old hook in it.')
            continue
        try:
            new, count, kept = remove_hooks(old, published)
        except SettingsSkipped as error:
            report.warnings.append(f'{rel}: {error}, so youngcrow could not look for the old setup.sh hook in it.')
            continue
        report.warnings += [f'{rel}: youngcrow kept a {event} hook that is the old setup.sh one with an edit. It runs '
                            'scripts/source_prompt.py and fails once that file is gone; remove it by hand.'
                            for event in kept]
        if count:
            steps.append(_Step(rel, new, old))
            report.hooks[rel] = count
    return steps


def _plan_clients(root: Path, client: str, gone: frozenset[str], report: Report,
                  cleaned: dict[str, bytes]) -> list[_Step]:
    """The steps that wire the clients (R36); each client's next step goes into `report`.

    Claude (`claude`, `both`): `add_wiring` on `.claude/settings.json`. A file that was there is
    saved first under `.youngcrow/originals/` (R37). One that already has the wiring is `skipped`;
    one `add_wiring` refuses is left alone too, with the reason in `warnings` and the manual install
    as the next step. Codex (`codex`, `both`): the agent file is written when it is missing, else
    `skipped`. A file in `gone` is about to be removed by the same run, so it counts as missing; one
    in `cleaned` is read as the same run leaves it before the wiring (the old hooks out).
    """
    steps = []
    if client != 'codex':
        if CLAUDE_SETTINGS in gone:
            old = None
        elif CLAUDE_SETTINGS in cleaned:
            old = cleaned[CLAUDE_SETTINGS]
        else:
            old = _read_bytes(root, CLAUDE_SETTINGS)
        try:
            new = add_wiring(old)
        except SettingsSkipped as error:
            report.skipped.append(CLAUDE_SETTINGS)
            report.warnings.append(f'{CLAUDE_SETTINGS}: {error}, so youngcrow left it as it is.')
            report.next_steps.append(CLAUDE_MANUAL_STEP)
        else:
            if new is None:
                report.skipped.append(CLAUDE_SETTINGS)
            else:
                if old is not None:
                    _refuse_leftover(root, ORIGINALS + CLAUDE_SETTINGS)
                    steps.append(_Step(ORIGINALS + CLAUDE_SETTINGS, old))
                steps.append(_Step(CLAUDE_SETTINGS, new, old))
            report.next_steps.append(CLAUDE_STEP)
    if client != 'claude':
        if CODEX_AGENT not in gone and os.path.lexists(safe_target(root, CODEX_AGENT)):
            report.skipped.append(CODEX_AGENT)
        else:
            steps.append(_Step(CODEX_AGENT, codex_agent()))
        report.next_steps.append(CODEX_STEP)
    return steps


def _original(root: Path, manifest: Manifest, rel: str) -> bytes | None:
    """The bytes `rel` had before init, from `.youngcrow/originals/`; None when that copy is gone or changed."""
    saved = ORIGINALS + rel
    data = _read_bytes(root, saved)
    return data if data is not None and _sha(data) == manifest.files.get(saved) else None


def _only_relaid(root: Path, manifest: Manifest, rel: str, current: bytes, created: bool) -> bool:
    """Whether the settings file `rel` holds the value of the bytes init wrote, only laid out anew (R52).

    `claude plugin install --scope project` writes the file back with the keys in another order and LF line
    endings. The bytes init wrote are recomputed with `add_wiring` from the saved original (from nothing for a
    file init created) and trusted only when their hash is the one the manifest recorded; a saved original that
    is gone or changed means the answer is no.
    """
    original = None
    if not created:
        original = _original(root, manifest, rel)
        if original is None:
            return False
    try:
        wrote = add_wiring(original)
    except SettingsSkipped:
        return False
    return wrote is not None and _sha(wrote) == manifest.files.get(rel) and same_value(current, wrote)


def init(root: Path, *, client: str = 'both', lang: str = 'en', rigor: str = 'light',
         remove: Sequence[str] = (), strip_hooks: tuple[dict, ...] = ()) -> Report:
    """Install the harness into `root`.

    Copies the scripts and the capability catalog into `.youngcrow/`, creates the vault indexes that
    are missing (a sub-index only when this run creates `vault/index.md` or the existing one already
    links to it), links the rules into CLAUDE.md (import line) and AGENTS.md (block), adds the
    .gitignore block, wires the clients (see `_plan_clients`: the plugin in `.claude/settings.json`,
    the Codex agent, one entry per client in `Report.next_steps`), and saves the manifest. A settings
    file it edits goes into `json_edits` with the keys it added (R49), and the bytes it had are saved
    in `.youngcrow/originals/`.
    Raises ValueError for an unsupported option, UnsafePathError for a linked or mistyped
    destination, ManagedBlockError for broken markers, AlreadyInitialized when the project has a
    manifest or install leftovers. None of these writes anything. A write that fails is rolled back
    before the error is raised again.

    `remove` lists project files to delete in the same run, before the install (`migrate` passes
    the copies an older `setup.sh` made). Each name must be a canonical relative path with `/`
    (no `./`, `//`, trailing `/`; else ValueError); a repeated name counts once and a name that is
    not there is skipped. One under `.youngcrow/` or `vault/`, in any letter case, is a ValueError.
    Each goes through `safe_target` and is read before the first write. A file it removes that init also writes (CLAUDE.md, AGENTS.md) is created anew,
    not edited. The files go into `Report.removed`, followed by the folders they leave empty (R18,
    with a trailing `/`); a failed run puts them all back.

    `strip_hooks` lists hook entries to take out of `.claude/settings.json` and `.codex/hooks.json`
    first (`migrate` passes the ones setup.sh published, R41); see `_plan_hooks`. Only that change is
    made to `.codex/hooks.json`, which goes into `Report.written` but not into the manifest, so `undo`
    leaves it. In `.claude/settings.json` the wiring comes after, so the bytes saved in
    `.youngcrow/originals/` are the file without those entries. `Report.hooks` counts them per file.
    """
    _check_options(client, lang, rigor)
    root = Path(root)
    if safe_target(root, MANIFEST_PATH).exists():
        raise AlreadyInitialized(f'{MANIFEST_PATH} already exists: this project is already set up.')

    harness = _template(f'HARNESS.{lang}.{rigor}.md')
    steps = [_Step(rel, data) for rel, data in _harness_files(harness).items()]
    for step in steps:
        _refuse_leftover(root, step.rel)

    drops = []
    for rel in dict.fromkeys(remove):
        canonical = PurePath(rel).as_posix()
        if canonical != rel:
            raise ValueError(f'{rel!r} is not a canonical relative path; write it as {canonical!r}.')
        if PurePath(rel).parts[:1] and PurePath(rel).parts[0].casefold() in ('.youngcrow', 'vault'):
            raise ValueError(f'{rel} cannot be removed: init never deletes the harness folder or vault notes.')
        if (data := _read_bytes(root, rel)) is not None:
            drops.append(_Step(rel, None, data))
    gone = frozenset(step.rel for step in drops)

    report = Report()
    parent, *children = VAULT_INDEXES
    own_parent = os.path.lexists(safe_target(root, parent))
    for rel in VAULT_INDEXES:
        # With the user's own vault/index.md, a sub-index is created only if that index links to it:
        # init never edits the user's index, and an unlinked sub-index would fail `vault.py check`.
        unlinked = own_parent and rel in children and not _links_to(root, parent, rel)
        if os.path.lexists(safe_target(root, rel)) or unlinked:
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
        step = _plan_managed(root, rel, fresh, add, gone)
        if step is None:
            report.skipped.append(rel)
        else:
            steps.append(step)
    cleaned = _plan_hooks(root, strip_hooks, gone, report)
    steps += _plan_clients(root, client, gone, report, {step.rel: step.data for step in cleaned})

    dirs = _empty_parents(root, [step.rel for step in drops], keep=[step.rel for step in steps])
    _apply(root, drops + cleaned + steps, manifest=Manifest(
        version=__version__, client=client, lang=lang, rigor=rigor,
        files={step.rel: _sha(step.data) for step in steps},
        created=[step.rel for step in steps if step.created],
        edits=[step.rel for step in steps if step.managed],
        json_edits={step.rel: added_pairs(step.old) for step in steps if step.rel == CLAUDE_SETTINGS},
    ), dirs=dirs)
    report.written = list(dict.fromkeys(step.rel for step in cleaned + steps))
    report.removed = [step.rel for step in drops] + [path.relative_to(root).as_posix() + '/' for path in dirs]
    return report


def upgrade(root: Path) -> Report:
    """Bring the harness files to this package's version without touching what the user changed.

    Only `.youngcrow/`, the Codex agent and the AGENTS.md block body are touched (never `vault/`,
    never text outside a block, never `.claude/settings.json` or the originals saved for it). A
    `.youngcrow/` file, or the Codex agent when the manifest records it (R50), whose hash matches the
    manifest is replaced, a missing one is written, a changed one is kept and listed in
    `kept_modified`. A payload file new in this version is written and recorded; a recorded one
    this version dropped is deleted (`removed`) when unmodified, else kept; folders that leaves
    empty go too (R18). The AGENTS.md block that init added, while it is still the installer's
    (R21: its body is the installed HARNESS text, or the whole file still has its recorded hash),
    gets `.youngcrow/HARNESS.md` as it stands after this upgrade: the new text, or the user's own
    when they changed that file. Otherwise it is kept.
    Raises NotInitialized without a manifest, ManagedBlockError (naming the file) for broken
    markers, UnsafePathError for a linked path, before any write. The manifest is saved last; a
    failed write rolls the whole upgrade back.
    """
    root = Path(root)
    manifest = _load(root)
    _check_options(manifest.client, manifest.lang, manifest.rigor)
    harness = _template(f'HARNESS.{manifest.lang}.{manifest.rigor}.md')
    fresh = _harness_files(harness)
    if CODEX_AGENT in manifest.files:  # only the agent init wrote (R50), by the same rule (R19a)
        fresh[CODEX_AGENT] = codex_agent()
    report, steps = Report(), []
    files, created = dict(manifest.files), list(manifest.created)
    installed = _installed_harness(root, manifest)  # what the AGENTS.md block should still hold
    for rel, data in fresh.items():
        current = _read_bytes(root, rel)
        if current is not None and _sha(current) != manifest.files.get(rel):
            report.kept_modified.append(rel)  # changed by the user, or not ours (a new path taken)
            continue
        if current != data:
            steps.append(_Step(rel, data, current))
            report.written.append(rel)
        files[rel] = _sha(data)
        if current is None and rel not in created:
            created.append(rel)

    if 'AGENTS.md' in manifest.edits:
        # The block mirrors HARNESS.md as it will stand after this upgrade (R21).
        kept = '.youngcrow/HARNESS.md' in report.kept_modified
        rules = _read(root, '.youngcrow/HARNESS.md') if kept else harness
        text = _read(root, 'AGENTS.md')
        if text is None:
            report.kept_modified.append('AGENTS.md')
        elif (new := _put_block('AGENTS.md', text, rules)) != text:
            whole = _sha(text.encode('utf-8')) == manifest.files.get('AGENTS.md')
            if _owns_block('AGENTS.md', text, installed, whole):
                for marker in (MD_START, MD_END):
                    if marker in (line.rstrip() for line in rules.splitlines()):
                        raise ManagedBlockError(f'.youngcrow/HARNESS.md has the line "{marker}"; '
                                                'it cannot go into the AGENTS.md block.')
                steps.append(_Step('AGENTS.md', new.encode('utf-8'), text.encode('utf-8'), managed=True))
                report.written.append('AGENTS.md')
                if whole:
                    files['AGENTS.md'] = _sha(new.encode('utf-8'))  # still wholly ours: undo may delete it
            else:
                report.kept_modified.append('AGENTS.md')

    for rel, digest in manifest.files.items():
        if not rel.startswith('.youngcrow/') or rel.startswith(ORIGINALS) or rel in fresh or rel == MANIFEST_PATH:
            continue
        current = _read_bytes(root, rel)
        if current is not None and _sha(current) != digest:
            report.kept_modified.append(rel)
            continue
        if current is not None:
            steps.append(_Step(rel, None, current))
            report.removed.append(rel)
        del files[rel]
        created = [name for name in created if name != rel]

    updated = Manifest(__version__, manifest.client, manifest.lang, manifest.rigor, files, created,
                       list(manifest.edits), dict(manifest.json_edits))
    dirs = _empty_parents(root, [step.rel for step in steps if step.data is None],
                          keep=[step.rel for step in steps if step.data is not None])
    report.removed += [path.relative_to(root).as_posix() + '/' for path in dirs]
    if steps or updated != manifest:
        _apply(root, steps, manifest=updated, dirs=dirs)
    return report


def _empty_parents(root: Path, removed: list[str], keep: list[str] = ()) -> list[Path]:
    """The folders a run may remove (R18), deepest first.

    A folder qualifies when it holds a file the run removes, is a real directory inside the root
    (not the root), holds nothing else once the run's removals are done, and gets none of the
    files in `keep` (the ones the run writes).
    """
    gone = set(removed)
    busy = {parent for rel in keep for parent in PurePath(rel).parents}
    parents = {parent for rel in removed for parent in PurePath(rel).parents if parent.parts} - busy
    emptied = []
    for parent in sorted(parents, key=lambda p: (-len(p.parts), p.as_posix())):
        path = root / parent
        if is_real_dir(path) and all((parent / name).as_posix() in gone for name in os.listdir(path)):
            gone.add(parent.as_posix())
            emptied.append(path)
    return emptied


def _env_files(root: Path) -> list[str]:
    """The entries in the project root that the .gitignore block keeps out of git: `.env` and
    `.env.*`, except `.env.example`."""
    return sorted(name for name in os.listdir(root)
                  if (name == '.env' or name.startswith('.env.')) and name != '.env.example')


def undo(root: Path, *, confirm: bool = False) -> Report:
    """Take out what init (and upgrade) put in. Without `confirm`, only report what would happen.

    A created file whose hash still matches the manifest is deleted (`removed`). A created file the
    user changed is kept, minus the managed text it carries (`kept_modified`). A file that existed
    before init gets the managed text taken out, which restores its original bytes (`written`).
    A block is taken out only while it is the installer's (R21): its body is what init wrote (for
    AGENTS.md, the HARNESS text known from `.youngcrow/HARNESS.md` with a matching hash) or the whole
    file still has its recorded hash. Otherwise the user typed inside it, and the whole file is
    left as it is (`kept_modified`), as is a pre-existing file whose managed text the user removed.
    A settings file init edited (R37) gets its saved original back while it is as init left it
    (`written`); once the user changed it, only the keys init added come out (R49) and it is listed
    in `kept_modified`. A settings file that holds the same JSON value as init's bytes, only laid out
    anew (R52, `_only_relaid`), counts as left as init left it: deleted when init created it, else its
    original comes back.
    Folders left empty by those deletions go too (`removed`, with a trailing `/`); the manifest is
    deleted last. Every path and managed edit is checked first: NotInitialized, UnsafePathError,
    ManagedBlockError (naming the file) or ValueError change nothing, and a failed write rolls the
    whole undo back. When the .gitignore block goes, `warnings` names each `.env` or `.env.*` file
    in the project root (not `.env.example`): that block was what kept it out of git.
    """
    root = Path(root)
    manifest = _load(root)
    bodies = {'AGENTS.md': _installed_harness(root, manifest), '.gitignore': GITIGNORE_BODY}
    report, steps = Report(), []
    for rel in dict.fromkeys(manifest.created + manifest.edits + list(manifest.json_edits)):
        if rel == MANIFEST_PATH:
            continue
        current = _read_bytes(root, rel)
        if current is None:
            continue
        created = rel in manifest.created
        unchanged = _sha(current) == manifest.files.get(rel)
        if rel in manifest.json_edits and not unchanged:
            unchanged = _only_relaid(root, manifest, rel, current, created)
        if created and unchanged:
            steps.append(_Step(rel, None, current))
            report.removed.append(rel)
            continue
        if rel in manifest.json_edits:
            # R37: the saved original while the file is as init left it (`written`); else only the keys
            # init added go (R49).
            new = unwire(current, _original(root, manifest, rel) if unchanged else None, manifest.json_edits[rel])
            if new != current:
                steps.append(_Step(rel, new, current, managed=True))
            (report.written if unchanged and new != current else report.kept_modified).append(rel)
            continue
        new = current
        if rel in manifest.edits and (rel == 'CLAUDE.md' or rel in _BLOCKS):
            stripped = _strip(rel, _decode(rel, current), bodies.get(rel), whole=unchanged)
            if stripped is None:
                report.kept_modified.append(rel)
                continue
            new = stripped.encode('utf-8')
        if new != current:
            steps.append(_Step(rel, new, current, managed=True))
        # Restored to its bytes from before init (`written`), or kept as the user left it.
        (report.written if new != current and not created else report.kept_modified).append(rel)
    if any(step.rel == '.gitignore' for step in steps):
        report.warnings = [f'{name}: without the youngcrow block, .gitignore may no longer keep this file '
                           'out of git. Run git status before you commit.' for name in _env_files(root)]
    steps.append(_Step(MANIFEST_PATH, None, safe_target(root, MANIFEST_PATH).read_bytes()))
    report.removed.append(MANIFEST_PATH)
    dirs = _empty_parents(root, [step.rel for step in steps if step.data is None])
    report.removed += [path.relative_to(root).as_posix() + '/' for path in dirs]
    if confirm:
        _apply(root, steps, dirs=dirs)
    return report
