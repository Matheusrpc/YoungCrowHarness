<p align="center">
  <img src="assets/vitral.png" alt="Vitral de capela com um corvo que usa a medalha de São Bento" width="100%">
</p>

<p align="center">
  <img src="assets/titulo.svg" alt="YoungCrowHarness: ponto de partida para projetos com Claude Code e Codex" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/licen%C3%A7a-MIT-E8A317?style=for-the-badge&labelColor=17130f" alt="Licença MIT">
  <img src="https://img.shields.io/badge/Claude_Code-harness-1F4FA3?style=for-the-badge&labelColor=17130f" alt="Claude Code">
  <img src="https://img.shields.io/badge/Codex-harness-1F7A4D?style=for-the-badge&labelColor=17130f" alt="Codex">
  <img src="https://img.shields.io/badge/segredos-local_only-B3202F?style=for-the-badge&labelColor=17130f" alt="Mantenha segredos locais">
</p>

<p align="center">
  <a href="#português"><img src="https://img.shields.io/badge/Ler_em-Portugu%C3%AAs-5B2E8A?style=for-the-badge&labelColor=17130f" alt="Português"></a>
  <a href="#english"><img src="https://img.shields.io/badge/Read_in-English-1B7F8C?style=for-the-badge&labelColor=17130f" alt="English"></a>
</p>

<img src="assets/vidro.svg" alt="" width="100%">

<a id="português"></a>

## <img src="assets/gema-cobalto.svg" height="24" alt=""> O que é

Um ponto de partida para projetos feitos com Claude Code e Codex. Você clona, roda um comando, e o
projeto novo já nasce com as regras da casa, os hooks, os atalhos de MCP e as skills que valem a pena.
Senhas, tokens e chaves devem ficar no ambiente local. O instalador protege o `.env` com uma regra
de ignore e recusa um `.env` já rastreado; revise também os demais arquivos antes de versionar.

O corvo do vitral é o mascote. Ele carrega uma medalha de São Bento, e o lema está na assinatura, no
fim desta página.

O `personalizer` ajuda a adaptar o harness ao seu produto: lê o projeto, pergunta o que falta,
registra as decisões e prepara a primeira feature. A entrevista fica no [vault](vault/index.md),
junto das entregas, integrações e evidências que permitem retomar o trabalho em outra sessão.
Para fornecedores, `integration-specialist` e `integrate-from-docs` orientam a implementação a partir
da documentação oficial. As duas skills funcionam com Claude Code e Codex.

A entrevista e a auditoria são conduzidas pelo agente. Os comandos organizam as notas e preservam
o conteúdo existente. A sincronização automática com Graphify/claude-mem e a orquestração autônoma
de papéis continuam na [evolução planejada](docs/superpowers/specs/2026-10-01-youngcrow-foundation-design.md).

## <img src="assets/gema-rubi.svg" height="24" alt=""> Começar em um comando

```bash
git clone https://github.com/Matheusrpc/YoungCrowHarness.git
bash YoungCrowHarness/setup.sh meu-projeto --client both --nome "Meu Projeto"
```

