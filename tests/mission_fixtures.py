"""Small real-project fixtures shared by mission checks and the adoption smoke."""
import json
import uuid

from test_documents import ProjectCase
from test_mission_config import configured
import personalize
from integrations import note
import vault

NOW = '2026-10-03T12:00:00+00:00'
START = '<!-- youngcrow:contract:start -->'
END = '<!-- youngcrow:contract:end -->'


class MissionCase(ProjectCase):
    def setUp(self):
        super().setUp()
        personalize.prepare(self.root, 'init', 'fixture', mode='new')
        self.project_id = self.store.prepare_storage(self.root)

    def configured(self):
        return configured()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and '.git' not in p.relative_to(self.root).parts}

    def index(self, relative, parent, title):
        path = self.root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(note(self.project_id, relative, 'index', title, parent,
                                 f'# {title}\n\n[Index]({parent})\n', NOW), encoding='utf-8')

    def write_item(self, kind, parent_id=None, complete=True):
        identity = str(uuid.uuid4())
        base = f'vault/local/product/{kind}s'
        self.index('vault/local/product/index.md', '../index.md', 'Product')
        self.store.append_link(self.root, 'vault/local/index.md', '[Product](product/index.md)')
        self.index(base + '/index.md', '../index.md', kind + 's')
        self.store.append_link(self.root, 'vault/local/product/index.md', f'[{kind}s]({kind}s/index.md)')
        path = f'{base}/{identity}/index.md'
        contract = dict(schema_version=1, project_id=self.project_id, parent_id=parent_id,
                        owner='tech_lead' if kind == 'pbi' else 'pm', objective='Fixture outcome' if complete else '',
                        acceptance=['observable outcome'] if complete else [], dor=['inputs available'] if complete else [],
                        dod=['verified production'] if complete else [], validation=['local test'] if complete else [],
                        dependencies=[], references=[])
        if kind == 'pbi' and complete:
            profile = 'vault/product/profile.md'
            contract['references'] = [dict(note_id=vault.metadata((self.root / profile).read_text(encoding='utf-8'))[0]['id'], path=profile)]
        body = f'# Fixture {kind}\n\n[Index](../index.md)\n\n{START}\n```json\n{json.dumps(contract, indent=2)}\n```\n{END}\n\nHuman prose stays here.\n'
        content = note(self.project_id, path, kind, 'Fixture ' + kind, '../index.md', body, NOW)
        fields, _ = vault.metadata(content)
        content = content.replace(fields['id'], identity).replace('youngcrow/integrations', 'youngcrow/missions')
        self.store.atomic_write(self.root, path, content.encode())
        self.store.append_link(self.root, base + '/index.md', f'[{identity}]({identity}/index.md)')
        return path

    def item_id(self, path):
        return vault.metadata((self.root / path).read_text(encoding='utf-8'))[0]['id']

    def contract(self, path, **patch):
        file = self.root / path
        text = file.read_text(encoding='utf-8')
        before, tail = text.split(START)
        block, after = tail.split(END)
        raw = json.loads(block.split('```json')[1].split('```')[0])
        raw.update(patch)
        file.write_text(before + START + '\n```json\n' + json.dumps(raw, indent=2) + '\n```\n' + END + after, encoding='utf-8')

    def tree(self, features=1, pbis=2):
        epic = self.write_item('epic')
        paths = [epic]
        for _ in range(features):
            feature = self.write_item('feature', self.item_id(epic))
            paths.append(feature)
            for _ in range(pbis):
                paths.append(self.write_item('pbi', self.item_id(feature)))
        return paths
