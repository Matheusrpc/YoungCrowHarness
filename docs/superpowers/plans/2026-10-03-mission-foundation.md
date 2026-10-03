# Mission foundation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir configurar agentes, refinar um backlog e preparar missões recuperáveis no vault de um projeto novo ou existente, sem despachar agentes de produto.

**Architecture:** Reaproveitar a personalizer, os metadados do vault e a governança existentes. Markdown guarda o conhecimento e os contratos dos itens; JSON guarda os padrões dos agentes; SQLite registra revisões importadas, missões e eventos. Uma CLI Python atende quatro entradas de skill nos dois clientes, com estado consultável e projeções recuperáveis.

**Tech Stack:** Python 3.11+, biblioteca padrão (`sqlite3`, `json`, `hashlib`, `unittest`), Bash do setup existente, Markdown e SVG. Nenhuma dependência nova de runtime.

**Spec:** [Esteira de produto com agentes de IA](../specs/2026-10-03-ai-product-pipeline-design.md), aprovada pelo mantenedor em 2026-10-03. Este plano implementa somente a frente 1, “Perfil e contrato da missão”.

Frente: preparação de missões. Estado: plano escrito aguardando revisão e escolha do método de execução. Nenhuma caixa marcada representa execução já realizada.

## Global Constraints

- “Três PBIs por padrão, configurável.” Salvar `max_active_pbis: 3` como padrão; isso não limita a quantidade total de PBIs de uma missão.
- “Três simultâneas por padrão, configurável e separado do limite de PBIs.” Salvar `max_parallel_agents: 3`.
- “Até três ciclos de correção e revalidação por PBI.” Salvar `max_correction_cycles: 3`; não aceitar outro valor nesta versão.
- “Manual por padrão; automático quando configurado explicitamente.” Salvar `deploy_mode: manual`; configurar `automatic` não publica nada nesta frente.
- “Uma ativa por repositório; outras podem ser preparadas; uma a N features.” Nesta frente só existem missões preparadas; nenhuma adquire a vaga de execução.
- “Somente após produção verificada.” Nunca permitir criar ou importar estado `completed` por estes comandos de preparação.
- “Padrões por agente no projeto, com substituições explícitas por missão.” Preservar o snapshot de uma missão quando o padrão mudar.
- Cliente autenticado é o padrão; API depende de escolha explícita. Sem JEV, fallback de provedor/modelo, leitura de credenciais, acesso à rede ou chamada de modelo pelo backend desta frente.
- Windows e Linux, Python 3.11+; biblioteca padrão e helpers existentes. Sem migração automática das features antigas e sem alteração de perfis globais.
- Um escritor por checkout; commits com caminhos explícitos e autoria humana. README e guia PT/EN acompanham cada entrega implementada, com `humanizer` e design preservado.
- Fontes, estado operacional, missões e novas notas sensíveis ficam privados. Registrar uso de capacidade separadamente de configuração e autorização.

## Review Focus

1. Instalação antiga com notas humanas e helpers preservados: nenhum overwrite, troca de UUID ou sucesso enganoso com helper incompatível. Testes nas tarefas 2 e 4.
2. Leituras e falhas de validação: `status` e entrada inválida não criam banco, diretórios, índices nem alteram `.gitignore`. Testes nas tarefas 1 e 3.
3. Escrita confirmada no banco seguida de falha na projeção: repetir a mesma operação recupera as notas sem duplicar missão, evento ou código legível. Testes na tarefa 3.
4. Fontes modificadas, dependências circulares ou referências de outro projeto: preparação indica o bloqueio e conserva a revisão anterior. Testes nas tarefas 2 e 3.
5. Segredos acidentais, tipos JSON ambíguos e caminhos ligados/externos: rejeitar sem ecoar valores nem escrever fora do projeto. Testes nas tarefas 1–3 e no setup da tarefa 4.

---

## Limites da entrega e reaproveitamento

O usuário poderá usar `yc-personalizer`, `yc-config`, `yc-missao` e `yc-status` para configurar,
documentar, preparar e consultar. `yc-iniciar`, `yc-pausar`, `yc-retomar`, `yc-transferir` e
`yc-deploy` pertencem às frentes seguintes e não serão instalados como comandos funcionais agora.
Também ficam fora deste plano: processos de agentes PM/TL/Dev/QA, worktrees de PBIs, testes de
produto por Playwright, merge, publicação e webhook. As configurações desses percursos podem
ser registradas como intenção, sem afirmar suporte operacional.

Os caminhos existentes `vault/product/profile.md`, `vault/product/onboarding.json` e
`vault/features/<slug>/` continuam válidos. O importador referencia notas existentes pelo UUID;
não move arquivos para adequá-los a uma árvore nova. Novas notas estruturadas começam privadas
em `vault/local/product/{epics,features,pbis}/<uuid>/index.md`. A publicação de cópias de backlog
não é automatizada nesta entrega. Essa escolha concretiza a política de visibilidade do desenho.

Reutilizar `integrations.check_path`, `project_identity`, `note` quando sua identidade baseada
em caminho for apropriada; `document_store.safe_path`, `atomic_write`, `prepare_storage`,
`verify_private_storage`; `vault.metadata`, `links`, `local_path`; e `capabilities.parse_json`,
`canonical`, `load_catalog`, `audit`. O lock de Docling não é lock de missão: SQLite coordena as
transações locais. Não refatorar esses módulos apenas para mudar seus nomes.

