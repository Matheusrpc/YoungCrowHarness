#!/usr/bin/env python3
"""Generate the youngcrow plugin tree, and the files derived from it, from the repository sources.

The sources stay where they are because setup.sh still installs from them: `skills/<name>/`, the
agents in `.claude/agents/` and `.codex/agents/`, `scripts/source_prompt.py` and the version in
`src/youngcrow/__init__.py`. Only the five core skills go into the plugin. Their text is rewritten
for a project that ran `youngcrow init`: `scripts/` becomes `.youngcrow/scripts/`, and a link to a
skill the plugin does not ship becomes plain text. The agents name the skill instead of its path in
the repository. The catalog `init` installs as `.youngcrow/capabilities.json` is cut from
`skills-lock.json`: the core entries, with the files `init` installs and the digests of those bytes,
checked by the `scripts/capabilities.py` that ships. Generated files are never edited by hand:
change the source and run

    python3 tools/build_plugin.py

`--check` writes nothing and exits 1, listing the paths that are missing, different or left over.
Two files in the plugin are written by hand and the generator leaves them alone (`HANDWRITTEN`).
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

CORE_SKILLS = ('govern-capabilities', 'ingest-source', 'integrate-from-docs', 'personalizer', 'retrieve-memory')
HANDWRITTEN = ('plugins/youngcrow/hooks/hooks.json', 'plugins/youngcrow/hooks/youngcrow_hook.py')
PLUGIN = 'plugins/youngcrow'
CODEX_AGENT = 'src/youngcrow/templates/codex/integration-specialist.toml'
CATALOG = 'src/youngcrow/templates/capabilities.json'
# Capabilities in the catalog `init` installs: the core skills, then the agent and the two optional runtimes.
CATALOG_IDS = (*CORE_SKILLS, 'integration-specialist', 'docling', 'graphify')
# Where `init` puts the Codex agent in a project, and the folder it puts the harness in.
CODEX_AGENT_INSTALLED = '.codex/agents/integration-specialist.toml'
INSTALLED = '.youngcrow/'
NAME = 'youngcrow'
OWNER = 'Matheusrpc'
URL = 'https://github.com/Matheusrpc/YoungCrowHarness'
DESCRIPTION = 'Proof-first memory, sources and capability governance for Claude Code and Codex projects.'

# A path the project holds after `youngcrow init`; the lookbehind skips `.youngcrow/scripts/`, URLs and `docs/scripts/`.
_INSTALLED = re.compile(r'(?<![\w./-])(scripts|requirements)/')
_SKILL_LINK = re.compile(r'\[[^\]]*\]\((?:\.\./)+([\w-]+)/SKILL\.md\)')
_SKILL_PATH = re.compile(r'(?<![\w./-])`?skills/([\w-]+)/SKILL\.md`?')
_FRONTMATTER = re.compile(r'---\n(.*?\n)---\n', re.S)
_SKILLS_BLOCK = re.compile(r'^skills:.*\n(?:(?:[ \t]+|-[ \t]).*\n)*', re.M)


def rewrite_skill(text: str) -> str:
    """A skill page as the plugin ships it: installed script paths, no links to skills left out."""
    text = _INSTALLED.sub(r'.youngcrow/\1/', text)
    return _SKILL_LINK.sub(lambda link: link[0] if link[1] in CORE_SKILLS else f'`{link[1]}`', text)


def _name_the_skill(text: str) -> str:
    """`skills/<name>/SKILL.md` is a path in this repository; the plugin's agent calls it "the <name> skill"."""
    return _SKILL_PATH.sub(r'the \1 skill', text)


def _claude_agent(text: str) -> str:
    """R39: the agent does not preload a skill, so the `skills:` block leaves the frontmatter."""
    head = _FRONTMATTER.match(text)
    if head:
        text = text[:head.start(1)] + _SKILLS_BLOCK.sub('', head[1]) + text[head.end(1):]
    return _name_the_skill(text)


def _json(data: dict) -> bytes:
    return (json.dumps(data, indent=2) + '\n').encode()


def _text(path: Path) -> str:
    return path.read_bytes().decode('utf-8')  # no newline translation: the bytes are what is compared


def _version(root: Path) -> str:
    found = re.search(r"^__version__\s*=\s*'([^']+)'", _text(root / 'src/youngcrow/__init__.py'), re.M)
    if not found:
        raise RuntimeError('src/youngcrow/__init__.py has no __version__')
    return found[1]


def _module(root: Path, relative: str, name: str):
    """A Python file of the repository under `root`, imported by its path: the copy that ships is the copy that checks."""
    path = root / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    folder, keep = str(path.parent), sys.dont_write_bytecode
    sys.path.insert(0, folder)  # capabilities.py imports document_store from its own folder
    sys.dont_write_bytecode = True  # a build leaves no __pycache__ in the repository
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(folder)
        sys.dont_write_bytecode = keep
    return module


