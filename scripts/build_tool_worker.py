"""Build the pinned worker with an already installed, verified official Codex binary."""
import argparse
import json
from pathlib import Path
import shutil

import adoption_fs as fs
import mission_tool_clients as clients
import mission_worker as worker

BWRAP_SHA256 = '77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c'


def build(docker, codex, output, *, bwrap):
    binary = clients.verify_binary('codex', codex)
    worker.require(Path(bwrap).is_absolute() and clients.hash_executable(bwrap) == BWRAP_SHA256,
                   'unsupported_codex_bwrap')
    output = fs.checked_path(Path(output).absolute())
    fs.private_dir(output)
    context = output/'context'
    fs.private_dir(context)
    source = Path(__file__).resolve().parents[1]/'runtime/worker'
    shutil.copyfile(codex, context/'codex')
    worker.require(clients.hash_executable(context/'codex') == binary['sha256'], 'worker_input_changed')
    shutil.copyfile(bwrap, context/'bwrap')
    worker.require(clients.hash_executable(context/'bwrap') == BWRAP_SHA256, 'worker_input_changed')
    for name in ('guardian.py', 'check.py', 'transfer.py', 'mcp.py', 'worker.dockerfile'):
        shutil.copyfile(source/name, context/name)
    worker.call(docker, ['build', '--network=none', '-q', '-f', str(context/'worker.dockerfile'),
                         '--iidfile', str(output/'image.id'), str(context)], seconds=120,
                buildx_config=output/'buildx')
    digest = (output/'image.id').read_text().strip()
    result = dict(kind='local-worker-build', image_digest=digest, codex=binary, engine=worker.engine(docker),
                  source_sha256={p.name:worker.sha(p.read_bytes()) for p in context.iterdir() if p.name!='codex'})
    (output/'build.json').write_bytes(fs.canonical(result)+b'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker-executable', type=Path, required=True)
    parser.add_argument('--codex-executable', type=Path, required=True)
    parser.add_argument('--bwrap-executable', type=Path, required=True,
                        help='Pinned codex-resources/bwrap from the official Codex package')
    parser.add_argument('--output', type=Path, required=True, help='New private directory; existing results are never overwritten')
    args = parser.parse_args()
    print(json.dumps(build(args.docker_executable,args.codex_executable,args.output,bwrap=args.bwrap_executable)))


if __name__ == '__main__':
    main()
