"""Crash a synthetic restore subprocess; never expose failure switches in the product."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import adoption

root, base, digest, point = sys.argv[1:]
original_rename = os.rename
original_journal = adoption.write_journal
renames = 0


def rename(source, destination):
    global renames
    renames += 1
    if point == f'before-rename-{renames}':
        os._exit(73)
    original_rename(source, destination)
    if point == f'after-rename-{renames}':
        os._exit(73)


def journal(transaction, previous, phase):
    result = original_journal(transaction, previous, phase)
    if phase == point:
        os._exit(73)
    return result


os.rename = rename
adoption.write_journal = journal
adoption.restore(Path(root), Path(base), digest)
raise SystemExit('requested crash point was not reached')
