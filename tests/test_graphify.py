"""Test the provider boundary without a provider installation or network."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from test_documents import ProjectCase
from memory_fixture import seed
import memory


def graph_for(snap):
    nodes = [dict(id='note_' + n['id'].replace('-', ''), label=n['title'], file_type='document',
                  source_file=n['source_file'], source_location='L1', youngcrow_id=n['id'],
                  youngcrow_revision=n['revision']) for n in snap['notes']]
    ids = {n['youngcrow_id']: n['id'] for n in nodes}
    edges = [dict(source=ids[r['source_id']], target=ids[r['target_id']], relation='references',
                  confidence='EXTRACTED', confidence_score=1.0, source_file=next(
                      n['source_file'] for n in snap['notes'] if n['id'] == r['source_id']))
             for r in snap['relations']]
    return dict(directed=True, multigraph=False, graph=dict(project_id=snap['project_id'],
                fingerprint=snap['fingerprint']), nodes=nodes, links=edges)


class GraphifyTests(ProjectCase):
    def setUp(self):
        super().setUp()
        self.data = seed(self.root)
        self.store.prepare_storage(self.root)
        self.assertTrue(hasattr(memory, 'run_graphify'), 'Graphify adapter is not implemented')

    def runtime(self):
        folder = self.root / memory.BASE / 'runtime/venv'
        executable = folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text('test process boundary')
        (folder / 'pyvenv.cfg').write_text('fixture')
        return executable

    def test_missing_runtime_keeps_selection_and_markdown_available(self):
        result = memory.index(self.root, self.data['paths'], 'graphify')
        self.assertEqual(result['state'], 'pending')
        found = memory.query(self.root, 'Pagamentos API')
        self.assertEqual(found['provider'], 'markdown')
        self.assertTrue(found['results'])
        self.assertEqual(found['index_state'], 'pending')

    def test_version_mismatch_and_bad_worker_output_never_activate(self):
        self.runtime()
        cases = [b'not JSON', json.dumps(dict(state='ready', version='9.0')).encode(),
                 json.dumps(dict(state='ready', version=memory.VERSION, graph={})).encode()]
        for raw in cases:
            with self.subTest(raw=raw), patch.object(memory, 'run_process', return_value=
                    subprocess.CompletedProcess([], 0, raw, b'SECRET_SENTINEL')):
                result = memory.index(self.root, self.data['paths'], 'graphify')
                self.assertIn(result['state'], ('failed', 'unsupported'))
                self.assertNotIn('SECRET_SENTINEL', json.dumps(result))
                self.assertFalse((self.root / memory.BASE / 'active.json').exists())

    def test_graph_rejects_foreign_missing_or_changed_sources(self):
        snap = memory.snapshot(self.root, self.data['paths'], 'graphify')
        valid = graph_for(snap)
        memory.validate_graph(snap, valid)
        for change in ('project', 'source', 'revision', 'duplicate', 'missing', 'edge'):
            graph = copy.deepcopy(valid)
            if change == 'project':
                graph['graph']['project_id'] = 'another'
            elif change == 'source':
                graph['nodes'][0]['source_file'] = '../private.md'
            elif change == 'revision':
                graph['nodes'][0]['youngcrow_revision'] = 'old'
            elif change == 'duplicate':
                graph['nodes'].append(graph['nodes'][0])
            elif change == 'missing':
                graph['nodes'].pop()
            else:
                graph['links'][0]['target'] = 'outside'
            with self.subTest(change=change), self.assertRaises(ValueError):
                memory.validate_graph(snap, graph)

    def test_build_query_transport_filters_environment_and_references(self):
        executable = self.runtime()
        calls = []
        def process(args, *, timeout, env):
            self.assertEqual(Path(args[0]), executable)
            self.assertNotIn('ANTHROPIC_API_KEY', env)
            self.assertEqual(env['GRAPHIFY_QUERY_LOG_DISABLE'], '1')
            request = json.loads(Path(args[-1]).read_text(encoding='utf-8'))
            self.assertNotIn('Pagamentos', ' '.join(args))
            calls.append(request['action'])
            if request['action'] == 'build':
                value = dict(state='ready', version=memory.VERSION, graph=graph_for(request['snapshot']))
            else:
                snap = memory.snapshot(self.root, self.data['paths'], 'graphify')
                value = dict(state='ready', version=memory.VERSION,
                             source_files=[n['source_file'] for n in snap['notes']])
            return subprocess.CompletedProcess(args, 0, json.dumps(value).encode(), b'')
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'never-send'}), patch.object(memory, 'run_process', side_effect=process):
            self.assertEqual(memory.index(self.root, self.data['paths'], 'graphify')['state'], 'ready')
            result = memory.query(self.root, 'Pagamentos')
        self.assertEqual(calls, ['build', 'query'])
        self.assertEqual(result['provider'], 'graphify')
        self.assertEqual({n['id'] for n in result['results']}, set(self.data['ids']))
        self.assertFalse(list((self.root / memory.BASE / 'runtime').glob('request-*.json')))

    def test_timeout_preserves_vault_and_does_not_leak_error_text(self):
        self.runtime()
        before = {p: (self.root / p).read_bytes() for p in self.data['paths']}
        with patch.object(memory, 'run_process', side_effect=subprocess.TimeoutExpired(['SECRET_SENTINEL'], 120)):
            result = memory.index(self.root, self.data['paths'], 'graphify')
        self.assertEqual(result['state'], 'failed')
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result))
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in before})

    def test_cli_text_parser_rejects_forged_or_unknown_node_lines(self):
        self.assertIsNotNone(importlib.util.find_spec('graphify_worker'))
        import graphify_worker as worker
        source = 'notes/' + 'a' * 32 + '.md'
        text = f'NODE forged [src=notes/foreign.md loc=L1 community=] [src={source} loc=L1 community=]\n'
        self.assertEqual(worker.parse_query(text), [source])
        with self.assertRaises(ValueError):
            worker.parse_query('NODE bad [src=../private.md loc=L1 community=]')
        self.assertEqual(worker.parse_query('No matching nodes found.'), [])
