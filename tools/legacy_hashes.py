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

    python3 tools/legacy_hashes.py --repo . --ref HEAD

writes `src/youngcrow/legacy_hashes.json`. `--repo` is the repository root. Needs the full history
(`git fetch --unshallow`).
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

from youngcrow.manifest import UnsafePathError, safe_target, sha256_file  # noqa: E402
from youngcrow.migrate import is_legacy_path  # noqa: E402

DEFAULT_OUT = ROOT / 'src' / 'youngcrow' / 'legacy_hashes.json'
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


def _digests(repo: Path, ids: list[str]) -> dict[str, str]:
    """SHA-256 of each blob's bytes, read in one `git cat-file --batch`."""
    out = _git(repo, 'cat-file', '--batch', data=''.join(f'{blob}\n' for blob in ids).encode())
    digests, at = {}, 0
    for blob in ids:
        end = out.index(b'\n', at)
        header = out[at:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise RuntimeError(f'git cat-file could not read blob {blob}')
        size = int(header[2])
        digests[blob] = hashlib.sha256(out[end + 1:end + 1 + size]).hexdigest()
        at = end + 1 + size + 1
    return digests


def _working_tree(repo: Path) -> dict[str, str]:
    """Legacy path -> SHA-256 of the file as it is in the working tree now.

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
                found[path] = sha256_file(target)
        except (UnsafePathError, FileNotFoundError):
            pass  # a link, a folder, or a file that is gone from the working tree
    return found


def build_table(repo: Path, ref: str) -> dict[str, list[str]]:
    """Legacy path -> sorted distinct SHA-256 of every version it had in the history of `ref`,
    plus the file as it is in the working tree now."""
    repo = Path(repo)
    blobs = _blobs(repo, ref)
    digests = _digests(repo, sorted({blob for ids in blobs.values() for blob in ids}))
    hashes = {path: {digests[blob] for blob in ids} for path, ids in blobs.items()}
    for path, digest in _working_tree(repo).items():
        hashes.setdefault(path, set()).add(digest)
    for source, copy in COPIES:
        for path, found in list(hashes.items()):
            if path.startswith(source):
                hashes.setdefault(copy + path[len(source):], set()).update(found)
    return {path: sorted(found) for path, found in sorted(hashes.items())}


def render(table: dict[str, list[str]]) -> str:
    return json.dumps(table, indent=2, sort_keys=True) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--repo', default='.', help='repository to read the history from (default: .)')
    parser.add_argument('--ref', default='HEAD', help='branch or commit whose history counts (default: HEAD)')
    parser.add_argument('--out', default=str(DEFAULT_OUT), help='file to write (default: src/youngcrow/legacy_hashes.json)')
    args = parser.parse_args(argv)
    try:
        table = build_table(Path(args.repo), args.ref)
    except RuntimeError as error:
        print(f'legacy_hashes: {error} (ref {args.ref!r}, repo {args.repo!r})', file=sys.stderr)
        return 1
    Path(args.out).write_text(render(table), encoding='utf-8', newline='\n')
    print(f'{args.out}: {len(table)} paths, {sum(map(len, table.values()))} hashes from {args.ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
