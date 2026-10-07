# Setup local e runner dedicado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Execução inline já escolhida pelo mantenedor; não pedir novamente o método. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configurar o destino local/dedicado e explicar os pré-requisitos com diagnósticos atribuíveis, preservando adoção reversível e bloqueios do executor.

**Architecture:** O mesmo harness executa no host do projeto, aberto localmente ou por VS Code Remote SSH. Uma preferência privada identifica o destino declarado; o preflight existente observa o host sem ativar recursos. O setup e o Personalizer usam esses contratos, mantendo missões, credenciais e provas de execução separados.

**Tech Stack:** Python 3.11+ e biblioteca padrão, Bash/Git Bash, `unittest`, helpers existentes de ACL/lock e supervisor. Sem novas dependências.

**Spec:** [Desenho aprovado](../specs/2026-10-05-execution-setup-design.md). Aprovação do mantenedor: “aprovado”, em 2026-10-05, incluindo Remote SSH.

**Estado:** três PBIs concluídos nesta branch. Oito combinações de adoção passaram; resultados finais cobrem 414 testes, com 403 aprovações e 11 skips de ambiente. Achado da revisão e falhas de fixtures/catálogo corrigidos; ver [relatório](../../relatorios/2026-10-05-execution-setup.md). Commits/publicação adiados conforme a regra de preservação abaixo. Três PBIs de preparação de YC-203, sem substituir R1/R2/R3 ou acrescentar itens à contagem principal.

## Global Constraints

- “A execução local será o padrão; um runner dedicado será opcional.” Os comandos rodam no host aberto, sem transporte próprio.
- “O registro contém somente `schema_version: 1`, `location: local|dedicated` e `selected_at` em UTC.” Caminho: `.operacao-local/execution/selection.json`.
- “A ausência do arquivo produz o padrão `local` sem escrita”; origem `default` ou `configured`.
- “Manter o limite atual de 30 segundos por consulta e 8 MiB de saída.” Sem retry ou ampliação de prazo.
- Estados de etapa: `observed|missing|unsupported|failed|timeout|not_checked`; horários UTC e duração monotônica.
- “Os controles `ssh=False` e `remote_control=False` do executor continuam exigidos.” SSH do operador não entra na sandbox.
- “Trocar a preferência não altera missão, geração responsável, limites ou recibos existentes.” `youngcrow/agents.json` conserva o esquema.
- “Quem escolheu adoção reversível obtém baseline antes de qualquer registro do destino.” `--force` preserva seleção e helpers modificados.
- Perfis continuam vazios; nenhum login, modelo, Docker, provisionamento ou ensaio nativo será iniciado por esta entrega. Fixtures executam somente processos de teste.
- Um escritor no checkout atual; preservar alterações preexistentes. Commits somente por conteúdo/caminhos desta entrega após revisar o diff; não incluir a frente inteira por acidente. Nenhum push implícito.
- Atualizar README e USAGE PT/EN com humanizer, mantendo imagens e diagramas existentes. Skills instaladas recebem guia portátil.

## Review Focus

1. Reinstalação sem flag em projeto configurado como `dedicated`: preservar escolha e timestamp, inclusive com `--force` (PBI 1).
2. Dois configuradores partem do mesmo digest: um vence; o outro informa conflito sem perder dados. Queda libera lock do SO, sem takeover de missão (PBI 1).
3. Seleção malformada, versionada no Git ou alcançada por symlink/junction/hardlink: recusar sem reparar ou escrever fora da raiz (PBI 1).
4. Uma consulta de virtualização expira e a de versão funciona: registrar a etapa em timeout, manter o outro resultado e o gate bloqueado; nada de stdout privado (PBI 2).
5. Projeto consumidor migrou com helper/skill anterior preservado: informar incompatibilidade quando necessário, nunca substituir conteúdo humano nem anunciar fluxo remoto testado (PBIs 1 e 3).

## Mapa de arquivos

