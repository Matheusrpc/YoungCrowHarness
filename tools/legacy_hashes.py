#!/usr/bin/env python3
"""Build the table of file versions `youngcrow migrate` recognises as unmodified setup.sh copies.

For every legacy path (`youngcrow.migrate.is_legacy_path`: what setup.sh copied into projects,
never the vault), the table lists each distinct SHA-256 that path had in the history of one ref.
The ref is the branch head (R27): its history holds everything origin/main published and what the
branch is about to publish. Only history reachable from the ref counts; a branch that never reached
it does not. On top of that comes each legacy file as it is in the working tree now (R28): a regular
file that git lists as tracked or as untracked and not ignored, never through a link. So a change to
a legacy file and the regenerated table can go into one commit. A file setup.sh copied to another
place also gets the hashes of its source (`COPIES`). Keys and hash lists are sorted and the file ends
with a newline, so the same history and files always give the same bytes.

From the same versions of the hook files (`.claude/settings.json`, `.codex/hooks.json`) it builds the
hook table (R43): every hook entry under `hooks.<event>[].hooks[]` whose `command` or `commandWindows`
cites `source_prompt.py`, each once, sorted by its canonical JSON. `migrate` takes those entries out of
the hook files it keeps (R41). A version that is not JSON gives none.

    python3 tools/legacy_hashes.py --repo . --ref HEAD

writes `src/youngcrow/legacy_hashes.json` and, next to it, `legacy_hooks.json`. `--repo` is the
repository root. Needs the full history (`git fetch --unshallow`).
"""
from pathlib import Path
import argparse
import hashlib
import json
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.manifest import UnsafePathError, safe_target  # noqa: E402
from youngcrow.migrate import is_legacy_path  # noqa: E402
from youngcrow.settings import HOOK_FILES, hook_entries  # noqa: E402

DEFAULT_OUT = ROOT / 'src' / 'youngcrow' / 'legacy_hashes.json'
HOOKS_NAME = 'legacy_hooks.json'  # written in the folder of the hash table
FILE_MODES = ('100644', '100755')  # regular files; a link (120000) or submodule is not a copy
# setup.sh copies skills/humanizer-ptbr into the project's .agents/skills/ (`cp -r`), so the copy there
# is a published version of the file it came from.
COPIES = (('skills/humanizer-ptbr/', '.agents/skills/humanizer-ptbr/'),)


def _git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    try:
        run = subprocess.run(['git', '-C', str(repo), *args], input=data, capture_output=True)
    except FileNotFoundError as error:
        raise RuntimeError('git is not installed or is not on PATH') from error
    if run.returncode != 0:
        raise RuntimeError(f'git {args[0]} failed: {run.stderr.decode(errors="replace").strip()}')
    return run.stdout


def _blobs(repo: Path, ref: str) -> dict[str, set[str]]:
    """Legacy path -> ids of the blobs it held in any commit reachable from `ref`."""
    # The ref is resolved to a commit first: `--end-of-options` keeps a name that starts with `-`
    # from being read as an option, and the hash cannot be mistaken for a path.
    commit = _git(repo, 'rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}').decode().strip()
    trees = sorted(set(_git(repo, 'log', '--format=%T', '--end-of-options', commit, '--').decode().split()))
    blobs: dict[str, set[str]] = {}
    for tree in trees:
        for entry in _git(repo, 'ls-tree', '-r', '-z', tree).split(b'\0'):
            meta, _, name = entry.partition(b'\t')
            if not name:
                continue
            mode, kind, blob = meta.decode().split()
            path = name.decode(errors='replace')
            if kind == 'blob' and mode in FILE_MODES and is_legacy_path(path):
                blobs.setdefault(path, set()).add(blob)
    return blobs


