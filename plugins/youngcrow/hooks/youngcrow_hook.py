#!/usr/bin/env python3
"""Hooks of the youngcrow plugin, written by hand (`tools/build_plugin.py` leaves this file alone).

A plugin installed per user fires its hooks in every repository the person opens, so nothing here may
run code that comes from the project (R35). A regular `.youngcrow/manifest.json` marks a project and
`.youngcrow/VERSION` names the release that installed it; both are read as data. `prompt` runs the
`source_prompt.py` that sits next to this file, which the generator copies from the repository.

    youngcrow_hook.py session-start   warn when the project's harness files and the plugin differ in version
    youngcrow_hook.py prompt          source guidance for the prompt that arrives on stdin

The hook writes nothing and always exits 0: a hook that fails would stand in the way of the person's work.
"""
from __future__ import annotations

import os
import sys

if __name__ == '__main__':
    # Second guard behind `-I` in hooks.json: without it `python -c` puts the working folder, which is the
    # project, first on sys.path. Take it out before the first import that is not built in.
    sys.path[:] = [entry for entry in sys.path if entry not in ('', '.')]

from collections.abc import Mapping  # noqa: E402
from importlib import util  # noqa: E402
from pathlib import Path  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402

HOOKS = Path(__file__).resolve().parent
MANIFEST_FILE = Path('.youngcrow') / 'manifest.json'
VERSION_FILE = Path('.youngcrow') / 'VERSION'
PLUGIN_MANIFEST = HOOKS.parent / '.claude-plugin' / 'plugin.json'
INPUT_LIMIT = 'Source guidance: input_limit. No source was inspected or registered.'  # as source_prompt.py says it
_PLAIN_VERSION = re.compile(r'[0-9A-Za-z.+_-]{1,64}')


def _plain_file(path: Path) -> bool:
    """A regular file and not a link: a project must not be able to point the hook at another file."""
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


def project_root(payload: dict, environ: Mapping[str, str]) -> Path | None:
    """The folder that holds `.youngcrow/manifest.json`, searched upward from where the client is working."""
    given = (environ.get('CLAUDE_PROJECT_DIR'), payload.get('cwd'))
    start = Path(next((path for path in given if isinstance(path, str) and path), None) or os.getcwd()).resolve()
    for folder in (start, *start.parents):
        if _plain_file(folder / MANIFEST_FILE):
            return folder
    return None


def _installed_version(root: Path) -> str | None:
    """The release named in the project's `.youngcrow/VERSION`, or None when that is not a plain version."""
    path = root / VERSION_FILE
    if not _plain_file(path):
        return None
    with open(path, 'rb') as handle:
        text = handle.read(64).decode('ascii', 'replace').strip()
    return text if _PLAIN_VERSION.fullmatch(text) else None


def _version_notice(root: Path) -> dict | None:
    installed = _installed_version(root)
    shipped = json.loads(PLUGIN_MANIFEST.read_text(encoding='utf-8'))['version']
    if installed is None or installed == shipped:
        return None
    message = (f'youngcrow: this project has harness files {installed}; the plugin is {shipped}. '
               'Run `uvx youngcrow upgrade` in the project.')
    return {'systemMessage': message,
            'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': message}}


def _load_source_prompt():
    """The `source_prompt.py` next to this file, the only code besides this file that a hook runs."""
    sys.dont_write_bytecode = True  # loading it must not leave a __pycache__ in the plugin
    spec = util.spec_from_file_location('youngcrow_source_prompt', HOOKS / 'source_prompt.py')
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(raw: bytes) -> dict:
    try:
        payload = json.loads(raw)
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str]) -> int:
    try:
        command = argv[0] if argv else ''
        if command in ('session-start', 'prompt'):
            source_prompt = _load_source_prompt()
            raw = sys.stdin.buffer.read(source_prompt.MAX_INPUT + 1)
            too_large = len(raw) > source_prompt.MAX_INPUT
            payload = {} if too_large else _payload(raw)
            root = project_root(payload, os.environ)
            if root is None:
                result = None
            elif command == 'session-start':
                result = _version_notice(root)
            elif too_large:
                result = source_prompt.context(INPUT_LIMIT)
            else:
                result = source_prompt.handle_prompt(payload, root)
            if result is not None:
                print(json.dumps(result))
    except Exception:  # whatever goes wrong, the hook stays silent and the prompt goes on
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