| Arquivo | Responsabilidade nesta entrega |
|---|---|
| `scripts/mission_environment.py` (novo) | Leitura/validação/gravação da preferência; CLI interna usada pelo setup |
| `scripts/missions.py` | `environment show/configure`, compatibilidade e erros públicos |
| `setup.sh`, `.gitignore`, `scripts/adoption.py` | Flag, proteção privada, preservação e propagação para o trial filho |
| `skills-lock.json`, `tests/test_capabilities.py` | Dependências e hashes das cinco skills afetadas; permissões existentes preservadas |
| `scripts/mission_process.py`, `scripts/mission_clients.py` | Medidas do supervisor e observação sanitizada de cada consulta |
| `scripts/mission_sandbox.py` | Associar observações às etapas do preflight existente |
| `skills/personalizer/SKILL.md`, `skills/personalizer/references/interview.md`, `skills/yc-personalizer/SKILL.md` | Reutilizar respostas, registrar escolha e encaminhar diagnóstico |
| `skills/personalizer/references/execution.md` (novo) | Guia PT/EN instalado: novo/migração, local/Remote SSH, limites e recuperação |
| `tests/test_mission_environment.py` (novo) | Preferência, privacidade, concorrência e consulta sem efeitos |
| `tests/test_setup.py`, `tests/test_adoption.py` | Propagação, preservação, conflito antes da instalação e baseline |
| `tests/test_mission_sandbox.py`, `tests/test_mission_clients.py`, `tests/test_mission_process.py` | Etapas, limite, sanitização e compatibilidade |
| `tests/smoke_adoption.py`, `tests/smoke_execution_setup.py` (novo) | Matriz instalada com restauração; reuso do smoke existente |
| `README.md`, `docs/USAGE.md`, `docs/BACKLOG.md` | Comandos que foram implementados e estado comprovado |

## Preparação da execução

- [x] Ler spec e plano; registrar `git status --short` e hashes dos arquivos afetados. Reutilizar este checkout, sem reset ou nova branch. Guardar logs privados em `.superpowers/sdd/2026-10-05-execution-setup/`.
- [x] Verificar os helpers instalados e comandos de teste descritos abaixo. No Windows, usar `tests/windows_fixture_runner.py` com uma raiz temporária curta, privada e fora de Git, como nas provas anteriores. Preservar o `RUNNER_TEMP` existente; se não servir, a escolha de outro diretório precisa respeitar a fronteira de escrita vigente. Não relaxar ACLs para fazer teste passar.
- [x] Preservar o marcador `exclusive-egress-v2-closed.json`, recibos e configuração Docker. Não executar scripts de prova dessa frente como parte do baseline.

## Task 1: PBI 1 — Seleção persistente e setup

**Interfaces** — em `mission_environment.py`:

- `read_selection(root: Path) -> dict`: retorna `schema_version`, `location`, `origin`, `selected_at`, `digest`. Ausente: `local`, `default`, `None`, `None`; existente: `configured`, data validada e SHA-256 dos bytes exatos.
- `configure_selection(root: Path, location: str, expected_digest: str | None) -> dict`: retorna o mesmo relatório. Mesmo valor com digest atual conserva bytes/data; digest divergente é `execution_selection_conflict`.
- `setup_selection(root: Path, requested: str | None, *, apply: bool) -> dict`: `apply=False` só verifica; seleção existente é preservada quando não há pedido ou quando ele coincide. Pedido divergente é `execution_location_conflict`. `apply=True` grava o padrão apenas se ausente.
- `main(argv=None) -> int`: comandos internos `setup-check` e `setup-apply`, com `--root`, `--location` opcional e JSON. O setup usa o helper da distribuição, sem executar um helper consumidor modificado.

`read_selection` aceita destino ainda ausente para o preflight do setup. Leitura existente valida objeto exato, inteiros sem booleano, destino enumerado e data ISO 8601 com offset UTC. Limite de 64 KiB; parser JSON existente recusa duplicatas. Erros são códigos, sem conteúdo bruto.

- [x] **RED: testar o contrato em `tests/test_mission_environment.py`.** Asserções mínimas:

Usar `ExecutionEnvironmentTests(StorageFixture)`, com `self.root = self.project`, regra
de ignore da área preparada pela fixture e `snapshot()` baseado em `snapshot_bytes`
de `test_setup`. A fixture prepara permissões; as leituras e recusas sob teste não fazem isso.

```python
def test_missing_is_local_without_writes(self):
    before = self.snapshot()
    report = read_selection(self.root)
    self.assertEqual((report['location'], report['origin'], report['digest']),
                     ('local', 'default', None))
    self.assertEqual(self.snapshot(), before)

def test_configured_same_value_preserves_bytes(self):
    first = configure_selection(self.root, 'dedicated', None)
    before = self.snapshot()
    self.assertEqual(configure_selection(self.root, 'dedicated', first['digest']), first)
    self.assertEqual(self.snapshot(), before)
```

Acrescentar `test_stale_digest_refuses_before_write`, `test_two_writers_one_digest`, `test_process_death_releases_selection_lock`, `test_unsafe_or_tracked_selection_refused` e `test_selection_does_not_change_mission_state`. Usar processos reais para concorrência/lock; fixtures existentes para estado de missão e permissões. Comparar bytes antes/depois e exigir um vencedor, sem relaxar as condições para concorrência.

