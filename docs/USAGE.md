<p align="center">
  <img src="../assets/titulo.svg" alt="YoungCrowHarness — guia de uso / usage guide" width="100%">
</p>

[← README](../README.md) · [Português](#portugues) · [English](#english)

<img src="../assets/vidro.svg" alt="" width="100%">

<a id="portugues"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Antes de começar

Este guia cobre o instalador atual e a adoção manual das regras do harness. O vault com índice geral e microíndices, o personalizer, a auditoria automática de migração e as integrações Graphify/claude-mem estão [planejados](superpowers/specs/2026-10-01-youngcrow-foundation-design.md). O setup ainda não os cria.

Use Bash no Linux ou Git Bash no Windows, com Git e Python 3 disponíveis no mesmo terminal:

```bash
bash --version
git --version
python3 --version
```

No Windows, se `python3` abrir a Microsoft Store ou não funcionar, configure o Python instalado no PATH do Git Bash antes de continuar. Os comandos abaixo são para Bash; não cole diretamente no PowerShell.

O setup atende os dois clientes por padrão (`--client both`). Use `--client claude` ou `--client codex` para preparar somente um. As regras em `CLAUDE.md` e `AGENTS.md` são comuns; configurações e skills seguem os caminhos de cada cliente:

| Componente | Claude Code | Codex |
|---|---|---|
| Instruções | `CLAUDE.md` | `AGENTS.md`, que orienta ler `CLAUDE.md` |
| Skills humanizer e humanizer-ptbr | `~/.claude/skills/`, no usuário | `.agents/skills/`, dentro do projeto |
| MCP | `.mcp.json` | `.codex/config.toml` |
| Hooks | `.claude/settings.json` | `.codex/hooks.json` |
| Plugins | Marketplace Claude, se instalado | Catálogo do Codex, instalação manual |

`--sem-plugins` pula os plugins do Claude; as skills dos clientes selecionados continuam sendo instaladas e humanizer precisa acessar o GitHub. Em modo Codex, nenhuma instalação de Claude é executada. O Git do projeto não desfaz alterações no usuário. As cópias locais das skills do Codex ficam ignoradas pelo Git: cada clone ou worktree novo precisa executar o setup. Skills próprias do produto podem ser versionadas separadamente, conforme a política de ignore do projeto.

No Codex para Windows, deixe `python` no PATH do cliente e, se usar o hook opcional de impeccable, também `bash`. A instalação continua sendo executada no Git Bash.

Execute uma instalação por destino de cada vez. O preflight recusa links em caminhos gerenciados, mas não é um sandbox contra mudanças feitas por outro processo durante a execução.

**Navegação:** [repo do zero](#zero-pt) · [migrar repo](#migrar-pt) · [conferir cada cliente](#clientes-pt) · [operar](#operar-pt) · [falhas e manutenção](#manutencao-pt).

<a id="zero-pt"></a>

## <img src="../assets/gema-rubi.svg" height="24" alt=""> Primeiro setup: repo do zero

1. Clone o harness ao lado da pasta que será seu produto. O destino não pode ser o próprio clone do harness.

   ```bash
   git clone https://github.com/Matheusrpc/YoungCrowHarness.git
   bash YoungCrowHarness/setup.sh meu-projeto --client both --nome "Meu Projeto" --sem-plugins
   cd meu-projeto
   ```

   Remova `--sem-plugins` se quiser instalar também os plugins de marketplace do inventário. A saída distingue componentes copiados, mantidos e pulados.

2. Inicialize o Git e confira a proteção do arquivo local:

   ```bash
   git init
   git check-ignore --no-index .env
   git ls-files -- .env
   ```

   O primeiro check deve mostrar `.env`; o segundo deve ficar vazio. O setup não cria um repositório Git. Em pasta sem Git, ele prepara a regra e pede esta verificação.

3. Abra `CLAUDE.md` e `AGENTS.md`. Preencha objetivo, comandos reais de teste, build, limites de escrita, ambientes e política de publicação. Defina quem autoriza produção e como reverter. Resolva os campos `<preencher>` antes de entregar trabalho ao agente. Preserve ou documente o design system do produto: componentes, cores, tipografia e referências existentes.

4. Revise `.mcp.json` para Claude e `.codex/config.toml` para Codex, além dos hooks selecionados. Remova MCPs que não serão usados e substitua URLs de exemplo. No Codex, os exemplos começam com `enabled = false`: revise autenticação e habilite apenas os necessários. Copiar `.env` não carrega suas variáveis automaticamente em nenhum dos clientes. Preencha valores locais sem colar credenciais em prompts ou documentação. Confirme o carregamento [no cliente](#clientes-pt).

5. Confira o diff e versione apenas os arquivos revisados. Nunca adicione `.env`. Abra a pasta no Codex ou execute `claude` nela. Comece com uma tarefa pequena e exija evidência de teste antes da primeira entrega.

<a id="migrar-pt"></a>

## <img src="../assets/gema-ambar.svg" height="24" alt=""> Primeiro setup: migrar um repo existente

1. No projeto existente, examine `git status`. Salve conscientemente o trabalho atual e abra uma branch de adoção. Revise segredos antes de qualquer commit; um backup não é motivo para versioná-los.

   ```bash
   git status --short
   git switch -c chore/adotar-youngcrow
   git ls-files -- .env
   ```

   Se o último comando mostrar `.env`, pare e resolva seu rastreamento antes do setup. Se credenciais já entraram no histórico, retirar o arquivo do índice não apaga esse histórico; trate as credenciais expostas.

2. Faça um inventário do código e do harness atual: arquitetura, testes existentes, comandos que realmente funcionam, design system, `AGENTS.md`, `CLAUDE.md`, skills, MCPs, hooks e documentos. Registre o que preservar e quais lacunas impedem uma entrega segura. O instalador não faz essa auditoria por você.

3. Com o clone do YoungCrowHarness em uma pasta irmã, execute sem `--force`:

   ```bash
   bash ../YoungCrowHarness/setup.sh . --client both --nome "Meu Produto" --sem-plugins
   git diff --stat
   git diff
   git status --short
   git check-ignore --no-index .env
   ```

4. Compare os arquivos marcados como **mantidos** com os templates do harness. Mescle manualmente as regras úteis com as instruções do produto; não apague sua arquitetura, comandos ou decisões. O setup preserva os arquivos existentes byte a byte e acrescenta proteção de env e downloads locais ao `.gitignore`. Ele não faz mesclagem semântica de guias, hooks ou MCPs, nem converte um `.mcp.json` já personalizado para TOML. Transcreva as entradas necessárias para `.codex/config.toml` e confira ambos. `git diff` não mostra o conteúdo de arquivos novos não rastreados: revise-os também.

5. Rode os testes e o build que existiam antes da adoção. Confira os hooks e MCPs no cliente escolhido. Registre a comparação antes/depois, os riscos e as pendências; revise o diff e entregue a adoção como uma mudança pequena.

**Primeiro pedido sugerido ao agente:** “Leia AGENTS.md e CLAUDE.md, inventarie o código e o harness existente, identifique o design system e rode as verificações disponíveis. Registre evidências, lacunas e uma proposta de adoção por pequenas entregas. Preserve decisões existentes e não publique em produção sem a autorização definida no projeto.”

<a id="clientes-pt"></a>

## <img src="../assets/gema-turquesa.svg" height="24" alt=""> Conferir Claude Code e Codex

**Claude Code:** abra `claude` na raiz do projeto. Confira as skills `humanizer` e `humanizer-ptbr` no menu `/`; use `/mcp` para revisar os servidores e autorizar apenas os configurados para seu projeto. Confira os hooks em `/hooks`. A ausência de impeccable deixa seu hook opcional sem ação; instalar o marketplace não garante que o executável exista no caminho configurado.

**Codex:** abra a pasta no aplicativo ou execute `codex` nela. Revise a confiança do projeto; configurações locais só são carregadas em projetos confiáveis. Confira `humanizer` e `humanizer-ptbr` em `/skills` no CLI ou no seletor de skills do cliente. Confira MCPs em `/mcp` no CLI e os hooks no cliente, com confiança explícita antes da execução. Se usar o mesmo MCP nos dois hosts, mantenha URL, autenticação e permissões coerentes nos dois arquivos; não há sincronização automática. O setup não reduz sandbox nem aprova ferramentas automaticamente.

**Trocar de cliente:** finalize ou registre o estado da frente, encerre o escritor atual e abra o outro cliente no mesmo projeto. Peça que leia `AGENTS.md`, `CLAUDE.md` e o relato atual. Não opere dois escritores no mesmo checkout.

O teste opcional `tests/smoke_clients.py` usa os clientes reais com configuração temporária: valida descoberta de skills/hooks/configuração no Codex e leitura de MCP pendente de aprovação no Claude. Não executa uma conversa de modelo, plugins reais ou chamadas MCP. Rode com Python 3.11+ e os caminhos dos executáveis:

```bash
python3 tests/smoke_clients.py --codex /caminho/codex --claude /caminho/claude
```

No Windows, use os `.exe` reais, não os wrappers `.ps1`/`.cmd` do npm. O teste termina seus processos e mantém sua configuração pessoal fora da fixture.

<a id="operar-pt"></a>

## <img src="../assets/gema-esmeralda.svg" height="24" alt=""> Como operar: da ideia à entrega

Este é o rito manual recomendado para a versão atual. Os papéis podem ser exercidos por uma pessoa com agentes; PM e tech lead ainda não são agentes provisionados pelo setup.

| Passo | Responsável | Registro e condição de saída |
|---|---|---|
| Definir | PM / dono do produto | Problema, usuário, resultado esperado, restrições e critérios de aceite. |
| Desenhar | Tech lead | Contexto existente, decisão técnica, riscos, design system e pequenas entregas testáveis. |
| Executar | Implementador | Uma frente por checkout; usar as skills pertinentes, registrar as realmente usadas e verificar cada entrega. |
| Revisar | Revisor | Código, testes, documentação, segurança e evidências confrontados com os critérios de aceite. |
| Publicar | Responsável pela publicação | Alvo, autorização exigida pelo projeto, rollback e verificação do resultado no ambiente. |
| Retomar | Próxima sessão | Estado atual, links, resultados, bloqueios e próximo passo escritos antes de encerrar. |

Para cada entrega, mantenha um relato em `docs/relatorios/` e evidências leves em `docs/medicoes/`, conforme `CLAUDE.md`. Crie as pastas quando usadas. O relato deve conter: tema e identificador, objetivo, status em desenvolvimento, status em produção com evidência, decisões, arquivos/commits, testes, agentes/skills/MCPs necessários e os efetivamente usados, pendências e links para relatos relacionados. Não registre prompts com segredos nem saídas brutas sensíveis.

Para retomar, peça ao agente que leia as instruções e o último relato da frente antes de modificar arquivos. Atualize links e estado ao concluir. Esse registro permite continuidade hoje; a organização automática em vault e seus índices será uma entrega posterior. Uma ferramenta disponível não concede permissão para usá-la em qualquer ambiente.

<a id="manutencao-pt"></a>

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Falhas, repetição e manutenção

| Situação | Comportamento e próximo passo |
|---|---|
| Reexecutar | Preserva arquivos existentes; renderiza o nome só nos guias recém-copiados. As regras finais de ignore não crescem em repetições do mesmo modo sem mudanças. |
| `--force` | Substitui os templates gerenciados, inclusive configurações. Revise o diff antes de usar. Nunca substitui `.env` nem as regras existentes de `.gitignore`. |
| Argumento inválido | Sai com código 2, antes de copiar arquivos. |
| Falha de preflight | Sai com código não zero; resolva dependências, caminhos, manifesto ou `.env` rastreado e tente novamente. |
| Humanizer divergente ou modificado | Preserva a instalação do usuário e interrompe. Compare com o commit do manifesto e decida manualmente como guardar suas mudanças; o setup não executa reset. |
| Download/checkout falhou | Não ativa o diretório incompleto da skill. Corrija acesso/rede e repita. Arquivos de projeto já copiados permanecem. |
| Plugin falhou | Informa marketplace ou instalação e sai com código não zero. As etapas anteriores permanecem; corrija a causa e reexecute. |
| Plugins pulados | `--sem-plugins` ou ausência de `claude` são informados. Impeccable e skills sem origem instalável exigem instalação manual. |

O commit de humanizer é verificado. As versões e revisões de marketplace em `skills-lock.json` são um inventário, ainda não um lock aplicado pelo instalador. `humanizer-ptbr` existente é preservada sem atualização automática. Um setup bem-sucedido não comprova que todos os plugins opcionais, hooks ou MCPs funcionam no seu cliente.

Para testar o instalador no clone do harness (Python 3.11+ para a suíte):

```bash
python3 -m unittest discover -s tests -v
bash -n setup.sh
git diff --check
```

Os testes usam Git local e simulam chamadas de rede/plugins, com um diretório de usuário temporário. Não acessam MCPs reais. Veja a [matriz de verificação](../README.md#verificacao).

<img src="../assets/vidro.svg" alt="" width="100%">

<a id="english"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Before you start

This guide covers the current installer and manual adoption. The indexed vault, personalizer, automated migration audit and Graphify/claude-mem integrations are [planned](superpowers/specs/2026-10-01-youngcrow-foundation-design.md), not created by setup.

Use Linux Bash or Windows Git Bash with working `bash --version`, `git --version` and `python3 --version` in that terminal. If Windows opens the Microsoft Store for `python3`, configure the installed Python on Git Bash's PATH first. These commands are not native PowerShell commands.

Setup defaults to `--client both`; select `--client claude` or `--client codex` for one host. Common rules stay in `CLAUDE.md` and `AGENTS.md`. Claude skills go under `~/.claude/skills/`; Codex skills go in the project's `.agents/skills/`. Downloaded copies are ignored by Git, so run setup in every new clone/worktree. Claude uses `.mcp.json` and `.claude/settings.json`; Codex uses `.codex/config.toml` and `.codex/hooks.json`.

Claude marketplace plugins are installed when `claude` is available, unless `--no-plugins` is passed. Codex-only mode never calls Claude; install Codex plugins separately through its catalog. Skills still install with `--no-plugins`, and humanizer requires GitHub access. Project Git cannot undo user-level installations. Run one installation per target at a time. On Windows, Codex's optional impeccable hook needs `python` and, if impeccable is installed, `bash` on the client's PATH.

**Navigation:** [new repo](#new-en) · [existing repo](#migrate-en) · [daily operation](#operate-en) · [maintenance](#maintenance-en).

<a id="new-en"></a>

## <img src="../assets/gema-rubi.svg" height="24" alt=""> First setup: a new repository

1. Clone the harness next to your future product directory. Do not target the harness clone itself.

   ```bash
   git clone https://github.com/Matheusrpc/YoungCrowHarness.git
   bash YoungCrowHarness/setup.sh my-project --client both --name "My Project" --no-plugins
   cd my-project
   git init
   git check-ignore --no-index .env
   git ls-files -- .env
   ```

   The ignore check must print `.env`; the tracked-files check must be empty. Setup prepares the ignore rule but does not initialize Git. Omit `--no-plugins` to install marketplace plugins as well.

2. Fill in the project rules in `CLAUDE.md` and `AGENTS.md`: objective, real test/build commands, write boundaries, environments, publication authorization and rollback. For English, use `docs/CLAUDE.en.md` as your `CLAUDE.md`. Resolve all `<fill in>` placeholders. Document the product's existing design system.

3. Review `.mcp.json` for Claude and `.codex/config.toml` for Codex, plus the selected hooks. Remove unused servers and replace sample URLs. Codex examples start with `enabled = false`; configure authentication before enabling them. Copying `.env` does not load variables into either client automatically. Keep credentials local.

4. Review the files and commit only explicit reviewed paths, excluding `.env`. Open the project in Codex or run `claude` there. Start with a small task and require test evidence before accepting it.

<a id="migrate-en"></a>

## <img src="../assets/gema-ambar.svg" height="24" alt=""> First setup: adopt an existing repository

1. Inspect `git status`, deliberately save current work and create an adoption branch. Review secrets before committing anything.

   ```bash
   git status --short
   git switch -c chore/adopt-youngcrow
   git ls-files -- .env
   ```

   A tracked `.env` blocks setup. Resolve it first; removing it from the index does not erase history or repair exposed credentials.

2. Inventory architecture, tests, working commands, design system, existing instructions, skills, MCPs, hooks and documents. Record what must be preserved and the gaps. Setup does not perform this audit automatically.

3. With the harness clone in a sibling folder, run without `--force`:

   ```bash
   bash ../YoungCrowHarness/setup.sh . --client both --name "My Product" --no-plugins
   git diff --stat
   git diff
   git status --short
   git check-ignore --no-index .env
   ```

4. Compare preserved files with the harness templates and reconcile them manually. Preserve product decisions and commands. Setup preserves existing files byte for byte and appends env/local-download protection to `.gitignore`. It does not semantically merge guides, hooks or MCP configuration, or convert a customized `.mcp.json` into TOML. Reconcile the required entries in `.codex/config.toml` yourself. Also inspect new untracked files, which `git diff` does not display.

5. Run the preexisting tests/build, verify client hooks and MCPs, record before/after evidence and remaining gaps, then deliver adoption as a small reviewed change.

**Suggested first task:** “Read AGENTS.md and CLAUDE.md, inventory the code and existing harness, identify the design system and run available checks. Record evidence, gaps and a proposal for small adoption deliveries. Preserve existing decisions and follow the project's production authorization policy.”

## <img src="../assets/gema-turquesa.svg" height="24" alt=""> Check each client

**Claude Code:** launch `claude` in the project root. Check humanizer skills in the `/` menu, servers in `/mcp` and hooks in `/hooks`. Approve only the configured project servers. The optional impeccable hook does nothing if its executable is absent; marketplace installation alone does not guarantee that executable is present at the configured path.

**Codex:** open the project in the app or CLI, review project trust, then check `/skills` or the skill selector and `/mcp` in the CLI. Local configuration needs project trust; hooks also need explicit trust before execution. Maintain matching server URLs, authentication and permissions in both MCP files yourself. Setup does not weaken the sandbox or approve tools automatically.

When switching clients, save the workstream state, end the current writer, then ask the next client to read `AGENTS.md`, `CLAUDE.md` and the current report. Use one writer per checkout.

Optional real-client check (Python 3.11+): `python3 tests/smoke_clients.py --codex /path/to/codex --claude /path/to/claude`. On Windows use actual `.exe` files. It checks Codex skill/hook/config discovery and Claude MCP configuration pending approval, in temporary configuration. It makes no model calls or MCP connections, does not run real plugins, and terminates its processes.

<a id="operate-en"></a>

## <img src="../assets/gema-esmeralda.svg" height="24" alt=""> Daily operation: idea to delivery

The current workflow is manual. One person can fill several roles with agents; setup does not provision PM or tech lead agents.

| Step | Owner | Required record |
|---|---|---|
| Define | PM / product owner | Problem, user, intended outcome, constraints and acceptance criteria. |
| Design | Tech lead | Existing context, technical decision, risks, design system and small testable deliveries. |
| Build | Implementer | One workstream per checkout; appropriate skills, actual capabilities used and checks for each delivery. |
| Review | Reviewer | Code, tests, documentation, security and evidence against acceptance criteria. |
| Publish | Publication owner | Target, required authorization, rollback and observed result in the environment. |
| Resume | Next session | Current state, links, results, blockers and next step saved before closing. |

Create delivery reports in `docs/relatorios/` and lightweight evidence in `docs/medicoes/` as needed, following `CLAUDE.md`. Include a topic identifier, objective, development status, production status with evidence, decisions, files/commits, tests, required versus actually used agents/skills/MCPs, unresolved work and links to related reports. Keep sensitive logs and secrets out.

At the next session, read the project instructions and latest workstream report before editing. Update links and state when finished. Automatic vault organization and indexes will follow in a later delivery. Tool availability does not grant authorization for every environment.

<a id="maintenance-en"></a>

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Failures and maintenance

Repeated runs preserve existing files and render the project name only in newly copied guides. `--force` replaces managed templates/configurations, but preserves `.env` and existing ignore rules. Review changes before using it.

Invalid arguments exit with code 2. Dependency, path, manifest, tracked-env and divergent-skill checks fail before project copies. Existing humanizer must be a clean repository at the manifest commit; changes are preserved and require your decision. Failed downloads/checkouts never activate the incomplete skill. Plugin failures identify their stage and return nonzero. Earlier successful steps remain in place; resolve the cause and retry.

Skipped plugins are reported for `--no-plugins` or missing `claude`. Impeccable and skills without an installable source require manual installation. Existing humanizer-ptbr is preserved without automatic updates. Humanizer's commit is verified; marketplace revisions/versions remain inventory information, not enforced locks. Successful setup does not verify optional plugins, hooks or real MCP access.

Run checks from the harness clone with Python 3.11+:

```bash
python3 -m unittest discover -s tests -v
bash -n setup.sh
git diff --check
```

Tests use local Git, simulated network/plugin calls and an isolated temporary home. See the [verification matrix](../README.md#verification).

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Referências oficiais / Official references

- [Codex skills](https://learn.chatgpt.com/docs/build-skills): descoberta no projeto / project discovery.
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli): TOML e confiança / TOML and trust.
- [Codex hooks](https://learn.chatgpt.com/docs/hooks): descoberta, confiança e comandos Windows / discovery, trust and Windows commands.
- [Claude skills](https://code.claude.com/docs/en/skills): skills do usuário e projeto / user and project skills.

<p align="center">
  <img src="../assets/assinatura.svg" alt="☧ Ora et labora ☧ et coda" width="100%">
</p>
