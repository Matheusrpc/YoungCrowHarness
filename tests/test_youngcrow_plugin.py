"""Check the youngcrow plugin tree is what `tools/build_plugin.py` generates from the repository sources."""
from contextlib import redirect_stderr, redirect_stdout
from importlib import util
from pathlib import Path
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'scripts'))

import capabilities as caps  # noqa: E402
from youngcrow import __version__  # noqa: E402
from youngcrow.payload import PAYLOAD  # noqa: E402

PLUGIN = REPO / 'plugins' / 'youngcrow'
CATALOG = REPO / 'src' / 'youngcrow' / 'templates' / 'capabilities.json'
CODEX_AGENT = '.codex/agents/integration-specialist.toml'
SOURCES = ('skills', '.claude/agents', '.codex/agents', 'scripts', 'requirements', 'skills-lock.json',
           'src/youngcrow/__init__.py', 'src/youngcrow/payload.py')


def load_tool():
    spec = util.spec_from_file_location('build_plugin_tool', REPO / 'tools' / 'build_plugin.py')
    tool = util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def copy_sources(root):
    """The files `render` reads, copied from the repository into `root`."""
    for rel in SOURCES:
        source, target = REPO / rel, root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copyfile(source, target)


class TreeTests(unittest.TestCase):
    """The committed plugin tree against the generator."""

    def test_generated_files_are_fresh(self):
        tool = load_tool()
        stale = [rel for rel, data in tool.render(REPO).items() if (REPO / rel).read_bytes() != data]
        self.assertEqual(stale, [], 'run: python3 tools/build_plugin.py')

    def test_the_plugin_holds_only_generated_and_handwritten_files(self):
        tool = load_tool()
        on_disk = {p.relative_to(REPO).as_posix() for p in PLUGIN.rglob('*') if p.is_file()}
        generated = {rel for rel in tool.render(REPO) if rel.startswith('plugins/')}
        self.assertEqual(on_disk - set(tool.HANDWRITTEN), generated)

    def test_the_core_skills_are_exactly_the_five_in_the_plan(self):
        tool = load_tool()
        self.assertEqual(tool.CORE_SKILLS, ('govern-capabilities', 'ingest-source', 'integrate-from-docs',
                                            'personalizer', 'retrieve-memory'))
        shipped = sorted(p.parent.name for p in (PLUGIN / 'skills').glob('*/SKILL.md'))
        self.assertEqual(shipped, list(tool.CORE_SKILLS))

    def test_skills_call_the_installed_scripts(self):
        for path in (PLUGIN / 'skills').rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(?<![\w./-])scripts/', path)
            self.assertNotIn('../yc-', text, path)

    def test_relative_links_stay_inside_the_plugin(self):
        pages = list(PLUGIN.rglob('*.md'))
        self.assertTrue(pages)
        for page in pages:
            for target in re.findall(r'\]\(([^)\s]+)\)', page.read_text(encoding='utf-8')):
                if re.match(r'[a-z][a-z0-9+.-]*:|#', target):
                    continue  # a URL or an anchor in the same page
                linked = (page.parent / target.split('#')[0]).resolve()
                self.assertTrue(linked.is_file(), f'{page.relative_to(REPO)} links to {target}, which is missing')
                self.assertTrue(linked.is_relative_to(PLUGIN.resolve()), f'{page.relative_to(REPO)} links outside the plugin: {target}')

    def test_versions_match_the_package(self):
        marketplace = json.loads((REPO / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        claude = json.loads((PLUGIN / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        codex = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(claude['version'], __version__)
        self.assertEqual(codex['version'], __version__)
        self.assertEqual(marketplace['plugins'][0]['version'], __version__)

    def test_manifests_name_the_plugin_and_its_parts(self):
        marketplace = json.loads((REPO / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        claude = json.loads((PLUGIN / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        codex = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        description = 'Proof-first memory, sources and capability governance for Claude Code and Codex projects.'
        self.assertEqual(marketplace['name'], 'youngcrow')
        self.assertEqual(marketplace['owner'], {'name': 'Matheusrpc'})
        self.assertEqual(marketplace['metadata'], {'description': description})
        self.assertEqual(marketplace['plugins'], [{'name': 'youngcrow', 'source': './plugins/youngcrow',
                                                   'description': description, 'version': __version__}])
        self.assertEqual(claude['name'], 'youngcrow')
        self.assertEqual(claude['description'], description)
        self.assertEqual(claude['author'], {'name': 'Matheusrpc'})
        self.assertEqual(claude['homepage'], 'https://github.com/Matheusrpc/YoungCrowHarness')
        self.assertEqual(claude['repository'], 'https://github.com/Matheusrpc/YoungCrowHarness')
        self.assertEqual(claude['license'], 'MIT')
        self.assertEqual(codex['name'], 'youngcrow')
        self.assertEqual(codex['description'], description)
        self.assertEqual(codex['skills'], './skills/')
        self.assertEqual(codex['hooks'], './hooks/hooks.json')

    def test_json_files_use_two_spaces_lf_and_a_final_newline(self):
        for path in (REPO / '.claude-plugin/marketplace.json', PLUGIN / '.claude-plugin/plugin.json',
                     PLUGIN / '.codex-plugin/plugin.json', CATALOG):
            raw = path.read_bytes()
            self.assertEqual(raw, (json.dumps(json.loads(raw), indent=2) + '\n').encode(), path)
            self.assertNotIn(b'\r', raw, path)

    def test_the_hook_script_is_a_byte_copy_of_source_prompt(self):
        self.assertEqual((PLUGIN / 'hooks/source_prompt.py').read_bytes(), (REPO / 'scripts/source_prompt.py').read_bytes())

    def test_the_claude_agent_drops_the_skills_block_and_names_the_skill(self):
        text = (PLUGIN / 'agents/integration-specialist.md').read_text(encoding='utf-8')
        frontmatter = text.split('---\n')[1]
        self.assertNotIn('skills:', frontmatter)
        self.assertIn('name: integration-specialist\n', frontmatter)
        self.assertIn('the integrate-from-docs skill', text)
        self.assertNotIn('skills/integrate-from-docs/SKILL.md', text)

    def test_the_codex_agent_template_names_the_skill_instead_of_its_path(self):
        text = (REPO / 'src/youngcrow/templates/codex/integration-specialist.toml').read_text(encoding='utf-8')
        self.assertIn('Read AGENTS.md, CLAUDE.md and the integrate-from-docs skill before acting.', text)
        self.assertNotIn('SKILL.md', text)

    def test_claude_validates_the_marketplace_and_the_plugin(self):
        claude = shutil.which('claude')
        if claude is None:
            self.skipTest('claude is not on PATH')
        # Without a marketplace file the validator takes the repository for a plugin and passes, so the
        # first line of the output says which of the two it checked.
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, HOME=str(Path(tmp, 'home')), CLAUDE_CONFIG_DIR=str(Path(tmp, 'claude')))
            for name in ('HOME', 'CLAUDE_CONFIG_DIR'):
                Path(env[name]).mkdir()
            for target, checked in ((REPO, 'Validating marketplace manifest'), (PLUGIN, 'Validating plugin manifest')):
                run = subprocess.run([claude, 'plugin', 'validate', str(target)], env=env, cwd=tmp,
                                     capture_output=True, text=True, timeout=180)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertIn(checked, run.stdout)


class CatalogTemplateTests(unittest.TestCase):
    """`src/youngcrow/templates/capabilities.json`: the catalog `youngcrow init` puts in a project."""

    CORE = ('govern-capabilities', 'ingest-source', 'integrate-from-docs', 'personalizer', 'retrieve-memory',
            'integration-specialist', 'docling', 'graphify')

    @classmethod
    def setUpClass(cls):
        cls.raw = CATALOG.read_bytes()
        cls.catalog = {cap['id']: cap for cap in caps.catalog_from_bytes(cls.raw)}
        cls.lock = {cap['id']: cap for cap in caps.load_catalog(REPO)}

    def test_it_is_a_version_3_catalog_with_nothing_but_capabilities(self):
        data = json.loads(self.raw)
        self.assertEqual(list(data), ['version', 'capabilities'])
        self.assertEqual(data['version'], 3)

    def test_it_lists_the_core_and_nothing_else(self):
        self.assertEqual(sorted(self.catalog), sorted(self.CORE))

    def test_each_entry_copies_what_the_repository_catalog_says_about_it(self):
        for name, cap in self.catalog.items():
            for field in ('kind', 'purpose', 'clients', 'required', 'scope', 'permissions'):
                self.assertEqual(cap[field], self.lock[name][field], f'{name}.{field}')

    def test_origin_version_and_native_are_the_marketplace_the_package_and_nothing(self):
        for name, cap in self.catalog.items():
            self.assertEqual(cap['origin'], {'kind': 'marketplace', 'revision': None,
                                             'locator': 'https://github.com/Matheusrpc/YoungCrowHarness'}, name)
            self.assertEqual(cap['declared_version'], __version__, name)
            self.assertEqual(cap['native'], {}, name)

    def test_files_are_the_installed_scripts_and_requirements_and_the_codex_agent(self):
        for name, cap in self.catalog.items():
            files = cap['files']
            self.assertEqual(files['claude'], [], name)
            self.assertEqual(files['codex'], [CODEX_AGENT] if name == 'integration-specialist' else [], name)
            for path in files['common']:
                self.assertTrue(path.startswith('.youngcrow/'), path)
                self.assertIn(path[len('.youngcrow/'):], PAYLOAD, f'{name}: init does not install {path}')
            # The repository's own list, less the skill pages the plugin carries and the scripts init does not install.
            kept = [f'.youngcrow/{p}' for p in self.lock[name]['files']['common'] if p in PAYLOAD]
            self.assertEqual(files['common'], kept, name)
        self.assertEqual(self.catalog['integration-specialist']['files']['common'], [])
        self.assertEqual(self.catalog['govern-capabilities']['files']['common'], [
            '.youngcrow/scripts/capabilities.py', '.youngcrow/scripts/integrations.py',
            '.youngcrow/scripts/document_store.py', '.youngcrow/scripts/vault.py'])
        self.assertEqual(self.catalog['docling']['files']['common'], ['.youngcrow/requirements/docling.txt'])
        self.assertEqual(self.catalog['graphify']['files']['common'], ['.youngcrow/requirements/graphify.txt'])

    def test_no_entry_names_a_script_that_init_leaves_out(self):
        for name, cap in self.catalog.items():
            self.assertFalse([p for p in cap['files']['common'] if 'mission' in p or '/skills/' in p], name)

    def test_expected_digests_are_those_of_the_bytes_init_installs(self):
        installed = {f'.youngcrow/{rel}': (REPO / rel).read_bytes() for rel in PAYLOAD}
        installed[CODEX_AGENT] = (REPO / 'src/youngcrow/templates/codex/integration-specialist.toml').read_bytes()
        for name, cap in self.catalog.items():
            self.assertEqual(cap['expected']['contract_sha256'], caps.contract_digest(cap), name)
            for client in caps.CLIENTS:
                paths = cap['files']['common'] + cap['files'][client]
                wanted = caps.records_digest({p: installed[p] for p in paths}) if paths else None
                self.assertEqual(cap['expected']['files_sha256'][client], wanted, f'{name}/{client}')

    def test_the_agent_has_a_digest_only_for_the_client_whose_file_it_carries(self):
        expected = self.catalog['integration-specialist']['expected']['files_sha256']
        self.assertIsNone(expected['claude'])
        self.assertRegex(expected['codex'], r'^[0-9a-f]{64}$')

    def test_the_skills_are_required_and_the_agent_and_runtimes_are_not(self):
        for name in self.CORE[:5]:
            self.assertEqual(self.catalog[name]['required'], {'claude': True, 'codex': True}, name)
        for name in self.CORE[5:]:
            self.assertEqual(self.catalog[name]['required'], {'claude': False, 'codex': False}, name)


class RewriteTests(unittest.TestCase):
    """The text rules applied to skills and agents."""

    def test_rewrite_skill(self):
        tool = load_tool()
        self.assertEqual(tool.rewrite_skill('Run `python3 scripts/vault.py check`.'),
                         'Run `python3 .youngcrow/scripts/vault.py check`.')
        self.assertEqual(tool.rewrite_skill('see [yc-config](../yc-config/SKILL.md)'), 'see `yc-config`')
        self.assertEqual(tool.rewrite_skill('[memory](../retrieve-memory/SKILL.md)'),
                         '[memory](../retrieve-memory/SKILL.md)')
        self.assertEqual(tool.rewrite_skill('.youngcrow/scripts/x.py'), '.youngcrow/scripts/x.py')

    def test_rewrite_skill_covers_requirements_and_links_from_references(self):
        tool = load_tool()
        self.assertEqual(tool.rewrite_skill('pip install -r requirements/docling.txt'),
                         'pip install -r .youngcrow/requirements/docling.txt')
        self.assertEqual(tool.rewrite_skill('[x](../../yc-status/SKILL.md) and [y](../../ingest-source/SKILL.md)'),
                         '`yc-status` and [y](../../ingest-source/SKILL.md)')

    def test_rewrite_skill_leaves_other_paths_alone(self):
        tool = load_tool()
        for text in ('docs/scripts/x.py', 'https://example.com/scripts/a', 'my-scripts/a', 'skills/MCPs/hooks',
                     '[x](references/memory.md)', '[x](https://example.com/yc-config/SKILL.md)'):
            self.assertEqual(tool.rewrite_skill(text), text)

    def test_rewrite_skill_is_idempotent(self):
        tool = load_tool()
        once = tool.rewrite_skill('python3 scripts/a.py then [c](../yc-config/SKILL.md)')
        self.assertEqual(tool.rewrite_skill(once), once)


class CommandTests(unittest.TestCase):
    """`main` writes the tree and `--check` reports what is stale."""

    def setUp(self):
        self.tool = load_tool()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        copy_sources(self.root)

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = self.tool.main([*args, '--root', str(self.root)])
        return code, err.getvalue()

    def test_a_written_tree_is_fresh(self):
        self.assertEqual(self.run_main(), (0, ''))
        self.assertEqual(self.run_main('--check'), (0, ''))
        self.assertEqual(self.root.joinpath('plugins/youngcrow/hooks/source_prompt.py').read_bytes(),
                         REPO.joinpath('scripts/source_prompt.py').read_bytes())

    def test_check_lists_a_missing_a_changed_and_an_extra_file(self):
        self.run_main()
        plugin = self.root / 'plugins/youngcrow'
        (plugin / '.claude-plugin/plugin.json').write_text('{}\n')
        (plugin / 'skills/personalizer/SKILL.md').unlink()
        (plugin / 'skills/leftover.md').write_text('old\n')
        code, err = self.run_main('--check')
        self.assertEqual(code, 1)
        for rel in ('plugins/youngcrow/.claude-plugin/plugin.json', 'plugins/youngcrow/skills/personalizer/SKILL.md',
                    'plugins/youngcrow/skills/leftover.md'):
            self.assertIn(rel, err)
        self.assertNotIn('marketplace.json', err)

    def test_writing_removes_files_the_generator_no_longer_makes_but_keeps_the_handwritten_ones(self):
        self.run_main()
        hooks = self.root / 'plugins/youngcrow/hooks'
        (hooks / 'hooks.json').write_text('{}\n')
        (self.root / 'plugins/youngcrow/skills/retired/references').mkdir(parents=True)
        (self.root / 'plugins/youngcrow/skills/retired/references/a.md').write_text('old\n')
        self.assertEqual(self.run_main()[0], 0)
        self.assertFalse((self.root / 'plugins/youngcrow/skills/retired').exists())
        self.assertEqual((hooks / 'hooks.json').read_text(), '{}\n')
        self.assertEqual(self.run_main('--check'), (0, ''))

    def test_a_new_reference_page_in_a_core_skill_is_picked_up(self):
        (self.root / 'skills/retrieve-memory/references').mkdir()
        (self.root / 'skills/retrieve-memory/references/extra.md').write_text('See scripts/memory.py\n')
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual((self.root / 'plugins/youngcrow/skills/retrieve-memory/references/extra.md').read_text(),
                         'See .youngcrow/scripts/memory.py\n')

    def test_the_catalog_template_is_written_with_the_tree(self):
        self.assertEqual(self.run_main(), (0, ''))
        self.assertEqual((self.root / 'src/youngcrow/templates/capabilities.json').read_bytes(), CATALOG.read_bytes())

    def test_a_change_to_an_installed_script_makes_the_catalog_template_stale(self):
        self.run_main()
        script = self.root / 'scripts/memory.py'
        script.write_bytes(script.read_bytes() + b'# changed\n')
        code, err = self.run_main('--check')
        self.assertEqual(code, 1)
        self.assertIn('stale: src/youngcrow/templates/capabilities.json', err)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.run_main('--check'), (0, ''))
        self.assertNotEqual((self.root / 'src/youngcrow/templates/capabilities.json').read_bytes(), CATALOG.read_bytes())

    def test_a_change_to_the_agent_template_source_makes_the_catalog_template_stale(self):
        self.run_main()
        agent = self.root / '.codex/agents/integration-specialist.toml'
        agent.write_text(agent.read_text() + '# changed\n')
        code, err = self.run_main('--check')
        self.assertEqual(code, 1)
        self.assertIn('stale: src/youngcrow/templates/capabilities.json', err)

    def test_a_core_capability_missing_from_the_repository_catalog_stops_the_build(self):
        lock = self.root / 'skills-lock.json'
        data = json.loads(lock.read_text(encoding='utf-8'))
        data['capabilities'] = [cap for cap in data['capabilities'] if cap['id'] != 'graphify']
        lock.write_text(json.dumps(data), encoding='utf-8')
        code, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn('graphify', err)
        self.assertFalse((self.root / 'plugins').exists())  # nothing written

    def test_the_version_comes_from_the_package(self):
        init = self.root / 'src/youngcrow/__init__.py'
        init.write_text(init.read_text().replace(__version__, '9.8.7'))
        self.run_main()
        manifest = json.loads((self.root / 'plugins/youngcrow/.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['version'], '9.8.7')


if __name__ == '__main__':
    unittest.main()
