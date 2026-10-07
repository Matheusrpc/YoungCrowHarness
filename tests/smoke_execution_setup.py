"""Eight installed trial combinations. No SSH, Docker or client/model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import sys

from smoke_adoption import ROOT, smoke, run, write, shell_path, fs
from test_setup import snapshot_bytes


def check(value, reason):
    if not value:
        raise ValueError(reason)


def matrix(root):
    root = fs.checked_path(root)
    check(not root.exists() and root.parent.is_dir(), 'requires_new_disposable_root')
    fs.outside_git(root)
    fs.private_dir(root)
    results = []
    for number, (client, location) in enumerate((c, l) for c in ('claude', 'codex')
                                               for l in ('local', 'dedicated')):
        preserved, observations = {}, []

        def prepare(project, case, env):
            for name, data in {'youngcrow/agents.json': b'{"human":"synthetic config"}\n',
                               'vault/product/human.md': b'# Existing product\n',
                               'vault/local/operations/human-receipt.json': b'{"synthetic":true}\n'}.items():
                write(project / name, data)
                preserved[name] = hashlib.sha256(data).hexdigest()

        def exercise(project, case, env):
            def cli(*args):
                return json.loads(run([sys.executable, '-B', 'scripts/missions.py', 'environment', *args, '--json'],
                                      env=env, cwd=project))
            before = snapshot_bytes(project)
            choice = cli('show')
            check(snapshot_bytes(project) == before, 'show_wrote_project')
            check((choice['origin'], choice['location']) == ('configured', location), 'wrong_selection')
            guide = project / 'skills/personalizer/references/execution.md'
            check(guide.is_file(), 'missing_installed_guide')
            check((project / ('./.claude' if client == 'claude' else './.agents') /
                   'skills/yc-personalizer/SKILL.md').is_file(), 'missing_client_entry')
            # No flag on reinstall: preserve explicit dedicated selection, including timestamp.
            bash = shutil.which('bash') or str(Path(shutil.which('git')).parent.parent / 'bin/bash.exe')
            prefix = f'export PATH={shlex.quote(shell_path(project.parent / "bin"))}:"$PATH"; exec bash "$@"'
            run([bash, '--noprofile', '--norc', '-c', prefix, 'execution-smoke',
                 shell_path(ROOT / 'setup.sh'), shell_path(project), '--trial', '--client', client,
                 '--backup-root', shell_path(project.parent / 'backups'), '--force'], env=env, cwd=project.parent)
            check(cli('show') == choice, 'reinstall_changed_selection')
            hashes = {}
            if case != 'absent':
                for name, expected in preserved.items():
                    hashes[name] = hashlib.sha256((project / name).read_bytes()).hexdigest()
                    check(hashes[name] == expected, 'reinstall_changed_human_data')
            observations.append(dict(case=case, location=choice['location'], origin=choice['origin'],
                                     selection_sha256=choice['digest'], read_only=True,
                                     reinstall_preserved=True, human_sha256=hashes))

        report = smoke(root / str(number), client, prepare_existing=prepare, exercise=exercise,
                       cases=('absent', 'dirty-git'), setup_options=('--execution-location', location))
        for observed, restored in zip(observations, report['cases'], strict=True):
            results.append(dict(observed, **{k: v for k, v in restored.items() if k != 'case'}, client=client))
    return dict(schema_version=1, matrix=results, model_calls=0, native_execution='not_run',
                dedicated_proof='selection_only', revision=fs.git_read(ROOT, 'rev-parse', 'HEAD').stdout.decode().strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(matrix(args.root), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