def _catalog(root: Path, version: str, codex_agent: bytes) -> bytes:
    """The catalog `init` installs as `.youngcrow/capabilities.json`, from the core entries of `skills-lock.json`.

    Each entry keeps what the repository says about it (purpose, permissions, kind, clients, required, scope).
    Its files are those it lists that `init` installs (`PAYLOAD`), under `.youngcrow/`: the skill pages live in
    the plugin, and the scripts for missions are not installed, so listing them would report a missing file in
    every project. The agent also lists the Codex file `init` writes from the template. The digests are those of
    the bytes shipped, with None where an entry has no file to hash for a client.
    """
    capabilities = _module(root, 'scripts/capabilities.py', 'capabilities_for_build')
    payload = _module(root, 'src/youngcrow/payload.py', 'payload_for_build').PAYLOAD
    try:
        lock = {cap['id']: cap for cap in capabilities.catalog_from_bytes((root / 'skills-lock.json').read_bytes())}
    except ValueError as error:
        raise RuntimeError(f'skills-lock.json is not a valid catalog: {error}') from error
    shipped = {INSTALLED + rel: (root / rel).read_bytes() for rel in payload}
    shipped[CODEX_AGENT_INSTALLED] = codex_agent
    entries = []
    for name in CATALOG_IDS:
        if name not in lock:
            raise RuntimeError(f'skills-lock.json has no capability {name!r}, which the catalog needs')
        source = lock[name]
        files = {'common': [INSTALLED + rel for rel in source['files']['common'] if rel in payload],
                 'claude': [], 'codex': [CODEX_AGENT_INSTALLED] if name == 'integration-specialist' else []}
        entry = {
            'id': name, 'kind': source['kind'], 'purpose': source['purpose'], 'clients': source['clients'],
            'scope': source['scope'], 'required': source['required'],
            'origin': {'kind': 'marketplace', 'locator': URL, 'revision': None}, 'declared_version': version,
            'files': files, 'permissions': source['permissions'], 'native': {},
        }
        found = {client: files['common'] + files[client] for client in entry['clients']}
        entry['expected'] = {
            'contract_sha256': capabilities.contract_digest(entry),
            'files_sha256': {client: capabilities.records_digest({p: shipped[p] for p in paths}) if paths else None
                             for client, paths in found.items()},
        }
        entries.append(entry)
    data = _json({'version': 3, 'capabilities': entries})
    try:
        capabilities.catalog_from_bytes(data)  # what init installs is what the audit accepts
    except ValueError as error:
        raise RuntimeError(f'the generated catalog is not valid: {error}') from error
    return data


def render(root: Path) -> dict[str, bytes]:
    """Repository-relative path -> bytes of every generated file, read from the sources under `root`."""
    root = Path(root)
    version = _version(root)
    files = {
        '.claude-plugin/marketplace.json': _json({
            'name': NAME,
            'owner': {'name': OWNER},
            'metadata': {'description': DESCRIPTION},
            'plugins': [{'name': NAME, 'source': f'./{PLUGIN}', 'description': DESCRIPTION, 'version': version}],
        }),
        f'{PLUGIN}/.claude-plugin/plugin.json': _json({
            'name': NAME, 'version': version, 'description': DESCRIPTION, 'author': {'name': OWNER},
            'homepage': URL, 'repository': URL, 'license': 'MIT',
        }),
        f'{PLUGIN}/.codex-plugin/plugin.json': _json({
            'name': NAME, 'version': version, 'description': DESCRIPTION,
            'skills': './skills/', 'hooks': './hooks/hooks.json',
        }),
        f'{PLUGIN}/agents/integration-specialist.md':
            _claude_agent(_text(root / '.claude/agents/integration-specialist.md')).encode(),
        CODEX_AGENT: _name_the_skill(_text(root / '.codex/agents/integration-specialist.toml')).encode(),
        f'{PLUGIN}/hooks/source_prompt.py': (root / 'scripts/source_prompt.py').read_bytes(),
    }
    for skill in CORE_SKILLS:
        source = root / 'skills' / skill
        for page in sorted([source / 'SKILL.md', *source.glob('references/*.md')]):
            files[f'{PLUGIN}/skills/{skill}/{page.relative_to(source).as_posix()}'] = rewrite_skill(_text(page)).encode()
    files[CATALOG] = _catalog(root, version, files[CODEX_AGENT])
    return dict(sorted(files.items()))


def _leftovers(root: Path, generated: dict[str, bytes]) -> list[str]:
    """Files in the plugin that are neither generated nor written by hand."""
    found = {p.relative_to(root).as_posix() for p in (root / PLUGIN).rglob('*') if p.is_file()}
    return sorted(found - set(generated) - set(HANDWRITTEN))


def _different(root: Path, generated: dict[str, bytes]) -> list[str]:
    return [rel for rel, data in generated.items() if not (root / rel).is_file() or (root / rel).read_bytes() != data]


def _write(root: Path, generated: dict[str, bytes]) -> None:
    """Make the tree equal to `generated`: drop leftovers and empty folders, write what differs."""
    for rel in _leftovers(root, generated):
        (root / rel).unlink()
    for folder in sorted((root / PLUGIN).rglob('*'), reverse=True):  # deepest first
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    for rel in _different(root, generated):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(generated[rel])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true', help='write nothing; exit 1 and list the paths that are stale')
    parser.add_argument('--root', default=str(ROOT), help='repository to read and write (default: this one)')
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        generated = render(root)
    except (OSError, RuntimeError) as error:
        print(f'build_plugin: {error}', file=sys.stderr)
        return 1
    if args.check:
        stale = sorted(_different(root, generated) + _leftovers(root, generated))
        for rel in stale:
            print(f'stale: {rel}', file=sys.stderr)
        if stale:
            print('run: python3 tools/build_plugin.py', file=sys.stderr)
        return 1 if stale else 0
    _write(root, generated)
    print(f'{root}: {len(generated)} generated files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
