"""Check vault metadata and navigation locally, without changing notes or fetching URLs."""
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import posixpath
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

# Reading a vault must not create a bytecode cache in the consumer project.
sys.dont_write_bytecode = True
from integrations import check_path

FIELDS = ('id', 'type', 'title', 'origin', 'updated', 'index')
DESTINATION = r'(<[^>\n]+>|(?:\\.|[^()\\\s]|\([^()\n]*\))+)'
INLINE = re.compile(r'!?\[[^\]\n]*\]\(\s*' + DESTINATION
                    + r'(?:\s+(?:"[^"\n]*"|\'[^\'\n]*\'|\([^\n)]*\)))?\s*\)')


def metadata(text):
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        raise ValueError('Expected frontmatter with id, type, title, origin, updated and index.')
    end = lines.index('---', 1)
    fields = {}
    for line in lines[1:end]:
        match = re.fullmatch(r'([a-z][a-z0-9_-]*):\s*(.*)', line)
        if not match or match[1] not in FIELDS:
            continue
        key, value = match.groups()
        if key in fields:
            raise ValueError('Repeated metadata field: ' + key + '.')
        if value.startswith('"'):
            try:
                value, used = json.JSONDecoder().raw_decode(value)
            except ValueError:
                raise ValueError('Invalid quoted metadata field: ' + key + '.') from None
            tail = match[2][used:].strip()
            if tail and not tail.startswith('#'):
                raise ValueError('Invalid metadata field: ' + key + '.')
        elif value.startswith("'"):
            quoted = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", value)
            if not quoted:
                raise ValueError('Invalid quoted metadata field: ' + key + '.')
            value = quoted[1].replace("''", "'")
        else:
            value = '' if value.startswith('#') else re.split(r'\s+#', value, maxsplit=1)[0].strip()
            if (value.startswith(('[', '{', '&', '*', '!', '|', '>', '@', '%'))
                    or value.lower() in ('null', 'true', 'false', '~')):
                raise ValueError('Use a single-line string for metadata field: ' + key + '.')
        if not value.strip():
            raise ValueError('Empty metadata field: ' + key + '.')
        fields[key] = value
    missing = [key for key in FIELDS if key not in fields]
    if missing:
        raise ValueError('Missing metadata fields: ' + ', '.join(missing) + '.')
    try:
        if len(fields['updated']) == 10:
            date.fromisoformat(fields['updated'])
        else:
            datetime.fromisoformat(fields['updated'].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Use an ISO date or timestamp for updated.') from None
    return fields, '\n'.join(lines[end + 1:])


def prose(text):
    """Leave out comments and fenced/inline code before inspecting Markdown links."""
    lines, fence = [], None
    for line in re.sub(r'<!--.*?-->', '', text, flags=re.S).splitlines():
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
        elif match:
            fence = match[1]
        else:
            lines.append(line)
    return re.sub(r'(`+).*?\1', '', '\n'.join(lines), flags=re.S)


def links(text):
    text = prose(text)
    found = []
    def wiki(match):
        found.append((match[1].split('|', 1)[0], 'wiki'))
        return ''
    text = re.sub(r'!?\[\[([^\]\n]+)\]\]', wiki, text)
    def inline(match):
        found.append((match[1], 'markdown'))
        return ''
    text = INLINE.sub(inline, text)
    references = {}
    def reference(match):
        references[' '.join(match[1].split()).casefold()] = match[2]
        return ''
    text = re.sub(r'^ {0,3}\[([^\]\n]+)\]:\s*' + DESTINATION + r'.*$', reference, text, flags=re.M)
    for match in re.finditer(r'!?\[([^\]\n]+)\](?:\[([^\]\n]*)\])?', text):
        label = ' '.join((match[2] or match[1]).split()).casefold()
        if label in references:
            found.append((references[label], 'markdown'))
        elif match[2] is not None:
            found.append(('', 'missing_reference'))
    return found


def local_path(source, target):
    target = re.sub(r'\\([ !"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~])', r'\1', target.strip('<>'))
    if not target or target.startswith('#'):
        return None
    # Absolute filesystem paths are never interpreted as remote URLs.
    if target.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', target):
        raise ValueError('Use a relative file path inside the project.')
    parsed = urlsplit(target)
    if parsed.scheme == 'file':
        raise ValueError('Local file URIs are not portable project links.')
    if parsed.scheme:
        return None
    decoded = unquote(parsed.path)
    if '\\' in decoded or ':' in decoded or '\x00' in decoded or decoded.startswith('/'):
        raise ValueError('Use a relative file path inside the project.')
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(source), decoded))
    if relative == '..' or relative.startswith('../'):
        raise ValueError('Local link leaves the project.')
    return relative


