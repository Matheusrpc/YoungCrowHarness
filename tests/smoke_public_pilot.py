"""Exercise the real board through new/existing trial adoption; no model calls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from smoke_adoption import ROOT, smoke, run, write
from integrations import note

EXAMPLE = ROOT / 'examples/delivery-board'
PUBLIC_FILES = ('index.html', 'style.css', 'app.mjs', 'model.mjs', 'data.json', 'gema-cobalto.svg')


def pilot(root, client):
    node, git = shutil.which('node'), shutil.which('git')
    if not node or not git:
        raise ValueError('requires_node_and_git')
    deliveries = []

    def prepare_existing(project, case, env):
        for name in ('data.json', 'model.mjs', 'tests/model.test.mjs'):
            write(project / name, (EXAMPLE / name).read_bytes())
        write(project / 'README.md', b'# Existing delivery board\n\nKeep this project-specific guide.\n')
        write(project / 'index.html', b'<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
              b'<title>Existing board</title><h1>Entregas</h1><ul id="results"></ul>'
              b'<script type="module" src="./app.mjs"></script></html>')
        write(project / 'app.mjs', b"import {validateFeatures} from './model.mjs';\n"
              b"const data = validateFeatures(await (await fetch('./data.json')).json());\n"
              b"for (const item of data) { const li = document.createElement('li'); "
              b"li.textContent = item.title; document.querySelector('#results').append(li); }\n")
        run([node, '--test', 'tests/model.test.mjs'], env=env, cwd=project)
        run([git, '-C', str(project), 'add', '--', 'data.json', 'model.mjs',
             'tests/model.test.mjs', 'README.md', 'index.html', 'app.mjs'], env=env, cwd=project)

    def exercise(project, case, env):
        mode = 'new' if case == 'absent' else 'existing'
        retained = {}
        if mode == 'existing':
            for name, expected in (('CLAUDE.md', b'Original instructions\n'),
                                   ('.codex/config.toml', b'# Original config\n'),
                                   ('README.md', b'# Existing delivery board\n\nKeep this project-specific guide.\n')):
                actual = (project / name).read_bytes()
                if actual != expected:
                    raise ValueError('existing_content_not_preserved')
                retained[name] = actual
        run([sys.executable, '-B', 'scripts/personalize.py', 'init', '--mode', mode,
             '--run', 'public-pilot'], env=env, cwd=project)
        run([sys.executable, '-B', 'scripts/personalize.py', 'feature', '--slug',
             'delivery-board', '--run', 'first-delivery'], env=env, cwd=project)
        project_id = json.loads((project / 'vault/project.json').read_text())['project_id']
        public_id = json.loads((EXAMPLE / 'vault/project.json').read_text())['project_id']
        if project_id == public_id:
            raise ValueError('copied_example_identity')
        for name in (*PUBLIC_FILES, 'tests/model.test.mjs'):
            write(project / name, (EXAMPLE / name).read_bytes())
        tests = run([node, '--test', '--test-reporter=tap', 'tests/model.test.mjs'], env=env, cwd=project)
        if b'# pass 4' not in tests:
            raise ValueError('model_tests_not_confirmed')
        audit = subprocess.run([sys.executable, '-B', 'scripts/capabilities.py', 'audit',
                                '--client', client, '--json'], env=env, cwd=project,
                               capture_output=True, timeout=60)
        if audit.returncode not in (0, 1):
            raise ValueError('capability_audit_invalid')
        json.loads(audit.stdout)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')

        def record(path, kind, title, parent, body):
            write(project / path, note(project_id, path, kind, title, parent, body, now).encode('utf8'))

        record('vault/product/profile.md', 'product', 'Perfil do consumidor do piloto', 'index.md',
               f'# Consumidor {mode}\n\n[Produto](index.md) · [Feature](../features/delivery-board/index.md)\n\n'
               'Fixture sintética: público inicial devs individuais/pequenos times. Quadro estático com dados fictícios.\n'
               'HTML/CSS/JavaScript, Node 24, paleta do YoungCrow. PM define aceite; Tech Lead divide a entrega;\n'
               'script de ensaio copia a versão revisada e verifica testes. Isso não é uma conversa nativa de IA.\n'
               'Aceite: lista, filtro, vazio e limpeza; prova de interface está no exemplo canônico.\n'
               'Teste executado: node --test tests/model.test.mjs, 4 aprovados.\n'
               'Desenvolvimento: modelo verificado e página copiada. Produção: não publicada.\n')
        record('vault/product/interviews/public-pilot.md', 'interview', 'Contexto do ensaio', '../index.md',
               f'# Contexto do ensaio\n\n[Produto](../index.md) · [Perfil](../profile.md)\n\nModo: {mode}. '
               'Respostas vêm do desenho aprovado do exemplo em 2026-10-03.\n'
               'Fixture controlada, sem usuário simulado ou respostas inventadas para produto real.\n'
               'Estado: suficiente para esta prova. Próxima ação: validar retorno; ensaio sem publicação.\n')
        record('vault/product/adoption.md', 'adoption', 'Adoção do consumidor', 'index.md',
               '# Adoção do consumidor\n\n[Produto](index.md) · [Perfil](profile.md)\n\n'
               'Trial instalado antes da primeira nota. Somente arquivos do projeto, nenhum plugin global.\n'
               f'CLI de auditoria de capacidades retornou {audit.returncode}; configurações preservadas, nenhum MCP iniciado.\n'
               'Mudança: página do exemplo, testes e referências de personalização. Produção: não publicada.\n'
               'Próxima ação: prévia e retorno controlado da fixture, com verificação de árvore e Git.\n')
        if mode == 'existing':
            record('vault/product/audit.md', 'audit', 'Auditoria da aplicação inicial', 'index.md',
                   '# Auditoria da aplicação inicial\n\n[Produto](index.md) · [Perfil](profile.md)\n\n'
                   'Observado: HTML/JS estático só com listagem; dados/modelo/testes em Git; README próprio;\n'
                   'CLAUDE.md e .codex/config.toml próprios; mudanças preparadas/não preparadas em app.txt.\n'
                   'Preservado: histórico, configuração Codex e prefixos das instruções/README.\n'
                   'Adaptado: acrescentados filtros à página e referência ao perfil. Sem instalação global.\n'
                   'Verificação: 4 testes Node passaram. Interface canônica tem prova independente.\n'
                   'Desconhecido: execução nativa de modelos e produção; não alegadas pelo script.\n')
        record('vault/features/delivery-board/index.md', 'feature', 'Quadro no consumidor', '../index.md',
               '# Quadro no consumidor\n\n[Features](../index.md) · [Perfil](../../product/profile.md)\n'
               '· [Entregas](delivery.md) · [Execução](runs/first-delivery.md)\n\n'
               f'Entrega: {"primeira aplicação" if mode == "new" else "filtro sobre aplicação existente"}.\n'
               'Desenvolvimento: página copiada e 4 testes do modelo aprovados. Produção: não publicada.\n'
               'Próxima ação: retorno controlado; preservar trabalho do trial.\n')
        record('vault/features/delivery-board/delivery.md', 'delivery', 'Entrega do consumidor', 'index.md',
               '# Entrega\n\n[Feature](index.md) · [Execução](runs/first-delivery.md)\n\n'
               'Aceite: modelo seleciona por estado/busca e recusa dados inválidos. Quatro testes passam.\n'
               'Página vem da versão canônica revisada; o script não reexecuta a prova visual.\n'
               'Próxima ação: confirmar restauração exata e cópia recuperável do trabalho.\n')
        record('vault/features/delivery-board/runs/first-delivery.md', 'run', 'Primeira entrega', '../index.md',
               '# Primeira entrega\n\n[Feature](../index.md) · [Entregas](../delivery.md)\n\n'
               f'Executor: smoke_public_pilot.py; cliente instalado: {client}; modo: {mode}.\n'
               'Setup e personalizer reais; modelo: node --test tests/model.test.mjs, 4 aprovados.\n'
               'Capacidades: scripts de personalizer/capabilities e validador do vault. Model calls: 0.\n'
               'Skills disponíveis não foram executadas por um modelo neste ensaio. MCP, Graphify e claude-mem: zero.\n'
               'Desenvolvimento: modelo testado; produção: não publicada; próxima ação: retorno controlado.\n')
        for name in ('CLAUDE.md', 'AGENTS.md'):
            path = project / name
            if path.is_file():
                write(path, path.read_bytes() + b'\nProduct context: vault/product/profile.md.\n')
        guide = retained.get('README.md', b'# Delivery board consumer\n')
        write(project / 'README.md', guide + b'\nTrial delivery: list and filter fictional features.\n'
              b'Test: node --test tests/model.test.mjs (4 passed).\n'
              b'Context: vault/product/profile.md. Production: not published.\n')
        for name, previous in retained.items():
            if not (project / name).read_bytes().startswith(previous):
                raise ValueError('existing_instructions_lost')
        run([sys.executable, '-B', 'scripts/vault.py', 'check', '--json'], env=env, cwd=project)
        deliveries.append(dict(mode=mode, project_id=project_id, tests_passed=4,
                               native_model_calls=0, capabilities_audit_exit=audit.returncode,
                               original_instructions_preserved=mode == 'existing'))

    result = smoke(root, client, prepare_existing=prepare_existing, exercise=exercise,
                   cases=('absent', 'dirty-git'))
    if len(deliveries) != 2 or len({item['project_id'] for item in deliveries}) != 2:
        raise ValueError('consumer_identity_collision')
    result['deliveries'] = deliveries
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--client', choices=('claude', 'codex', 'both'), default='both')
    args = parser.parse_args()
    try:
        print(json.dumps(pilot(args.root, args.client), ensure_ascii=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, KeyError):
        print(json.dumps(dict(state='failed', code='public_pilot_smoke_failed')), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