- [x] **Rodar RED.** `python -X utf8 -B tests/windows_fixture_runner.py -m unittest discover -s tests -p test_mission_environment.py -v`; falha esperada por helper/contrato ainda ausente, não por ACL ou import de fixture inválido. No Linux, omitir o runner Windows.
- [x] **Implementar preferência mínima.** Reutilizar `adoption_fs.checked_path/private_dir/inspect_permissions/git_read`, `document_store.safe_path/atomic_write` e `adoption.lock_guard` no diretório privado `execution` (seu `reclaim.lock` permanece ignorado). Não usar `prepare_storage`, SQLite ou índices do vault para guardar a preferência. Criar apenas pais necessários; validar diretório já existente sem mudar sua ACL. Conferir permissões do temporário antes de gravar via callback `before_write`.
- [x] **Fixar exclusão Git.** O setup acrescenta `/.operacao-local/execution/` às regras gerenciadas. `configure_selection` exige regra efetiva e nenhum arquivo da área tracked; sem Git, exige a regra ancorada. Recusar override que reexponha o arquivo. Validar entrada/digest antes de criar diretório/lock e conferir novamente sob lock. Não apagar seleção ou lock de outro processo na recusa.
- [x] **Adicionar CLI pública.** Em `missions.py`, carregar o novo helper somente nos comandos que o usam. `environment show --json` e `environment configure --location ... --expected-digest ... --json`; mapear `none` para `None`. Sucesso 0, erro validado 2. Sem helper compatível, `incompatible_helper`. Outros comandos continuam utilizáveis sem importar o helper novo. Novos códigos permitidos: `invalid_execution_selection`, `execution_selection_conflict`, `execution_location_conflict`, `execution_selection_busy`, `execution_storage_unprotected`.
- [x] **RED da adoção.** Em `test_setup.py`: default novo, `dedicated` explícito, repetição sem flag, repetição com `--force`, conflito antes de copiar arquivos, helper humano preservado, opção inválida e diretório com espaços. Em `test_adoption.py`: passar a opção ao filho e conservar baseline após falha/repetição. Todas as recusas comparam a árvore e o perfil global antes/depois.
- [x] **Integrar setup/trial.** Parsear flag em `setup.sh`, executar `setup-check` antes da primeira escrita e novamente no filho; incluir o helper em `FILES` e na lista de preservação com `--force`. Propagar opção em `scripts/adoption.py` e `run_install`; não adicioná-la aos `RUNNER_FILES` de restauração, que não dependem da seleção. Após baseline e merge de ignore, usar `setup-apply`. Omitir a flag preserva escolha existente; default `local` só vale para registro ausente. Saída distingue arquivos instalados de execução ainda bloqueada.
- [x] **GREEN e documentação do PBI.** Rodar os novos testes, `test_setup.py`, `test_adoption.py` e regressões de CLI/configuração afetadas. Registrar saídas reais; atualizar README/USAGE PT/EN com os comandos disponíveis e sem prometer runner validado.
- [x] **Checkpoint de commit.** Inspecionar diff por conteúdo e caminhos antes de registrar este PBI. Como há alterações anteriores nesses arquivos, preparar hunks somente desta entrega; se a separação não for segura, registrar o impedimento e manter os bytes. Mensagem proposta: `feat: configure local and dedicated execution locations`.

## Task 2: PBI 2 — Diagnóstico por etapa

**Interfaces**:

- `mission_process.supervise(plan, *, on_started, stop_requested) -> dict`: manter campos existentes e acrescentar `started_at`/`ended_at` UTC, inclusive quando executável estiver ausente; duração continua em `elapsed_seconds`.
- `mission_clients._exchange(..., observation: dict | None = None)`: keyword opcional, mantendo os argumentos e o retorno atuais. Preencher observação sanitizada a partir do resultado do supervisor antes das validações que levantam erros. Sem stdout, argv, ambiente ou proprietário na observação.
- `mission_sandbox.inspect_environment(root: Path, executable: Path) -> dict`: preservar campos/gaps atuais; acrescentar `selection` (relatório do PBI 1) e `phases`.
- `mission_sandbox.inspect_sandbox(root: Path, executable: Path, name: str) -> dict`: conservar controles e acrescentar fases das consultas `ls/inspect/ls`. A CLI concatena as fases sem repetir consulta.

