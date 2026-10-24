"""`youngcrow migrate`: move a project from the old `setup.sh` install to the `.youngcrow/` layout.

`setup.sh` copied harness files straight into the project. `scan` looks for those copies and sorts
them with a table of the versions the harness published (`legacy_hashes.json`, built by
`tools/legacy_hashes.py`): a file byte-identical to a published version is a match and may go; any
other file at a legacy path is the user's own, so it is kept and listed as modified.
`apply` removes the matches and installs the new layout in one all-or-nothing run.
"""
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
import json
import stat

from youngcrow.install import Report, init
from youngcrow.manifest import UnsafePathError, safe_target, sha256_file

# Every path in the FILES arrays of setup.sh (both client branches) except the vault (R22), then the
# folders it copied skills into: an entry ending in `/*` stands for every file under that folder.
LEGACY_PATHS: tuple[str, ...] = (
    'CLAUDE.md', 'AGENTS.md', '.env.example', 'skills-lock.json', 'docs/CLAUDE.en.md',
    'scripts/integrations.py', 'skills/integrate-from-docs/SKILL.md',
    'skills/integrate-from-docs/references/memory.md',
    'scripts/personalize.py', 'skills/personalizer/SKILL.md', 'skills/personalizer/references/interview.md',
    'scripts/vault.py', 'scripts/document_store.py',
    'scripts/documents.py', 'scripts/docling_worker.py', 'requirements/docling.txt',
    'scripts/source_fetch.py', 'requirements/docling-media.txt',
    'scripts/source_prompt.py', 'skills/ingest-source/SKILL.md',
    'scripts/memory.py', 'scripts/graphify_worker.py', 'requirements/graphify.txt',
    'skills/retrieve-memory/SKILL.md',
    'scripts/capabilities.py', 'skills/govern-capabilities/SKILL.md',
    'scripts/adoption.py', 'scripts/adoption_fs.py', 'scripts/adoption_acl.ps1',
    'scripts/mission_config.py', 'scripts/mission_backlog.py', 'scripts/mission_store.py',
    'scripts/mission_vault.py', 'scripts/missions.py',
    'scripts/mission_clients.py', 'scripts/mission_process.py', 'scripts/mission_runs.py',
    'skills/yc-personalizer/SKILL.md', 'skills/yc-config/SKILL.md', 'skills/yc-missao/SKILL.md',
    'skills/yc-status/SKILL.md',
    '.mcp.json', '.claude/settings.json', '.claude/agents/integration-specialist.md',
    '.claude/skills/integrate-from-docs/SKILL.md', '.claude/skills/personalizer/SKILL.md',
    '.claude/skills/ingest-source/SKILL.md', '.claude/skills/retrieve-memory/SKILL.md',
    '.claude/skills/govern-capabilities/SKILL.md',
    '.claude/skills/yc-personalizer/SKILL.md', '.claude/skills/yc-config/SKILL.md',
    '.claude/skills/yc-missao/SKILL.md', '.claude/skills/yc-status/SKILL.md',
    '.codex/hooks.json', '.codex/config.toml', '.codex/agents/integration-specialist.toml',
    '.agents/skills/integrate-from-docs/SKILL.md', '.agents/skills/personalizer/SKILL.md',
    '.agents/skills/ingest-source/SKILL.md', '.agents/skills/retrieve-memory/SKILL.md',
    '.agents/skills/govern-capabilities/SKILL.md',
    '.agents/skills/yc-personalizer/SKILL.md', '.agents/skills/yc-config/SKILL.md',
    '.agents/skills/yc-missao/SKILL.md', '.agents/skills/yc-status/SKILL.md',
    '.claude/skills/*', '.agents/skills/*', 'skills/*',
)


@dataclass
class MigrationPreview:
    matches: list[str]   # unmodified copies: byte-identical to a published version, `apply` removes them
    modified: list[str]  # the user's own versions of legacy files: kept, and listed in the report


def is_legacy_path(rel: str) -> bool:
    """Whether `rel` (a project-relative path with `/`) is one `setup.sh` could have copied.

    True for an entry of `LEGACY_PATHS` or any file under one of its `folder/*` entries. Nothing
    under `vault/` is ever legacy (R22), so a table entry there is ignored.
    """
    return any(rel == entry or (entry.endswith('/*') and rel.startswith(entry[:-1])) for entry in LEGACY_PATHS)


def legacy_hashes() -> dict[str, list[str]]:
    """The published table: relative path -> every SHA-256 that path had in the history it was built from."""
    return json.loads(files('youngcrow').joinpath('legacy_hashes.json').read_text(encoding='utf-8'))


def _classify(root: Path, rel: str, published: list[str]) -> str | None:
    """'match' or 'modified' for a regular file at `rel`; None when there is none to judge.

    Nothing is followed: a link or junction on the path, a folder, or any other kind of file
    gives None, so migrate neither reads nor removes it (R9). A path that cannot be looked at (a
    folder we may not enter) also gives None, but a file that is there and cannot be read is
    'modified': it is kept and listed, and the scan goes on.
    """
    try:
        path = safe_target(root, rel)
        if not stat.S_ISREG(path.lstat().st_mode):
            return None
    except (UnsafePathError, FileNotFoundError, PermissionError):
        return None
    try:
        return 'match' if sha256_file(path) in published else 'modified'
    except FileNotFoundError:
        return None
    except PermissionError:
        return 'modified'


def _scan(root: Path, table: dict[str, list[str]]) -> MigrationPreview:
    preview = MigrationPreview([], [])
    for rel, published in sorted(table.items()):
        if not is_legacy_path(rel):
            continue
        kind = _classify(root, rel, published)
        if kind == 'match':
            preview.matches.append(rel)
        elif kind == 'modified':
            preview.modified.append(rel)
    return preview


def scan(root: Path) -> MigrationPreview:
    """Find the files `setup.sh` left in `root`. Reads only; writes nothing.

    Every path of the table that is a legacy path (never under `vault/`) is checked as a regular
    file without following links. A file whose hash is in the table is a match; one at a table path
    with another hash is modified; a path not in the table is not the harness's and is ignored.
    Both lists are sorted.
    """
    return _scan(Path(root), legacy_hashes())


def apply(root: Path, preview: MigrationPreview, *, client: str = 'both') -> Report:
    """Remove the preview's matches and run `init`, as one all-or-nothing run.

    The matches are checked again first: a file that changed since the scan, or is gone, is not
    removed (a changed one is reported in `kept_modified`), and a path that is not in the table
    raises ValueError, so a stale or hand-built preview cannot delete anything the user owns. Then
    `init(remove=...)` removes the matches, the folders they empty, and installs; a failure puts
    every file and folder back. Raises what `init` raises (AlreadyInitialized when the project has a
    manifest, UnsafePathError, ManagedBlockError, ...) before anything is removed.

    The report is init's: `removed` holds the matches and the folders they emptied, `written` what
    init wrote (CLAUDE.md among them when it added the import line to a kept file), `kept_modified`
    the user's legacy files left in place.
    """
    root = Path(root)
    table = legacy_hashes()
    for rel in preview.matches:
        if rel not in table or not is_legacy_path(rel):
            raise ValueError(f'{rel} is not a file that setup.sh installed; migrate does not remove it.')
    current = _scan(root, table)
    report = init(root, client=client, remove=[rel for rel in preview.matches if rel in current.matches])
    report.kept_modified = current.modified
    return report
