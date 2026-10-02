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


class ProjectCase(unittest.TestCase):
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


class StorageTests(ProjectCase):
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


class IngestCase(ProjectCase):
    def setUp(self):
        super().setUp()
        self.documents = importlib.import_module('documents')
        self.source = self.root / 'private original.html'
        self.source.write_text('<p>Original content.</p>', encoding='utf-8')
        self.calls = []

    def convert(self, source, output, runtime, profile):
        self.calls.append(source.read_bytes())
        output.mkdir(parents=True)
        (output / 'content.md').write_text('Extracted source.\n<script>untrusted()</script>\n'
            '[Unsafe](file:///private.txt) ![remote](https://example.invalid/tracker.png)\n', encoding='utf-8')
        (output / 'document.json').write_text('{}')
        return dict(state='ready', warnings=[], coverage={'pages': [1]})

    def ingest(self, **kwargs):
        return self.documents.ingest(self.root, self.source, convert=self.convert, **kwargs)


class IngestTests(IngestCase):
    def test_ingest_and_repeat_keep_note_and_original_and_clean_vault(self):
        original = self.source.read_bytes()
        first = self.ingest()
        self.assertEqual(first['state'], 'ready')
        self.assertEqual(self.source.read_bytes(), original)
        text = (self.root / first['note_path']).read_text(encoding='utf-8')
        self.assertIn('Extracted source.', text)
        self.assertNotIn('<script>', text)
        self.assertNotIn('](file:', text)
        self.assertNotIn('![remote](https:', text)
        second = self.ingest()
        self.assertEqual(first['source_id'], second['source_id'])
        self.assertEqual(first['revision'], second['revision'])
        self.assertNotEqual(first['attempt_id'], second['attempt_id'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(vault.check(self.root)['issues'], [])
        self.git('add', '--', 'vault', '.gitignore')
        self.assertNotIn(b'vault/local/', self.git('ls-files', '-z').stdout)

    def test_same_bytes_different_sources_reuse_extraction_not_identity(self):
        first = self.ingest()
        other = self.root / 'different context.html'
        other.write_bytes(self.source.read_bytes())
        second = self.documents.ingest(self.root, other, convert=self.convert)
        self.assertNotEqual(first['source_id'], second['source_id'])
        self.assertEqual(first['revision'], second['revision'])
        self.assertNotEqual(first['note_path'], second['note_path'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(vault.check(self.root)['issues'], [])

    def test_failed_update_keeps_previous_revision(self):
        first = self.ingest()
        original = (self.root / first['note_path']).read_bytes()
        self.source.write_text('changed input')
        retry = self.documents.ingest(self.root, self.source, source_id=first['source_id'],
                                      convert=lambda *args: dict(state='failed', warnings=['conversion_failed']))
        self.assertEqual(retry['state'], 'failed')
        self.assertIsNone(retry['note_path'])
        self.assertEqual((self.root / first['note_path']).read_bytes(), original)
        status = self.documents.status(self.root, first['source_id'])[0]
        self.assertEqual(status['current_revision'], first['revision'])
        self.assertEqual(status['latest_attempt']['attempt_id'], retry['attempt_id'])

    def test_manual_note_edits_are_preserved(self):
        first = self.ingest()
        note = self.root / first['note_path']
        manual = note.read_text(encoding='utf-8') + '\nHuman clarification.\n'
        note.write_text(manual, encoding='utf-8')
        self.ingest()
        self.assertEqual(note.read_text(encoding='utf-8'), manual)

    def test_configuration_changes_create_new_revision(self):
        first = self.ingest()
        original = self.documents.converter_info(self.root, 'documents')
        changed = {**original, 'options': {**original['options'], 'fixture_option': True}}
        with patch('documents.converter_info', return_value=changed):
            second = self.ingest()
        self.assertNotEqual(first['revision'], second['revision'])
        self.assertEqual(len(self.calls), 2)

    def test_foreign_source_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.ingest(source_id=str(uuid.uuid4()))
        self.assertEqual(self.calls, [])

    def test_hash_and_conversion_use_copied_bytes(self):
        original = self.source.read_bytes()
        def mutate_original(source, output, runtime, profile):
            self.source.write_text('changed after snapshot')
            return self.convert(source, output, runtime, profile)
        first = self.documents.ingest(self.root, self.source, convert=mutate_original)
        self.assertEqual(first['state'], 'ready')
        self.assertEqual(self.calls, [original])
        second = self.ingest()
        self.assertNotEqual(first['revision'], second['revision'])

    def test_interrupt_is_resumable_and_lock_rejects_another_writer(self):
        def interrupt(*args):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.documents.ingest(self.root, self.source, convert=interrupt)
        records = self.documents.status(self.root)
        self.assertEqual(records[0]['latest_attempt']['state'], 'pending')
        self.assertEqual(self.ingest()['state'], 'ready')
        with self.store.project_lock(self.root):
            with self.assertRaises(ValueError):
                self.ingest()
            with patch('documents.run_process', side_effect=AssertionError('setup must not start')):
                with self.assertRaises(ValueError):
                    self.documents.setup(self.root)

    def test_pending_receipt_is_opaque_and_status_read_only(self):
        result = self.documents.record_pending(self.root, 'source_unavailable')
        self.assertEqual(result['state'], 'pending')
        self.assertIsNone(result['note_path'])
        files = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        status = self.documents.status(self.root)
        self.assertEqual(status[0]['latest_attempt']['source_id'], result['source_id'])
        self.assertEqual(files, {p: p.read_bytes() for p in files})

    def test_assets_have_working_links_in_a_project_with_a_long_path(self):
        def with_asset(source, output, runtime, profile):
            result = self.convert(source, output, runtime, profile)
            asset = 'image_' + 'a' * 64 + '.png'
            (output / 'assets').mkdir()
            (output / 'assets' / asset).write_bytes(b'controlled image bytes')
            (output / 'content.md').write_text(f'![Figure](assets/{asset})')
            return result
        result = self.documents.ingest(self.root, self.source, convert=with_asset)
        self.assertEqual(result['state'], 'ready')
        self.assertEqual(vault.check(self.root)['issues'], [])
        self.assertEqual(len(list((self.root / 'vault/local').rglob('*.png'))), 1)

    def test_partial_and_completed_attempts_have_separate_notes(self):
        def partial(source, output, runtime, profile):
            return {**self.convert(source, output, runtime, profile), 'state': 'partial'}
        first = self.documents.ingest(self.root, self.source, convert=partial)
        self.assertEqual(first['state'], 'partial')
        self.assertTrue(first['warnings'])
        original = (self.root / first['note_path']).read_bytes()
        second = self.ingest()
        self.assertEqual(second['state'], 'ready')
        self.assertNotEqual(first['note_path'], second['note_path'])
        self.assertEqual((self.root / first['note_path']).read_bytes(), original)
        self.assertEqual(vault.check(self.root)['issues'], [])

    def test_lock_recovery_requires_dead_owner_and_exact_token(self):
        self.store.prepare_storage(self.root)
        with self.store.project_lock(self.root):
            lock = self.store.lock_status(self.root)
            self.assertTrue(lock['owner_alive'])
            with self.assertRaises(ValueError):
                self.store.recover_lock(self.root, lock['token'])
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait(timeout=10)
        token = str(uuid.uuid4())
        lock_path = self.root / self.documents.BASE / 'lock.json'
        lock_path.write_text(json.dumps(dict(pid=child.pid, token=token)))
        self.assertFalse(self.store.lock_status(self.root)['owner_alive'])
        with self.assertRaises(ValueError):
            self.store.recover_lock(self.root, str(uuid.uuid4()))
        self.assertTrue(lock_path.exists())
        self.store.recover_lock(self.root, token)
        self.assertFalse(lock_path.exists())


class ReviewTests(IngestCase):
    def convert(self, source, output, runtime, profile):
        result = super().convert(source, output, runtime, profile)
        (output / 'content.md').write_text('Public evidence paragraph.\n\n![Figure](assets/figure.png)\n')
        (output / 'assets').mkdir()
        (output / 'assets/figure.png').write_bytes(b'controlled image')
        return result

    def review(self):
        receipt = self.ingest()
        return receipt, self.store.prepare_review(self.root, receipt['source_id'], receipt['revision'])

    def test_relation_uses_evidence_and_keeps_shared_feature_unchanged(self):
        for args in (['init', '--mode', 'existing', '--run', 'intake'],
                     ['feature', '--slug', 'source-proof', '--run', 'first']):
            subprocess.run([sys.executable, str(ROOT / 'scripts/personalize.py'), *args], cwd=self.root,
                           check=True, capture_output=True)
        feature = self.root / 'vault/features/source-proof/index.md'
        original = feature.read_bytes()
        identity = vault.metadata(feature.read_text(encoding='utf-8'))[0]['id']
        receipt = self.ingest()
        result = self.store.relate(self.root, receipt['source_id'], receipt['revision'], identity,
                                   'supports', 'Public evidence paragraph.')
        self.assertEqual(feature.read_bytes(), original)
        self.assertTrue(result['note_path'].startswith('vault/local/'))
        self.assertEqual(self.store.relate(self.root, receipt['source_id'], receipt['revision'], identity,
                                          'supports', 'Public evidence paragraph.'), result)
        self.assertEqual(vault.check(self.root)['issues'], [])
        with self.assertRaises(ValueError):
            self.store.relate(self.root, receipt['source_id'], receipt['revision'], identity, 'supports', 'Invented quote')
        with self.assertRaises(ValueError):
            self.store.relate(self.root, receipt['source_id'], receipt['revision'], str(uuid.uuid4()), 'supports', 'Public evidence')

    def test_promotion_uses_new_identity_and_survives_without_private_storage(self):
        receipt, review = self.review()
        result = self.store.promote(self.root, review['review_id'], review['digest'])
        self.assertTrue(result['note_path'].startswith('vault/sources/'))
        note = self.root / result['note_path']
        fields, body = vault.metadata(note.read_text(encoding='utf-8'))
        self.assertNotEqual(fields['id'], receipt['source_id'])
        self.assertNotIn(receipt['source_id'], body)
        self.assertNotIn(receipt['revision'], body)
        self.assertNotIn('private original', body)
        self.assertEqual(vault.check(self.root)['issues'], [])
        self.assertEqual(self.git('diff', '--cached', '--name-only').stdout, b'')
        self.assertEqual(self.store.promote(self.root, review['review_id'], review['digest']), result)
        # Copy just shared notes, as a clone would; private originals are absent.
        import shutil
        clone = Path(self.temp.name) / 'clone'
        shutil.copytree(self.root / 'vault', clone / 'vault', ignore=shutil.ignore_patterns('local'))
        self.assertEqual(vault.check(clone)['issues'], [])

    def test_changed_review_text_or_asset_invalidates_approval(self):
        for relative in ('index.md', 'assets/1.png'):
            with self.subTest(relative=relative):
                receipt, review = self.review()
                path = Path(review['directory']) / relative
                path.write_bytes(path.read_bytes() + b'changed')
                with self.assertRaises(ValueError):
                    self.store.promote(self.root, review['review_id'], review['digest'])
                self.assertFalse((self.root / 'vault/sources').exists())

    def test_review_rejects_private_and_absolute_links_even_with_current_digest(self):
        for target in ('../../local/index.md', 'file:///private.txt', 'C:/private.txt',
                       '../../../.operacao-local/docling/lock.json'):
            with self.subTest(target=target):
                receipt, review = self.review()
                directory = Path(review['directory'])
                with (directory / 'index.md').open('a', encoding='utf-8') as output:
                    output.write(f'\n[Forbidden]({target})\n')
                with self.assertRaises(ValueError):
                    self.store.promote(self.root, review['review_id'], self.store.tree_digest(directory))
                self.assertFalse((self.root / 'vault/sources').exists())

    def test_duplicate_public_id_and_partial_warning_removal_are_rejected(self):
        receipt, review = self.review()
        directory = Path(review['directory'])
        note = directory / 'index.md'
        public_id = vault.metadata(note.read_text())[0]['id']
        existing_id = vault.metadata((self.root / 'vault/index.md').read_text())[0]['id']
        note.write_text(note.read_text().replace(public_id, existing_id))
        with self.assertRaises(ValueError):
            self.store.promote(self.root, review['review_id'], self.store.tree_digest(directory))
        def partial(*args):
            return {**self.convert(*args), 'state': 'partial', 'warnings': ['incomplete_conversion']}
        self.source.write_text('partial revision')
        receipt = self.documents.ingest(self.root, self.source, convert=partial)
        review = self.store.prepare_review(self.root, receipt['source_id'], receipt['revision'])
        directory = Path(review['directory'])
        note = directory / 'index.md'
        note.write_text(note.read_text().replace('partial', 'ready').replace('incomplete_conversion', 'none'))
        with self.assertRaises(ValueError):
            self.store.promote(self.root, review['review_id'], self.store.tree_digest(directory))

    def test_source_changes_after_preparation_do_not_change_review_snapshot(self):
        receipt, review = self.review()
        directory = Path(review['directory'])
        before = self.store.tree_digest(directory)
        (self.root / receipt['note_path']).write_text('Changed after preparation.')
        self.assertEqual(self.store.tree_digest(directory), before)
        result = self.store.promote(self.root, review['review_id'], before)
        self.assertIn('Public evidence paragraph.', (self.root / result['note_path']).read_text())

    def test_shared_index_identity_conflict_is_rejected_before_public_writes(self):
        receipt, review = self.review()
        index = self.root / 'vault/index.md'
        original = index.read_text(encoding='utf-8')
        identity = vault.metadata(original)[0]['id']
        reserved = str(uuid.uuid5(uuid.UUID(receipt['project_id']), 'vault/sources/index.md'))
        index.write_text(original.replace(identity, reserved), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.store.promote(self.root, review['review_id'], review['digest'])
        self.assertFalse((self.root / 'vault/sources').exists())


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
