"""The `youngcrow` command: init, upgrade, undo and migrate, on top of the install and migrate modules.

Exit codes: 0 done, 2 the command line itself is wrong (argparse), 3 youngcrow refused to touch
the project, or the system refused a read or write (OSError), and it said why on stderr, with the
notes a roll back left. Anything else is a bug and surfaces as a traceback.
Without `--json` the output is a few plain lines; with `--json` stdout holds one JSON object.
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Callable
import argparse
import json
import os
import sys

from youngcrow import __version__
from youngcrow.install import AlreadyInitialized, NotInitialized, Report, init, undo, upgrade
from youngcrow.migrate import apply, dangling_references, scan, vault_check

# ManagedBlockError and UnsafePathError are ValueErrors too, as is a client, lang or rigor init does not support.
REFUSALS = (AlreadyInitialized, NotInitialized, ValueError)
# What setup.sh wrote that holds the old harness rules (R26). Kept when the user changed them.
LEGACY_RULE_FILES = ('CLAUDE.md', 'AGENTS.md', 'docs/CLAUDE.en.md')
REPORT_HEADINGS = (
    ('written', 'Written:'),
    ('kept_modified', 'Kept (you changed these):'),
    ('removed', 'Removed:'),
    ('skipped', 'Skipped:'),
)

Result = tuple[dict, str]  # what `--json` prints, and what the plain output says


def _listing(heading: str, paths: list[str]) -> list[str]:
    return [heading, *(f'  {path}' for path in paths)]


def _report_lines(report: Report) -> list[str]:
    lines: list[str] = []
    for name, heading in REPORT_HEADINGS:
        if paths := getattr(report, name):
            lines += _listing(heading, paths)
    return lines or ['Nothing changed.']


def _legacy_notice(paths: list[str], *, migrated: bool) -> list[str]:
    """R26: the old rule files migrate keeps still hold the rules `.youngcrow/HARNESS.md` now carries."""
    carries = ('.youngcrow/HARNESS.md carries the rules now.' if migrated else
               'Migrate installs .youngcrow/HARNESS.md, which carries the rules.')
    return ['', *_listing('Note: these files came from the old setup.sh install and still contain the old harness rules:',
                          paths),
            f'{carries} Trim these files by hand so the rules are not stated twice.']


@contextmanager
def _project_folder(root: Path):
    """Create the project folder when it is missing (`init` itself needs it to exist).

    If anything fails, here or in the command inside the block, the folders made are removed
    again, so a refusal leaves nothing behind.
    """
    missing = []
    for folder in (root, *root.parents):
        if os.path.lexists(folder):
            break
        missing.append(folder)
    made = []
    try:
        for folder in reversed(missing):
            try:
                folder.mkdir()
            except FileExistsError:  # a `..` in `a/../b` stands for a folder that exists by now
                continue
            made.append(folder)
        yield
    except BaseException:
        for folder in reversed(made):
            try:
                folder.rmdir()
            except OSError:
                break
        raise


def _init(args: argparse.Namespace) -> Result:
    with _project_folder(args.root):
        report = init(args.root, client=args.client)
    return report.to_json(), '\n'.join(_report_lines(report))


def _upgrade(args: argparse.Namespace) -> Result:
    report = upgrade(args.root)
    return report.to_json(), '\n'.join(_report_lines(report))


def _undo(args: argparse.Namespace) -> Result:
    report = undo(args.root, confirm=args.confirm)
    lines = _report_lines(report)
    if not args.confirm:
        lines.insert(0, 'Preview only, nothing was changed. Add --confirm to undo.')
    for warning in report.warnings:  # on stderr in both modes, so --json output stays one object
        print(f'youngcrow: warning: {warning}', file=sys.stderr)
    return {**report.to_json(), 'warnings': report.warnings}, '\n'.join(lines)


def _comes_back(rel: str, client: str) -> bool:
    """Whether `init` writes `rel` again after migrate removes it: the rule file each client reads."""
    return (rel == 'CLAUDE.md' and client != 'codex') or (rel == 'AGENTS.md' and client != 'claude')


def _references_notice(found: dict[str, list[str]]) -> list[str]:
    """R30: the kept files and vault notes that still name a file migrate removes, one line each."""
    lines = ['', 'These files still point at files migrate removes:']
    for rel, paths in found.items():
        lines.append(f'  {rel}: {paths[0]}' + (f' and {len(paths) - 1} more' if len(paths) > 1 else ''))
    return lines + ['Update them by hand. --json lists every path.']


def _migrate(args: argparse.Namespace) -> Result:
    preview = scan(args.root)
    found = bool(preview.matches)  # not one unmodified copy: setup.sh never installed this project
    check = None
    if args.confirm:
        with _project_folder(args.root):
            report = apply(args.root, preview, client=args.client)
        if not found:
            report.kept_modified = []  # the project's own files, not setup.sh copies someone edited
        # apply looked at the files again: only what it removed, and what it kept, count.
        matches = [path for path in preview.matches if path in report.removed]
        modified = report.kept_modified
        gone = [rel for rel in report.removed if not rel.endswith('/') and not os.path.lexists(args.root / rel)]
        lines = _report_lines(report)
        check = vault_check(args.root)
    else:
        matches, modified = preview.matches, preview.modified if found else []
        gone = [rel for rel in matches if not _comes_back(rel, args.client)]
        lines = ['Preview only, nothing was changed. Add --confirm to migrate.']
        if matches:
            lines += _listing('Will be removed (unmodified setup.sh copies):', matches)
        if modified:
            lines += _listing('Kept (you changed these):', modified)
    if not found:
        lines.append('No setup.sh install found.')
    rules = [path for path in modified if path in LEGACY_RULE_FILES]
    if rules:
        lines += _legacy_notice(rules, migrated=args.confirm)
    references = dangling_references(args.root, gone, modified)
    if references:
        lines += _references_notice(references)
    if check:
        lines += ['', check['summary']]
        if check['exit_code']:
            lines.append('Run .youngcrow/scripts/vault.py check in the project to see each issue.')
    data = {'applied': args.confirm, 'matches': matches, 'modified': modified, 'legacy_rules': rules,
            'dangling_references': references, 'vault_check': check}
    return data, '\n'.join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='youngcrow', description='Set up, upgrade or remove the YoungCrow harness in a project.')
    parser.add_argument('--version', action='version', version=f'youngcrow {__version__}')
    commands = parser.add_subparsers(dest='command', required=True, metavar='command')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', type=Path, default=Path('.'), help='the project folder (default: .)')
    common.add_argument('--json', action='store_true', help='print one JSON object instead of plain lines')
    client = argparse.ArgumentParser(add_help=False)
    client.add_argument('--client', default='both', help='claude, codex or both (default: both)')

    def add(name: str, run: Callable[[argparse.Namespace], Result], summary: str, *parents: argparse.ArgumentParser,
            confirm: str | None = None) -> None:
        sub = commands.add_parser(name, parents=[common, *parents], help=summary, description=summary)
        if confirm:
            sub.add_argument('--confirm', action='store_true', help=confirm)
        sub.set_defaults(run=run)

    add('init', _init, 'Install the harness into the project.', client)
    add('upgrade', _upgrade, 'Bring the installed harness files up to this version.')
    add('undo', _undo, 'Take the install out. Without --confirm it only shows what would happen.',
        confirm='actually undo; without it, only show what would happen')
    add('migrate', _migrate, 'Replace an old setup.sh install. Without --confirm it only shows what it found.',
        client, confirm='actually migrate; without it, only show what was found')
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as stop:  # argparse exits for --help (0) and for a wrong command line (2)
        return stop.code
    try:
        if args.root.exists() and not args.root.is_dir():
            raise ValueError(f'{args.root} is not a folder.')
        data, text = args.run(args)
    except (*REFUSALS, OSError) as error:
        for line in (error, *getattr(error, '__notes__', ())):
            print(f'youngcrow: {line}', file=sys.stderr)
        return 3
    print(json.dumps(data, indent=2) if args.json else text)
    return 0
