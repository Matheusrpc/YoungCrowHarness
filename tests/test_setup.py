"""Exercise the actual installer without network, user plugins or real credentials."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ('setup.sh', 'CLAUDE.md', 'AGENTS.md', '.mcp.json', '.env.example',
         '.gitignore', '.codex/hooks.json', '.claude/settings.json',
         'skills-lock.json', 'docs/CLAUDE.en.md', 'skills/humanizer-ptbr/SKILL.md')


def shell_path(path):
    value = Path(path).absolute().as_posix()
    return '/' + value[0].lower() + value[2:] if os.name == 'nt' else value


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def fake_git(args):
    with open(os.environ['TEST_CALLS'], 'a', encoding='utf-8') as log:
        log.write(json.dumps(['git', *args]) + '\n')
    if args and args[0] == 'clone':
        args = ['clone', '-q', '--', os.environ['TEST_UPSTREAM'], args[-1]]
    elif 'checkout' in args and os.environ.get('TEST_FAIL_CHECKOUT') == '1':
        return 17
    elif any(x in args for x in ('fetch', 'pull', 'push', 'ls-remote', 'submodule')):
        return 97
    return subprocess.run([os.environ['TEST_REAL_GIT'], *args]).returncode


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.bash = shutil.which('bash') or 'C:/Program Files/Git/bin/bash.exe'
        self.real_git = shutil.which('git')
        if not Path(self.bash).is_file() or not self.real_git:
            self.fail('Tests require Bash (Git Bash on Windows) and Git.')
        runtime = ROOT / '.runtime'
        runtime.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='setup-test-', dir=runtime)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.target = self.base / 'source', self.base / 'project with spaces'
        self.home, self.bin = self.base / 'home', self.base / 'bin'
        self.calls, self.upstream = self.base / 'calls.jsonl', self.base / 'upstream'
        for folder in (self.source, self.target, self.home, self.bin, self.upstream):
            folder.mkdir()
        for rel in FILES:
            dest = self.source / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)
        # Only OS necessities cross this boundary. No provider tokens or user Git settings.
        self.child_env = {key: value for key, value in os.environ.items()
                          if key.upper() in ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'PATHEXT')}
        self.child_env.update(
            HOME=shell_path(self.home), TEST_BIN=shell_path(self.bin),
            TEST_PYTHON=sys.executable.replace('\\', '/'), TEST_RUNNER=str(Path(__file__).resolve()).replace('\\', '/'),
            TEST_REAL_GIT=self.real_git, TEST_UPSTREAM=str(self.upstream), TEST_CALLS=str(self.calls),
            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
            PATH=os.pathsep.join((str(Path(self.real_git).parent), str(Path(sys.executable).parent))),
        )
        self.git('init', '-q', str(self.upstream))
        write(self.upstream / 'SKILL.md', '# Local test skill\n')
        self.git('-C', str(self.upstream), 'add', '--', 'SKILL.md')
        self.git('-C', str(self.upstream), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'test fixture')
        self.expected_commit = self.git('-C', str(self.upstream), 'rev-parse', 'HEAD').stdout.strip()
        manifest = json.loads((self.source / 'skills-lock.json').read_text(encoding='utf-8'))
        manifest['skills_de_usuario']['humanizer']['upstream']['commit'] = self.expected_commit
        write(self.source / 'skills-lock.json', json.dumps(manifest))
        self.wrapper('python3', 'exec "$TEST_PYTHON" "$@"')
        self.wrapper('git', 'exec "$TEST_PYTHON" "$TEST_RUNNER" --fake-git "$@"')
        self.wrapper('claude', 'exec "$TEST_PYTHON" "$TEST_RUNNER" --fake-claude "$@"')

    def wrapper(self, name, body):
        path = self.bin / name
        write(path, '#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)

    def git(self, *args, check=True):
        return subprocess.run([self.real_git, *args], env=self.child_env, capture_output=True,
                              encoding='utf-8', check=check, timeout=20)

    def run_setup(self, *args, env=None):
        child = self.child_env.copy()
        child.update(env or {})
        return subprocess.run(
            [self.bash, '-c', 'export PATH="$TEST_BIN:/usr/bin:/bin"; exec /usr/bin/bash "$@"',
             'test-setup', shell_path(self.source / 'setup.sh'), shell_path(self.target), *args],
            cwd=self.source, env=child, capture_output=True, encoding='utf-8', errors='replace', timeout=45)

    def assert_no_project_writes(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.target / 'CLAUDE.md').exists())
        self.assertFalse((self.target / '.env').exists())

    def symlink(self, dest, source, directory=False):
        try:
            dest.symlink_to(source, target_is_directory=directory)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows needs Developer Mode or symlink privilege; Linux CI must run this case.')
            raise

    def test_missing_name_fails_before_writes(self):
        result = self.run_setup('--nome')
        self.assertEqual(result.returncode, 2)
        self.assert_no_project_writes(result)

    def test_unknown_option_fails_before_writes(self):
        self.assert_no_project_writes(self.run_setup('--not-an-option'))

    def test_broken_python_fails_before_writes(self):
        self.wrapper('python3', 'exit 127')
        self.assert_no_project_writes(self.run_setup('--sem-plugins'))

    def test_bad_manifest_fails_before_writes(self):
        write(self.source / 'skills-lock.json', '{bad json')
        self.assert_no_project_writes(self.run_setup('--sem-plugins'))

    def test_managed_parent_file_fails_before_writes(self):
        write(self.target / '.claude', 'keep this')
        self.assert_no_project_writes(self.run_setup('--sem-plugins'))
        self.assertEqual((self.target / '.claude').read_text(), 'keep this')

    def test_dangling_env_link_is_rejected(self):
        missing = self.base / 'outside-env'
        self.symlink(self.target / '.env', missing)
        self.assert_no_project_writes(self.run_setup('--sem-plugins'))
        self.assertFalse(missing.exists())

    def test_directory_link_cannot_write_outside_project(self):
        outside = self.base / 'outside'
        outside.mkdir()
        write(outside / 'settings.json', 'sentinel')
        self.symlink(self.target / '.claude', outside, directory=True)
        self.assert_no_project_writes(self.run_setup('--sem-plugins', '--force'))
        self.assertEqual((outside / 'settings.json').read_text(), 'sentinel')

    def test_tool_interception(self):
        result = subprocess.run([self.bash, '-c',
                                 'export PATH="$TEST_BIN:/usr/bin:/bin"; command -v git; command -v claude'],
                                env=self.child_env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines(), [shell_path(self.bin / 'git'), shell_path(self.bin / 'claude')])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fake-git':
        sys.exit(fake_git(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == '--fake-claude':
        args = sys.argv[2:]
        with open(os.environ['TEST_CALLS'], 'a', encoding='utf-8') as log:
            log.write(json.dumps(['claude', *args]) + '\n')
        stage = 'marketplace' if 'marketplace' in args else 'install'
        sys.exit(19 if os.environ.get('TEST_CLAUDE_FAIL_STAGE') == stage else 0)
    unittest.main()
