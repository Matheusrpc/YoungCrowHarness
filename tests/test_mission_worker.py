"""Trust-boundary checks; Docker acceptance lives in smoke_tool_worker.py."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


@unittest.skipUnless(sys.platform == 'linux', 'OCI tools require Linux')
class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('mission_worker'), 'worker not implemented')
        import mission_worker
        self.w = mission_worker
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()

    def test_package_roundtrip_keeps_exact_bytes_and_original(self):
        (self.source / 'hello.py').write_bytes(b'print("hello")\n')
        destination = self.root / 'package.tar'
        result = self.w.pack(self.source, ['hello.py'], destination)
        self.assertEqual(result['sha256'], hashlib.sha256(destination.read_bytes()).hexdigest())
        files = self.w.archive_files(destination.read_bytes())
        self.assertEqual(files, {'hello.py': b'print("hello")\n'})
        self.assertEqual((self.source / 'hello.py').read_bytes(), files['hello.py'])
        with self.assertRaises(ValueError):
            self.w.pack(self.source, ['hello.py'], destination)

    def test_package_rejects_escape_links_and_special_files(self):
        (self.root / 'outside').write_text('private')
        (self.source / 'plain').write_text('safe')
        os.symlink(self.root / 'outside', self.source / 'linked')
        os.link(self.source / 'plain', self.source / 'hard')
        for name in ('../outside', '/outside', 'linked', 'hard', '.env', '.git/config'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.w.pack(self.source, [name], self.root / 'bad.tar')
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.source / 'pipe')
            with self.assertRaises(ValueError):
                self.w.pack(self.source, ['pipe'], self.root / 'pipe.tar')

    def test_package_rejects_nested_parent_symlink(self):
        (self.source / 'sub').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.w.pack(self.source, ['sub/outside'], self.root / 'bad.tar')

    def test_archive_rejects_traversal_duplicates_links_and_limits(self):
        for kind, name in ((tarfile.REGTYPE, '../escape'), (tarfile.SYMTYPE, 'link'),
                           (tarfile.LNKTYPE, 'hard'), (tarfile.FIFOTYPE, 'pipe'),
                           (tarfile.CHRTYPE, 'device'), (tarfile.REGTYPE, '/absolute')):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w') as archive:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.linkname = '/private'
                archive.addfile(info)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.w.archive_files(stream.getvalue())
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for _ in range(2):
                archive.addfile(tarfile.TarInfo('same'))
        with self.assertRaises(ValueError):
            self.w.archive_files(stream.getvalue())
        with self.assertRaises(ValueError):
            self.w.archive_files(b'x' * (self.w.ARCHIVE_LIMIT + 1))

    def test_nested_archive_directories_have_owner_and_traversal(self):
        data = self.w.archive_bytes({'sub/nested/file': b'content'})
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            directory = archive.getmember('sub/nested')
            self.assertTrue(directory.isdir())
            self.assertEqual(directory.uid, 1000)
            self.assertEqual(directory.mode, 0o700)
        with self.assertRaises(ValueError):
            self.w.archive_bytes({'sub': b'file', 'sub/child': b'collision'})

    def test_archive_rejects_directory_file_collision(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name in ('parent', 'parent/child'):
                archive.addfile(tarfile.TarInfo(name))
        with self.assertRaises(ValueError):
            self.w.archive_files(stream.getvalue())

    def test_parent_swap_never_opens_outside_tree(self):
        sub = self.source / 'sub'
        sub.mkdir()
        (sub / 'file').write_bytes(b'safe')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'file').write_bytes(b'private')
        actual_open = os.open
        opened_outside = []
        swapped = False
        def racing_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if str(path) == 'file' and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                sub.rename(self.source / 'old')
                sub.symlink_to(outside, target_is_directory=True)
            fd = actual_open(path, flags, *args, **kwargs)
            if Path('/proc/self/fd/' + str(fd)).resolve() == outside / 'file':
                opened_outside.append(fd)
            return fd
        with patch('os.open', side_effect=racing_open):
            try:
                self.w.pack(self.source, ['sub/file'], self.root / 'race.tar')
            except ValueError:
                pass
        self.assertTrue(swapped, 'the race fixture must actually replace the parent')
        self.assertEqual(opened_outside, [])

    def test_fixed_checker_accepts_only_pure_clamp_expressions(self):
        spec=importlib.util.spec_from_file_location('worker_check',
            Path(__file__).resolve().parents[1]/'runtime/worker/check.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        for expression in ('min(high, max(low, value))',
                           'low if value < low else high if value > high else value'):
            self.assertEqual(checker.check_source('def clamp(value, low, high):\n return '+expression),
                             dict(cases=3,exit_code=0))
        for source in ('import os\nprint(\'{"cases":3,"exit_code":0}\',flush=True)\nos._exit(0)',
                       'def clamp(value, low, high):\n return max(low, value)',
                       'def clamp(value, low, high):\n return value.__class__',
                       'def clamp(value, low, high):\n return __import__("os")._exit(0)',
                       '@print\ndef clamp(value, low, high):\n return value',
                       'def clamp(value, low, high):\n return [0]*1000000'):
            with self.subTest(source=source),self.assertRaises(ValueError):checker.check_source(source)

    def test_command_uses_fixed_socket_and_nonprivileged_identity(self):
        handle = dict(container_id='a' * 64, docker='/usr/local/bin/docker', operation_id=str(uuid.uuid4()))
        command = self.w.exec_argv(handle, ['/bin/sh', '-c', 'echo harmless; id'])
        self.assertEqual(command[:5], ['/usr/local/bin/docker', '--host=unix:///var/run/docker.sock',
                                      'exec', '-i', '--user=1000:1000'])
        self.assertIn('a' * 64, command)
        self.assertEqual(command[-3:], ['/bin/sh', '-c', 'echo harmless; id'])
        self.assertIn('--workdir=/tmp/youngcrow-' + handle['operation_id'] + '/cwd', command)
        for changed in ('--privileged', 'short', '../container'):
            with self.assertRaises(ValueError):
                self.w.exec_argv(dict(handle, container_id=changed), ['/bin/true'])

    def test_package_rejects_sensitive_state_and_excess_size(self):
        for name in ('auth.json', '.credentials.json', 'id_rsa', 'registry.json'):
            (self.source / name).write_text('not a real secret')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.w.pack(self.source, [name], self.root / 'sensitive.tar')
        (self.source / 'large').write_bytes(b'x' * (self.w.DATA_LIMIT + 1))
        with self.assertRaises(ValueError):
            self.w.pack(self.source, ['large'], self.root / 'large.tar')

    def test_invalid_or_expired_plan_cannot_start_worker(self):
        self.assertTrue(callable(getattr(self.w, 'validate_plan', None)), 'plan validation missing')
        plan = dict(contract='isolated-tools', schema_version=1, operation_id=str(uuid.uuid4()),
                    deadline_ms=int(time.time() * 1000) + 5000, image_digest='sha256:' + 'a' * 64,
                    package_sha256='b' * 64, engine=dict(id='engine', version='28.4.0', boot_id=str(uuid.uuid4())))
        self.w.validate_plan(plan)
        for change in ({'deadline_ms': True}, {'deadline_ms': 0}, {'schema_version': True},
                       {'image_digest': 'python:latest'}, {'other': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.w.validate_plan(dict(plan, **change))

    def test_workspace_rejects_noncanonical_operation_ids(self):
        for operation in ('../outside', '00000000000000000000000000000000', None):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                self.w.workspace(operation)

    def test_inspection_rejects_missing_or_unconfined_seccomp(self):
        handle = dict(docker='/usr/local/bin/docker', engine={}, container_id='a'*64,
                      image_digest='sha256:'+'b'*64, operation_id='operation', plan_sha256='plan')
        row = dict(Id=handle['container_id'], Image=handle['image_digest'], Created='created', Mounts=[],
                   Config=dict(User='0:0', Labels={'youngcrow.operation':'operation', 'youngcrow.plan':'plan'}),
                   HostConfig=dict(NetworkMode='none', ReadonlyRootfs=True, Privileged=False,
                       CapDrop=['ALL'], CapAdd=None, PidMode='', IpcMode='private', RestartPolicy={'Name':'no'},
                       Binds=None, Devices=[], PortBindings={}, PidsLimit=128, Memory=1073741824,
                       MemorySwap=1073741824, NanoCpus=2000000000))
        profile = self.w.seccomp_profile()
        expected = ['no-new-privileges', 'seccomp='+json.dumps(profile)]
        row['HostConfig']['SecurityOpt'] = expected
        with patch.object(self.w, 'engine', return_value={}), \
                patch.object(self.w, 'call', return_value=json.dumps([row]).encode()):
            self.w._inspection(handle)
        changed = dict(profile, defaultAction='SCMP_ACT_ALLOW')
        for options in (['no-new-privileges'], ['no-new-privileges', 'seccomp=unconfined'],
                        ['no-new-privileges', 'apparmor=unconfined'],
                        ['no-new-privileges', 'seccomp='+json.dumps(changed)],
                        expected+['apparmor=unconfined']):
            row['HostConfig']['SecurityOpt'] = options
            with self.subTest(options=options), patch.object(self.w, 'engine', return_value={}), \
                    patch.object(self.w, 'call', return_value=json.dumps([row]).encode()), \
                    self.assertRaisesRegex(ValueError, 'worker_boundary_changed'):
                self.w._inspection(handle)

    def test_changed_seccomp_profile_is_refused(self):
        profile = self.root / 'seccomp.json'
        profile.write_text('{"defaultAction":"SCMP_ACT_ALLOW"}')
        with patch.object(self.w, 'SECCOMP_PATH', profile), \
                self.assertRaisesRegex(ValueError, 'worker_seccomp_changed'):
            self.w.seccomp_profile()

    def test_build_refuses_unverified_bwrap_before_docker_or_output(self):
        import build_tool_worker as builder
        bwrap = self.root / 'bwrap'
        bwrap.write_bytes(b'unverified executable')
        output = self.root / 'build'
        with patch.object(builder.clients, 'verify_binary', return_value={'sha256': 'a'*64}), \
                patch.object(builder.worker, 'call') as docker:
            with self.assertRaisesRegex(ValueError, 'unsupported_codex_bwrap'):
                builder.build('/usr/local/bin/docker', self.root/'codex', output, bwrap=bwrap)
            docker.assert_not_called()
        self.assertFalse(output.exists())

    def test_build_refuses_bwrap_changed_during_copy(self):
        import build_tool_worker as builder
        codex, bwrap = self.root/'codex', self.root/'bwrap'
        codex.write_bytes(b'codex fixture')
        bwrap.write_bytes(b'bwrap fixture')
        output = self.root/'build'
        expected = hashlib.sha256(bwrap.read_bytes()).hexdigest()
        actual_copy = builder.shutil.copyfile
        def copy(source, target):
            actual_copy(source, target)
            if Path(source) == bwrap:
                Path(target).write_bytes(b'changed during copy')
        with patch.object(builder, 'BWRAP_SHA256', expected), \
                patch.object(builder.clients, 'verify_binary', return_value={'sha256': hashlib.sha256(codex.read_bytes()).hexdigest()}), \
                patch.object(builder.shutil, 'copyfile', side_effect=copy), \
                patch.object(builder.worker, 'call') as docker:
            with self.assertRaisesRegex(ValueError, 'worker_input_changed'):
                builder.build('/usr/local/bin/docker', codex, output, bwrap=bwrap)
            docker.assert_not_called()

    def test_worker_driver_is_present_for_native_smoke(self):
        for name in ('start', 'observe', 'stop', 'collect'):
            self.assertTrue(callable(getattr(self.w, name, None)), name + ' missing')


if __name__ == '__main__':
    unittest.main()
