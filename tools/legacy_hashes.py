#!/usr/bin/env python3
"""Build the table of file versions `youngcrow migrate` recognises as unmodified setup.sh copies.

For every legacy path (`youngcrow.migrate.is_legacy_path`: what setup.sh copied into projects,
never the vault), the table lists each distinct SHA-256 that path had in the history of one ref,
origin/main by default (R24). Only history reachable from the ref counts; a branch that never
reached it does not. Keys and hash lists are sorted and the file ends with a newline, so the same
history always gives the same bytes.

    python3 tools/legacy_hashes.py --repo . --ref origin/main

writes `src/youngcrow/legacy_hashes.json`. Needs the full history (`git fetch --unshallow`).
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.migrate import is_legacy_path  # noqa: E402

DEFAULT_OUT = ROOT / 'src' / 'youngcrow' / 'legacy_hashes.json'
FILE_MODES = ('100644', '100755')  # regular files; a link (120000) or submodule is not a copy


def _git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    run = subprocess.run(['git', '-C', str(repo), *args], input=data, capture_output=True)
    if run.returncode != 0:
        raise RuntimeError(f'git {args[0]} failed: {run.stderr.decode(errors="replace").strip()}')
    return run.stdout


def _blobs(repo: Path, ref: str) -> dict[str, set[str]]:
    """Legacy path -> ids of the blobs it held in any commit reachable from `ref`."""
    trees = sorted(set(_git(repo, 'log', '--format=%T', ref).decode().split()))
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


def build_table(repo: Path, ref: str) -> dict[str, list[str]]:
    """Legacy path -> sorted distinct SHA-256 of every version it had on `ref`."""
    repo = Path(repo)
    blobs = _blobs(repo, ref)
    digests = _digests(repo, sorted({blob for ids in blobs.values() for blob in ids}))
    return {path: sorted({digests[blob] for blob in ids}) for path, ids in sorted(blobs.items())}


def render(table: dict[str, list[str]]) -> str:
    return json.dumps(table, indent=2, sort_keys=True) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--repo', default='.', help='repository to read the history from (default: .)')
    parser.add_argument('--ref', default='origin/main', help='branch or commit whose history counts (default: origin/main)')
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
