"""Document storage tests use real Git and isolated project files."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vault


class StorageTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATHEXT')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CEILING_DIRECTORIES=str(self.root.parent))
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.git('init', '-q')
        self.store = importlib.import_module('document_store')

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], env=self.env,
                              capture_output=True, check=check, timeout=10)

    def test_private_storage_is_ignored_and_vault_valid(self):
        identity = self.store.prepare_storage(self.root)
        uuid.UUID(identity)
        for rel in ('vault/local/index.md', '.operacao-local/docling/receipt.json'):
            self.assertEqual(self.git('check-ignore', '--quiet', '--', rel, check=False).returncode, 0)
        self.assertEqual(vault.check(self.root)['issues'], [])
        original = (self.root / 'vault/local/index.md').read_bytes()
        self.assertEqual(self.store.prepare_storage(self.root), identity)
        self.assertEqual((self.root / 'vault/local/index.md').read_bytes(), original)

    def test_tracked_private_file_refuses_before_changing_anything(self):
        target = self.root / 'vault/local/private.md'
        target.parent.mkdir(parents=True)
        target.write_text('private fixture', encoding='utf-8')
        self.git('add', '-f', '--', 'vault/local/private.md')
        with self.assertRaises(ValueError):
            self.store.prepare_storage(self.root)
        self.assertFalse((self.root / '.gitignore').exists())
        self.assertFalse((self.root / 'vault/project.json').exists())
        self.assertEqual(target.read_text(), 'private fixture')

    def test_parent_repository_and_negated_rule(self):
        self.root = self.root / 'nested'
        self.root.mkdir()
        ignore = self.root / '.gitignore'
        ignore.write_text('# preserve\n/vault/local/\n!/vault/local/', encoding='utf-8')
        self.store.prepare_storage(self.root)
        self.assertTrue(ignore.read_text().startswith('# preserve\n'))
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/index.md', check=False).returncode, 0)
        self.git('add', '--', '.')
        self.assertNotIn(b'vault/local/', self.git('ls-files', '-z').stdout)

    def test_nested_ignore_cannot_expose_an_existing_private_note(self):
        folder = self.root / 'vault/local'
        folder.mkdir(parents=True)
        (folder / '.gitignore').write_text('!*.md\n', encoding='utf-8')
        (folder / 'private.md').write_text('private', encoding='utf-8')
        self.store.prepare_storage(self.root)
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/private.md', check=False).returncode, 0)

    def test_without_git_rules_protect_after_git_init(self):
        self.root = Path(self.temp.name) / 'not yet git'
        self.root.mkdir()
        self.store.prepare_storage(self.root)
        self.git('init', '-q')
        self.assertEqual(self.git('check-ignore', '--quiet', '--', 'vault/local/index.md', check=False).returncode, 0)

    def test_wrong_directory_type_and_hardlink_refuse_without_writes(self):
        for rel in ('vault', '.gitignore'):
            with self.subTest(rel=rel):
                root = self.root / rel.replace('.', 'dot')
                root.mkdir()
                if rel == 'vault':
                    (root / rel).write_text('preserve')
                else:
                    outside = root / 'shared'
                    outside.write_text('preserve')
                    os.link(outside, root / rel)
                with self.assertRaises(ValueError):
                    self.store.prepare_storage(root)
                self.assertFalse((root / 'vault/project.json').exists())

    def test_junction_private_root_is_rejected(self):
        if os.name != 'nt':
            self.skipTest('Windows junction')
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'vault').mkdir()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.root / 'vault/local'), str(outside)],
                       check=True, capture_output=True)
        with self.assertRaises(ValueError):
            self.store.prepare_storage(self.root)
        self.assertEqual(list(outside.iterdir()), [])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.documents = importlib.import_module('documents')

    def test_doctor_missing_runtime_does_not_write_or_install(self):
        before = list(self.root.rglob('*'))
        with patch('subprocess.Popen', side_effect=AssertionError('must not execute')):
            result = self.documents.doctor(self.root)
        self.assertEqual(result['state'], 'pending')
        self.assertIn('runtime_missing', result['warnings'])
        self.assertEqual(list(self.root.rglob('*')), before)

    def test_model_and_package_caches_are_private_without_inheriting_tokens(self):
        with patch.dict(os.environ, {'HF_TOKEN': 'private', 'PIP_INDEX_URL': 'https://private.invalid'}):
            env = self.documents.worker_environment(self.root)
        self.assertNotIn('HF_TOKEN', env)
        self.assertNotIn('PIP_INDEX_URL', env)
        for key in ('PIP_CACHE_DIR', 'HF_HOME', 'TORCH_HOME', 'LOCALAPPDATA', 'APPDATA', 'TEMP'):
            self.assertTrue(Path(env[key]).is_relative_to(self.root))

    def test_doctor_does_not_call_an_incomplete_ocr_runtime_ready(self):
        base = self.root / self.documents.BASE
        executable = self.documents.runtime_python(base / 'venv')
        executable.parent.mkdir(parents=True)
        executable.touch()
        model = base / 'models/model.bin'
        model.parent.mkdir()
        model.write_bytes(b'model')
        info = dict(docling=self.documents.VERSION, packages={'docling': self.documents.VERSION},
                    python='3.12.10', profile='documents', models=[dict(path='model.bin', size=5)])
        (base / 'environment.json').write_text(json.dumps(info))
        response = subprocess.CompletedProcess([], 0, json.dumps(info).encode(), b'')
        with patch('subprocess.run', return_value=response):
            result = self.documents.doctor(self.root)
        self.assertEqual(result['state'], 'pending')
        self.assertIn('runtime_dependencies_missing', result['warnings'])

    def test_worker_timeout_and_error_do_not_disclose_stderr(self):
        runtime = self.root / 'runtime'
        runtime.mkdir()
        executable = self.documents.runtime_python(runtime)
        executable.parent.mkdir()
        executable.touch()
        source = self.root / 'secret-name.html'
        source.write_text('private content')
        for failure in (subprocess.TimeoutExpired(['private'], 1800, stderr=b'secret'),
                        subprocess.CompletedProcess([], 1, b'', b'secret')):
            with self.subTest(failure=type(failure).__name__):
                output = self.root / str(uuid.uuid4())
                if isinstance(failure, Exception):
                    arguments = dict(side_effect=failure)
                else:
                    arguments = dict(return_value=failure)
                with patch('documents.run_process', **arguments):
                    result = self.documents.run_worker(source, output, runtime, 'documents')
                self.assertEqual(result['state'], 'failed')
                self.assertNotIn('secret', json.dumps(result))
                self.assertIsNone(result.get('note_path'))

    def test_worker_rejects_invalid_output_and_absent_runtime(self):
        source = self.root / 'input.html'
        source.touch()
        result = self.documents.run_worker(source, self.root / 'out', self.root / 'missing', 'documents')
        self.assertEqual(result['state'], 'pending')
        runtime = self.root / 'runtime'
        executable = self.documents.runtime_python(runtime)
        executable.parent.mkdir(parents=True)
        executable.touch()
        with patch('documents.run_process', return_value=subprocess.CompletedProcess([], 0, b'private text', b'')):
            result = self.documents.run_worker(source, self.root / 'out2', runtime, 'documents')
        self.assertEqual(result['state'], 'failed')
        self.assertNotIn('private text', json.dumps(result))

    def test_setup_does_not_replace_a_different_runtime(self):
        executable = self.documents.runtime_python(self.root / self.documents.BASE / 'venv')
        executable.parent.mkdir(parents=True)
        executable.touch()
        response = subprocess.CompletedProcess([], 0, b'{"docling":"0.0.1"}', b'')
        with patch('documents.run_process', return_value=response) as process:
            result = self.documents.setup(self.root)
        self.assertEqual(result['warnings'], ['runtime_version_mismatch'])
        self.assertEqual(process.call_count, 1)
        self.assertEqual(process.call_args.args[0][-1], 'versions')

    def test_worker_does_not_accept_linked_export_files(self):
        runtime = self.root / 'runtime'
        executable = self.documents.runtime_python(runtime)
        executable.parent.mkdir(parents=True)
        executable.touch()
        source = self.root / 'input.html'
        source.write_text('preserve original')
        output = self.root / 'out'
        def linked_export(*args, **kwargs):
            os.link(source, output / 'content.md')
            (output / 'document.json').write_text('{}')
            return subprocess.CompletedProcess([], 0, b'{"state":"ready","coverage":{},"warnings":[],"converter":{}}', b'')
        with patch('documents.run_process', side_effect=linked_export):
            result = self.documents.run_worker(source, output, runtime)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(source.read_text(), 'preserve original')


if __name__ == '__main__':
    unittest.main()
