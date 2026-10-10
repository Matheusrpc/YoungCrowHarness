"""Coordination fixtures: native ACLs have separate Windows coverage."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import sys
from unittest.mock import patch

import adoption_fs as fs
import mission_execution as execution


@contextmanager
def registry_storage(base):
    """Avoid hundreds of PowerShell launches only in this temporary registry.

    Ledger, OS locks, atomic writes and process supervision stay real. Product
    permissions and every path outside the fixture retain their original checks.
    """
    base = Path(base).resolve()
    with ExitStack() as stack:
        if sys.platform == 'win32':
            for module, name, replacement in (
                    (execution, 'check_private', fs.checked_path),
                    (fs, 'private_dir', lambda p: fs.checked_path(p).mkdir(mode=0o700)),
                    (fs, 'protect_for_storage', fs.checked_path)):
                original = getattr(module, name)
                def scoped(path, original=original, replacement=replacement):
                    checked = fs.checked_path(path)
                    return (replacement if checked == base or base in checked.parents else original)(path)
                stack.enter_context(patch.object(module, name, side_effect=scoped))
        yield