## Arquivos e contratos comuns

| Arquivo | Responsabilidade |
|---|---|
| `scripts/mission_config.py` | Ler/validar configuração, aplicar substituições permitidas e calcular digest |
| `scripts/mission_backlog.py` | Ler contratos Markdown, validar relações/DoR/DoD e capturar revisões das fontes |
| `scripts/mission_store.py` | SQLite, identidade do projeto, revisões, operações idempotentes e eventos |
| `scripts/mission_vault.py` | Modelos de notas, índices privados e projeções recuperáveis sem apagar texto humano |
| `scripts/missions.py` | CLI e operações de configuração, importação, preparação, revisão e consulta |
| `tests/test_mission_config.py`, `test_mission_backlog.py`, `test_missions.py` | Verificações dos contratos acima usando `unittest` |
| `tests/mission_fixtures.py` | Fixtures pequenas para esses testes e o smoke; sem runtime de IA |
| `tests/smoke_mission_foundation.py` | Percurso completo em consumidores descartáveis |
| `skills/yc-personalizer/`, `yc-config/`, `yc-missao/`, `yc-status/` | Uma instrução compartilhada por comando |
| `.claude/skills/yc-*/SKILL.md`, `.agents/skills/yc-*/SKILL.md` | Oito adaptadores pequenos para os quatro comandos desta entrega |
| `setup.sh`, `skills-lock.json`, `.gitignore` | Instalação selecionada, catálogo e exclusões |
| `README.md`, `docs/USAGE.md`, `assets/process-mission-planning-{pt,en}.svg` | Uso verificável, limitações e processo visível |

Os nomes abreviados de arquivos na tabela pertencem ao mesmo diretório indicado na primeira
entrada da célula. Cada tarefa abaixo enumera os caminhos que realmente altera.

### Configuração, esquema 1

`youngcrow/agents.json` é configurado pelo adotante; o template não o instala com modelos ou
orçamentos escolhidos. O esquema contém:

| Campo | Tipo e regra |
|---|---|
| `schema_version` | Inteiro 1; rejeitar `true`, versão desconhecida e chaves duplicadas |
| `agents` | Papéis obrigatórios `pm`, `tech_lead`, `developer`, `qa`; `integration_specialist` opcional |
| Cada agente | `client: codex\|claude\|null`, `connection: authenticated\|api`, `model: string\|null`, `effort`, `credential_env: string\|null`, `capabilities: list[str]` |
| `effort` | `{level: low\|medium\|high\|native\|null, native_value: string\|null}`; valor nativo obrigatório só para `native` |
| `limits` | `max_active_pbis`, `max_parallel_agents`, `max_correction_cycles`, `mission_active_seconds`, `agent_seconds`, `max_agent_runs`, `max_deploy_attempts`, `api_budget_usd` |
| Limites | Inteiros positivos, sem bool; os quatro limites de tempo/tentativas podem ser `null` enquanto rascunho; orçamento API é string decimal positiva ou `null` |
| `deploy_mode` | `manual\|automatic`; padrão `manual` |

Omissão de cliente/modelo/effort permanece `null`, com pendência. Não escolher um modelo pelo
usuário. Limites sem valor permanecem pendentes, exceto os três padrões numéricos aprovados.
`connection` omitida vira `authenticated`; nesse modo `credential_env` deve ser `null`. Em API,
aceitar somente nome de variável no formato `[A-Z][A-Z0-9_]*`; nunca resolver seu conteúdo.
Rejeitar campos como `api_key`, `token`, `password`, `endpoint` e campos desconhecidos, sem
reproduzir o valor na mensagem. A validação de esquema não promete detectar segredos escondidos
em todo texto livre: a skill também revisa o arquivo antes de qualquer publicação.

`low`, `medium` e `high` são pedidos comuns, com tradução nominal mostrada para os dois clientes.
`native` guarda a intenção exata, ainda não comprovada. Nos relatórios de validação e status,
toda combinação cliente/modelo/effort traz `compatibility: not_verified`; esse campo derivado
não é gravado no arquivo de configuração nem aceito como prova fornecida pelo usuário.
Não consultar catálogos remotos nem
marcar um modelo como suportado apenas porque passou no esquema. A frente 2 fará a validação
de compatibilidade e enforcement antes de permitir iniciar uma missão.

### Notas do backlog e leitura de contratos

Notas novas usam frontmatter do vault com UUID estável, origem `youngcrow/missions`, tipo
`epic|feature|pbi`, índice relativo e horário UTC. Título e IDs não são derivados de entrada
usada como caminho. O UUID determina o diretório; o título é texto escapado no Markdown.

Um bloco cercado por `<!-- youngcrow:contract:start -->` e `<!-- youngcrow:contract:end -->`
contém exatamente um fenced block `json`. O resto da nota permanece prosa livre, preservada.
Seu objeto tem `schema_version: 1`, `project_id: UUID`, `parent_id: UUID|null`, `owner: pm|tech_lead`, `objective`,
`acceptance: list[str]`, `dor: list[str]`, `dod: list[str]`, `validation: list[str]`,
`dependencies: list[UUID]` e `references: list[{note_id, path}]`. Epics usam pai nulo;
features referenciam epic; PBIs referenciam feature. `validation` descreve comandos/critérios;
o importador nunca executa essas strings. Links Markdown legíveis acompanham as referências.

