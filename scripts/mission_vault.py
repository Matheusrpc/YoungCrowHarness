"""Mission notes use explicit UUIDs; source Markdown remains human editable."""
import json
import hashlib
import posixpath
import re
import uuid

from capabilities import read_inputs
from document_store import safe_path, atomic_write, append_link
from mission_backlog import identity, KINDS, START, END, require


def escape(value):
    return re.sub(r'([\\`*_{}\[\]()<>#!|])', r'\\\1', value)


def markdown(note_id, kind, title, index, body, now):
    fields = dict(id=identity(note_id), type=kind, title=title, origin='youngcrow/missions', updated=now, index=index)
    return '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fields.items()) + '---\n\n' + body


def render_item(project_id: str, item_id: str, kind: str, title: str, parent_id: str | None, now: str) -> str:
    identity(project_id)
    identity(item_id)
    if parent_id is not None:
        identity(parent_id)
    require(kind in KINDS and isinstance(title, str) and title.strip() and '\n' not in title)
    contract = dict(schema_version=1, project_id=project_id, parent_id=parent_id,
                    owner='tech_lead' if kind == 'pbi' else 'pm', objective='', acceptance=[], dor=[], dod=[],
                    validation=[], dependencies=[], references=[])
    body = (f'# {escape(title)}\n\n[Index](../index.md)\n\n{START}\n```json\n'
            + json.dumps(contract, ensure_ascii=False, indent=2) + f'\n```\n{END}\n')
    return markdown(item_id, kind, title, '../index.md', body, now)


def projection_paths(record, event):
    folder = 'vault/local/missions' if record['kind'] == 'mission' else 'vault/local/operations/items'
    return [f"{folder}/{record['id']}/index.md", f"vault/local/operations/events/{event['sequence']:06}-{event['event_id']}.md"]


def project_receipt(root, receipt, record):
    from mission_store import transaction, event_dict, record_dict
    with transaction(root) as conn:
        row = conn.execute('SELECT * FROM events WHERE seq=? AND id=?', (receipt['sequence'], receipt['event_id'])).fetchone()
        require(row is not None, 'unknown_event')
        event = event_dict(row)
        record = record_dict(conn.execute('SELECT * FROM records WHERE id=?', (event['record_id'],)).fetchone())
        current_event = event_dict(conn.execute('SELECT * FROM events WHERE record_id=? ORDER BY seq DESC LIMIT 1', (record['id'],)).fetchone())
        paths = projection_paths(record, event)
        indices = {
            'vault/local/operations/index.md': ('../index.md', 'Operations'),
            'vault/local/operations/items/index.md': ('../index.md', 'Imported items'),
            'vault/local/operations/events/index.md': ('../index.md', 'Events'),
            'vault/local/missions/index.md': ('../index.md', 'Missions'),
        }
        for path in [*paths, *indices, 'vault/local/index.md']:
            safe_path(root, path)
        title = record['snapshot'].get('title', record['code'])
        parent = '../index.md'
        body = (f"# {record['code']} · {escape(title)}\n\n[Index]({parent})\n\n"
                f"Revision: {record['revision']}. Event: {current_event['sequence']}.\n\n"
                'Runtime available: false. Production: not verified.\n\n'
                + '```json\n' + json.dumps(record['snapshot'], ensure_ascii=False, indent=2) + '\n```\n')
        # Keep source identity exclusively on the editable backlog note.
        projection_id = str(uuid.uuid5(uuid.UUID(receipt['project_id']), paths[0]))
        current = markdown(projection_id, 'mission' if record['kind'] == 'mission' else 'receipt',
                           title, parent, body, current_event['created_at']).encode()
        event_body = (f"# Event {event['sequence']}\n\n[Events](index.md)\n\n"
                      + '```json\n' + json.dumps({k: v for k, v in event.items() if k not in ('projection_state', 'request_hash')}, ensure_ascii=False, indent=2) + '\n```\n')
        history = markdown(event['event_id'], 'event', f"Event {event['sequence']}", 'index.md', event_body, event['created_at']).encode()
        outputs = [(paths[0], current, current_event['sequence']), (paths[1], history, event['sequence'])]
        # Check every output before changing any of them. A crash after a write can adopt identical bytes.
        for path, data, _ in outputs:
            if (root / path).exists():
                observed = read_inputs(root, [path])[path]
                saved = conn.execute('SELECT sha256 FROM projections WHERE path=?', (path,)).fetchone()
                if observed != data and (saved is None or hashlib.sha256(observed).hexdigest() != saved[0]):
                    conn.execute("UPDATE events SET projection_state='conflict' WHERE seq=?", (event['sequence'],))
                    return dict(state='conflict', paths=paths)
        for path, (index, label) in indices.items():
            if not (root / path).exists():
                note_id = str(uuid.uuid5(uuid.UUID(receipt['project_id']), path))
                atomic_write(root, path, markdown(note_id, 'index', label, index, f'# {label}\n\n[Index]({index})\n', event['created_at']))
        for source, target, label in (
                ('vault/local/index.md', 'operations/index.md', 'Operations'),
                ('vault/local/index.md', 'missions/index.md', 'Missions'),
                ('vault/local/operations/index.md', 'items/index.md', 'Imported items'),
                ('vault/local/operations/index.md', 'events/index.md', 'Events')):
            append_link(root, source, f'[{label}]({target})')
        for path, data, sequence in outputs:
            if not (root / path).exists() or read_inputs(root, [path])[path] != data:
                atomic_write(root, path, data)
            conn.execute('INSERT INTO projections VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,sequence=excluded.sequence',
                         (path, hashlib.sha256(data).hexdigest(), sequence))
        for path, index in ((paths[0], posixpath.dirname(posixpath.dirname(paths[0])) + '/index.md'),
                            (paths[1], 'vault/local/operations/events/index.md')):
            target = posixpath.relpath(path, posixpath.dirname(index))
            append_link(root, index, f'[{record["code"]}]({target})')
        conn.execute("UPDATE events SET projection_state='current' WHERE seq=?", (event['sequence'],))
        return dict(state='current', paths=paths)
