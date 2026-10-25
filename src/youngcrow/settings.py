"""What `youngcrow init` wires into the clients: the plugin in `.claude/settings.json`, the Codex agent.

Claude Code reads the plugin from the project (R36): `init` adds a marketplace entry and turns the
plugin on in `.claude/settings.json`, and both take effect once the person trusts the folder. Codex
installs plugins per user, so `init` only writes the project's agent file and prints the commands.
The functions here work on bytes; reading, writing and the manifest are `install`'s job.
"""
from importlib.resources import files
import json

CLAUDE_SETTINGS = '.claude/settings.json'
CODEX_AGENT = '.codex/agents/integration-specialist.toml'
# Where init keeps the bytes a settings file had before it was edited (R37), under the same path.
ORIGINALS = '.youngcrow/originals/'
WIRING = {
    'extraKnownMarketplaces': {'youngcrow': {'source': {'source': 'github', 'repo': 'Matheusrpc/YoungCrowHarness'}}},
    'enabledPlugins': {'youngcrow@youngcrow': True},
}
CLAUDE_STEP = 'Claude Code: open this folder and accept the workspace trust prompt; it then offers the youngcrow plugin.'
CLAUDE_MANUAL_STEP = ('Claude Code: /plugin marketplace add Matheusrpc/YoungCrowHarness, then /plugin install '
                      'youngcrow@youngcrow --scope project.')
CODEX_STEP = ('Codex: run codex plugin marketplace add Matheusrpc/YoungCrowHarness, then codex plugin add '
              'youngcrow@youngcrow, and trust its hooks in /hooks.')


class SettingsSkipped(ValueError):
    """A settings file youngcrow does not edit; the message says why."""


def codex_agent() -> bytes:
    """The Codex agent `init` writes, byte for byte as the package ships it (the catalog pins its hash)."""
    return files('youngcrow').joinpath('templates', 'codex', 'integration-specialist.toml').read_bytes()


def _same(a, b) -> bool:
    """Equal as JSON values: `true` is not `1`."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _object(data: bytes) -> dict:
    """The JSON object in `data`, or SettingsSkipped."""
    try:
        value = json.loads(data.decode('utf-8'))
    except UnicodeDecodeError as error:
        raise SettingsSkipped('it is not UTF-8 text') from error
    except ValueError as error:
        raise SettingsSkipped(f'it is not valid JSON ({error})') from error
    if not isinstance(value, dict):
        raise SettingsSkipped('it does not hold a JSON object')
    return value


def _dump(value: dict, like: bytes | None) -> bytes:
    """`value` with two-space indent and a final newline, in the line ending `like` starts with."""
    text = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    at = like.find(b'\n') if like else -1
    if at > 0 and like[at - 1:at] == b'\r':
        text = text.replace('\n', '\r\n')
    return text.encode('utf-8')


def add_wiring(data: bytes | None) -> bytes | None:
    """`data` (None for a missing file) with the WIRING keys added; None when it has them all already.

    The other keys and their order stay; a key that is added goes last in its object. Raises
    SettingsSkipped when `data` is not a JSON object in UTF-8, when `extraKnownMarketplaces` or
    `enabledPlugins` is there and is not an object, or when one of our sub-keys holds another value.
    """
    settings = {} if data is None else _object(data)
    changed = False
    for key, ours in WIRING.items():
        table = settings.setdefault(key, {})
        if not isinstance(table, dict):
            raise SettingsSkipped(f'"{key}" is not a JSON object')
        for name, value in ours.items():
            if name not in table:
                table[name] = value
                changed = True
            elif not _same(table[name], value):
                raise SettingsSkipped(f'"{key}" already has "{name}" with another value')
    return _dump(settings, data) if changed else None


def remove_wiring(data: bytes) -> bytes | None:
    """`data` without the sub-keys that still hold our value, nor the top keys that leaves empty.

    None when nothing but `{}` would be left; `data` itself when none of our values is there.
    Raises SettingsSkipped when `data` is not a JSON object in UTF-8.
    """
    settings = _object(data)
    changed = False
    for key, ours in WIRING.items():
        table = settings.get(key)
        if not isinstance(table, dict):
            continue
        ours_here = [name for name, value in ours.items() if name in table and _same(table[name], value)]
        for name in ours_here:
            del table[name]
        if ours_here and not table:
            del settings[key]
        changed = changed or bool(ours_here)
    if not changed:
        return data
    return _dump(settings, data) if settings else None


def unwire(current: bytes, original: bytes | None) -> bytes:
    """What `undo` writes back into a settings file init edited (R37).

    `original` is the file's bytes from before init, given only while the file is as init left it:
    then those come back. Otherwise our keys come out and the rest stays; `{}` when nothing else is
    left, and the file as it is when it no longer holds a JSON object.
    """
    if original is not None:
        return original
    try:
        stripped = remove_wiring(current)
    except SettingsSkipped:
        return current
    return _dump({}, current) if stripped is None else stripped
