"""Create integration notes or export revision-addressed records. No network calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import uuid


def slug(value):
    if (not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', value)
            or re.fullmatch(r'con|prn|aux|nul|com[0-9]|lpt[0-9]', value)):
        raise argparse.ArgumentTypeError('Use a lowercase slug, 1–63 letters/digits/hyphens; no reserved device names.')
    return value


def check_path(root, relative):
    current = root
    parts = Path(relative).parts
    for i, part in enumerate(parts):
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        # Windows FILE_ATTRIBUTE_REPARSE_POINT, including Python 3.11 junctions.
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked vault path is not supported.')
        if stat.S_ISDIR(metadata.st_mode) != (i < len(parts) - 1):
            raise ValueError('Wrong path type in vault.')
        if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink > 1:
            raise ValueError('Hardlinked vault file is not supported.')


def note(project, path, kind, title, parent, body, now):
    identity = str(uuid.uuid5(uuid.UUID(project), path))
    fields = {'id': identity, 'type': kind, 'title': title, 'origin': 'youngcrow/integrations',
              'updated': now, 'index': parent}
    return '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fields.items()) + '---\n\n' + body


def initialize(root, provider, service, run):
    base = f'vault/integrations/{provider}/{service}'
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    # All destinations are checked before creating anything. One writer per checkout.
    notes = {
        'vault/index.md': ('index', 'Vault', 'index.md', '# Vault\n\nConhecimento durável deste projeto.\n'),
        'vault/integrations/index.md': ('index', 'Integrações', '../index.md', '# Integrações\n\n[Vault](../index.md)\n'),
        f'vault/integrations/{provider}/index.md': ('index', provider, '../index.md', f'# {provider}\n\n[Integrações](../index.md)\n'),
        f'{base}/index.md': ('integration', service, '../index.md', f'''# {provider} / {service}

[Fornecedor](../index.md)

- Objetivo e responsável: não registrados.
- Feature/frente e decisões relacionadas: adicionar links de ida e volta aos registros existentes.
- Desenvolvimento: não verificado; registrar versão/API/SDK e evidência.
- Produção: desconhecida; exigir release/revisão, ambiente, data e evidência.
- Próxima ação: consultar fontes oficiais e conferir as dependências do projeto.

[Fontes](sources.md) · [Implementação](implementation.md) · [Operação](operations.md)
'''),
        f'{base}/sources.md': ('sources', 'Fontes oficiais', 'index.md', '''# Fontes oficiais

[Integração](index.md)

| URL oficial / seção | API/SDK/versão | Consulta UTC | Orientação aplicável | Limitações |
|---|---|---|---|---|

Fonte ainda não consultada. Registrar fonte inacessível ou versão indefinida como bloqueio.
Distinguir orientação do fornecedor, decisão do projeto, evidência de teste e hipótese.
Revisões obsoletas devem apontar para a substituta; preservar o histórico no Git.
'''),
        f'{base}/implementation.md': ('implementation', 'Implementação', 'index.md', '''# Implementação

[Integração](index.md) · [Fontes](sources.md)

## Contrato e decisões

Ainda não implementado. Registrar autenticação/escopos, schemas, erros, limites,
paginação, timeouts, retries, idempotência e webhooks quando aplicáveis.
Registrar SDK instalado, versão alvo, compatibilidade e desvios justificados do fornecedor.
Linkar feature, decisões, código e testes. Somente nomes de variáveis; nunca valores secretos.

## Entregas e aceite

Dividir em pequenas entregas verificáveis; registrar teste, comando, resultado e pendências.
'''),
        f'{base}/operations.md': ('operations', 'Operação', 'index.md', '''# Operação

[Integração](index.md) · [Implementação](implementation.md)

| Ambiente | API/SDK | Revisão/release | Evidência/data | Estado |
|---|---|---|---|---|
| Desenvolvimento | não verificada | não verificada | ausente | desconhecido |
| Produção | não verificada | não verificada | ausente | desconhecido |

Registrar configuração sem segredos, publicação autorizada, observabilidade, limites,
falhas conhecidas, recuperação e rollback. Sandbox não comprova produção.
'''),
        f'{base}/runs/{run}.md': ('run', run, '../index.md', '''# Execução

[Integração](../index.md) · [Fontes](../sources.md) · [Operação](../operations.md)

- Objetivo/frente: não registrado.
- Agente/host: não registrado.
- Capacidades previstas (skills, MCPs, agentes): não registradas.
- Capacidades realmente usadas (nome, versão, finalidade): nenhuma registrada.
- Código/decisões alterados: nenhum registrado.
- Evidências sanitizadas (comando, saída, ambiente, revisão): nenhuma registrada.
- Resultado: não executado.
- Bloqueios e próxima ação: recuperar contexto e verificar fontes.
- Graphify: pending — não sincronizado.
- claude-mem: pending — não sincronizado.

Registrar IDs de recibos/consultas e revisão da origem somente após confirmação do destino.
Falha de indexação não desfaz uma entrega no vault nem comprova sucesso no destino.
'''),
    }
    for path in [*notes, 'vault/project.json']:
        check_path(root, path)
    identity_file = root / 'vault/project.json'
    project = project_identity(identity_file) if identity_file.exists() else str(uuid.uuid4())
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    if not identity_file.exists():
        with identity_file.open('x', encoding='utf-8', newline='\n') as output:
            output.write(json.dumps({'project_id': project}, indent=2) + '\n')
    for path, (kind, title, parent, body) in notes.items():
        destination = root / path
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('x', encoding='utf-8', newline='\n') as output:
                output.write(note(project, path, kind, title, parent, body, now))
    links = [
        ('vault/index.md', '[Integrações](integrations/index.md)'),
        ('vault/integrations/index.md', '[Vault](../index.md)'),
        ('vault/integrations/index.md', f'[{provider}]({provider}/index.md)'),
        (f'vault/integrations/{provider}/index.md', '[Integrações](../index.md)'),
        (f'vault/integrations/{provider}/index.md', f'[{service}]({service}/index.md)'),
        (f'{base}/index.md', '[Fornecedor](../index.md)'),
        (f'{base}/index.md', '[Fontes](sources.md)'),
        (f'{base}/index.md', '[Implementação](implementation.md)'),
        (f'{base}/index.md', '[Operação](operations.md)'),
        (f'{base}/index.md', f'[{run}](runs/{run}.md)'),
    ]
    for path, link in links:
        destination = root / path
        data = destination.read_bytes()
        target = link[link.index('](') + 1:]
        if target.encode() not in data:
            with destination.open('ab') as output:
                output.write(('\n- ' + link + '\n').encode('utf-8'))
    print(f'Ready: {base}/index.md (existing knowledge preserved).')


def project_identity(path):
    return str(uuid.UUID(json.loads(path.read_text(encoding='utf-8'))['project_id']))


def export(root, provider, service):
    base = root / f'vault/integrations/{provider}/{service}'
    check_path(root, 'vault/project.json')
    check_path(root, (base / 'index.md').relative_to(root))
    project = project_identity(root / 'vault/project.json')
    if not (base / 'index.md').is_file():
        raise ValueError('Initialize the integration first.')
    records = []
    identities = set()
    paths = sorted(base.rglob('*.md'))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        check_path(root, relative)
        data = path.read_bytes()
        content = data.decode('utf-8')
        header = content.replace('\r\n', '\n').split('---\n', 2)
        match = re.search(r'^id: *"?([0-9a-f-]{36})"? *$', header[1], re.MULTILINE) if len(header) == 3 and header[0] == '' else None
        if not match:
            raise ValueError('Note requires a UUID id in frontmatter.')
        identity = str(uuid.UUID(match[1]))
        if identity in identities:
            raise ValueError('Duplicate note id.')
        identities.add(identity)
        records.append({'id': identity, 'path': relative,
                        'revision': hashlib.sha256(data).hexdigest(), 'content': content})
    print(json.dumps({'schema_version': 1, 'project_id': project,
                      'integration': f'{provider}/{service}', 'sync_state': 'pending',
                      'observed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                      'notes': records}, ensure_ascii=False, indent=2))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'export'))
    parser.add_argument('--provider', required=True, type=slug)
    parser.add_argument('--service', required=True, type=slug)
    parser.add_argument('--run', type=slug)
    args = parser.parse_args()
    if args.command == 'init' and not args.run:
        parser.error('init requires --run (a unique execution slug).')
    try:
        root = Path.cwd()
        if args.command == 'init':
            initialize(root, args.provider, args.service, args.run)
        else:
            export(root, args.provider, args.service)
    except (OSError, ValueError, KeyError, TypeError):
        # Do not echo file content or credentials from corrupt notes/configuration.
        print('Vault operation failed: check paths, permissions and vault/project.json. No sync was attempted.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