O `project_id` do contrato deve corresponder a `vault/project.json`. Referências devem resolver
para notas regulares dentro do projeto, com UUID correspondente;
fontes locais ingeridas são referências válidas. URLs permanecem na prosa como pendências para
`ingest-source`, não substituem evidência local revisada. O recibo captura SHA-256 dos bytes
da nota e de cada referência direta. A consulta segue os índices; não varre todo o vault para
montar contexto nem aumenta a seleção de Graphify.

Notas antigas sem bloco são registradas como `draft`, com `missing_contract`, sem serem
reescritas. Um bloco malformado é erro de entrada, distinto de bloco ausente. Adicionar um bloco
a uma nota antiga é edição explícita na sessão; repetir importação nunca injeta conteúdo nela.
Renomear nota mantém UUID e exige importação da nova localização; colisão com outra nota viva
usando o mesmo UUID é recusada. Notas compartilhadas não podem referenciar arquivos privados;
uma fonte privada pode referenciar o conhecimento compartilhado. Datas antigas desconhecidas
permanecem desconhecidas; o horário da importação registra essa operação, não a criação histórica
do documento.

### Banco e resultado operacional

SQLite fica em `vault/local/operations/state.sqlite3`. Usar transações `BEGIN IMMEDIATE`,
foreign keys e espera finita de lock; `journal_mode=DELETE` nesta frente. Metadados guardam
esquema 1 e `project_id`. Tabela `records` guarda UUID, tipo, código, revisão inteira e snapshot
JSON; `events` guarda sequência, UUID, operação, hash do pedido, ator, horário UTC, revisão
anterior/nova, snapshot e projeção pendente. A chave de operação é única por projeto.

Mudanças só nascem das operações permitidas; não oferecer setter genérico de status. UUIDs são
estáveis; códigos `E001`, `F001`, `P001`, `M001` são alocados dentro da transação por tipo,
sem reutilizar números de registros existentes. Rollback não deixa registro parcialmente salvo.
Repetir operação com o mesmo pedido devolve o recibo; mudar o pedido mantendo o ID é conflito.
`expected_revision` implementa compare-and-swap: 0 cria, revisão atual permite substituir,
qualquer outra recusa. Repetição idempotente é verificada antes de comparar essa revisão.

Registro importado preserva critérios e referências daquela revisão. Markdown é o conhecimento
editável; mudar a nota invalida a atualidade do snapshot até nova importação. Projeção operacional
é outra nota, identificada pela sequência do evento; ela não altera o contrato original.
Mudar os padrões globais não marca a configuração congelada como inválida: alterações nela
exigem `revise` com substituições explícitas. Configuração nativa/capacidades externas ao snapshot
continuam sujeitas a nova verificação na frente de execução.
Antes de sobrescrever projeção, comparar seu hash com o último salvo. Divergência conserva a
edição humana e retorna `projection_conflict`. Índices recebem somente links faltantes.

Um recibo tem `schema_version`, `project_id`, `operation_id`, `record_id`, `code`, `revision`,
`event_id`, `sequence`, `created_at`, `projection_state`. Snapshot da missão contém seleção
de features e seus PBIs, revisões de notas/fontes, perfil, configuração efetiva e digest,
substituições, prioridade explícita, pendências e estado `draft|prepared`. `prepared` significa
contrato de planejamento completo; `runtime_available: false` e `runnable: false` continuam
explícitos. Desenvolvimento, QA e produção da missão permanecem não iniciados/não verificados.

## Task 1: Configuração por agente e substituições por missão

**Files:** Create `scripts/mission_config.py`, `tests/test_mission_config.py`.
Modify `README.md`, `docs/USAGE.md` apenas para documentar o contrato offline entregue.

**Interfaces:**
- Consumes `capabilities.parse_json(data: bytes) -> dict`, `canonical(value) -> bytes` e `document_store.safe_path(root, relative) -> Path`.
- Produces `normalize_config(raw: dict) -> dict`, `load_config(root: Path) -> dict`, `effective_config(defaults: dict, overrides: dict) -> dict`, `config_digest(config: dict) -> str`, `config_gaps(config: dict) -> list[str]`.
- Validação inválida levanta `ValueError` com código fixo; configuração é dado, sem leitura de variável nem escrita.

- [ ] **Step 1: Escrever testes de herança, tipos e privacidade.** Em `ConfigTests`, usar fixture `minimal_config()` definida no mesmo teste, com quatro papéis sem modelo escolhido; `configured()` preenche valores sintéticos e limites apenas para teste. Cobrir estas asserções:

```python
def test_defaults_do_not_choose_models(self):
    c = normalize_config(minimal_config())
    self.assertEqual(c['limits']['max_active_pbis'], 3)
    self.assertEqual(c['limits']['max_parallel_agents'], 3)
    self.assertEqual(c['limits']['max_correction_cycles'], 3)
    self.assertEqual(c['deploy_mode'], 'manual')
    self.assertIsNone(c['agents']['pm']['model'])
    self.assertIn('agents.pm.model', config_gaps(c))

def test_overrides_preserve_project_and_other_roles(self):
    defaults = configured()
    before = copy.deepcopy(defaults)
    effective = effective_config(defaults, {'agents': {'pm': {'model': 'fixture-b'}}})
    self.assertEqual(defaults, before)
    self.assertEqual(effective['agents']['pm']['model'], 'fixture-b')
    self.assertEqual(effective['agents']['qa'], defaults['agents']['qa'])
    self.assertNotEqual(config_digest(effective), config_digest(defaults))
```

