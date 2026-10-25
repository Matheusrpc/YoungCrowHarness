"""Check the plugin wiring `youngcrow init` adds to `.claude/settings.json`, and takes out again."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from youngcrow.settings import (  # noqa: E402
    CLAUDE_SETTINGS, WIRING, SettingsSkipped, add_wiring, added_pairs, remove_wiring, unwire,
)

MARKETPLACE = ['extraKnownMarketplaces', 'youngcrow']
PLUGIN = ['enabledPlugins', 'youngcrow@youngcrow']
BOTH = [MARKETPLACE, PLUGIN]

FRESH = (b'{\n  "extraKnownMarketplaces": {\n    "youngcrow": {\n      "source": {\n        "source": "github",\n'
         b'        "repo": "Matheusrpc/YoungCrowHarness"\n      }\n    }\n  },\n  "enabledPlugins": {\n'
         b'    "youngcrow@youngcrow": true\n  }\n}\n')


class AddWiringTests(unittest.TestCase):
    # The brief's tests.

    def test_add_wiring_keeps_other_plugins_and_crlf(self):
        data = b'{\r\n  "enabledPlugins": {"other@x": true}\r\n}\r\n'
        out = add_wiring(data)
        self.assertIn(b'\r\n', out)
        self.assertNotIn(b'\n', out.replace(b'\r\n', b''))
        self.assertEqual(json.loads(out)['enabledPlugins'], {'other@x': True, 'youngcrow@youngcrow': True})

    def test_add_wiring_refuses_what_it_does_not_own(self):
        for data in (b'not json', b'[]', b'{"enabledPlugins": []}', b'{"enabledPlugins": {"youngcrow@youngcrow": false}}'):
            with self.subTest(data=data), self.assertRaises(SettingsSkipped):
                add_wiring(data)

    # The values and the format.

    def test_the_constants_are_the_planned_ones(self):
        self.assertEqual(CLAUDE_SETTINGS, '.claude/settings.json')
        self.assertEqual(WIRING, {
            'extraKnownMarketplaces': {'youngcrow': {'source': {'source': 'github', 'repo': 'Matheusrpc/YoungCrowHarness'}}},
            'enabledPlugins': {'youngcrow@youngcrow': True}})

    def test_a_missing_file_gets_the_wiring_with_two_space_indent_lf_and_a_final_newline(self):
        self.assertEqual(add_wiring(None), FRESH)

    def test_other_keys_and_their_order_stay_and_ours_go_last(self):
        data = '{"permissions": {"allow": ["Read"]}, "enabledPlugins": {"a@b": false}, "título": "ação"}'.encode()
        out = json.loads(add_wiring(data))
        self.assertEqual(list(out), ['permissions', 'enabledPlugins', 'título', 'extraKnownMarketplaces'])
        self.assertEqual(list(out['enabledPlugins']), ['a@b', 'youngcrow@youngcrow'])
        self.assertEqual(out['título'], 'ação')
        self.assertIn('"título": "ação"'.encode(), add_wiring(data))  # written as text, not \u escapes

    def test_a_file_that_already_has_everything_gives_none(self):
        self.assertIsNone(add_wiring(FRESH))
        self.assertIsNone(add_wiring(json.dumps({'x': 1, **WIRING}).encode()))

    def test_a_file_with_one_of_our_keys_gets_only_the_other(self):
        out = json.loads(add_wiring(b'{"enabledPlugins": {"youngcrow@youngcrow": true}}'))
        self.assertEqual(out, WIRING)
        self.assertEqual(list(out), ['enabledPlugins', 'extraKnownMarketplaces'])

    def test_every_refusal_names_the_reason(self):
        cases = {
            b'\xff\xfe{}': 'UTF-8',
            '﻿{}'.encode(): 'JSON',
            b'{"a": 1} trailing': 'JSON',
            b'"text"': 'object',
            b'{"extraKnownMarketplaces": "github"}': 'extraKnownMarketplaces',
            b'{"extraKnownMarketplaces": {"youngcrow": {"source": {"source": "git", "url": "x"}}}}': 'youngcrow',
            b'{"enabledPlugins": {"youngcrow@youngcrow": 1}}': 'youngcrow@youngcrow',
        }
        for data, word in cases.items():
            with self.subTest(data=data), self.assertRaises(SettingsSkipped) as caught:
                add_wiring(data)
            self.assertIn(word, str(caught.exception))
        self.assertTrue(issubclass(SettingsSkipped, ValueError))

    # The pairs init records (R49): only the ones add_wiring itself adds.

    def test_added_pairs_names_what_add_wiring_adds(self):
        self.assertEqual(added_pairs(None), BOTH)
        self.assertEqual(added_pairs(b'{"enabledPlugins": {"youngcrow@youngcrow": true}}'), [MARKETPLACE])
        self.assertEqual(added_pairs(FRESH), [])
        with self.assertRaises(SettingsSkipped):
            added_pairs(b'{"enabledPlugins": []}')


class RemoveWiringTests(unittest.TestCase):
    def test_remove_wiring_undoes_add_wiring(self):
        self.assertIsNone(remove_wiring(add_wiring(None), BOTH))
        self.assertEqual(json.loads(remove_wiring(add_wiring(b'{"permissions": {"allow": ["Read"]}}'), BOTH)),
                         {'permissions': {'allow': ['Read']}})

    def test_only_the_pairs_init_added_come_out(self):
        before = b'{"enabledPlugins": {"youngcrow@youngcrow": true}}'
        out = remove_wiring(add_wiring(before), added_pairs(before))
        self.assertEqual(json.loads(out), {'enabledPlugins': {'youngcrow@youngcrow': True}})
        self.assertEqual(remove_wiring(FRESH, []), FRESH)

    def test_a_pair_that_is_not_ours_is_ignored(self):
        data = b'{"enabledPlugins": {"other@x": true}}'
        self.assertEqual(remove_wiring(data, [['enabledPlugins', 'other@x'], ['permissions', 'allow']]), data)

    def test_other_plugins_and_marketplaces_stay(self):
        data = json.dumps({'enabledPlugins': {'other@x': True, 'youngcrow@youngcrow': True},
                           'extraKnownMarketplaces': {'x': {'source': {'source': 'github', 'repo': 'a/x'}},
                                                      **WIRING['extraKnownMarketplaces']}}).encode()
        self.assertEqual(json.loads(remove_wiring(data, BOTH)), {
            'enabledPlugins': {'other@x': True},
            'extraKnownMarketplaces': {'x': {'source': {'source': 'github', 'repo': 'a/x'}}}})

    def test_a_sub_key_the_user_changed_stays(self):
        data = json.dumps({'enabledPlugins': {'youngcrow@youngcrow': False},
                           **{k: v for k, v in WIRING.items() if k != 'enabledPlugins'}}).encode()
        self.assertEqual(json.loads(remove_wiring(data, BOTH)), {'enabledPlugins': {'youngcrow@youngcrow': False}})

    def test_an_object_the_user_left_empty_stays(self):
        data = json.dumps({'enabledPlugins': {}, 'extraKnownMarketplaces': WIRING['extraKnownMarketplaces']}).encode()
        self.assertEqual(json.loads(remove_wiring(data, BOTH)), {'enabledPlugins': {}})

    def test_crlf_stays(self):
        out = remove_wiring(add_wiring(b'{\r\n  "model": "x"\r\n}\r\n'), BOTH)
        self.assertEqual(out, b'{\r\n  "model": "x"\r\n}\r\n')

    def test_a_file_without_our_keys_comes_back_as_it_is(self):
        for data in (b'{"model":"x"}', b'{}', b'{"enabledPlugins": {}}'):
            with self.subTest(data=data):
                self.assertEqual(remove_wiring(data, BOTH), data)

    def test_a_file_that_is_not_a_json_object_is_refused(self):
        for data in (b'{oops', b'[]', b'\xff'):
            with self.subTest(data=data), self.assertRaises(SettingsSkipped):
                remove_wiring(data, BOTH)


class UnwireTests(unittest.TestCase):
    def test_the_original_comes_back_when_there_is_one(self):
        self.assertEqual(unwire(FRESH, b'{"model": "x"}', BOTH), b'{"model": "x"}')

    def test_without_an_original_only_our_keys_come_out(self):
        wired = add_wiring(b'{\r\n"model": "x"}')
        self.assertEqual(unwire(wired, None, BOTH), b'{\r\n  "model": "x"\r\n}\r\n')
        self.assertEqual(unwire(FRESH.replace(b'\n', b'\r\n'), None, BOTH), b'{}\r\n')
        self.assertEqual(json.loads(unwire(FRESH, None, [PLUGIN])), {'extraKnownMarketplaces': WIRING['extraKnownMarketplaces']})

    def test_a_file_that_is_no_longer_json_stays_as_it_is(self):
        self.assertEqual(unwire(b'{broken', None, BOTH), b'{broken')


if __name__ == '__main__':
    unittest.main()
