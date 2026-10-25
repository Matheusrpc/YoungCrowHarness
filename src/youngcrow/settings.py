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


def _merge(data: bytes | None) -> tuple[dict, list[list[str]]]:
    """The settings in `data` with the WIRING added, and the `[top, sub]` pairs that were missing."""
    settings = {} if data is None else _object(data)
    added = []
    for key, ours in WIRING.items():
        table = settings.setdefault(key, {})
        if not isinstance(table, dict):
            raise SettingsSkipped(f'"{key}" is not a JSON object')
        for name, value in ours.items():
            if name not in table:
                table[name] = value
                added.append([key, name])
            elif not _same(table[name], value):
                raise SettingsSkipped(f'"{key}" already has "{name}" with another value')
    return settings, added


def add_wiring(data: bytes | None) -> bytes | None:
    """`data` (None for a missing file) with the WIRING keys added; None when it has them all already.

    The other keys and their order stay; a key that is added goes last in its object. Raises
    SettingsSkipped when `data` is not a JSON object in UTF-8, when `extraKnownMarketplaces` or
    `enabledPlugins` is there and is not an object, or when one of our sub-keys holds another value.
    """
    settings, added = _merge(data)
    return _dump(settings, data) if added else None


def added_pairs(data: bytes | None) -> list[list[str]]:
    """The `[top, sub]` pairs `add_wiring(data)` adds, which init records (R49); SettingsSkipped as there."""
    return _merge(data)[1]


def remove_wiring(data: bytes, added: list[list[str]]) -> bytes | None:
    """`data` without the `added` pairs that still hold our value, nor the top keys that leaves empty.

    Only pairs init itself added are taken out (R49): a sub-key the file already had stays, and a
    pair that is not one of WIRING is ignored. None when nothing but `{}` would be left; `data`
    itself when nothing comes out. Raises SettingsSkipped when `data` is not a JSON object in UTF-8.
    """
    settings = _object(data)
    changed = False
    for key, name in added:
        table = settings.get(key)
        ours = WIRING.get(key, {})
        if isinstance(table, dict) and name in ours and name in table and _same(table[name], ours[name]):
            del table[name]
            if not table:
                del settings[key]
            changed = True
    if not changed:
        return data
    return _dump(settings, data) if settings else None


def unwire(current: bytes, original: bytes | None, added: list[list[str]]) -> bytes:
    """What `undo` writes back into a settings file init edited (R37).

    `original` is the file's bytes from before init, given only while the file is as init left it:
    then those come back. Otherwise the `added` pairs come out and the rest stays; `{}` when nothing
    else is left, and the file as it is when it no longer holds a JSON object.
    """
    if original is not None:
        return original
    try:
        stripped = remove_wiring(current, added)
    except SettingsSkipped:
        return current
    return _dump({}, current) if stripped is None else stripped