Acrescentar `test_invalid_inputs_do_not_echo_or_write`: subtests para chave duplicada, bool no
limite, zero/negativo, NaN, decimal infinito, versão desconhecida, papel extra, chave secreta,
nome de variável inválido e arquivo ligado. Esperar `ValueError`, mensagem sem o valor secreto
e snapshot do diretório inalterado. `test_unknown_native_effort_stays_unverified` conserva
o pedido literal e verifica `self.assertNotIn('supported', c['agents']['pm'])`; a indicação
`not_verified` nos relatórios da CLI será verificada na tarefa 3.

- [ ] **Step 2: Executar o teste vermelho.** `python -B -m unittest discover -s tests -p test_mission_config.py -v`. Esperado: falha por ausência do módulo/funções, antes de implementar.
- [ ] **Step 3: Implementar as cinco funções em `mission_config.py`.** Usar cópia profunda e merge somente nos campos conhecidos: agente por papel, limites por campo, modo de deploy. Listas são substituídas integralmente; `null` só onde admitido; nenhuma remoção de papel obrigatório. Carregar no máximo 1 MiB; conferir estabilidade do arquivo durante leitura. Digest sobre JSON canônico normalizado; não incluir horário no digest.
- [ ] **Step 4: Documentar os nomes, padrões e limite de validação offline em README e USAGE PT/EN.** Não anunciar skills ou execução ainda ausentes; usar `humanizer`.
- [ ] **Step 5: Rodar novamente o comando da etapa 2.** Esperado: todos os testes passam; nenhum acesso a cliente, modelo ou rede.
- [ ] **Step 6: Commit explícito.** `git add -- scripts/mission_config.py tests/test_mission_config.py README.md docs/USAGE.md`; `git commit -m "feat: define mission agent configuration"`.

## Task 2: Backlog em Markdown com identidade e critérios verificáveis

**Files:** Create `scripts/mission_backlog.py`, `scripts/mission_vault.py`,
`tests/test_mission_backlog.py`, `tests/mission_fixtures.py`.
Modify `README.md`, `docs/USAGE.md` para o formato de backlog, privacidade e migração.

**Interfaces:**
- Consumes `vault.metadata(text) -> (dict, str)`, `document_store.safe_path`, `atomic_write`, `verify_private_storage`, `integrations.project_identity`.
- Produces `read_item(root: Path, note_path: str) -> dict`, `validate_graph(items: list[dict]) -> list[dict]`, `item_gaps(item: dict) -> list[str]` em `mission_backlog.py`.
- `read_item` retorna `id`, `kind`, `title`, `note_path`, `note_sha256`, `contract` ou `null`, `references` com hash/UUID, e `gaps`. `validate_graph` retorna diagnósticos `{code, item_id}` sem mutar dados; ciclo/pai errado/referência ausente nunca vira dependência satisfeita.
- Produces `render_item(project_id: str, item_id: str, kind: str, title: str, parent_id: str|None, now: str) -> str` em `mission_vault.py`: nota rascunho com índice e contrato vazio tipado, usando o UUID fornecido. Escrita e importação ficam na tarefa 3.
- Fixture `MissionCase(ProjectCase)` em `mission_fixtures.py` reutiliza `test_documents.ProjectCase`; prepara perfil pelo CLI existente e armazenamento privado; fornece `write_item(kind, parent_id=None, complete=True) -> str`, `configured() -> dict` e `snapshot() -> dict[str, bytes]`. Não inicializa o banco de missões implicitamente.

- [ ] **Step 1: Escrever testes de nota nova, legado e integridade.** `BacklogTests(MissionCase)` deve incluir:

```python
def test_existing_feature_is_read_without_rewrite(self):
    path = self.legacy_feature()  # helper: personalize.py feature em vault/features
    before = self.snapshot()
    item = read_item(self.root, path)
    self.assertEqual(item['kind'], 'feature')
    self.assertIn('missing_contract', item['gaps'])
    self.assertEqual(self.snapshot(), before)

def test_changed_reference_changes_evidence_revision(self):
    path, source = self.feature_with_reference()  # duas notas locais com UUID
    first = read_item(self.root, path)
    source.write_text(source.read_text(encoding='utf-8') + '\nNew evidence.\n', encoding='utf-8')
    second = read_item(self.root, path)
    self.assertNotEqual(first['references'][0]['sha256'], second['references'][0]['sha256'])
```

Os helpers adicionais são métodos de fixture dessa classe, definidos na mesma etapa.
`test_invalid_graph_reports_cycle_and_wrong_parent` constrói dois PBIs dependentes entre si e
um PBI cujo pai é epic; verificar códigos `dependency_cycle` e `invalid_parent`.
`test_contract_boundaries_reject_ambiguous_or_foreign_input` cobre dois blocos, JSON inválido,
projeto divergente, referência com UUID diferente, link público para nota privada, ausência de
fonte, escape de caminho, hardlink e reparse point;
esperar erro ou diagnóstico nomeado, zero escrita e nenhum comando executado a partir de texto.
As fixtures garantem `self.assertEqual(self.snapshot(), before)` nas falhas e
`self.assertEqual(vault.check(self.root)['issues'], [])` após criar notas válidas e seus índices.