Uma fase contém exatamente `id`, `started_at`, `ended_at`, `elapsed_seconds`, `timeout_seconds`, `output_limit_bytes`, `state`, `reason`. IDs fixos: `host_metadata`, `virtualization`, `runtime_identity`, `runtime_version`, `sandbox_inventory_before`, `sandbox_inspect`, `sandbox_inventory_after`. Sem `--sandbox`, as três últimas ficam `not_checked`, com motivo `not_requested`.

Etapas sem subprocesso usam limites `null`; consultas externas usam 30 e 8388608. Etapa não iniciada usa horários/duração `null`. Resultado `timeout` exige razão do supervisor; falha de recolhimento mantém `unsupported_containment` e bloqueio. Erro desconhecido usa razão fixa `observation_failed`, nunca `str(error)`.

Publicar `SUPERVISOR_OBSERVATION_VERSION = 1` em `mission_process` e
`DISCOVERY_OBSERVATION_VERSION = 1` em `mission_clients`. A CLI também confere
`ENVIRONMENT_OBSERVATION_VERSION = 1` de `mission_sandbox`, para recusar o helper legado
ainda chamável antes de consultá-lo. O caminho novo confere os contratos
antes da primeira consulta; versões ausentes/divergentes retornam `incompatible_helper`.
Esses identificadores demonstram compatibilidade do contrato, nunca prova de isolamento.
Testar combinações de helpers antigos/novos preservados, exigindo zero subprocessos na recusa.

- [x] **RED: ampliar testes de supervisor e cliente.** Em `test_mission_process.py`, exigir horários UTC e duração não negativa em sucesso, spawn ausente e timeout. Reutilizar a fixture `hang` com limite curto de teste, mantendo os 30 segundos do produto. Em `test_mission_clients.py`, verificar que `_exchange` preenche a observação antes de propagar `client_discovery_timeout`; incluir canário em stderr e exigir ausência dele na observação.
- [x] **Rodar RED focado.** `python -X utf8 -B tests/windows_fixture_runner.py -m unittest discover -s tests -p test_mission_process.py -v` e o equivalente para `test_mission_clients.py`; asserções novas falham, os testes antigos não são removidos.
- [x] **Implementar medidas na origem.** Em `supervise`, inicializar horários antes dos retornos antecipados e finalizar após recolher processos; duração monotônica inclui a limpeza já existente e não redefine o prazo. Em `_exchange`, copiar somente campos permitidos do resultado para `observation`, com `completed`, `timeout`, `output_limit`, `spawn_failed`, `cancelled` ou motivo conhecido. Preservar retornos/erros antigos para todos os chamadores sem observação.
- [x] **RED do preflight.** Em `test_mission_sandbox.py`, testar explicitamente:

```python
# Resultado após simular timeout só na consulta de virtualização:
self.assertEqual(by_id['virtualization']['state'], 'timeout')
self.assertEqual(by_id['virtualization']['timeout_seconds'], 30)
self.assertEqual(by_id['runtime_version']['state'], 'observed')
self.assertIn('runtime_profile_unverified', result['gaps'])
self.assertEqual(result['profile_ids'], [])
self.assertNotIn('secret-canary', json.dumps(result['phases']))
self.assertEqual(self.snapshot(), before)
```

Cobrir também Linux/KVM ausente, plataforma não suportada, versão inválida, binário substituído, seleção inválida, inventário não solicitado e falha na primeira consulta que marca as dependentes `not_checked`. `ls/inspect/ls` deve continuar nessa ordem, uma vez por consulta; sem `create/start/run/exec/restart`.

- [x] **Integrar fases e seleção.** Separar a coleta pura do host da consulta de virtualização já existente; capturar motivos antes de descartá-los. Não duplicar `_exchange` nem introduzir supervisor alternativo. Mapear valores observados às fases e manter todos os gates. Preferência inválida encerra o comando antes de consultar o runtime. O agregado descreve preparação, nunca `runtime_available=true` com perfis vazios.
- [x] **GREEN e compatibilidade.** Rodar testes de preflight, supervisor, clientes e `test_mission_runs.py`; exigir recusas originais, recibos de execução compatíveis e sem alteração dos limites. Acrescentar a README/USAGE um exemplo sanitizado de timeout por etapa, identificado como saída de fixture quando for o caso.
- [x] **Checkpoint de commit.** Revisar apenas a mudança de observabilidade, conforme a regra de hunks do PBI 1. Mensagem proposta: `feat: report bounded environment checks by phase`.

## Task 3: PBI 3 — Personalizer e adoção instalada

**Interfaces**:

- `tests.smoke_adoption.smoke(root, client, *, prepare_existing=None, exercise=None, cases=..., setup_options=()) -> dict`: acrescentar apenas o parâmetro opcional; valores padrão e chamadores atuais não mudam. Repassar a lista como argumentos, sem montar shell com texto do usuário.
- `tests/smoke_execution_setup.py --root RAIZ_DESCARTAVEL`: exigir raiz ausente/privada fora de Git, como o smoke atual; executar novo/migração × Claude/Codex × local/dedicated. Retornar matriz, hashes preservados, restauração e `native_execution: not_run`, `model_calls: 0`.

- [x] **RED de distribuição.** Em `test_setup.py`, exigir guia `skills/personalizer/references/execution.md` e helper disponíveis nos dois clientes; testar que o helper consumidor preservado provoca `incompatible_helper` e orientação, sem sobrescrita. Em vez de simular sessões LLM, o smoke usa as interfaces instaladas e declara essa limitação.
- [x] **Escrever o guia e ajustar as skills.** O guia PT/EN cobre: baseline quando trial; setup normal e migração; seleção; leitura do diagnóstico; Remote SSH preparado pelo operador; clientes autenticados no host; diferença entre planejar e executar; consulta a recibos após desconexão; limites de transferência/supervisor pendentes. Personalizer lê preferência antes de perguntar, registra fonte/data no perfil e usa `environment configure` somente quando há uma escolha autorizada. Não repete cliente/modelo/effort já conhecidos nem coleta credenciais.
- [x] **Distribuir e preservar.** Incluir guia em `setup.sh` e fixture `FILES`; manter preservação de skills modificadas. As entradas `.claude/skills` e `.agents/skills` já apontam para a skill compartilhada: não copiar lógica para cada cliente. Conferir todos os links relativos no projeto instalado.
- [x] **Implementar e rodar matriz.** Reutilizar `smoke_adoption` para oito combinações, em diretórios distintos. Exigir `selection.origin=configured`, destino correto, `show` sem mudanças, mesma escolha após reinstalação e retorno à árvore/baseline anterior após trial. Comparar configuração de agentes, vault humano e recibos antes/depois. Em `dedicated`, registrar que só a seleção foi testada: não há servidor ou SSH real nessa corrida.
- [x] **Verificação final.** Rodar suíte geral uma vez após os testes focados; Windows: `python -X utf8 -B tests/windows_fixture_runner.py -m unittest discover -s tests -v`. Rodar `smoke_execution_setup.py --root CAMINHO_DESCARTAVEL` sob o mesmo runner e `python -B scripts/vault.py check --json`. Os skips devem indicar requisitos reais, sem substituir aceite por teste ignorado. Não repetir suíte verde sem mudança ou preocupação nova.
- [x] **Registrar entrega.** Criar `docs/relatorios/2026-10-05-execution-setup.md` e `docs/medicoes/execution-setup.json` com revisão/hashes, comandos, contagem real, matriz e limitações. Atualizar README/USAGE/BACKLOG e microíndice; distinguir entrega de setup de R1 ainda parcial. Preservar assets e BPMNs; se precisar explicar o novo fluxo, usar o diagrama aprovado como proposta até corresponder ao comportamento implementado.
- [x] **Checkpoint e revisão final.** Mensagem proposta: `docs: guide local and dedicated runner onboarding`. Usar o método inline preservado e a revisão final prevista no fluxo escolhido, sem reabrir revisões/provas antigas ou criar revisores por PBI. Verificar diff completo, gates e comandos instalados antes de propor publicação.

## Aceite e continuidade

- [x] Setup e preferência funcionam com preservação e retorno comprovados; oito combinações de adoção passam sem consulta a modelos ou servidor remoto.
- [x] Cada falha de consulta identifica fase/limite, mantém dados privados fora da saída e não repete efeitos; consulta não grava estado do projeto.
- [x] Documentação acompanha o que foi implementado, com Remote SSH aprovado como acesso do operador e autonomia ainda condicionada às provas.
- [x] `REVIEWED_PROFILES = ()`, `NATIVE_PROFILES = set()` e encerramento da prova v2 permanecem preservados. Nenhum teste declara que outra máquina resolveu o timeout anterior.

Depois desta entrega, retomar a pendência de isolamento/rede de R1 com observabilidade
melhorada e proposta de prova delimitada. Não certificar um perfil nem iniciar R2/R3
por causa do aceite do setup. Máquina remota, autenticação real, supervisor e transferência
continuam exigindo suas próprias condições e evidências.
