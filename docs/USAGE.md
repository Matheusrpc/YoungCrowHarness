<p align="center">
  <img src="../assets/titulo.svg" alt="YoungCrowHarness — guia de uso / usage guide" width="100%">
</p>

[← README](../README.md) · [Português](#portugues) · [English](#english)

<img src="../assets/vidro.svg" alt="" width="100%">

<a id="portugues"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Antes de começar

Este guia cobre o instalador, o vault de integrações e o especialista em fornecedores. O setup cria o índice geral, os índices de integrações/capacidades, a skill e a entrada nativa do agente para os clientes selecionados. Fornecedores, serviços e execuções são criados sob demanda.
A skill `personalizer` conduz entrevista e auditoria de adoção; seu comando cria os registros de produto, features, decisões e operação quando necessário. Sincronização automática Graphify/claude-mem e orquestração autônoma de papéis continuam [planejadas](superpowers/specs/2026-10-01-youngcrow-foundation-design.md).

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
| Skill integrate-from-docs | `.claude/skills/integrate-from-docs/` | `.agents/skills/integrate-from-docs/` |
| Skill personalizer | `.claude/skills/personalizer/` | `.agents/skills/personalizer/` |
| Agente integration-specialist | `.claude/agents/integration-specialist.md` | `.codex/agents/integration-specialist.toml` |
| MCP | `.mcp.json` | `.codex/config.toml` |
| Hooks | `.claude/settings.json` | `.codex/hooks.json` |
| Plugins | Marketplace Claude, se instalado | Catálogo do Codex, instalação manual |

`--sem-plugins` pula os plugins do Claude; as skills dos clientes selecionados continuam sendo instaladas e humanizer precisa acessar o GitHub. Em modo Codex, nenhuma instalação de Claude é executada. O Git do projeto não desfaz alterações no usuário. As cópias locais de humanizer e humanizer-ptbr no Codex ficam ignoradas pelo Git: cada clone ou worktree novo precisa executar o setup. Skills próprias do produto podem ser versionadas separadamente, conforme a política de ignore do projeto.

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

Para retomar, peça ao agente que leia as instruções e o último relato da frente antes de modificar arquivos. Para integrações, comece em `vault/index.md` e siga fornecedor → serviço → execução. Atualize links e estado ao concluir. Uma ferramenta disponível não concede permissão para usá-la em qualquer ambiente.

<a id="personalizer-pt"></a>

## <img src="../assets/gema-ambar.svg" height="24" alt=""> Personalizar e retomar

Depois do setup, abra o Claude ou Codex na raiz do produto. Use `/personalizer` no Claude ou `$personalizer` no Codex e informe a ideia ou o objetivo da adoção. O agente lê o que já existe e pergunta pelas decisões que faltam. Não precisa haver um plano completo para começar.

> Use personalizer para adaptar este projeto à minha ideia: [descreva]. Preserve as convenções e o design existentes. Registre respostas e dúvidas no vault, personalize os guias e prepare uma primeira feature pequena. Produção fica fora deste pedido.

O modo `new` parte de uma ideia; `existing` inclui leitura do código, instruções, testes, skills/MCPs/hooks, documentação e design. Essa auditoria é conduzida pelo agente, com evidências registradas. O comando abaixo apenas prepara os arquivos:

```bash
python3 scripts/personalize.py init --mode new --run descoberta-inicial
# Para adoção de código existente, use --mode existing.
```

O índice `vault/product/index.md` leva ao perfil, plano de adoção e entrevistas. No modo existente, também leva a `audit.md`. O modo fica em `vault/product/onboarding.json`; retome com o mesmo modo e ID de entrevista. Se os registros divergirem, reconcilie o contexto antes de mudar de modo. Repetir o comando preserva as notas.

Peça uma pausa quando precisar. A skill salva respostas, fontes, dúvidas e a próxima pergunta. Em outra sessão, diga “retome personalizer por `vault/product/index.md`”. Um orçamento desconhecido pode bloquear hospedagem sem impedir uma entrega local independente.

Com escopo e aceite definidos, prepare a primeira feature:

```bash
python3 scripts/personalize.py feature --slug agendamento --run primeira-entrega
```

O microíndice da feature reúne contexto e estados; `delivery.md` contém a divisão em entregas; `runs/` guarda mudanças, testes, revisão, capacidades usadas e próximo passo. Linke decisões e integrações existentes, acrescentando referências de volta. O [fluxo no README](../README.md#processo-pt) mostra a passagem entre responsáveis e as decisões de publicação.

O agente adapta os guias por edições pontuais e registra o diff em `adoption.md`; o CLI não substitui suas regras. Toda implementação atualiza README e uso afetado, com revisão `humanizer` e preservação do design. Publicação e custos precisam estar no escopo autorizado. PM/Tech Lead são papéis do rito, e memória externa continua separada da gravação no vault.

<a id="integracoes-pt"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Documentar e executar integrações

1. Execute o setup normalmente para um repo novo ou siga a migração acima. Ele instala `scripts/integrations.py`, o vault e a skill compartilhada em `skills/integrate-from-docs/`. A skill especializada é versionável no projeto; humanizer e humanizer-ptbr continuam downloads locais. Os índices existentes do vault são preservados **mesmo com `--force`**. Se já existirem, acrescente os links para integrações e capacidades ao seu índice geral; mescle entradas úteis de capacidades. O primeiro `init` também acrescenta a navegação de integrações sem apagar o conteúdo.

2. Abra o cliente na raiz do produto e peça:

   > Use integration-specialist com integrate-from-docs para integrar [serviço] de [fornecedor] na frente [feature], em desenvolvimento. Consulte [URL oficial], confira o SDK instalado, implemente e teste. Registre fontes, decisões, capacidades usadas e pendências no vault.

   A skill pode ser invocada diretamente como `/integrate-from-docs` no Claude ou `$integrate-from-docs` no Codex. Reinicie a sessão após instalar novas entradas. Se o cliente não suportar agentes personalizados, use a skill na sessão principal, preservando um único escritor. Não habilite permissões extras apenas para obter a descoberta.

3. Para preparar notas manualmente, na raiz do produto:

   ```bash
   python3 scripts/integrations.py init --provider example --service payments --run first-contract
   ```

   Troque os slugs pelo fornecedor, serviço e execução reais. Use um novo ID a cada execução; repetir o ID retoma os mesmos arquivos. A navegação fica `vault/index.md` → integrações → fornecedor → serviço → fontes/implementação/operação/execuções. Versione `vault/project.json` com as notas: clones do mesmo produto compartilham identidade; produtos independentes precisam de um vault novo.

4. Ao concluir, confira fontes oficiais e versões, links de código/testes, estados distintos de desenvolvimento e produção, capacidades previstas/usadas, evidências e próxima ação. Abra `vault/` no Obsidian para navegar pelas mesmas notas. A próxima sessão deve recuperar o trabalho pelos índices, sem depender deste chat.

5. Para preparar o envio a uma memória opcional:

   ```bash
   python3 scripts/integrations.py export --provider example --service payments
   ```

   A saída contém IDs, caminhos, conteúdo e hashes de revisão. **É um envelope YoungCrow, não um importador nem sincronização automática.** Revise os dados antes de transmitir; não há remoção automática de segredos. A [referência da skill](../skills/integrate-from-docs/references/memory.md) orienta verificar ferramentas instaladas, isolamento do projeto, atualização sem duplicatas e confirmação da indexação. Sem adaptador compatível, registre `pending`/`unsupported` e continue recuperando pelo vault. Esta entrega não instala Graphify nem claude-mem.

<a id="manutencao-pt"></a>

### Autoria de commits e PRs

O projeto configura `.claude/settings.json` com `attribution.commit` e `attribution.pr` vazios,
conforme a [documentação do Claude](https://code.claude.com/docs/en/settings-reference#attribution).
Os guias de Claude e Codex também orientam não acrescentar assistentes como coautores. Preserve a
identidade Git de quem realizou o trabalho e os créditos de terceiros. O setup preserva configurações
existentes: em um projeto já adotado, ajuste apenas essas duas propriedades no JSON e mantenha os
demais campos. Remover atribuições de commits antigos exige uma alteração separada do histórico.

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Falhas, repetição e manutenção

| Situação | Comportamento e próximo passo |
|---|---|
| Reexecutar | Preserva arquivos existentes; renderiza o nome só nos guias recém-copiados. As regras finais de ignore não crescem em repetições do mesmo modo sem mudanças. |
| `--force` | Substitui os templates gerenciados, inclusive configurações. Revise o diff antes de usar. Preserva notas do vault, `.env` e regras existentes de `.gitignore`. |
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

<a id="protection-pt"></a>

## <img src="../assets/gema-rubi.svg" height="24" alt=""> Proteger a branch principal

No YoungCrowHarness, o ruleset `Protect main` está ativo para `main`, sem atores autorizados a
ignorar as regras. Ele exige PR, resolução das conversas de revisão e o check `installer` emitido
pelo GitHub Actions, com a branch atualizada em relação à base. Também bloqueia exclusão e force
push. O arquivo [main.json](../.github/rulesets/main.json) registra a configuração; editar esse
arquivo sozinho não altera o GitHub. Consulte o estado atual em **Settings → Rules → Rulesets**.

Para adotar a proteção em outro repositório:

1. Ative seu workflow de testes e confirme o nome do check em um PR. Aqui ele se chama `installer`.
2. Em **Settings → Rules → Rulesets**, crie um ruleset de branch, selecione `main` e marque **Active**.
3. Deixe a lista de bypass vazia. Ative **Restrict deletions**, **Block force pushes**,
   **Require a pull request before merging** e a resolução das conversas.
4. Em **Require status checks to pass**, selecione o check real, sua origem GitHub Actions e
   **Require branches to be up to date before merging**. Um nome inexistente impedirá o merge.
5. Com um único mantenedor, mantenha zero aprovações obrigatórias. Quando houver outro revisor com
   escrita, exija uma aprovação e invalide aprovações antigas após mudanças. O autor não aprova o
   próprio PR. Revisão de IA continua útil, mas não substitui essa aprovação humana independente.

O fluxo diário passa a ser branch → PR → testes → revisão → merge. Até o administrador segue as
regras; ele ainda pode editá-las nas configurações. Esta proteção não verifica sozinha segredos,
vulnerabilidades ou a qualidade dos testes. O setup local não cria regras remotas.

Referência: [regras disponíveis no GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

<a id="english"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Before you start

This guide covers setup, the integration vault and vendor specialist. Setup installs the general, integration and capability indices, shared skill and native agent entries for the selected clients. Provider/service/run notes are created on demand.
The `personalizer` skill conducts discovery and adoption audits; its command creates product, feature, decision and operation notes on demand. Automatic Graphify/claude-mem synchronization and autonomous role orchestration remain [planned](superpowers/specs/2026-10-01-youngcrow-foundation-design.md).

Use Linux Bash or Windows Git Bash with working `bash --version`, `git --version` and `python3 --version` in that terminal. If Windows opens the Microsoft Store for `python3`, configure the installed Python on Git Bash's PATH first. These commands are not native PowerShell commands.

Setup defaults to `--client both`; select `--client claude` or `--client codex` for one host. Common rules stay in `CLAUDE.md` and `AGENTS.md`. Claude's humanizer skills go under `~/.claude/skills/`; Codex's go in the project's `.agents/skills/`. Those downloaded copies are ignored by Git, so run setup in every new clone/worktree. The integration skill is project-local and versionable in both clients. Claude uses `.mcp.json` and `.claude/settings.json`; Codex uses `.codex/config.toml` and `.codex/hooks.json`.

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

At the next session, read the project instructions and latest workstream report before editing. For integrations, follow `vault/index.md` → provider → service → run. Update links and state when finished. Tool availability does not grant authorization for every environment.

<a id="personalizer-en"></a>

## <img src="../assets/gema-ambar.svg" height="24" alt=""> Personalize and resume

After setup, open your client at the product root and invoke `/personalizer` in Claude or `$personalizer` in Codex. Describe the idea or adoption goal. The agent reads existing evidence and asks about missing decisions.

> Use personalizer to adapt this project to [idea]. Preserve its conventions and design, record answers and unknowns, adapt the guides and prepare one small feature. Production is outside this request.

```bash
python3 scripts/personalize.py init --mode new --run initial-discovery
# Use --mode existing when adopting an existing codebase.
```

The command prepares records; the agent performs the interview and audit. `vault/product/index.md` links profile, adoption plan and interview notes; existing mode adds `audit.md`. Resume with the recorded mode in `vault/product/onboarding.json` and the same interview ID. Repeated commands preserve notes; conflicting modes require reconciling the context.

When you pause, the skill saves confirmed answers, sources, open questions and the next question. A new session can resume from the product index. An unknown hosting budget need not block an independent local delivery.

```bash
python3 scripts/personalize.py feature --slug booking --run first-slice
```

The feature index links context and state, `delivery.md` defines small slices, and `runs/` records changes, checks, review, capabilities used and the next step. Crosslink canonical decisions and integrations. The [README process](../README.md#process-en) shows responsibilities and release decisions.

Guide adaptation uses targeted agent edits recorded in `adoption.md`; the CLI does not replace project rules. Every implementation updates README and affected usage docs with humanizer review, preserving the design. Publication and costs follow current authorization. PM/Tech Lead are process roles; external memory synchronization remains separate.

<a id="integrations-en"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Document and implement integrations

1. Run the new-project setup or migration steps above. Setup installs `scripts/integrations.py`, the vault and shared `skills/integrate-from-docs/`. Client discovery entries are project-local: `.claude/skills/integrate-from-docs/` and `.agents/skills/integrate-from-docs/`; native agents live in `.claude/agents/integration-specialist.md` and `.codex/agents/integration-specialist.toml`. Existing vault indices are preserved **even with `--force`**. For an existing vault, add integration/capability links to its general index and merge useful capability entries; `init` appends missing integration navigation without replacing prose.

2. Open the selected client in your product root and ask:

   > Use integration-specialist with integrate-from-docs to integrate [vendor/service] for [feature] in development. Read [official URL], check the installed SDK, implement and test. Record sources, decisions, capabilities used and remaining work in the vault.

   Invoke `/integrate-from-docs` in Claude or `$integrate-from-docs` in Codex. Restart after installing entries. If custom agents are unavailable, run the skill in the main session with one writer; do not grant extra permissions just for discovery.

3. To prepare notes manually:

   ```bash
   python3 scripts/integrations.py init --provider example --service payments --run first-contract
   ```

   Use real lowercase slugs and a new execution ID for each run; repeating the ID resumes existing files. Open `vault/` in Obsidian or follow relative links in GitHub. Commit `vault/project.json` with the notes; clones of one product keep its identity, independent products need a fresh vault.

4. Verify official sources/versions, code/test links, separate development/production states, planned/used capabilities, evidence and next action. A fresh session should recover those from the indices without the previous conversation.

5. `python3 scripts/integrations.py export --provider example --service payments` prints a YoungCrow envelope with IDs, paths, content and revision hashes. **This is not a vendor import format or automatic synchronization.** Review before transmission; no automatic secret redaction is performed. Follow the [memory reference](../skills/integrate-from-docs/references/memory.md) to check installed tools, project isolation, idempotency and confirmation. Without a compatible adapter, record `pending`/`unsupported` and use Markdown. Setup does not install Graphify or claude-mem.

<a id="protection-en"></a>

## <img src="../assets/gema-rubi.svg" height="24" alt=""> Protect the default branch

YoungCrowHarness has an active `Protect main` ruleset for `main`, with no bypass actors. It requires
a PR, resolved review conversations and the `installer` check from GitHub Actions, with the branch
up to date against its base. Deletion and force pushes are blocked. The
[main.json](../.github/rulesets/main.json) file records the configuration; changing that file alone
does not update GitHub. Check the current state in **Settings → Rules → Rulesets**.

To adopt this protection in another repository:

1. Enable your test workflow and confirm its check name on a PR. This repository uses `installer`.
2. In **Settings → Rules → Rulesets**, create a branch ruleset targeting `main` and choose **Active**.
3. Leave the bypass list empty. Enable **Restrict deletions**, **Block force pushes**,
   **Require a pull request before merging** and review conversation resolution.
4. Under **Require status checks to pass**, choose the actual check, its GitHub Actions source and
   **Require branches to be up to date before merging**. A nonexistent check name will block merges.
5. With one maintainer, keep required approvals at zero. Once another reviewer has write access,
   require one approval and dismiss stale approvals after changes. Authors cannot approve their own
   PRs. AI review remains useful but does not replace this independent human approval.

The daily path is branch → PR → tests → review → merge. Administrators follow the rules too, though
they can still edit them in settings. Branch protection alone does not check secrets, vulnerabilities
or test quality. Local setup does not create remote rules.

Reference: [available GitHub rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

<a id="maintenance-en"></a>

### Commit and PR authorship

The project sets `attribution.commit` and `attribution.pr` to empty strings in `.claude/settings.json`,
following [Claude's documentation](https://code.claude.com/docs/en/settings-reference#attribution).
Claude and Codex guides also instruct agents not to add assistants as coauthors. Preserve the Git
identity of the person doing the work and third-party credits. Setup preserves existing settings:
in an adopted project, edit only those two JSON properties and keep the remaining fields. Removing
attribution from older commits requires a separate history change.

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Failures and maintenance

Repeated runs preserve existing files and render the project name only in newly copied guides. `--force` replaces managed templates/configurations, but preserves vault notes, `.env` and existing ignore rules. Review changes before using it.

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