- [ ] **Step 2: Executar o teste vermelho.** `python -B -m unittest discover -s tests -p test_mission_backlog.py -v`. Esperado: falha pelas funções ausentes.
- [ ] **Step 3: Implementar leitura, renderização e validação do grafo.** Ler cada nota/referência direta com limite de 1 MiB e estabilidade verificada. Aceitar só metadados/contrato definidos, listas de strings sem vazios para critérios completos e UUIDs únicos. Dependências de PBIs apontam a PBIs; referências não resolvidas permanecem lacunas em legados, mas contrato explícito inconsistente é rejeitado. Não tentar deduzir critérios da prosa por regex ou chamar IA.
- [ ] **Step 4: Definir lacunas de preparo.** Feature exige pai epic, objetivo, aceite, DoR/DoD; PBI acrescenta validação e referências pertinentes. Dependência ainda não desenvolvida impede puxar o PBI no futuro, mas não impede preparar uma missão cujo grafo e critérios estão completos. PM é proprietário do DoR/DoD; `owner` registra atribuição, sem provar autenticação do ator.
- [ ] **Step 5: Documentar o contrato e sua importação futura; rodar testes.** Comando da etapa 2 e `python -B -m unittest discover -s tests -p test_personalize.py -v`. Esperado: passam, UUID e bytes de notas antigas preservados. Atualizar README/USAGE PT/EN no mesmo commit.
- [ ] **Step 6: Commit explícito.** Adicionar os seis arquivos desta tarefa e `git commit -m "feat: define linked product backlog contracts"`.

## Task 3: Preparar e consultar missões com histórico durável

**Files:** Create `scripts/mission_store.py`, `scripts/missions.py`, `tests/test_missions.py`.
Modify `scripts/mission_vault.py`, `tests/mission_fixtures.py`, `README.md`, `docs/USAGE.md`.

**Interfaces:**
- Consumes configuração da tarefa 1 e leitura/validação das notas da tarefa 2.
- `mission_store.transaction(root: Path) -> ContextManager[sqlite3.Connection]` valida armazenamento e identidade, cria esquema só em escrita explícita e abre transação. `commit_record(conn, *, record: dict, expected_revision: int, operation_id: str, actor: dict, now: str) -> dict` retorna recibo; `get_record(root: Path, identifier: str) -> dict|None` e `list_records(root: Path, kind: str) -> list[dict]` são somente leitura, inclusive sem banco.
- `mission_vault.project_receipt(root: Path, receipt: dict, record: dict) -> dict` concilia projeção e índices e retorna `{state: current|pending|conflict, paths: list[str]}`. Consumir apenas registros confirmados no banco. História permanece no banco e em notas de evento com UUID/índice.
- `missions.apply_config(root, raw: dict, expected_digest: str|None) -> dict`; `import_item(root, note_path: str, expected_revision: int, operation_id: str, actor: dict) -> dict`; `prepare_mission(root, request: dict, operation_id: str, actor: dict) -> dict`; `revise_mission(root, mission_id: str, request: dict, expected_revision: int, operation_id: str, actor: dict) -> dict`; `mission_status(root, mission_id: str) -> dict`; `main(argv: list[str]|None=None) -> int`.
- `request` contém `title`, `feature_ids` únicos e não vazios, `priority` como permutação completa dos PBIs selecionados, `overrides` e `scope_reference` textual. Não aceitar `status`, contadores, timestamps ou produção fornecidos pelo chamador.

CLI: `python -B scripts/missions.py --root PATH <operação>`, sempre com `--json` opcional.
Operações: `config show`, `config validate --input FILE`, `config apply --input FILE --expected-digest HASH|absent`;
`backlog import --note PATH --expected-revision N --operation-id UUID --actor-id ID --actor-role pm|tech_lead`;
`prepare --input FILE --operation-id UUID --actor-id ID --actor-role pm`;
`revise M001 --input FILE --expected-revision N --operation-id UUID --actor-id ID --actor-role pm`;
`status M001`; `repair M001`. Caminhos de entrada são relativos ao projeto, regulares e limitados.
`--actor-role` é atribuição declarada nesta frente, não controle de identidade ou autorização.
Na CLI, saída 0 indica operação válida, mesmo quando o resultado é rascunho com pendências;
saída 1 indica conflito/falha operacional; saída 2 indica uso ou entrada inválida. JSON de erro
contém somente `schema_version: 1`, `error` como código estável e campos de orientação sanitizados.
`repair` só concilia projeções de registros existentes; não cria eventos de produto nem desfaz
edições conflitantes. Não há `start`, `deploy` ou setter arbitrário escondido na CLI.

- [ ] **Step 1: Escrever testes de preparação, repetição e snapshot.** `MissionTests(MissionCase)` define `prepared_fixture()` para importar epic/feature/PBIs e salvar configuração sintética. Usa IDs de operação UUID fixos por teste e timestamps UTC controlados no backend.

