"""Text the installer adds to a user's files, and takes out again byte for byte.

A managed block sits between two marker lines (AGENTS.md, .gitignore) and one import line
sits in CLAUDE.md. Everything here works on `str`; reading and writing files is the caller's job.

Adding text to a non-empty file puts the file's line ending in front of it, then the text,
then a closing line ending. That one rule is what lets the removal restore the original:
it ends the last line when the file had no final newline and makes a blank line when it did.
"""
import re

MD_START = '<!-- youngcrow:start -->'
MD_END = '<!-- youngcrow:end -->'
GITIGNORE_START = '# youngcrow:start'
GITIGNORE_END = '# youngcrow:end'
IMPORT_LINE = '@.youngcrow/HARNESS.md'


class ManagedBlockError(ValueError):
    """The text has markers or an import line that cannot be told apart safely."""


def _eol(text: str) -> str:
    """First line ending in the text (CRLF or LF); LF when there is none."""
    at = text.find('\n')
    return '\r\n' if at > 0 and text[at - 1] == '\r' else '\n'


def _lines(text: str) -> list[str]:
    """The text cut after each LF, so joining the pieces gives the text back."""
    return re.findall(r'[^\n]*\n|[^\n]+', text)


def _split(line: str) -> tuple[str, str]:
    """A piece from `_lines` as (content, line ending)."""
    for ending in ('\r\n', '\n'):
        if line.endswith(ending):
            return line[:-len(ending)], ending
    return line, ''


def _where(lines: list[str], wanted: str) -> list[int]:
    """Positions of the pieces that are exactly `wanted` (trailing blanks aside)."""
    return [at for at, line in enumerate(lines) if _split(line)[0].rstrip() == wanted]


def _find_block(lines: list[str], start: str, end: str) -> tuple[int, int] | None:
    """Positions of the start and end marker lines, None when there are no markers."""
    starts, ends = _where(lines, start), _where(lines, end)
    for marker, found in ((start, starts), (end, ends)):
        if len(found) > 1:
            raise ManagedBlockError(f'"{marker}" appears {len(found)} times; expected once.')
    if not starts and not ends:
        return None
    if not ends:
        raise ManagedBlockError(f'"{start}" has no matching "{end}".')
    if not starts:
        raise ManagedBlockError(f'"{end}" appears without "{start}".')
    if ends[0] < starts[0]:
        raise ManagedBlockError(f'"{end}" comes before "{start}".')
    return starts[0], ends[0]


def _add(text: str, added: list[str]) -> str:
    """Append `added` lines to the text, in the text's own line ending."""
    eol = _eol(text)
    return eol.join(added) + eol if not text else text + eol + eol.join(added) + eol


def _cut(lines: list[str], first: int, last: int) -> str:
    """The text without lines `first..last`.

    When nothing follows, it also drops the line ending `_add` put in front.
    """
    head, rest = lines[:first], lines[last + 1:]
    if head and not rest:
        ending = _split(lines[last])[1]
        before = head[-1]
        if not (ending and before.endswith(ending)):
            ending = _split(before)[1]
        head[-1] = before[:len(before) - len(ending)]
    return ''.join(head + rest)


def upsert_block(text: str, body: str, start: str, end: str) -> str:
    """Put `body` between the markers: replace an existing block, else append one."""
    lines = _lines(text)
    found = _find_block(lines, start, end)
    inner = body.replace('\r\n', '\n').rstrip('\n')
    block = [start, *(inner.split('\n') if inner else []), end]
    if found is None:
        return _add(text, block)
    first, last = found
    eol = _split(lines[first])[1]
    return ''.join(lines[:first]) + eol.join(block) + _split(lines[last])[1] + ''.join(lines[last + 1:])


def remove_block(text: str, start: str, end: str) -> str:
    """Take the block out; text without one comes back unchanged."""
    lines = _lines(text)
    found = _find_block(lines, start, end)
    return text if found is None else _cut(lines, *found)


def ensure_line(text: str, line: str) -> str:
    """Add `line` as its own line unless the text already has it."""
    if _where(_lines(text), line):
        return text
    return _add(text, [line])


def remove_line(text: str, line: str) -> str:
    """Take `line` out; text without it comes back unchanged."""
    lines = _lines(text)
    found = _where(lines, line)
    if len(found) > 1:
        raise ManagedBlockError(f'"{line}" appears {len(found)} times; expected once.')
    return text if not found else _cut(lines, found[0], found[0])
