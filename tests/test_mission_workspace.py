"""Git workspaces are real; no model, network or fixture worker is involved."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch

from runtime_fixtures import RuntimeCase
import mission_store as store
import missions


class WorkspaceTests(RuntimeCase):
    def setUp(self):
        super().setUp()
        self.ws = importlib.import_module('mission_workspace')
        self.make_manifest()
        self.pbi = store.get_record(self.root, self.mission['record_id'])['snapshot']['pbi_ids'][0]
        (self.root / 'app.txt').write_text('base\n')
        (self.root / '.gitignore').write_text((self.root / '.gitignore').read_text() + '\n/ignored.txt\n/.runtime/workspaces/\n')
        self.git('add', '--', 'app.txt', '.gitignore')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.op = str(uuid.uuid4())

    def prepare(self, **kwargs):
        args = dict(mission=self.mission['record_id'], pbi=self.pbi, base=self.base,
                    expected_revision=1, operation_id=self.op, actor_id='operator')
        args.update(kwargs)
        return self.ws.prepare(self.root, **args)

    def release(self, record, **kwargs):
        args = dict(expected_revision=record['revision'], operation_id=str(uuid.uuid4()), actor_id='operator')
        args.update(kwargs)
        return self.ws.release(self.root, record['id'], **args)

    def test_prepare_preserves_original_and_release_keeps_commits(self):
        (self.root / 'app.txt').write_text('staged\n')
        self.git('add', 'app.txt')
        (self.root / 'app.txt').write_text('unstaged\n')
        (self.root / 'human.txt').write_text('untracked\n')
        before = [self.git(*args).stdout for args in [('status', '--porcelain=v1', '-uall'), ('diff',), ('diff', '--cached'), ('rev-parse', 'HEAD')]]
        record = self.prepare()
        path = Path(record['path'])
        self.assertEqual(record['state'], 'prepared')
        self.assertEqual((path / 'app.txt').read_text(), 'base\n')
        self.assertEqual(self.prepare(), record)
        self.assertEqual(before, [self.git(*args).stdout for args in [('status', '--porcelain=v1', '-uall'), ('diff',), ('diff', '--cached'), ('rev-parse', 'HEAD')]])
        (path / 'app.txt').write_text('delivery\n')
        self.git('-C', str(path), 'add', 'app.txt')
        self.git('-C', str(path), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'delivery')
        tip = self.git('-C', str(path), 'rev-parse', 'HEAD').stdout.decode().strip()
        op = str(uuid.uuid4())
        result = self.release(record, operation_id=op)
        self.assertEqual(result['state'], 'released')
        self.assertFalse(path.exists())
        self.assertEqual(result['last_commit'], tip)
        self.assertEqual(self.git('rev-parse', record['branch']).stdout.decode().strip(), tip)
        self.assertEqual(self.release(record, operation_id=op), result)
        self.assertEqual(self.prepare(), record)  # Receipt replay never recreates a released directory.
        self.assertEqual(missions.mission_status(self.root, self.mission['record_id'])['snapshot']['development'], 'not_started')

    def test_rejects_duplicate_pbi_stale_revision_and_changed_replay(self):
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.prepare(expected_revision=2)
        record = self.prepare()
        with self.assertRaisesRegex(ValueError, 'workspace_busy'):
            self.prepare(operation_id=str(uuid.uuid4()))
        with self.assertRaisesRegex(ValueError, 'operation_conflict'):
            self.prepare(base='0' * 40)
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.release(record, expected_revision=0)

    def test_rejects_abbreviated_or_noncommit_base(self):
        for base in (self.base[:8], 'HEAD', '0' * 40):
            with self.subTest(base=base), self.assertRaises(ValueError):
                self.prepare(base=base)
        self.assertFalse((self.root / '.runtime/workspaces').exists())

    def test_release_refuses_dirty_untracked_ignored_and_detached(self):
        record = self.prepare()
        path = Path(record['path'])
        for filename in ('app.txt', 'human.txt', 'ignored.txt'):
            file = path / filename
            before = file.read_bytes() if file.exists() else None
            file.write_text('keep me\n')
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'workspace_dirty'):
                self.release(record)
            self.assertEqual(file.read_text(), 'keep me\n')
            file.write_bytes(before) if before is not None else file.unlink()
        self.git('-C', str(path), 'checkout', '--detach', '-q')
        with self.assertRaisesRegex(ValueError, 'workspace_changed'):
            self.release(record)
        self.assertTrue(path.exists())

    def test_foreign_branch_and_path_are_never_adopted(self):
        original = self.ws.resume_prepare
        def foreign(root, record):
            self.git('branch', record['branch'], self.base)
            return original(root, record)
        with patch.object(self.ws, 'resume_prepare', side_effect=foreign):
            with self.assertRaisesRegex(ValueError, 'workspace_collision'):
                self.prepare()
        with self.assertRaisesRegex(ValueError, 'workspace_collision'):
            self.prepare()
        # A separate PBI is not needed: retry the same reserved operation, preserving the branch.
        self.assertEqual(len(self.git('for-each-ref', 'refs/heads/youngcrow/').stdout.splitlines()), 1)

    def test_recovery_after_git_effects_and_lost_ack(self):
        original = self.ws.git_write
        for command in ('update-ref', 'worktree'):
            def crash(root, record, *args, **kwargs):
                result = original(root, record, *args, **kwargs)
                if args[0] == command:
                    raise RuntimeError('lost controller')
                return result
            with patch.object(self.ws, 'git_write', side_effect=crash):
                with self.assertRaisesRegex(RuntimeError, 'lost controller'):
                    self.prepare()
        record = self.prepare()
        self.assertEqual(record['state'], 'prepared')
        self.assertEqual(len(self.git('worktree', 'list', '--porcelain').stdout.split(b'worktree ')), 3)
        operation = str(uuid.uuid4())
        def lost(root, record, *args, **kwargs):
            result = original(root, record, *args, **kwargs)
            if args[:2] == ('worktree', 'remove'):
                raise RuntimeError('lost receipt')
            return result
        with patch.object(self.ws, 'git_write', side_effect=lost):
            with self.assertRaisesRegex(RuntimeError, 'lost receipt'):
                self.release(record, operation_id=operation)
        self.assertEqual(self.release(record, operation_id=operation)['state'], 'released')

    def test_status_does_not_write_and_pending_owner_blocks_retry(self):
        record = self.prepare()
        before = self.snapshot()
        self.assertEqual(self.ws.status(self.root, record['id'])['state'], 'prepared')
        self.assertEqual(self.snapshot(), before)
        original = self.ws.resume_prepare
        def stop(root, record):
            raise RuntimeError('stop')
        self.release(record)
        self.op = str(uuid.uuid4())
        with patch.object(self.ws, 'resume_prepare', side_effect=stop):
            with self.assertRaises(RuntimeError):
                self.prepare()
        pending = self.ws.status(self.root, self.op)
        pending['owner'] = {'kind': 'linux-group', 'name': str(uuid.uuid4()), 'pid': 12345}
        self.ws.save(self.root, pending)
        with patch.object(self.ws.processes, 'owner_gone', return_value=False):
            with self.assertRaisesRegex(ValueError, 'workspace_busy'):
                self.prepare()
        self.assertFalse(Path(pending['path']).exists())

    def test_checkout_hooks_are_disabled_and_filters_refused(self):
        marker = self.root / 'hook-ran'
        hook = self.root / '.git/hooks/post-checkout'
        hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n')
        hook.chmod(0o755)
        self.prepare()
        self.assertFalse(marker.exists())
        self.git('config', 'filter.external.smudge', 'echo unexpected')
        with self.assertRaisesRegex(ValueError, 'unsupported_workspace_repository'):
            self.prepare(operation_id=str(uuid.uuid4()))

    def test_trial_return_still_requires_releasing_all_worktrees(self):
        import adoption
        import tempfile
        temporary = tempfile.TemporaryDirectory(prefix='yc-workspace-backup-', dir=Path(__file__).resolve().parents[2])
        self.addCleanup(temporary.cleanup)
        backup = Path(temporary.name) / 'backups'
        adoption.prepare(self.root, backup)
        record = self.prepare()
        with self.assertRaisesRegex(ValueError, 'unsupported_git'):
            adoption.preview(self.root, backup)
        self.release(record)
        self.assertTrue(adoption.preview(self.root, backup)['digest'])

    def test_release_preserves_hidden_changes_and_staged_files(self):
        record = self.prepare()
        path = Path(record['path'])
        for flag in ('assume-unchanged', 'skip-worktree'):
            self.git('-C', str(path), 'update-index', '--' + flag, 'app.txt')
            (path / 'app.txt').write_text('hidden work\n')
            with self.assertRaisesRegex(ValueError, 'workspace_changed'):
                self.release(record)
            self.assertEqual((path / 'app.txt').read_text(), 'hidden work\n')
            self.git('-C', str(path), 'update-index', '--no-' + flag, 'app.txt')
            (path / 'app.txt').write_text('base\n')
        (path / 'app.txt').write_text('staged work\n')
        self.git('-C', str(path), 'add', 'app.txt')
        with self.assertRaisesRegex(ValueError, 'workspace_dirty'):
            self.release(record)

    def test_foreign_directory_and_replacement_preserved(self):
        target = self.root / '.runtime/workspaces' / self.op
        target.mkdir(parents=True)
        (target / 'human.txt').write_text('foreign\n')
        with self.assertRaisesRegex(ValueError, 'workspace_collision'):
            self.prepare()
        self.assertEqual((target / 'human.txt').read_text(), 'foreign\n')
        target.rename(target.with_name('foreign'))
        record = self.prepare()
        path = Path(record['path'])
        path.rename(path.with_name('original'))
        path.mkdir()
        (path / 'human.txt').write_text('replacement\n')
        with self.assertRaisesRegex(ValueError, 'workspace_changed'):
            self.release(record)
        self.assertEqual((path / 'human.txt').read_text(), 'replacement\n')

    def test_incomplete_checkout_is_preserved_after_interruption(self):
        original = self.ws.git_write
        def partial(root, record, *args, **kwargs):
            result = original(root, record, *args, **kwargs)
            if args[:2] == ('worktree', 'add'):
                (Path(record['path']) / 'app.txt').unlink()
                raise RuntimeError('interrupted checkout')
            return result
        with patch.object(self.ws, 'git_write', side_effect=partial):
            with self.assertRaises(RuntimeError):
                self.prepare()
        with self.assertRaisesRegex(ValueError, 'workspace_dirty'):
            self.prepare()
        record = self.ws.status(self.root, self.op)
        self.assertFalse((Path(record['path']) / 'app.txt').exists())
        self.assertEqual(record['state'], 'preparing')

    def test_branch_changed_and_stale_mission_do_not_prevent_safe_release(self):
        record = self.prepare()
        path = Path(record['path'])
        self.git('-C', str(path), 'checkout', '-qb', 'human-branch')
        with self.assertRaisesRegex(ValueError, 'workspace_changed'):
            self.release(record)
        self.git('-C', str(path), 'checkout', '-q', record['branch'])
        item = store.get_record(self.root, self.pbi)
        (self.root / item['snapshot']['note_path']).write_text('human changed input\n')
        self.assertEqual(self.release(record)['state'], 'released')

    def test_configuration_boundary_and_runtime_ignore_fail_before_git_write(self):
        for key in ('extensions.partialClone', 'include.path', 'core.sparseCheckout', 'remote.origin.promisor'):
            self.git('config', key, 'true')
            with self.assertRaisesRegex(ValueError, 'unsupported_workspace_repository'):
                self.prepare()
            self.git('config', '--unset', key)
        ignore = self.root / '.gitignore'
        ignore.write_text(ignore.read_text().replace('/.runtime/workspaces/\n', ''))
        with self.assertRaisesRegex(ValueError, 'unsupported_workspace_repository'):
            self.prepare()
        self.assertFalse((self.root / '.runtime/workspaces').exists())

    def test_cli_round_trip_and_schema_compatibility(self):
        import mission_queue
        import mission_runs
        from test_documents import ROOT
        argv = [sys.executable, '-B', str(ROOT / 'scripts/missions.py'), '--root', str(self.root), '--json']
        options = ['--expected-revision', '1', '--operation-id', self.op, '--actor-id', 'operator']
        command = argv + ['workspace', 'prepare', self.mission['record_id'], '--pbi', self.pbi, '--base', self.base] + options
        first = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        record = json.loads(first.stdout)
        self.assertEqual(record['state'], 'prepared')
        with store.transaction(self.root) as conn:
            mission_queue.migrate(conn)
            mission_runs.migrate(conn)
            self.assertEqual(conn.execute('SELECT schema_version FROM metadata').fetchone()[0], 6)
            self.assertTrue(mission_queue.available(conn))
            self.assertTrue(mission_runs.has_runs(conn))
        report = missions.mission_status(self.root, self.mission['record_id'])
        self.assertEqual(report['workspaces'][0]['id'], record['id'])
        self.assertFalse(report['runtime_available'])
        before = self.snapshot()
        result = subprocess.run(argv + ['workspace', 'status', record['id']], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(result.stdout), record)
        self.assertEqual(before, self.snapshot())

    def test_dangling_symbolic_refs_cannot_create_a_foreign_branch(self):
        branch = 'refs/heads/youngcrow/p001-' + self.op
        for name in (branch, 'refs/youngcrow/workspaces/' + self.op):
            self.git('symbolic-ref', name, 'refs/heads/foreign-target')
            with self.assertRaisesRegex(ValueError, 'workspace_collision'):
                self.prepare()
            self.assertNotEqual(self.git('show-ref', '--verify', 'refs/heads/foreign-target', check=False).returncode, 0)
            self.assertEqual(self.git('symbolic-ref', name).stdout.strip(), b'refs/heads/foreign-target')
            self.git('symbolic-ref', '--delete', name)
        self.assertEqual(self.prepare()['state'], 'prepared')

    def test_concurrent_cli_requests_create_only_one_worktree(self):
        from test_documents import ROOT
        command = [sys.executable, '-B', str(ROOT / 'scripts/missions.py'), '--root', str(self.root), '--json',
                   'workspace', 'prepare', self.mission['record_id'], '--pbi', self.pbi, '--base', self.base,
                   '--expected-revision', '1', '--operation-id', self.op, '--actor-id', 'operator']
        children = [subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        try:
            replies = [json.loads(child.communicate(timeout=30)[0]) for child in children]
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.communicate()
        self.assertTrue(any(r.get('state') == 'prepared' for r in replies), replies)
        self.assertTrue(all(r.get('state') == 'prepared' or r.get('error') in ('locked', 'store_busy') for r in replies), replies)
        self.assertEqual(self.prepare()['state'], 'prepared')
        self.assertEqual(len(self.git('worktree', 'list', '--porcelain').stdout.split(b'worktree ')), 3)

    def test_interrupted_prepare_resumes_frozen_intent_after_input_change(self):
        original = self.ws.git_write
        def crash(root, record, *args, **kwargs):
            result = original(root, record, *args, **kwargs)
            if args[:2] == ('worktree', 'add'):
                raise RuntimeError('lost ack')
            return result
        with patch.object(self.ws, 'git_write', side_effect=crash):
            with self.assertRaises(RuntimeError):
                self.prepare()
        item = store.get_record(self.root, self.pbi)
        (self.root / item['snapshot']['note_path']).write_text('changed since intent\n')
        result = self.prepare()
        self.assertEqual(result['state'], 'prepared')
        self.assertEqual(result['mission_revision'], 1)
        self.assertEqual(self.release(result)['state'], 'released')

    def test_git_metadata_links_never_write_to_external_storage(self):
        import os
        for relative in ('objects', 'refs', 'logs'):
            path = self.root / '.git' / relative
            external = self.root.parent / ('external-' + relative)
            if path.exists():
                path.rename(external)
            else:
                external.mkdir()
            try:
                path.symlink_to(external, target_is_directory=True)
            except OSError:
                if not path.exists():
                    external.rename(path)
                self.skipTest('symlink creation unavailable')
            try:
                before = {str(p.relative_to(external)): p.read_bytes() for p in external.rglob('*') if p.is_file()}
                with self.assertRaisesRegex(ValueError, 'unsupported_entry'):
                    self.prepare()
                self.assertEqual(before, {str(p.relative_to(external)): p.read_bytes() for p in external.rglob('*') if p.is_file()})
            finally:
                path.unlink()
                external.rename(path)

    def test_old_queue_helper_cannot_silently_hide_schema_six_history(self):
        self.prepare()
        self.ws.mission_queue.apply(self.root, 'start', self.mission['code'], 1,
                                   str(uuid.uuid4()), 'operator')
        before = self.snapshot()
        with patch.object(self.ws.mission_queue, 'STORE_SCHEMA', None, create=True):
            with self.assertRaisesRegex(ValueError, 'incompatible_helper'):
                missions.mission_status(self.root, self.mission['code'])
        self.assertEqual(self.snapshot(), before)