```python
def test_repeat_returns_same_mission_and_single_event(self):
    request, actor = self.prepared_fixture()
    first = prepare_mission(self.root, request, self.op_id, actor)
    second = prepare_mission(self.root, request, self.op_id, actor)
    self.assertEqual(first['record_id'], second['record_id'])
    self.assertEqual(first['sequence'], second['sequence'])
    self.assertEqual(len(list_records(self.root, 'mission')), 1)

def test_configuration_change_does_not_rewrite_mission(self):
    request, actor = self.prepared_fixture()
    receipt = prepare_mission(self.root, request, self.op_id, actor)
    first = get_record(self.root, receipt['record_id'])
    current = load_config(self.root)
    changed = effective_config(current, {'agents': {'pm': {'model': 'fixture-b'}}})
    apply_config(self.root, changed, config_digest(current))
    self.assertEqual(get_record(self.root, receipt['record_id']), first)
    self.assertFalse(mission_status(self.root, first['id'])['runnable'])
```

Adicionar testes nomeados com as seguintes asserções:

| Teste | Asserções |
|---|---|
| `test_revision_and_operation_conflicts_are_read_only` | ID repetido com pedido diferente e revisão antiga geram conflito; bytes e quantidade de eventos iguais |
| `test_status_does_not_initialize_or_repair` | Banco ausente retorna `not_initialized`; arquivo corrompido retorna erro sanitizado; nenhum byte criado/alterado |
| `test_projection_failure_recovers_without_duplicate` | Falha injetada em `project_receipt` após commit; status aponta atraso; repetir mesma operação/repair recupera uma única missão/evento |
| `test_private_and_linked_storage_is_rejected` | Vault privado rastreado, ignore negado, DB/sidecar hardlinked e diretório ligado são recusados antes de escrita; alvo externo intacto |
| `test_snapshot_staleness_and_source_identity` | Alteração da nota/fonte/perfil marca `stale_inputs`; revisão anterior intacta; UUID estrangeiro não importado |
| `test_revisions_keep_all_refinement_events` | Duas revisões com datas distintas mantêm criação e ambos refinamentos; sequência crescente mesmo com relógio atrasado |
| `test_multiple_drafts_are_not_active_missions` | Duas missões preparadas coexistem; nenhuma inicia; 4 PBIs totais são aceitos com WIP configurado em 3 |
| `test_no_advanced_transition_or_shell_execution` | Entrada com `completed`, contadores, deploy ou texto de shell não executa processo; rejeita campos não previstos |
| `test_human_projection_edit_is_preserved` | Edição manual da projeção sobrevive a repair, que retorna `projection_conflict` |
| `test_capability_selection_does_not_activate_tools` | ID conhecido guarda digest/limite da auditoria; ID desconhecido gera pendência; nenhuma configuração nativa ou MCP é alterado |

- [ ] **Step 2: Executar o teste vermelho.** `python -B -m unittest discover -s tests -p test_missions.py -v`. Esperado: falhas por funções ausentes.
- [ ] **Step 3: Implementar o armazenamento e as operações da CLI.** Validar todo o pedido e as fontes antes da transação. `apply_config` usa a transação como exclusão entre escritores do YoungCrow, reconfere o digest e grava o JSON atomicamente; o arquivo é a autoridade dos padrões. Nenhum modelo ou credencial é resolvido. Antes de gravar, resolver IDs de capacidades pelo catálogo e conservar observações/digests na preparação; ID desconhecido é pendência explícita, nunca ativação implícita. Uma operação de missão registra estado e evento na mesma transação, fecha-a, depois concilia Markdown. Armazenar hash de cada projeção escrita e sequência conciliada no estado operacional. Falha de projeção preserva resultado confirmado e recibo recuperável.
- [ ] **Step 4: Implementar privacidade e recuperação de leitura.** Escritas novas chamam `prepare_storage` somente após validar entradas e checar destinos; leituras chamam apenas verificação. Preflight inclui banco, journal/sidecars e índices; recusar caminhos externos, links, arquivos rastreados e root pertencente a outro projeto. Abrir leituras SQLite em URI `mode=ro`, sem reparo implícito. Versão de esquema desconhecida bloqueia; não criar migração adivinhada. Erros JSON/CLI nunca incluem conteúdo cru do input.
- [ ] **Step 5: Implementar preparação e status.** Importar grafo vinculado às features selecionadas, conferir critérios e prioridades, congelar configuração/perfil/fontes. Lacunas de planejamento deixam `draft`; completo vira `prepared`. Dependência de fora da seleção sem evidência aceita permanece bloqueio explícito. Status mostra revisão, critérios faltantes, atualidade das fontes, limites e próximas ações; mantém compatibilidade nativa não comprovada e execução indisponível. Alterar notas não atualiza snapshot sem `import`/`revise` explícito.
- [ ] **Step 6: Documentar comandos técnicos e rodar todos os testes da frente.** `python -B -m unittest discover -s tests -p "test_mission*.py" -v` e `python -B -m unittest discover -s tests -p test_vault.py -v`. Esperado: passam; notas produzidas nas fixtures passam em `vault.check(root)`, inclusive após recuperação. README/USAGE PT/EN distinguem preparar de executar.
- [ ] **Step 7: Commit explícito.** Adicionar os sete caminhos desta tarefa e `git commit -m "feat: prepare missions with durable history"`.

## Task 4: Personalizer e quatro comandos instaláveis nos dois clientes