def _contents(repo: Path, ids: list[str]) -> dict[str, bytes]:
    """The bytes of each blob, read in one `git cat-file --batch`."""
    out = _git(repo, 'cat-file', '--batch', data=''.join(f'{blob}\n' for blob in ids).encode())
    contents, at = {}, 0
    for blob in ids:
        end = out.index(b'\n', at)
        header = out[at:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise RuntimeError(f'git cat-file could not read blob {blob}')
        size = int(header[2])
        contents[blob] = out[end + 1:end + 1 + size]
        at = end + 1 + size + 1
    return contents


def _working_tree(repo: Path) -> dict[str, bytes]:
    """Legacy path -> the bytes of the file as it is in the working tree now.

    The files git lists (tracked, or untracked and not ignored, so a local clone in an ignored
    folder stays out) that are regular files. Nothing is followed: a link, or a path behind a linked
    folder, is skipped. A repository without a working tree gives nothing.
    """
    if _git(repo, 'rev-parse', '--is-inside-work-tree').decode().strip() != 'true':
        return {}
    found = {}
    for raw in _git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0'):
        path = raw.decode(errors='replace')
        if not raw or not is_legacy_path(path):
            continue
        try:
            target = safe_target(repo, path)
            if stat.S_ISREG(target.lstat().st_mode):
                found[path] = target.read_bytes()
        except (UnsafePathError, FileNotFoundError):
            pass  # a link, a folder, or a file that is gone from the working tree
    return found


def _versions(repo: Path, ref: str) -> dict[str, list[bytes]]:
    """Legacy path -> the bytes of every version it had in the history of `ref`, then as it is in the working tree now."""
    blobs = _blobs(repo, ref)
    contents = _contents(repo, sorted({blob for ids in blobs.values() for blob in ids}))
    versions = {path: [contents[blob] for blob in sorted(ids)] for path, ids in blobs.items()}
    for path, data in _working_tree(repo).items():
        versions.setdefault(path, []).append(data)
    return versions


def build_table(repo: Path, ref: str) -> dict[str, list[str]]:
    """Legacy path -> sorted distinct SHA-256 of every version it had in the history of `ref`,
    plus the file as it is in the working tree now."""
    hashes = {path: {hashlib.sha256(data).hexdigest() for data in found}
              for path, found in _versions(Path(repo), ref).items()}
    for source, copy in COPIES:
        for path, found in list(hashes.items()):
            if path.startswith(source):
                hashes.setdefault(copy + path[len(source):], set()).update(found)
    return {path: sorted(found) for path, found in sorted(hashes.items())}


def render(table: dict[str, list[str]]) -> str:
    return json.dumps(table, indent=2, sort_keys=True) + '\n'


def _cites_source_prompt(entry: dict) -> bool:
    return any(isinstance(entry.get(key), str) and 'source_prompt.py' in entry[key] for key in ('command', 'commandWindows'))


def build_hooks(repo: Path, ref: str) -> list[dict]:
    """Every hook entry citing `source_prompt.py` that a version of a hook file had in the history of
    `ref` or has in the working tree now: each once, sorted by its canonical JSON."""
    versions = _versions(Path(repo), ref)
    found = {}
    for path in HOOK_FILES:
        for data in versions.get(path, ()):
            try:
                settings = json.loads(data.decode('utf-8'))
            except ValueError:  # not UTF-8 or not JSON: that version holds no entry a client could run
                continue
            for entry in hook_entries(settings):
                if _cites_source_prompt(entry):
                    found[json.dumps(entry, sort_keys=True)] = entry
    return [found[key] for key in sorted(found)]


def render_hooks(entries: list[dict]) -> str:
    return json.dumps({'entries': entries}, indent=2, sort_keys=True) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--repo', default='.', help='repository to read the history from (default: .)')
    parser.add_argument('--ref', default='HEAD', help='branch or commit whose history counts (default: HEAD)')
    parser.add_argument('--out', default=str(DEFAULT_OUT),
                        help=f'file to write (default: src/youngcrow/legacy_hashes.json); {HOOKS_NAME} goes next to it')
    args = parser.parse_args(argv)
    try:
        table = build_table(Path(args.repo), args.ref)
        hooks = build_hooks(Path(args.repo), args.ref)
    except RuntimeError as error:
        print(f'legacy_hashes: {error} (ref {args.ref!r}, repo {args.repo!r})', file=sys.stderr)
        return 1
    out = Path(args.out)
    out.write_text(render(table), encoding='utf-8', newline='\n')
    out.with_name(HOOKS_NAME).write_text(render_hooks(hooks), encoding='utf-8', newline='\n')
    print(f'{out}: {len(table)} paths, {sum(map(len, table.values()))} hashes from {args.ref}')
    print(f'{out.with_name(HOOKS_NAME)}: {len(hooks)} hook entries from {args.ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
