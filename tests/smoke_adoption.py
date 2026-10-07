"""Real local setup and return. Requires an absent disposable root; no client/model calls."""
import argparse
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import adoption_fs as fs


def shell_path(path):
    value = Path(path).absolute().as_posix()
    return '/' + value[0].lower() + value[2:] if os.name == 'nt' else value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def run(args, *, env, cwd, expected=0):
    result = subprocess.run(args, env=env, cwd=cwd, capture_output=True, timeout=300)
    if result.returncode != expected:
        raise ValueError('subprocess_failed_' + str(result.returncode))
    return result.stdout


def smoke(root, client, *, prepare_existing=None, exercise=None,
          cases=('absent', 'dirty-git', 'interrupted'), setup_options=()):
    root = fs.checked_path(root)
    if root.exists() or not root.parent.is_dir():
        raise ValueError('requires_new_disposable_root')
    fs.outside_git(root)
    bash, git = shutil.which('bash'), shutil.which('git')
    if not bash and os.name == 'nt' and git:
        candidate = Path(git).parent.parent / 'bin/bash.exe'
        if candidate.is_file():
            bash = str(candidate)
    if not bash or not git:
        raise ValueError('requires_bash_and_git')
    fs.private_dir(root)
    home, shim, backups = root / 'home', root / 'bin', root / 'backups'
    home.mkdir()
    if os.name == 'nt':
        # Model an initialized Windows profile; native PowerShell resolves these folders.
        (home / 'AppData/Roaming').mkdir(parents=True)
        (home / 'AppData/Local').mkdir()
    shim.mkdir()
    write(shim / 'python3', b'#!/usr/bin/env bash\nexec "$YC_PYTHON" -B "$@"\n')
    write(shim / 'claude', b'#!/usr/bin/env bash\nexit 97\n')
    for path in shim.iterdir():
        path.chmod(0o755)
    env = {k: v for k, v in os.environ.items()
           if k.upper() in ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'PATHEXT', 'PATH')}
    env.update(HOME=str(home), USERPROFILE=str(home), YC_PYTHON=sys.executable,
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0',
               GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1')
    home_before = fs.inspect_tree(home)
    results = []
    for case in cases:
        project = root / case
        def git_call(*args):
            return run([git, '-c', 'core.fsmonitor=false', '-C', str(project), *args], env=env, cwd=root)
        if case != 'absent':
            project.mkdir()
            git_call('init', '-q')
            write(project / 'app.txt', b'original commit\n')
            write(project / '.gitignore', b'.env\n')
            if prepare_existing is not None:
                prepare_existing(project, case, env)
            git_call('add', '--', 'app.txt', '.gitignore')
            git_call('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'initial')
            write(project / 'app.txt', b'staged before adoption\n')
            git_call('add', '--', 'app.txt')
            write(project / 'app.txt', b'unstaged before adoption\n')
            write(project / '.env', b'SYNTHETIC_ONLY=initial\n')
            write(project / 'CLAUDE.md', b'Original instructions\n')
            write(project / '.codex/config.toml', b'# Original config\n')
            (project / 'empty').mkdir()
        def git_state():
            return [git_call(*args) for args in (('rev-parse', 'HEAD'), ('symbolic-ref', 'HEAD'),
                    ('diff', '--cached', '--binary'), ('diff', '--binary'), ('status', '--porcelain=v1', '-z'))]
        initial_git = git_state() if case != 'absent' else None
        initial = fs.inspect_tree(project)
        prefix = f'export PATH={shlex.quote(shell_path(shim))}:"$PATH"; exec bash "$@"'
        output = run([bash, '--noprofile', '--norc', '-c', prefix, 'trial-smoke',
                      shell_path(ROOT / 'setup.sh'), shell_path(project), '--trial', '--client', client,
                      '--backup-root', shell_path(backups), *setup_options], env=env, cwd=root)
        receipt = json.loads(output.decode('utf-8', errors='replace').splitlines()[-1])
        if receipt['state'] != 'installed':
            raise ValueError('installation_not_verified')
        if exercise is not None:
            exercise(project, case, env)
        runner = receipt['runner']
        def cli(*args):
            return json.loads(run([sys.executable, '-B', runner, '--root', str(project),
                                   '--backup-root', str(backups), *args, '--json'], env=env, cwd=root))
        write(project / 'feature.txt', b'new trial work\n')
        write(project / 'vault/local/trial-note.md', b'# Synthetic trial evidence\n')
        if initial_git is not None:
            git_call('add', '--', 'feature.txt')
            write(project / 'app.txt', b'new trial unstaged work\n')
        trial = fs.inspect_tree(project)
        proposal = cli('restore', '--dry-run')
        if case == 'interrupted':
            run([sys.executable, '-B', str(ROOT / 'tests/adoption_crash.py'), str(project),
                 str(backups), proposal['digest'], 'after-rename-1'], env=env, cwd=root, expected=73)
            status = cli('status')
            cli('recover-lock', '--confirm', status['lock_id'])
            restored = cli('recover', '--confirm', status['transaction_id'])
        else:
            restored = cli('restore', '--confirm', proposal['digest'])
        if restored['state'] != 'restored' or fs.inspect_tree(project) != initial:
            raise ValueError('baseline_not_restored')
        if fs.inspect_tree(Path(restored['recovery_path'])) != trial:
            raise ValueError('trial_work_not_preserved')
        if initial_git is not None and git_state() != initial_git:
            raise ValueError('git_state_changed')
        if fs.inspect_tree(home) != home_before:
            raise ValueError('global_profile_changed')
        results.append(dict(case=case, restored=True, trial_preserved=True, home_unchanged=True))
    return dict(platform=platform.system(), python=platform.python_version(), client=client,
                git=run([git, '--version'], env=env, cwd=root).decode().strip(),
                revision=fs.git_read(ROOT, 'rev-parse', 'HEAD').stdout.decode().strip(),
                cases=results, model_calls=0, native_client_conversation='not_exercised')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--client', choices=('claude', 'codex', 'both'), default='both')
    args = parser.parse_args()
    try:
        print(json.dumps(smoke(args.root, args.client), ensure_ascii=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, KeyError):
        print(json.dumps(dict(state='failed', code='adoption_smoke_failed')), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