**Files:** Create `skills/yc-personalizer/SKILL.md`, `skills/yc-config/SKILL.md`,
`skills/yc-missao/SKILL.md`, `skills/yc-status/SKILL.md`; os mesmos quatro nomes sob
`.claude/skills/` e `.agents/skills/`, cada um com `SKILL.md`.
Modify `skills/personalizer/SKILL.md`, `skills/personalizer/references/interview.md`, `setup.sh`,
`skills-lock.json`, `.gitignore`, `vault/capabilities/index.md`, `tests/test_setup.py`,
`tests/test_capabilities.py`, `scripts/missions.py`, `tests/test_missions.py`, `README.md`, `docs/USAGE.md`.

**Interfaces:**
- Consumes CLI da tarefa 3; a instrução compartilhada contém os comandos e os adaptadores nativos só a referenciam.
- Produces entradas `yc-personalizer`, `yc-config`, `yc-missao`, `yc-status`, descobertas como skills pelo cliente instalado. Nenhum novo agente autônomo é instalado nesta frente.
- Setup preserva manifestos, notas e skills existentes, mesmo com `--force`; diferenças de versão geram instrução de comparação/mescla, não overwrite semântico.

- [ ] **Step 1: Escrever testes de instalação e descoberta estática.** Em `SetupTests`, adicionar `test_mission_commands_follow_client_selection`, `test_mission_setup_preserves_existing_contracts` e `test_mission_setup_rejects_missing_dependency`. Asserções: para `claude|codex|both`, somente os adaptadores selecionados existem; os cinco scripts e quatro skills compartilhadas existem; `.gitignore` protege `vault/local`; reexecução preserva config, notas, UUID, manifesto e skills modificadas; arquivo obrigatório ausente faz preflight falhar antes de mudar o consumidor. Atualizar a lista `FILES` da fixture.
- [ ] **Step 2: Escrever testes do catálogo e contrato de skill.** Em `test_capabilities.py`, verificar os quatro IDs únicos, arquivos referenciados presentes, hashes reais, sem permissões de rede/credenciais, e auditoria estática `matched` em instalação nova. Verificar também conteúdo dos adaptadores: nomes iguais à entrada esperada, link compartilhado válido e ausência de instrução que afirme execução/produção disponível. Auditoria estática não é prova de uso nativo.
- [ ] **Step 3: Rodar testes vermelhos.** `python -B -m unittest discover -s tests -p test_setup.py -k mission -v` e `python -B -m unittest discover -s tests -p test_capabilities.py -k mission -v`. Esperado: falhas porque componentes não existem.
- [ ] **Step 4: Escrever as skills com `superpowers:writing-skills` e instalar os arquivos.** `yc-personalizer` retoma o perfil e encaminha perguntas de configuração para a rotina de `yc-config`; `yc-config` salva escolhas somente após respostas suficientes, sem pedir valores secretos. `yc-missao` orienta PM/Tech Lead na sessão atual a escrever/importar contratos e selecionar features; não lança outros agentes. `yc-status` é somente leitura. As quatro mantêm adoção trial antes de primeira escrita, fontes via Docling e capacidades via governança. Atualizar o guia de entrevista com perguntas faltantes sobre modelos, effort, limites e publicação.
- [ ] **Step 5: Preservar compatibilidade de instalação.** Adicionar arquivos às listas selecionadas do setup; inserir exceções dos quatro adaptadores Codex no `.gitignore` do template. Não instalar `youngcrow/agents.json` preenchido. No backend, checar dependências de helpers preservados antes da primeira escrita e retornar `incompatible_helper` se faltarem; incluir esse caso em `test_mission_setup_preserves_existing_contracts` e testar o erro sanitizado em `test_missions.py`. Não mudar os helpers antigos de forma incompatível.
- [ ] **Step 6: Atualizar catálogo e documentação.** Recalcular `expected.contract_sha256` e `files_sha256` usando as funções existentes para os registros alterados; não fabricar hashes nem zerar provas de outros registros. Preservar campos de consumidores. README/USAGE mostram `/yc-*` no Claude e seletor/`$yc-*` no Codex, explicitando os quatro comandos disponíveis e os cinco futuros. Usar `humanizer`.
- [ ] **Step 7: Rodar verificações.** Comandos da etapa 3, `python -B -m unittest discover -s tests -p test_capabilities.py -v` e `bash -n setup.sh`. Esperado: passam; auditoria nenhuma vez inicia MCP ou modelo. Provas de comportamento das skills seguem os limites autorizados do método de execução escolhido; nenhuma chamada nativa extra ou paga é implicitamente autorizada por este plano.
- [ ] **Step 8: Commit explícito.** Adicionar somente os arquivos enumerados nesta tarefa e `git commit -m "feat: add mission planning skills for Claude and Codex"`.

## Task 5: Percursos de adoção, processo visível e revisão final

**Files:** Create `tests/smoke_mission_foundation.py`, `assets/process-mission-planning-pt.svg`,
`assets/process-mission-planning-en.svg`, `docs/relatorios/2026-10-03-mission-foundation.md`,
`docs/medicoes/2026-10-03-mission-foundation.json`.
Modify `.github/workflows/test.yml`, `README.md`, `docs/USAGE.md`.