**Passo a passo:** [repo do zero](docs/USAGE.md#zero-pt) · [migrar repo existente](docs/USAGE.md#migrar-pt) · [como operar](docs/USAGE.md#operar-pt).

Requer Bash, Git e `python3` funcionando no mesmo terminal. No Windows, use Git Bash.
O `setup.sh` copia o harness preservando os arquivos existentes e acrescenta proteção ao `.gitignore`.
Cria um `.env` local a partir do `.env.example`, com permissão 600 onde suportada, para você preencher à mão.
Instala a skill `humanizer` do upstream (commit pinado) e a `humanizer-ptbr`: em `~/.claude/skills/` para Claude
e `.agents/skills/` no projeto para Codex. Use `--client claude`, `--client codex` ou `--client both` (padrão). E,
se o Claude Code estiver instalado, adiciona os marketplaces e instala os plugins listados em
`skills-lock.json`. Rode com `--sem-plugins` para pular essa última parte, ou com `--force` para trocar
os templates que já existem. `.env` e as regras existentes de `.gitignore` são preservados mesmo com force.
As skills dos clientes selecionados continuam com `--sem-plugins`; as do Claude afetam o usuário.
O modo Codex não chama o Claude. Plugins do Codex são instalados pelo catálogo do próprio cliente.
Humanizer divergente ou modificado é preservado e interrompe o setup; falhas de instalação retornam código não zero.
O guia explica como retomar e quais componentes exigem instalação manual.

Depois disso, abra o `CLAUDE.md` e troque cada `<preencher>` pelo que é seu: comandos de teste, alvos de
publicação, fronteiras. Configure MCPs em `.mcp.json` para Claude e `.codex/config.toml` para Codex.
Abra o cliente na pasta e [confira skills, MCPs e hooks](docs/USAGE.md#clientes-pt).

Peça: “Use personalizer para adaptar este projeto. Leia o que já existe, pergunte o que falta e
registre a primeira feature no vault.” Veja o [guia de personalização](docs/USAGE.md#personalizer-pt)
para começar do zero, migrar ou retomar uma entrevista.

Depois de registrar uma entrega, confira a organização da memória na raiz do produto:

```bash
python3 scripts/vault.py check
```

O comando aponta notas sem índice, links locais quebrados, IDs duplicados e memórias que ficaram
fora da navegação. Ele só lê os arquivos. Veja [como validar e corrigir o vault](docs/USAGE.md#vault-check-pt).

<a id="processo-pt"></a>

## <img src="assets/gema-violeta.svg" height="24" alt=""> Da ideia à entrega

Os fluxos abaixo mostram como começar, migrar e trabalhar com o harness. Círculos marcam eventos,
caixas representam tarefas e losangos indicam decisões. O desenho é inspirado em BPMN; pessoas e
agentes executam as etapas. PM e Tech Lead são responsabilidades, sem orquestração autônoma.

### 1. Começar do zero

![Projeto novo: clonar o harness, rodar setup, conferir guias, skills e MCPs, abrir personalizer e salvar perfil e primeira feature.](assets/process-new-pt.svg)

[Passo a passo e comandos](docs/USAGE.md#zero-pt) · [Abrir diagrama](assets/process-new-pt.svg)

### 2. Migrar um projeto existente

![Migração: salvar trabalho e abrir branch, auditar código e harness, executar setup sem force, usar personalizer em modo existing e validar uma entrega.](assets/process-migrate-pt.svg)

[Passo a passo da adoção](docs/USAGE.md#migrar-pt) · [Abrir diagrama](assets/process-migrate-pt.svg)

### 3. Operar até a entrega

![Operação: recuperar o vault, definir e implementar uma entrega, testar e atualizar README, revisar, publicar somente quando autorizado, verificar o ambiente e salvar o resultado; falhas retornam à correção.](assets/process-delivery-pt.svg)

[Como operar](docs/USAGE.md#operar-pt) · [Abrir diagrama](assets/process-delivery-pt.svg) · [Fluxo completo com pausas e retomada](docs/PROCESS.md#portugues)

Cada entrega atualiza o README com revisão de texto por `humanizer`. O vault guarda fontes, decisões,
capacidades usadas, testes e próximo passo. Produção exige evidência do ambiente. Uma publicação
fora do escopo fica como não aplicável; se faltar autorização, salve a pendência para a próxima sessão.

## <img src="assets/gema-ambar.svg" height="24" alt=""> O que vem dentro

| Arquivo | Para que serve |
|---|---|
| `CLAUDE.md` | O guia que o Claude Code lê no início de cada sessão: dez leis de trabalho, alvos de publicação, comandos e fronteiras. Em português. |
| `docs/CLAUDE.en.md` | O mesmo guia em inglês. Fique com um dos dois. |
| `AGENTS.md` | A entrada do Codex: lê o `CLAUDE.md` primeiro, um executor escreve por vez, revisores só leem, e o navegador fecha ao terminar. |
| `.claude/settings.json` | Hooks do Claude Code. Chamam o detector de design do plugin `impeccable` depois de cada edição, só se ele estiver instalado. |
| `.codex/hooks.json` | Os mesmos hooks, no formato do Codex. |
| `.codex/config.toml` | MCPs do Codex no escopo do projeto. Exemplos desativados até revisão; exige confiança do projeto. |
| `.mcp.json` | Atalhos de MCP com URLs de exemplo. Nunca ponha token aqui; o token vai por variável de ambiente. |
| `.env.example` | Os nomes das variáveis que o projeto espera, com valores falsos. O `.env` real nasce daqui e nunca entra no git. |
| `.gitignore` | Segredos, caches, evidência pesada e estado local fora do repositório. |
| `skills-lock.json` | Inventário dos plugins e origem das skills. O instalador verifica o commit de humanizer; versões dos plugins de marketplace ainda não são fixadas por este manifesto. |
| `skills/humanizer-ptbr/` | Juiz de texto em português: 25 padrões de escrita de máquina e como reescrever. |
| `skills/personalizer/` | Entrevista retomável, auditoria guiada e adaptação do projeto. |
| `skills/integrate-from-docs/` | Documentação oficial, implementação e histórico de integrações. |
| `vault/` | Índice geral e capacidades; produto, features, decisões e operação crescem conforme o uso. |
| `scripts/personalize.py` | Cria os registros de personalização e a primeira feature sem substituir notas. |
| `scripts/integrations.py` | Cria notas de fornecedores e exporta registros com identidade e revisão. |
| `scripts/vault.py` | Confere metadados, links e navegação do vault sem alterar as memórias. |
| `setup.sh` | O comando que monta tudo. |

## <img src="assets/gema-esmeralda.svg" height="24" alt=""> As dez leis

<p align="center">
  <img src="assets/leis-pt.svg" alt="I. Medir antes de afirmar; II. Nenhum segredo no git; III. Escrever só onde é seu; IV. Divergiu? Pare e reporte; V. Idempotência antes de pagar; VI. Estado salvo, nunca pendurado; VII. A regra nasce ligada; VIII. Publicar na hora; IX. Uma frente por checkout; X. O navegador fecha no fim" width="100%">
</p>

O texto completo, com o porquê de cada uma, está no `CLAUDE.md`.

## <img src="assets/gema-violeta.svg" height="24" alt=""> O que não está aqui

Use exemplos públicos; mantenha credenciais e dados de clientes fora dos arquivos versionados.
As skills de terceiros não estão copiadas: o `setup.sh` instala do upstream,
com a licença e o commit de cada uma. Os plugins do `skills-lock.json` que vêm de diretório local (o
`impeccable`) você instala à mão, seguindo a página do próprio plugin.

## <img src="assets/gema-turquesa.svg" height="24" alt=""> Créditos

Mantido por [Matheus Couto](https://github.com/Matheusrpc). Claude Code e Codex são ferramentas
de desenvolvimento; os guias orientam preservar a autoria humana. A configuração do Claude desativa
a atribuição automática em novos commits e PRs. A remoção das atribuições antigas da `main` está
registrada no [relatório de autoria](docs/relatorios/2026-10-02-ai-attribution.md).

A skill `humanizer` é de [blader/humanizer](https://github.com/blader/humanizer), MIT, e os padrões
vêm de [«Signs of AI writing»](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) da
Wikipédia. Os plugins listados no `skills-lock.json` pertencem aos seus autores. O resto deste
repositório é MIT.

<img src="assets/vidro.svg" alt="" width="100%">

<a id="english"></a>

## <img src="assets/gema-cobalto.svg" height="24" alt=""> What it is

A starting point for projects built with Claude Code and Codex. Clone it, run one command, and the new
project starts with the house rules, the hooks, the MCP shortcuts and the skills that earn their place.
Passwords, tokens and keys belong in the local environment. Setup protects `.env` with an ignore rule
and rejects a tracked `.env`; review other files before committing them as well.

The crow in the stained glass is the mascot. It wears a Saint Benedict medal, and the motto is in the
signature at the end of this page.

The `personalizer` reads your project, asks about missing decisions and prepares its profile and first
feature. Interviews, deliveries, integrations and evidence live in the [vault](vault/index.md), so a
later session can resume from the saved records. For vendor work, `integration-specialist` and
`integrate-from-docs` guide implementation from official documentation. Both skills support Claude Code and Codex.

The agent conducts the interview and adoption audit. Commands organize notes and preserve existing
content. Automatic Graphify/claude-mem synchronization and autonomous role orchestration remain planned.

## <img src="assets/gema-rubi.svg" height="24" alt=""> Start with one command

```bash
git clone https://github.com/Matheusrpc/YoungCrowHarness.git
bash YoungCrowHarness/setup.sh my-project --client both --name "My Project"
```

**Step by step:** [new repository](docs/USAGE.md#new-en) · [adopt an existing repo](docs/USAGE.md#migrate-en) · [daily operation](docs/USAGE.md#operate-en).

Requires Bash, Git and a working `python3` in the same terminal. On Windows, use Git Bash.
`setup.sh` preserves existing project files and appends protection to `.gitignore`.
It creates a local `.env` from `.env.example`, with permission 600 where supported, for you to fill in
by hand. It installs the `humanizer` skill from upstream (pinned commit) and `humanizer-ptbr` into
`~/.claude/skills/` for Claude and project-local `.agents/skills/` for Codex. Choose `--client claude`,
`--client codex` or `--client both` (default). For Claude, it adds the marketplaces and installs the plugins
listed in `skills-lock.json`. Run it with `--no-plugins` to skip that last part, or with `--force` to
replace existing templates. `.env` and existing ignore rules are preserved even with force.
Selected clients' skills still install with `--no-plugins`; Claude installations affect the user.
Codex-only mode does not call Claude. Install Codex plugins through its own catalog.
A dirty or mismatched humanizer is preserved and blocks setup; installation failures return nonzero.
The guide explains recovery and manual components.

After that, open `CLAUDE.md` and replace each `<preencher>` (fill in) with what is yours: test commands,
publication targets, boundaries. If you work in English, move `docs/CLAUDE.en.md` over `CLAUDE.md`.
Configure `.mcp.json` for Claude and `.codex/config.toml` for Codex. Open your client inside the folder
and check loaded skills, MCPs and hooks using the [usage guide](docs/USAGE.md#english).

Ask: “Use personalizer to adapt this project. Read what is already here, ask about missing decisions
and record the first feature in the vault.” Follow the [personalization guide](docs/USAGE.md#personalizer-en)
for a new product, adoption or a resumed interview.

After recording a delivery, check the memory structure from the product root:

```bash
python3 scripts/vault.py check
```

The command reports missing indices, broken local links, duplicate IDs and notes that cannot be
reached through navigation. It only reads files. See [how to check and repair the vault](docs/USAGE.md#vault-check-en).

<a id="process-en"></a>

## <img src="assets/gema-violeta.svg" height="24" alt=""> From idea to delivery

These flows show how to start, adopt and work with the harness. Circles mark events, boxes are
tasks and diamonds are decisions. The diagrams are inspired by BPMN; people and agents carry out
the steps. PM and Tech Lead are responsibilities, without autonomous orchestration.

### 1. Start from scratch

![New project: clone the harness, run setup, check guides, skills and MCPs, open personalizer, then save the profile and first feature.](assets/process-new-en.svg)

[Steps and commands](docs/USAGE.md#new-en) · [Open diagram](assets/process-new-en.svg)

### 2. Adopt an existing project

![Adoption: save work and create a branch, audit the code and harness, run setup without force, use personalizer in existing mode, then verify a delivery.](assets/process-migrate-en.svg)

[Adoption steps](docs/USAGE.md#migrate-en) · [Open diagram](assets/process-migrate-en.svg)

### 3. Work through a delivery

![Daily work: recover vault context, define and implement a delivery, test and update README, review, release only when authorized, verify the environment and save the outcome; failures return to correction.](assets/process-delivery-en.svg)

[Daily operation](docs/USAGE.md#operate-en) · [Open diagram](assets/process-delivery-en.svg) · [Full flow with pauses and resumption](docs/PROCESS.md#english)

Each delivery updates the README with `humanizer` prose review. The vault keeps sources, decisions,
capabilities used, tests and the next action. Production requires environment evidence. Mark a
release outside scope as not applicable; when authorization is missing, save it as pending for a later session.

## <img src="assets/gema-ambar.svg" height="24" alt=""> What is inside

| File | What it is for |
|---|---|
| `CLAUDE.md` | The guide Claude Code reads at the start of every session: ten working laws, publication targets, commands and boundaries. In Portuguese. |
| `docs/CLAUDE.en.md` | The same guide in English. Keep one of the two. |
| `AGENTS.md` | The Codex entry point: read `CLAUDE.md` first, one writer at a time, reviewers only read, and the browser closes when the task ends. |
| `.claude/settings.json` | Claude Code hooks. They call the `impeccable` plugin's design detector after each edit, only if it is installed. |
| `.codex/hooks.json` | The same hooks, in Codex format. |
| `.codex/config.toml` | Project-scoped Codex MCP servers. Examples start disabled for review; project trust is required. |
| `.mcp.json` | MCP shortcuts with example URLs. Never put a token here; tokens travel through environment variables. |
| `.env.example` | The names of the variables the project expects, with fake values. The real `.env` is born from it and never enters git. |
| `.gitignore` | Secrets, caches, heavy evidence and local state stay out of the repository. |
| `skills-lock.json` | Plugin inventory and skill sources. The installer verifies the humanizer commit; this manifest does not yet pin marketplace plugin versions. |
| `skills/humanizer-ptbr/` | A text judge for Brazilian Portuguese: 25 patterns of machine writing and how to rewrite them. |
| `skills/personalizer/` | Resumable interview, agent-led audit and project adoption. |
| `skills/integrate-from-docs/` | Official sources, implementation and integration history. |
| `vault/` | General and capability indices; product, feature, decision and operation records grow as needed. |
| `scripts/personalize.py` | Creates onboarding and feature records without replacing notes. |
| `scripts/integrations.py` | Creates vendor records and exports identity/revision-addressed notes. |
| `scripts/vault.py` | Checks vault metadata, links and navigation without changing memories. |
| `setup.sh` | The command that puts it all together. |

## <img src="assets/gema-esmeralda.svg" height="24" alt=""> The ten laws

<p align="center">
  <img src="assets/leis-en.svg" alt="I. Measure before you claim; II. No secret in git; III. Write only where it's yours; IV. Off plan? Stop and report; V. Idempotent before paid; VI. Persist state, never hang; VII. Rules ship switched on; VIII. Publish right away; IX. One task per checkout; X. The browser closes at the end" width="100%">
</p>

The full text, with the reason behind each law, is in `docs/CLAUDE.en.md`.

## <img src="assets/gema-violeta.svg" height="24" alt=""> What is not here

Use public examples; keep credentials and customer data out of tracked files.
Third party skills are not copied: `setup.sh` installs them from upstream, with each one's
license and commit. Plugins in `skills-lock.json` that come from a local directory (`impeccable`) you
install by hand, following the plugin's own page.

## <img src="assets/gema-turquesa.svg" height="24" alt=""> Credits

Maintained by [Matheus Couto](https://github.com/Matheusrpc). Claude Code and Codex are development
tools; the guides preserve human authorship. Claude settings disable automatic attribution in new
commits and PRs. Removal of the older `main` attributions is recorded in the
[authorship report](docs/relatorios/2026-10-02-ai-attribution.md) (Portuguese).

The `humanizer` skill is [blader/humanizer](https://github.com/blader/humanizer), MIT, and its patterns
come from Wikipedia's [«Signs of AI writing»](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
The plugins listed in `skills-lock.json` belong to their authors. The rest of this repository is MIT.

<a id="verificacao"></a>
<a id="verification"></a>

## <img src="assets/gema-cobalto.svg" height="24" alt=""> Verificação / Verification

A `main` deste repositório exige PR, check `installer` do GitHub Actions aprovado, branch atualizada
e conversas de revisão resolvidas. Exclusão e force push estão bloqueados, sem exceção para admins.
Há um único mantenedor, portanto não se exige uma segunda aprovação. Veja a
[configuração e como adotá-la](docs/USAGE.md#protection-pt); o setup não altera regras do GitHub.

This repository's `main` requires a PR, the `installer` check from GitHub Actions, an up-to-date branch
and resolved review conversations. Deletion and force pushes are blocked, with no admin bypass.
With one maintainer, a second approval is not required. See the
[configuration and adoption steps](docs/USAGE.md#protection-en); setup does not change GitHub rules.

```bash
python3 -m unittest discover -s tests -v  # Python 3.11+
bash -n setup.sh
```

| Ambiente / Environment | Evidência / Evidence |
|---|---|
| Windows + Git Bash + Python 3.14 | Suíte local; casos de symlink exigem privilégio e rodam no CI Linux / local suite; symlink cases require privileges and run in Linux CI. |
| Linux | Suíte automática a cada push/PR, incluindo symlinks / automated suite on every push/PR, including symlinks — [execuções / runs](https://github.com/Matheusrpc/YoungCrowHarness/actions). |
| macOS / PowerShell nativo | Não verificados / not verified. Use Bash. |

Os testes cobrem instalação, preservação, caminhos, índices e retomada. Casos de symlink rodam no Linux;
o teste de junction nativa é exclusivo de Windows. A suíte usa Git local, usuário temporário e chamadas
de plugins simuladas. Execute um setup por destino de cada vez.
O teste opcional [smoke_clients.py](tests/smoke_clients.py) confere skills e agente nos clientes reais.
O Codex envia uma requisição a um modelo fictício em loopback; o Claude carrega metadados pelo SDK.
Não há chamada de modelo pago, execução de plugins reais ou conexão MCP. Confira o
[guia dos clientes](docs/USAGE.md#clientes-pt) para confiança e ativação.

Tests cover installation, preservation, paths, indices and resumption. Symlink cases run on Linux;
the native junction test runs on Windows. The optional smoke check uses real client loaders, a
loopback model fixture for Codex and SDK metadata initialization for Claude. It makes no paid model
calls or MCP connections and does not prove third-party plugin execution.

<p align="center">
  <img src="assets/assinatura.svg" alt="☧ Ora et labora ☧ et coda &lt;/&gt;" width="100%">
</p>
