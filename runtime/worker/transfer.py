"""Fixed, bounded import used by the controller, never a root command dispatcher."""
import io
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import stat


def export():
    if os.getuid() != 1000:
        return 125
    output = io.BytesIO()
    workspace = Path(os.environ['HOME'])
    total = count = entries = 0
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for root, dirs, names, parent in os.fwalk(workspace, follow_symlinks=False):
            for name in dirs + names:
                entries += 1
                before = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if entries > 256 or not (stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode)):
                    return 125
            for name in names:
                count += 1
                descriptor = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
                with os.fdopen(descriptor, 'rb') as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                        return 125
                    data = stream.read(8 * 1024 * 1024 + 1)
                    after = os.fstat(stream.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    return 125
                total += len(data)
                if total > 8 * 1024 * 1024 or count > 128:
                    return 125
                info = tarfile.TarInfo(str((Path(root) / name).relative_to(workspace)))
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    if len(output.getvalue()) > 9 * 1024 * 1024:
        return 125
    sys.stdout.buffer.write(output.getvalue())
    return 0


def main():
    target = Path('/snapshot' if os.getuid() == 0 else os.environ['HOME'])
    if os.getuid() not in (0, 1000) or len(sys.argv) != 1:
        return 125
    limit = 8 * 1024 * 1024
    data = sys.stdin.buffer.read(limit + 1024 * 1024 + 1)
    if len(data) > limit + 1024 * 1024:
        return 125
    files, total, entries = {}, 0, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for info in archive:
            entries += 1
            path = PurePosixPath(info.name)
            if entries > 256 or not path.parts or path.is_absolute() or '..' in path.parts or str(path) != info.name:
                return 125
            if info.isdir():
                continue
            total += info.size
            if not info.isreg() or info.issparse() or info.name in files or total > limit or len(files) >= 128:
                return 125
            files[info.name] = archive.extractfile(info).read(info.size)
    # The target is empty and private before any tools start, or root-owned /snapshot.
    if any(target.iterdir()):
        return 125
    for name, content in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        with path.open('xb') as stream:
            stream.write(content)
        path.chmod(0o444 if os.getuid() == 0 else 0o600)
    print('imported', flush=True)
    return 0


if __name__ == '__main__':
    try:
        result = export() if sys.argv[1:] == ['--export'] else main()
    except Exception:
        result = 125
    sys.exit(result)
