"""Prepare a resumable product profile and feature records; no audit or deployment is run."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import stat
import sys
import uuid

from integrations import check_path, note, project_identity, slug


def prepare(root, command, run, mode=None, feature=None):
    state_path = 'vault/product/onboarding.json'
    for path in ('vault/project.json', state_path, 'vault/product/profile.md'):
        check_path(root, path)
    state_file = root / state_path
    if state_file.exists():
        recorded = json.loads(state_file.read_text(encoding='utf-8'))['mode']
        if recorded not in ('new', 'existing') or (mode and mode != recorded):
            raise ValueError('Mode conflict; resume the recorded mode.')
        mode = recorded
    if command == 'feature' and not (state_file.is_file() and (root / 'vault/product/profile.md').is_file()
                                      and (root / 'vault/project.json').is_file()):
        raise ValueError('Initialize the profile first.')

    notes = {}
    links = []

    def add(path, kind, title, parent, body):
        notes[path] = (kind, title, parent, f'# {title}\n\n' + body)

    def link(path, label, target):
        links.append((path, f'[{label}]({target})'))

    add('vault/index.md', 'index', 'Vault', 'index.md', 'Conhecimento durável do projeto.\n')
    for area, title in (('product', 'Produto'), ('features', 'Features'), ('decisions', 'Decisões'),
                        ('operations', 'Operação')):
        path = f'vault/{area}/index.md'
        add(path, 'index', title, '../index.md', '[Vault](../index.md)\n')
        link('vault/index.md', title, f'{area}/index.md')
        link(path, 'Vault', '../index.md')

    if command == 'init':
        add('vault/product/profile.md', 'product', 'Perfil do produto', 'index.md', '''[Produto](index.md)

Estado da entrevista: em andamento. Modo e respostas são retomados do registro ligado no índice.

## Contexto confirmado

Registrar problema, público, resultado esperado, limites do primeiro lançamento e quem decide.
Cada resposta deve indicar origem (operador, arquivo, medição), data e grau de certeza.

## Decisões e dúvidas

Registrar stack existente/escolhida, design system com referência, restrições, dados tratados,
integrações, orçamento/prazo e perguntas ainda abertas. Desconhecido permanece desconhecido.
Referenciar decisões canônicas em vez de duplicá-las. Não guardar credenciais.

## Operação e aceite

Registrar papéis PM/Tech Lead/implementação/revisão/publicação, comandos de teste/build realmente
verificados, política de publicação e rollback. Separar disponibilidade de skill/MCP de autorização.
Definir aceite da primeira feature e quais dúvidas bloqueiam essa entrega.

Desenvolvimento: não verificado. Produção: desconhecida, sem evidência de implantação.
''')
        add('vault/product/adoption.md', 'adoption', 'Adoção do harness', 'index.md', '''[Produto](index.md) · [Perfil](profile.md)

| Arquivo/capacidade | Estado observado e fonte | Preservar/adaptar/criar | Alteração e motivo | Verificação/retorno |
|---|---|---|---|---|

Não executado. Inventariar guias, skills, MCPs, hooks, design e documentos antes de adaptar.
Editar somente o necessário dentro da autorização atual; preservar regras e histórico do produto.
Registrar diff e resultado real dos checks. Scripts sugeridos pela documentação ainda exigem conferência.

| Capacidade | Necessária por quê | Encontrada/versão | Permissão e responsável | Verificação |
|---|---|---|---|---|

Configuração, credenciais e instalação de fornecedores são etapas distintas. Não habilitar tudo por padrão.
''')
        add(f'vault/product/interviews/{run}.md', 'interview', f'Entrevista {run}', '../index.md', f'''[Produto](../index.md) · [Perfil](../profile.md) · [Adoção](../adoption.md)

- Modo: {mode}.
- Estado: em andamento; marcar pausada, bloqueada ou suficiente para a próxima entrega quando observado.
- Contexto já recuperado: não registrado.
- Respostas confirmadas e respectivas fontes: nenhuma registrada.
- Hipóteses e decisões substituídas: nenhuma registrada.
- Perguntas abertas e dependências: não registradas.
- Próxima pergunta: a formular com base nas lacunas reais.
- Capacidades previstas/usadas: não registradas.
- Próximo passo e motivo da pausa: não registrados.

Salvar após cada rodada e antes de encerrar. Retomar este registro sem repetir respostas confirmadas.
''')
        for label, target in (('Perfil', 'profile.md'), ('Adoção', 'adoption.md'),
                              (f'Entrevista {run}', f'interviews/{run}.md')):
            link('vault/product/index.md', label, target)
        if mode == 'existing':
            add('vault/product/audit.md', 'audit', 'Auditoria de adoção', 'index.md', '''[Produto](index.md) · [Perfil](profile.md) · [Adoção](adoption.md)

Estado: ainda não auditado. O agente deve ler código, instruções e evidências antes de preencher.

| Área | Observado (arquivo/comando/revisão) | Intenção documentada | Desconhecido/conflito | Ação |
|---|---|---|---|---|

Cobrir arquitetura/dependências, scripts/testes/build, AGENTS/CLAUDE, skills/MCPs/hooks,
documentos/memórias, design system e fronteiras dos ambientes. Registrar checks executados e saídas
sanitizadas. Comando ausente ou não executado não é teste aprovado. Não inferir produção pelo código.
''')
            link('vault/product/index.md', 'Auditoria', 'audit.md')
    else:
        base = f'vault/features/{feature}'
        add(f'{base}/index.md', 'feature', feature, '../index.md', '''[Features](../index.md) · [Perfil](../../product/profile.md)

- Problema, resultado, responsável e critérios de aceite: não definidos.
- Prioridade/dependências: não definidas.
- Decisões e integrações: linkar registros existentes e acrescentar o link de volta.
- Desenvolvimento: não iniciado.
- Produção: desconhecida, sem release/evidência.
- Próxima ação: definir a menor entrega verificável.
''')
        add(f'{base}/delivery.md', 'delivery', 'Plano de entregas', 'index.md', '''[Feature](index.md)

| Entrega pequena | Aceite verificável | Dependências | Responsável | Estado/evidência |
|---|---|---|---|---|

Não iniciado. Cada entrega inclui mudança, testes pertinentes, revisão e atualização do README.
O PM define resultado/prioridade; o Tech Lead verifica dependências e divisão; o executor implementa;
o revisor avalia diff/evidências. Esses papéis podem ser exercidos em sessões diferentes.
Publicação só se incluída no escopo e autorizada; registrar versão, observação e rollback.
''')
        add(f'{base}/runs/{run}.md', 'run', run, '../index.md', '''[Feature](../index.md) · [Entregas](../delivery.md)

- Objetivo/entrega e revisão inicial: não registrados.
- Agente/host e capacidades previstas/usadas: não registrados.
- Mudanças e decisões: não registradas.
- Testes (comando, ambiente, resultado, evidência): não executados.
- Revisão (responsável, independência, achados, resolução): não realizada.
- README/documentação atualizados e revisão humanizer: não realizados.
- Desenvolvimento: não verificado. Produção: desconhecida.
- Publicação autorizada, release e observação/rollback: não realizados.
- Bloqueios, próximo passo e responsável: não registrados.
- Vault: registro criado; Graphify/claude-mem: não sincronizados.
''')
        link('vault/features/index.md', feature, f'{feature}/index.md')
        link(f'{base}/index.md', 'Features', '../index.md')
        link(f'{base}/index.md', 'Perfil', '../../product/profile.md')
        link(f'{base}/index.md', 'Entregas', 'delivery.md')
        link(f'{base}/index.md', run, f'runs/{run}.md')

    for path in notes:
        check_path(root, path)
    # Check append targets before creating notes, including with an older installed helper.
    for path, value in links:
        destination = root / path
        if destination.exists():
            target = value[value.index('](') + 1:].encode()
            if target not in destination.read_bytes():
                metadata = destination.stat()
                if metadata.st_nlink > 1 or not metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                    raise ValueError('Index must be writable and not hardlinked.')
                with destination.open('ab'):
                    pass  # Check actual access without changing the index bytes.
    identity = root / 'vault/project.json'
    project = project_identity(identity) if identity.exists() else str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    # Keep the original helper signature: setup preserves existing consumer scripts.
    records = {path: note(project, path, *fields, now).replace(
                   '\norigin: "youngcrow/integrations"\n', '\norigin: "youngcrow/personalizer"\n', 1)
               for path, fields in notes.items()}
    records['vault/project.json'] = json.dumps({'project_id': project}, indent=2) + '\n'
    records[state_path] = json.dumps({'mode': mode}, indent=2) + '\n'
    for path, content in records.items():
        destination = root / path
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('x', encoding='utf-8', newline='\n') as output:
                output.write(content)
    for path, value in links:
        destination = root / path
        target = value[value.index('](') + 1:]
        if target.encode() not in destination.read_bytes():
            with destination.open('ab') as output:
                output.write(('\n- ' + value + '\n').encode('utf-8'))
    print('Ready: vault/product/index.md' if command == 'init' else f'Ready: vault/features/{feature}/index.md')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Create or resume onboarding notes.')
    init.add_argument('--mode', choices=('new', 'existing'), required=True)
    init.add_argument('--run', type=slug, required=True)
    feature = commands.add_parser('feature', help='Create or resume a feature and delivery run.')
    feature.add_argument('--slug', type=slug, required=True)
    feature.add_argument('--run', type=slug, required=True)
    args = parser.parse_args()
    try:
        prepare(Path.cwd(), args.command, args.run, getattr(args, 'mode', None), getattr(args, 'slug', None))
    except (OSError, ValueError, KeyError, TypeError):
        print('Personalizer failed: check paths, project identity, and recorded onboarding mode; initialize the profile before features.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