def check(root):
    issues, notes = [], {}
    def private(path):
        value = path.casefold()
        return any(value == p or value.startswith(p + '/') for p in ('vault/local', '.operacao-local/docling'))
    def issue(path, code, message):
        issues.append(dict(path=path, code=code, message=message))

    def safe(relative):
        try:
            check_path(root, relative)
            try:
                info = (root / relative).lstat()
            except FileNotFoundError:
                return True
            return stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        except (OSError, ValueError):
            return False

    if not safe('vault/index.md'):
        issue('vault', 'unsafe_path', 'Vault must contain regular files and directories, without links.')
    elif not (root / 'vault').is_dir():
        issue('vault', 'missing_vault', 'Initialize or install the vault first.')
    else:
        pending = [root / 'vault']
        while pending:
            directory = pending.pop()
            try:
                children = sorted(directory.iterdir())
            except OSError:
                issue(directory.relative_to(root).as_posix(), 'unreadable', 'Cannot list this directory.')
                continue
            for path in children:
                relative = path.relative_to(root).as_posix()
                if path.name == '.obsidian':
                    continue
                try:
                    directory_entry = path.is_dir()
                    permitted = safe(relative + '/index.md' if directory_entry else relative)
                    if not permitted:
                        issue(relative, 'unsafe_path', 'Linked paths, hardlinks and wrong file types are unsupported.')
                    elif directory_entry:
                        pending.append(path)
                    elif path.suffix.lower() == '.md':
                        text = path.read_text(encoding='utf-8-sig')
                        try:
                            fields, body = metadata(text)
                        except ValueError as error:
                            fields, body = {}, text
                            issue(relative, 'metadata', str(error))
                        notes[relative] = (fields, body)
                except (OSError, UnicodeError):
                    issue(relative, 'unreadable', 'Cannot read this note as UTF-8.')

    if 'vault/index.md' not in notes:
        issue('vault/index.md', 'missing_root_index', 'The general index must be a readable Markdown note.')
    roots = {'vault/index.md', 'vault/local/index.md'} & notes.keys()
    identities, edges, parents = {}, {}, {}
    for source, (fields, body) in notes.items():
        identity = fields.get('id')
        if identity in identities:
            issue(source, 'duplicate_id', 'Identity also used by ' + identities[identity] + '.')
        elif identity:
            identities[identity] = source
        edges[source] = set()
        for target, kind in links(body):
            try:
                if kind == 'missing_reference':
                    issue(source, 'broken_link', 'Undefined Markdown reference label.')
                    continue
                if kind == 'wiki':
                    target = target.split('#', 1)[0]
                    if not target:
                        continue
                    if not Path(target).suffix:
                        target += '.md'
                    relative = local_path(source if target.startswith(('./', '../')) else 'vault/index.md', target)
                    if '/' not in target and relative not in notes:
                        matches = [p for p in notes if p.rsplit('/', 1)[-1] == target]
                        if len(matches) > 1:
                            issue(source, 'ambiguous_link', 'Wiki note name is ambiguous; use its vault-relative path.')
                            continue
                        if matches:
                            relative = matches[0]
                else:
                    relative = local_path(source, target)
                if relative is None:
                    continue
                if not private(source) and private(relative):
                    issue(source, 'private_reference', 'Shared notes must not reference private storage.')
                    continue
                if not safe(relative):
                    raise ValueError('Local link uses an unsupported path.')
                if not (root / relative).is_file():
                    issue(source, 'broken_link', 'Local file target does not exist.')
                elif relative in notes:
                    edges[source].add(relative)
            except ValueError:
                issue(source, 'unsafe_link', 'Use a relative path to a regular file inside the project.')
        if 'index' in fields:
            try:
                parent = local_path(source, fields['index'])
                if parent is not None and not private(source) and private(parent):
                    issue(source, 'private_reference', 'Shared notes must not reference private storage.')
                    continue
                if parent not in notes or not parent.endswith('/index.md'):
                    raise ValueError
                if (source in roots and parent != source) or private(source) != private(parent):
                    raise ValueError
                parents[source] = parent
            except ValueError:
                issue(source, 'invalid_index', 'index must reference a vault index.md; the general index references itself.')
    for source, parent in parents.items():
        if source not in roots and source not in edges.get(parent, set()):
            issue(source, 'missing_index_link', 'The declared index does not link back to this note.')
        current, seen = source, set()
        while current in parents and current not in roots:
            if current in seen:
                issue(source, 'index_cycle', 'The index chain contains a cycle instead of reaching the general index.')
                break
            seen.add(current)
            current = parents[current]
    reached, pending = set(), list(roots)
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(edges.get(current, ()))
    for source in notes.keys() - reached:
        issue(source, 'unreachable', 'No path from the general index reaches this note.')
    return dict(schema_version=1, notes_checked=len(notes),
                issues=sorted(issues, key=lambda x: (x['path'], x['code'], x['message'])))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check',))
    parser.add_argument('--json', action='store_true', help='Print structured diagnostics without note content.')
    args = parser.parse_args()
    result = check(Path.cwd())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result['issues']:
            print(f'{json.dumps(item["path"], ensure_ascii=False)} [{item["code"]}] {json.dumps(item["message"], ensure_ascii=False)}')
        print(f'Vault: {result["notes_checked"]} notes checked; {len(result["issues"])} issues. No files changed.')
    return 1 if result['issues'] else 0


if __name__ == '__main__':
    sys.exit(main())
