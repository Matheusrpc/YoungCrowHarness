"""Mission notes use explicit UUIDs; source Markdown remains human editable."""
import json
import re

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
