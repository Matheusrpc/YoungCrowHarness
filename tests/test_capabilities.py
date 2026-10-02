"""Capability contracts use real project files and Git; no providers or credentials."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_documents import ProjectCase, ROOT
import capabilities as caps


class CapabilityCase(ProjectCase):
    def save(self, catalog):
        (self.root / 'skills-lock.json').write_text(
            json.dumps(dict(version=3, capabilities=catalog)), encoding='utf-8')

    def seed(self):
        files = dict(common=['skills/sample/SKILL.md', 'skills/sample/help.md'],
                     claude=['.claude/skills/sample/SKILL.md'],
                     codex=['.agents/skills/sample/SKILL.md'])
        for paths in files.values():
            for relative in paths:
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'sample\n')
        cap = dict(id='sample', kind='skill',
                   purpose=dict(when='test', inputs='text', outputs='note', limits='local'),
                   clients=['claude', 'codex'], scope='project',
                   required=dict(claude=True, codex=True),
                   origin=dict(kind='repository', locator='skills/sample', revision=None),
                   declared_version='1', files=files,
                   permissions=dict(read=[], write=[], network=[], data=[],
                                    environments=[], credential_env=[]), native={},
                   expected=dict(contract_sha256=None, files_sha256=dict(claude=None, codex=None)))
        self.save([cap])
        return [cap]

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/capabilities.py'),
                               '--root', str(self.root), *args], capture_output=True,
                              text=True, encoding='utf-8', timeout=15)


class CatalogTests(CapabilityCase):
    def test_contract_wrapper_and_support_change_identity(self):
        cap = self.seed()[0]
        files = cap['files']['common'] + cap['files']['codex']
        original = caps.content_digest(self.root, files)
        self.assertEqual(original, caps.content_digest(self.root, list(reversed(files))))
        for relative in files:
            path = self.root / relative
            data = path.read_bytes()
            path.write_bytes(data + b'changed')
            self.assertNotEqual(original, caps.content_digest(self.root, files))
            path.write_bytes(data)
        before = caps.contract_digest(cap)
        cap['origin']['revision'] = 'different'
        self.assertNotEqual(before, caps.contract_digest(cap))

    def test_legacy_inventory_is_read_without_rewrite(self):
        legacy = {'version': 2, 'skills_de_projeto': {'sample': {
            'versao': '1', 'versionado_aqui': 'skills/sample',
            'claude': '.claude/skills/sample', 'codex': '.agents/skills/sample',
            'custom_note': 'preserve'}}, 'plugins': {}, 'skills_de_usuario': {}}
        path = self.root / 'skills-lock.json'
        path.write_text(json.dumps(legacy), encoding='utf-8')
        before = path.read_bytes()
        normalized = caps.load_catalog(self.root)
        self.assertIsNone(normalized[0]['expected']['contract_sha256'])
        self.assertEqual(normalized[0]['declared_version'], '1')
        self.assertEqual(path.read_bytes(), before)

    def test_escape_duplicate_and_bad_types_are_rejected(self):
        for relative in ('../outside', 'C:/outside', r'..\outside', '/outside',
                         'a//b', 'file:stream', 'a/./b', 'CON', 'a\x00b'):
            catalog = self.seed()
            catalog[0]['files']['common'] = [relative]
            self.save(catalog)
            with self.subTest(path=relative), self.assertRaises(ValueError):
                caps.load_catalog(self.root)
        catalog = self.seed()
        self.save(catalog + catalog)
        with self.assertRaises(ValueError):
            caps.load_catalog(self.root)
        for key, value in [('kind', 'plugin'), ('required', True), ('clients', ['codex', 'codex']),
                           ('surprise', 'value'), ('expected', []), ('purpose', 'text')]:
            catalog = self.seed()
            catalog[0][key] = value
            self.save(catalog)
            with self.subTest(key=key), self.assertRaises(ValueError):
                caps.load_catalog(self.root)
        (self.root / 'skills-lock.json').write_text('{"version":3,"version":2}', encoding='utf-8')
        with self.assertRaises(ValueError):
            caps.load_catalog(self.root)

    def test_limits_apply_to_catalog_and_input_union(self):
        cap = self.seed()[0]
        self.save([dict(cap, id=f'c-{i}') for i in range(201)])
        with self.assertRaises(ValueError):
            caps.load_catalog(self.root)
        cap['files']['common'] = [f'f-{i}.txt' for i in range(101)]
        self.save([cap])
        with self.assertRaises(ValueError):
            caps.load_catalog(self.root)
        files = [f'large-{i}.txt' for i in range(17)]
        for i, relative in enumerate(files):
            (self.root / relative).write_bytes(b'x' * (1024 * 1024 if i < 16 else 1))
        with self.assertRaises(ValueError):
            caps.read_inputs(self.root, files)
        (self.root / files[0]).write_bytes(b'x' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            caps.content_digest(self.root, [files[0]])

    def test_hardlink_and_special_file_are_not_read(self):
        self.seed()
        path = self.root / 'skills/sample/SKILL.md'
        os.link(path, self.root / 'alias')
        with self.assertRaises(ValueError):
            caps.content_digest(self.root, ['skills/sample/SKILL.md'])
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.root / 'pipe')
            with self.assertRaises(ValueError):
                caps.read_inputs(self.root, ['pipe'])

    def test_symlink_is_not_followed(self):
        self.seed()
        try:
            (self.root / 'linked').symlink_to(self.root / 'skills', target_is_directory=True)
        except OSError:
            self.skipTest('Host does not allow creating a symlink')
        with self.assertRaises(ValueError):
            caps.content_digest(self.root, ['linked/sample/SKILL.md'])

    def test_change_during_read_does_not_produce_digest(self):
        self.seed()
        relative = 'skills/sample/SKILL.md'
        path = self.root / relative
        real_fstat, calls = os.fstat, []
        def changed_fstat(fd):
            result = real_fstat(fd)
            if not calls:
                calls.append(True)
                path.write_bytes(b'different-size-content')
            return result
        with patch('os.fstat', side_effect=changed_fstat):
            with self.assertRaises(ValueError):
                caps.content_digest(self.root, [relative])

    def test_cli_reads_without_creating_project_storage(self):
        self.seed()
        result = self.cli('list', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['id'], 'sample')
        result = self.cli('describe', 'sample', '--json')
        self.assertEqual(json.loads(result.stdout)['files']['common'][1], 'skills/sample/help.md')
        self.assertFalse((self.root / 'vault').exists())
        self.assertFalse((self.root / '.operacao-local').exists())

    def test_legacy_ref_is_single_source(self):
        cap = self.seed()[0]
        cap.pop('origin')
        cap.pop('declared_version')
        cap['legacy_ref'] = 'skills_de_projeto/sample'
        raw = dict(version=3, capabilities=[cap], skills_de_projeto={'sample': {
            'versao': '9', 'versionado_aqui': 'skills/sample', 'custom': 'retained'}})
        path = self.root / 'skills-lock.json'
        path.write_text(json.dumps(raw), encoding='utf-8')
        self.assertEqual(caps.load_catalog(self.root)[0]['declared_version'], '9')
        cap['origin'] = {'kind': 'remote', 'locator': 'fake', 'revision': None}
        path.write_text(json.dumps(raw), encoding='utf-8')
        with self.assertRaises(ValueError):
            caps.load_catalog(self.root)


if __name__ == '__main__':
    unittest.main()