**Interfaces:**
- Smoke: `python -B tests/smoke_mission_foundation.py --root PATH --client claude|codex|both` cria exclusivamente consumidores descartáveis novos sob raiz verificada. Recusar raiz de projeto real ou fixture de outra execução; reusar apenas fixture com marcador próprio e estado reconhecido.
- Produces relatório JSON com adoção, preservação, registros, snapshots, recuperação, validação do vault e `native_execution: not_run`. Nunca chama LLM, faz push ou usa credencial real.

- [ ] **Step 1: Escrever o smoke com critérios que falhem se a passagem completa estiver quebrada.** Cobrir projeto novo via setup trial e migração de fixture com perfil/feature antiga. Guardar hashes de instruções, nota antiga, configuração personalizada e UUID. Criar epic, duas features e pelo menos quatro PBIs no total; importar critérios; salvar configuração; preparar missões de uma e duas features; mudar os padrões e conferir snapshots antigos; reexecutar operação; interromper projeção e recuperar. Cada asserção gera medição explícita, não apenas código de saída zero do subprocesso.
- [ ] **Step 2: Executar o smoke e corrigir somente falhas demonstradas.** Linux: comando acima para os três clientes, raízes distintas sob diretório temporário. Windows: `python -B tests/windows_fixture_runner.py tests/smoke_mission_foundation.py --root PATH --client both`. Esperado: vault válido, dados preservados, estados `draft|prepared`, nenhuma execução de produto, recuperação sem duplicação. Usar `systematic-debugging` se houver falha; não enfraquecer checks para passar.
- [ ] **Step 3: Integrar a prova ao CI existente.** Acrescentar smoke de `both` ao job Linux e ao job Windows com o runner de fixtures já existente; suíte unitária geral já descobre os novos testes. Linux não precisa repetir três smokes no CI se seleção individual estiver coberta em `test_setup`. Usar diretórios do runner fora do checkout de produto. Não acrescentar deploy ao workflow.
- [ ] **Step 4: Produzir os diagramas SVG PT/EN.** Reutilizar paleta/tipografia dos assets `process-*.svg`; caixas para personalizer, configuração, backlog, missão e consulta, decisão para critérios suficientes e retorno ao refinamento. Terminar em “Missão preparada; execução automática ainda indisponível”. Incorporar imagens visíveis no README com link para abrir; sem esconder em bloco recolhido. Conferir XML, ausência de scripts/recursos externos, leitura em desktop/celular e fechar apenas o navegador do ensaio em `finally`, verificando zero processos próprios restantes. Não abrir navegador durante prova paga.
- [ ] **Step 5: Fechar o passo a passo PT/EN e evidências.** USAGE cobre setup do zero, migração preservada, trial, configuração, uma ou N features, importação/atualização, status, recuperação e limitações. Distinguir conferência estática, execução real da CLI, prova nativa de skills e funcionalidade futura. Nos relatórios, registrar testes, versões, pendências e estado de publicação real; nenhum segredo, transcrição privada ou caminho pessoal. Incluir nota local e microíndice da frente.
- [ ] **Step 6: Verificação final proporcional.** Rodar `python -B -m unittest discover -s tests -v`, `bash -n setup.sh`, `python -B scripts/vault.py check --json` e `git diff --check`. Ler resultados completos. Exigir smoke real Linux/Windows pelo CI antes de anunciar ambos; medição ausente permanece pendente. Revisão independente somente leitura conforme método escolhido; corrigir achados materiais e repetir apenas checks afetados.
- [ ] **Step 7: Commit explícito e integração.** Adicionar os oito arquivos desta tarefa e `git commit -m "docs: verify and document mission preparation"`. A revisão de branch verifica diferenças com a spec aprovada. Preparar PR com escopo desta frente e provas; anexá-lo ao chat quando criado. Merge/publicação seguem autorização vigente e proteções do projeto, sem concluir a esteira completa por ter entregue sua fundação.

## Cobertura do desenho e continuação

| Contrato da especificação | Onde fica |
|---|---|
| Personalizer reaproveitada; novo/migração; trial antes das notas | Tarefas 2, 4, 5 |
| Configuração por agente, conexão explícita, effort, padrões/snapshot | Tarefas 1, 3, 4 |
| Epics/features/PBIs, DoR/DoD, referências, timestamps e revisão | Tarefas 2, 3 |
| Comandos separados nos dois clientes | Tarefa 4: quatro comandos de preparação; restantes na frente 2/4 |
| Memória privada, índices, revisões e retomada | Tarefas 2, 3, 5 |
| Filas, paralelismo efetivo, processos, branches, transferência e enforcement | Frente 2, plano próprio após esta fundação |
| QA de produto, Playwright do produto, correções e integração | Frente 3; não confundir com teste do harness/diagrama |
| Release, deploy, verificação, recuperação de produção e avisos | Frente 4 |

O plano foi revisto quanto a cobertura da frente 1, interfaces, ausência de execução prematura,
preservação de legado, recuperação e diferença entre contrato preparado e produção. Estados
futuros são recusados, não simulados. A implementação só começa após revisão deste plano e
escolha do método.

Recomendação de execução: nativa nesta sessão, um escritor, tarefas em sequência e um revisor
independente ao final. As interfaces dependem umas das outras e não se beneficia de escritores
paralelos. A alternativa é um subagente novo por tarefa, com revisão por tarefa e revisão final,
ao custo de mais contextos. Nenhum dos métodos foi selecionado ainda para esta frente.
