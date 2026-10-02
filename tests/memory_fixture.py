"""Synthetic memory corpus; expected claims fixed before search implementation."""
import hashlib
import json
from pathlib import Path
import uuid

PROJECT = '9865926d-6293-4c63-a8ff-c8441674a043'
OTHER = '345466fa-9688-4630-b542-20c8c2ef5e7b'


def seed(root: Path, project_id: str = PROJECT) -> dict:
    root = Path(root)
    folder = root / 'vault/local/demo'
    folder.mkdir(parents=True, exist_ok=True)
    (root / 'vault/project.json').write_text(json.dumps({'project_id': project_id}), encoding='utf-8')
    claims = {
        'api.md': ('Pagamentos API', 'Desenvolvimento: webhook implementado. Produção: não publicado.\nPróxima ação: validar assinatura do webhook.\n[Decisão vigente](webhook.md)\n[Decisão anterior](fila.md)'),
        'portal.md': ('Pagamentos Portal', 'Produção: publicado em release/demo-1 (evidência sintética).\n[Publicação](release.md)'),
        'fila.md': ('Pagamentos decisão substituída', 'Decisão substituída: processar por fila.\n[Substituta vigente](webhook.md)'),
        'webhook.md': ('Pagamentos decisão vigente', 'Decisão vigente: usar webhook para confirmação.\n[Substitui fila](fila.md)\n[API](api.md)'),
        'release.md': ('Pagamentos evidência de publicação', 'Evidência sintética: release/demo-1 publicou somente Pagamentos Portal.\nNão comprova publicação de Pagamentos API.'),
    }
    paths, identities = [], []
    for name, (title, body) in claims.items():
        relative = 'vault/local/demo/' + name
        identity = str(uuid.uuid5(uuid.UUID(project_id), relative))
        fields = dict(id=identity, type='feature' if name in ('api.md', 'portal.md') else 'decision',
                      title=title, origin='youngcrow/synthetic-fixture', updated='2026-10-02', index='index.md')
        if project_id != PROJECT:
            body = 'Outro projeto. Não usar como resultado do projeto principal.\n' + body
        content = '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fields.items())
        (folder / name).write_text(content + '---\n\n# ' + title + '\n\n' + body + '\n', encoding='utf-8')
        paths.append(relative)
        identities.append(identity)
    for relative, parent, body in (
        ('vault/index.md', 'index.md', 'Local: `local/index.md`.'),
        ('vault/local/index.md', 'index.md', '[Demo](demo/index.md)'),
        ('vault/local/demo/index.md', '../index.md', '\n'.join(f'[{n}]({n})' for n in claims)),
    ):
        fields = dict(id=str(uuid.uuid5(uuid.UUID(project_id), relative)), type='index', title='Demo index',
                      origin='youngcrow/synthetic-fixture', updated='2026-10-02', index=parent)
        (root / relative).write_text('---\n' + ''.join(f'{k}: {json.dumps(v)}\n' for k, v in fields.items()) +
                                    '---\n\n' + body + '\n', encoding='utf-8')
    expected = [
        dict(question='Pagamentos API', path=paths[0], quote='Produção: não publicado.', state='development'),
        dict(question='Pagamentos Portal', path=paths[1], quote='Produção: publicado em release/demo-1', state='production'),
        dict(question='decisão vigente', path=paths[3], quote='Decisão vigente: usar webhook', state='current'),
        dict(question='assinatura webhook', path=paths[0], quote='validar assinatura do webhook', state='next_action'),
    ]
    for item in expected:
        item['revision'] = hashlib.sha256((root / item['path']).read_bytes()).hexdigest()
    return dict(project_id=project_id, paths=paths, ids=identities, expected=expected)
