"""Agent choices remain declarations; validation never opens a model connection."""
import copy
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def minimal_config():
    return dict(schema_version=1, agents={role: {} for role in ('pm', 'tech_lead', 'developer', 'qa')})


def configured():
    raw = minimal_config()
    for agent in raw['agents'].values():
        agent.update(client='codex', model='fixture-a', effort=dict(level='medium', native_value=None))
    raw['limits'] = dict(mission_active_seconds=600, agent_seconds=60, max_agent_runs=10, max_deploy_attempts=1)
    return raw


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_config'), 'mission_config not implemented')
        self.config = importlib.import_module('mission_config')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_defaults_do_not_choose_models(self):
        c = self.config.normalize_config(minimal_config())
        self.assertEqual(c['limits']['max_active_pbis'], 3)
        self.assertEqual(c['limits']['max_parallel_agents'], 3)
        self.assertEqual(c['limits']['max_correction_cycles'], 3)
        self.assertEqual(c['deploy_mode'], 'manual')
        self.assertIsNone(c['agents']['pm']['model'])
        self.assertEqual(c['agents']['pm']['connection'], 'authenticated')
        self.assertIn('agents.pm.model', self.config.config_gaps(c))
        self.assertEqual(self.snapshot(), {})

    def test_overrides_preserve_project_and_other_roles(self):
        defaults = self.config.normalize_config(configured())
        before = copy.deepcopy(defaults)
        effective = self.config.effective_config(defaults, {'agents': {'pm': {'model': 'fixture-b'}}})
        self.assertEqual(defaults, before)
        self.assertEqual(effective['agents']['pm']['model'], 'fixture-b')
        self.assertEqual(effective['agents']['qa'], defaults['agents']['qa'])
        self.assertNotEqual(self.config.config_digest(effective), self.config.config_digest(defaults))
        self.assertEqual(self.config.config_gaps(effective), [])
        reordered = dict(reversed(list(defaults.items())))
        self.assertEqual(self.config.config_digest(reordered), self.config.config_digest(defaults))

    def test_invalid_inputs_do_not_echo_or_write(self):
        path = self.root / 'youngcrow/agents.json'
        path.parent.mkdir()
        cases = []
        for key, value in [('max_active_pbis', True), ('agent_seconds', 0), ('max_agent_runs', -1),
                           ('max_correction_cycles', 4), ('api_budget_usd', 'Infinity')]:
            raw = configured(); raw['limits'][key] = value; cases.append(json.dumps(raw))
        for patch in ({'schema_version': True}, {'schema_version': 2}, {'api_key': 'secret-fixture'},
                      {'agents': {'unexpected': {}}}):
            raw = configured(); raw.update(patch); cases.append(json.dumps(raw))
        for field, value in [('credential_env', 'secret-fixture'), ('password', 'secret-fixture'),
                             ('effort', {'level': 'medium', 'native_value': 'extra'})]:
            raw = configured(); raw['agents']['pm'][field] = value; cases.append(json.dumps(raw))
        cases += ['{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}']
        for text in cases:
            with self.subTest(text=text[:40]):
                path.write_text(text, encoding='utf-8')
                before = self.snapshot()
                with self.assertRaises(ValueError) as raised:
                    self.config.load_config(self.root)
                self.assertNotIn('secret-fixture', str(raised.exception))
                self.assertEqual(self.snapshot(), before)

    def test_unknown_native_effort_stays_unverified(self):
        raw = configured()
        raw['agents']['pm']['effort'] = dict(level='native', native_value='future-level')
        c = self.config.normalize_config(raw)
        self.assertEqual(c['agents']['pm']['effort']['native_value'], 'future-level')
        self.assertNotIn('supported', c['agents']['pm'])
        self.assertEqual(self.snapshot(), {})

    def test_api_is_explicit_and_budget_is_not_a_secret_lookup(self):
        raw = configured()
        raw['agents']['pm'].update(connection='api', credential_env='YC_FIXTURE_API')
        c = self.config.normalize_config(raw)
        self.assertIn('limits.api_budget_usd', self.config.config_gaps(c))
        raw['limits']['api_budget_usd'] = '1.50'
        self.assertEqual(self.config.config_gaps(self.config.normalize_config(raw)), [])
        self.assertEqual(self.config.normalize_config(raw)['agents']['pm']['credential_env'], 'YC_FIXTURE_API')
        for overrides in ({'agents': {'pm': None}}, {'limits': {'surprise': 5}}, {'agents': {'new': {}}}):
            with self.assertRaises(ValueError):
                self.config.effective_config(c, overrides)

    def test_linked_or_oversized_file_is_rejected(self):
        path = self.root / 'youngcrow/agents.json'
        path.parent.mkdir()
        source = self.root / 'source.json'
        source.write_text(json.dumps(configured()), encoding='utf-8')
        os.link(source, path)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.config.load_config(self.root)
        self.assertEqual(self.snapshot(), before)
        path.unlink()
        path.write_bytes(b' ' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            self.config.load_config(self.root)


if __name__ == '__main__':
    unittest.main()
