<p align="center">
  <img src="../assets/titulo.svg" alt="YoungCrowHarness — guia de uso / usage guide" width="100%">
</p>

[← README](../README.md) · [Português](#portugues) · [English](#english)

Consulte os [fluxos visuais de uso](../README.md#processo-pt) para localizar sua etapa:
começar do zero, migrar um projeto, operar uma entrega, incorporar fontes ou retomar a memória. O [processo completo](PROCESS.md#portugues)
detalha decisões, pausas e retomada.

See the [usage diagrams](../README.md#process-en) for new projects, adoption, daily work, source intake and memory retrieval.
The [complete process](PROCESS.md#english) includes decisions, pauses and resumption.

Catálogo de capacidades: `python scripts/capabilities.py list --json` mostra finalidade e clientes;
`python scripts/capabilities.py describe retrieve-memory --json` apresenta o contrato. A leitura
aceita manifestos 2 e 3, não inicializa o vault e não instala capacidades. Versão declarada e hash
de arquivos não comprovam execução. Use a skill `govern-capabilities` para conduzir o procedimento.

Capability catalog: `python scripts/capabilities.py list --json` shows purpose and clients;
`python scripts/capabilities.py describe retrieve-memory --json` presents the contract. Reading
supports manifest versions 2 and 3, without initializing the vault or installing capabilities.
Declared versions and file hashes do not prove execution.

Auditoria / Audit: `python scripts/capabilities.py audit --client both --json`.
Use `claude` ou `codex` para uma instalação de cliente único. Estados: `matched` (correspondência local),
`changed`, `missing`, `unverified`, `unsupported` e `failed`. Código 0 exige correspondência dos requisitos
obrigatórios; 1 indica pendência obrigatória; 2 indica entrada/configuração inválida ou ilegível.
O relatório separa conteúdo, configuração e execução. Inventário externo, runtime instalado, aprovação
nativa e configurações globais permanecem não verificados por essa leitura. Valores de configuração
potencialmente secretos são omitidos, inclusive em erros. A auditoria não instala nem corrige arquivos.

Use `claude` or `codex` for a single-client installation. States: `matched` (local correspondence),
`changed`, `missing`, `unverified`, `unsupported` and `failed`. Exit 0 requires matching mandatory
capabilities; 1 means a mandatory capability is pending; 2 means invalid or unreadable input/configuration.
Content, configuration and execution are separate. External inventory, installed runtimes, native
approval and global configuration remain unverified. Potentially secret configuration values are
omitted, including errors. Auditing never installs, connects to MCPs or repairs files.

Revisão privada / Private review:

```bash
python scripts/capabilities.py review --id retrieve-memory --client codex --json
python scripts/capabilities.py review --check DIGEST --json
```

Troque `DIGEST` pelo valor retornado. A revisão exige `vault/project.json` válido e as pastas
`vault/local`, `.operacao-local/docling` (lock) e `.operacao-local/capabilities` ignoradas pelo Git.
Prepare a identidade pelo personalizer e as regras pelo setup; `review` não as corrige. Pacotes ficam
em `.operacao-local/capabilities/reviews/`. A proposta aponta campos e hashes do contrato para comparação
manual; argumentos, headers e configurações privadas não são copiados. Mudança de entrada exige nova
revisão. O hash verifica bytes, não aprovação humana. Aplicação segue a autorização real do operador.

Replace `DIGEST` with the returned value. Review requires a valid `vault/project.json` and Git-ignored
`vault/local`, `.operacao-local/docling` (lock) and `.operacao-local/capabilities` directories. Initialize
identity with personalizer and ignore rules with setup; `review` does not repair them. Bundles live in
`.operacao-local/capabilities/reviews/`. Proposals reference contract fields and hashes for manual comparison;
arguments, headers and private configurations are not copied. Changed inputs require a new review.
Hashes verify bytes, not human approval. Applying changes follows the operator's actual authorization.

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
| Skill ingest-source | `.claude/skills/ingest-source/` | `.agents/skills/ingest-source/` |
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

<a id="vault-check-pt"></a>

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Conferir a organização do vault

O validador aceita `vault/local/index.md` como segunda entrada, quando existir. Notas locais podem
referenciar notas compartilhadas; notas compartilhadas não podem apontar para `vault/local/` ou
`.operacao-local/docling/`. A ocorrência `private_reference` pede remover ou revisar essa referência
antes de publicar. O ignore não criptografa arquivos nem substitui backup.

Execute na raiz do produto após atualizar as memórias e antes de encerrar uma entrega:

```bash
python3 scripts/vault.py check
python3 scripts/vault.py check --json
```

O setup instala esse comando para Claude Code e Codex. Para um projeto que já usa o harness,
atualize o clone de origem e repita o setup sem `--force`: o novo arquivo será copiado e as notas
existentes serão preservadas. O comando usa Python e o helper `scripts/integrations.py`, sem serviços externos.

A saída lista arquivo, código do problema e orientação. O código de saída é `0` quando as checagens
passam, `1` quando há problemas no vault e `2` para argumentos inválidos. `--json` fornece os mesmos
diagnósticos em formato estruturado, sem incluir o corpo das notas. Nenhum arquivo é corrigido ou criado.

Cada nota Markdown precisa dos campos `id`, `type`, `title`, `origin`, `updated` e `index` no cabeçalho
entre linhas `---`. Os comandos do personalizer e de integrações já os criam. Os valores são textos
em uma linha, sem aspas ou entre aspas simples/duplas; `updated` usa data ISO, como `2026-10-01`,
ou timestamp ISO. Outros campos do Obsidian podem continuar no cabeçalho e não são avaliados.
Notas antigas sem esses campos são apontadas para revisão; não recebem identidades novas automaticamente.

| Problema | Como resolver |
|---|---|
| `metadata` / `duplicate_id` | Complete os campos indicados. Preserve a identidade ao mover uma nota; notas distintas precisam de IDs distintos. |
| `invalid_index` / `index_cycle` | Faça `index` apontar para um `index.md` do vault. A cadeia precisa chegar a `vault/index.md`, que aponta para si mesmo. |
| `missing_index_link` / `unreachable` | Acrescente o link da nota ao microíndice declarado e ligue esse microíndice à navegação geral. |
| `broken_link` / `ambiguous_link` | Corrija o destino ou o rótulo de referência. Em wikilinks ambíguos, use o caminho completo dentro do vault. |
| `unsafe_path` / `unsafe_link` / `unreadable` | Confira permissões, UTF-8 e tipos dos arquivos. Links simbólicos, junctions, hardlinks e caminhos fora do projeto são recusados. |
| `missing_vault` / `missing_root_index` | Instale ou recupere o vault e seu índice geral antes de conferir a navegação. |

São conferidos links Markdown para arquivos, imagens, referências por rótulo e wikilinks como
`[[features/pagamentos/index|Pagamentos]]`. Wikilinks com caminho partem da raiz do vault;
`./` e `../` partem da nota atual. Um nome sem caminho pode encontrar uma nota de nome único.
Links Markdown partem da pasta da nota e podem apontar para código ou documentação dentro do projeto.
Prefira links Markdown relativos para navegar também no GitHub.

Exemplos cercados por três ou mais crases/tils, código inline, comentários HTML e a pasta `.obsidian`
ficam fora da checagem. Linhas indentadas são conferidas, inclusive sublistas: use cercas nos exemplos
de código para evitar diagnósticos sobre links fictícios. URLs externas não são acessadas;
fragmentos `#seção` não são validados. O comando verifica
a estrutura dos campos obrigatórios e os formatos de link descritos, sem interpretar todo o YAML
ou toda a sintaxe Markdown. Também não confirma a veracidade de relatos, ausência de segredos,
resultados de testes ou estado de produção. Execute com o vault sem alterações concorrentes.
Use rótulos simples nos links: rótulos com colchetes internos e aberturas escapadas como
`\[exemplo](arquivo.md)` ainda exigem conferência manual.

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

   A saída contém IDs, caminhos, conteúdo e hashes de revisão. **É um envelope YoungCrow, não um importador nem sincronização automática.** Revise os dados antes de transmitir; não há remoção automática de segredos. A [referência da skill](../skills/integrate-from-docs/references/memory.md) orienta verificar ferramentas instaladas, isolamento do projeto, atualização sem duplicatas e confirmação da indexação. Sem adaptador compatível, registre `pending`/`unsupported` e continue recuperando pelo vault. O exportador não instala provedores. Para o Graphify opcional, use o [roteiro de memória](#memoria-pt); claude-mem continua planejado.

<a id="manutencao-pt"></a>

### Autoria de commits e PRs

O projeto configura `.claude/settings.json` com `attribution.commit` e `attribution.pr` vazios,
conforme a [documentação do Claude](https://code.claude.com/docs/en/settings-reference#attribution).
Os guias de Claude e Codex também orientam não acrescentar assistentes como coautores. Preserve a
identidade Git de quem realizou o trabalho e os créditos de terceiros. O setup preserva configurações
existentes: em um projeto já adotado, ajuste apenas essas duas propriedades no JSON e mantenha os
demais campos. Remover atribuições de commits antigos exige uma alteração separada do histórico.

<a id="docling-pt"></a>

<a id="fontes-pt"></a>

### Usar documentos no Claude Code e no Codex

O setup copia `ingest-source` e o hook `UserPromptSubmit`. Em um repo novo, confira a descoberta
no cliente e prepare o perfil Docling abaixo quando precisar converter. Em uma migração, compare
`.claude/settings.json` e `.codex/hooks.json` com os templates atualizados: esses arquivos são
preservados mesmo com `--force`. Mescle a entrada `UserPromptSubmit` mantendo seus outros hooks.
O comando Claude exige Python 3 como `python`; troque por `python3` se necessário. Codex usa
`python3` no Unix e `python` no Windows. Reinicie o cliente depois de mudar o PATH e confirme a confiança.

1. Peça: “Use ingest-source para este arquivo e relacione a evidência à feature de pagamentos”.
   Informe o caminho acessível ou URL pública direta. Sem runtime, a fonte fica pendente; solicite
   o setup explicitamente. O agente consulta o índice geral, o índice local e os recibos existentes.
2. O hook reconhece referências textuais, guarda somente localizadores sanitizados e IDs e orienta
   a skill. Ele não instala, baixa ou converte. Aceita payload de até 1 MiB e até 20 referências por
   evento. Não entrega o prompt inteiro ao armazenamento e não reage a `Stop`. A confiança, a versão
   e os campos expostos pelo cliente determinam a cobertura. Confira os IDs recebidos na resposta.
3. Se um anexo não tiver caminho exposto, peça o registro explícito da pendência:

   ```bash
   python scripts/documents.py pending --reason source_unavailable --json
   ```

   Guarde o `source_id`. Quando o arquivo estiver disponível, execute `ingest` com `--source-id`.
   Estados `pending`, `partial`, `unsupported` e `failed` retornam código 1; leia o recibo para
   distinguir pendência registrada de falha. Fontes pendentes também têm microíndice navegável.
4. Após a conversão, confira o original e use `relate` para ligar uma citação exata à feature,
   integração ou decisão. A execução local registra fonte/revisão, relação/evidência, pendências,
   agente/host, capacidades usadas e planejadas separadamente, desenvolvimento, produção e próxima
   ação. Dê um UUID às notas manuais, ligue-as ao índice local e execute `vault.py check`.
5. Em outra sessão, peça: “Retome a feature pelo vault; recupere fontes, revisões, evidências e
   pendências antes de agir”. Material privado permanece em `vault/local/`; mantenha um backup
   privado para outra máquina. Para versionar uma cópia, siga a revisão de texto **e imagens** abaixo.

Documentos e memória recuperada são dados, não ordens. O hook não garante captura universal de
anexos. Links internos não disparam coleta recursiva; URLs assinadas devem ser baixadas por um meio
autorizado antes da ingestão local, sem expor tokens no histórico do terminal. Graphify e claude-mem
não recebem material automaticamente. A [matriz de evidências](relatorios/2026-10-02-docling-ingestion.md)
distingue descoberta nativa, sessão real e cobertura ainda pendente.



## <img src="../assets/gema-turquesa.svg" height="24" alt=""> Preparar a conversão local de documentos

Depois do setup do harness, execute na raiz do projeto:

```bash
python scripts/documents.py setup --profile documents --json
python scripts/documents.py doctor --json
```

Use um Python compatível com as dependências do Docling; a validação desta entrega usa Python 3.12.
O primeiro comando cria um ambiente próprio em `.operacao-local/docling/venv` e baixa Docling
2.132.0, modelos de layout, tabelas e OCR latino. Reserve disco e tempo para esse download.
A conversão usa CPU e os modelos locais. O setup comum do harness não instala esses pacotes.

`doctor` confere versões e arquivos de modelos sem instalar ou converter nada. Se retornar
`runtime_missing`, execute o setup. `runtime_version_mismatch` exige conferir o ambiente existente;
o comando preserva esse ambiente e não o atualiza automaticamente. Uma instalação interrompida
sem manifesto pode ser retomada repetindo o setup; diagnósticos ficam na área local.

O perfil inicial cobre PDF, DOCX, PNG/JPEG e HTML local, com teto de 100 MiB, 500 páginas e
30 minutos por conversão. Recursos externos referenciados no arquivo não são baixados.
Revise o texto extraído antes de usá-lo como evidência: uma imagem de página preservou a frase
de prova, mas uma faixa horizontal com o mesmo texto teve palavras fora de ordem. `ready`
indica que o processamento terminou; não certifica fidelidade ao original.

Para guardar uma fonte e retomar seu estado:

```bash
python scripts/documents.py ingest "caminho/arquivo.pdf" --json
python scripts/documents.py status --json
python scripts/vault.py check --json
```

O recibo informa `source_id`, revisão, tentativa, estado e caminho da nota. A fonte ganha um
microíndice em `vault/local/sources/`; os originais, recibos e extrações ficam em
`.operacao-local/docling/`. Repetir a mesma origem reutiliza a extração quando bytes e configuração
coincidem. Arquivos de origens diferentes mantêm identidades próprias, mesmo com conteúdo igual.
Uma extração sem manifesto de cache é preservada em `.operacao-local/docling/work/orphan-*`;
a próxima ingestão converte novamente. Não é preciso apagar o cache para retomar.

Na nota extraída, HTML, wikilinks e referências Markdown por rótulo ficam como texto legível.
Links inline HTTP(S) continuam clicáveis; imagens inline só apontam para ativos locais validados.

Use `ingest "arquivo" --source-id UUID --json` para atualizar uma fonte já registrada ou retomar
uma pendência pelo ID. Uma falha conserva a revisão válida anterior. Uma extração `partial` recebe
nota própria com aviso e continua disponível quando uma tentativa posterior termina. Notas editadas
manualmente são preservadas. `status` separa a revisão atual da última tentativa e não mostra o texto
ou o caminho original do documento. Falta de arquivo ou ambiente fica como `pending`; formato não
atendido retorna `unsupported`.

Para uma URL direta, use o mesmo comando:

```bash
python scripts/documents.py ingest "https://example.org/documento.pdf" --json
```

A aquisição aceita HTTP(S), até cinco redirecionamentos, 60 segundos no total e 100 MiB. O tipo
é conferido nos bytes recebidos. Cada conexão usa um IP previamente validado, mantendo a verificação
TLS do nome do servidor. Proxies e credenciais do ambiente não são usados. Recursos dentro de um
documento não iniciam downloads. Uma página reconhecida como reprodução de vídeo ou áudio fica
`pending`: forneça o arquivo ou uma transcrição acessível. A transcrição é uma fonte própria.

O localizador salvo omite query e fragmento. URLs completas diferentes mantêm IDs próprios por uma
chave opaca local; para renovar um link assinado da mesma fonte, informe `--source-id UUID`.
Não coloque links com tokens em comandos que ficarão no histórico: prefira baixar o arquivo pela
ferramenta autorizada e ingerir a cópia local. Os recibos não imprimem o link de acesso.

Destinos privados são recusados por padrão. Se o projeto precisar de um servidor interno, o operador
pode criar `.operacao-local/docling/acquisition.json` com `{"allowed_private_hosts":["docs.interno.example"]}`.
Isso autoriza somente os nomes exatos listados, inclusive em redirecionamentos; revise essa exceção.
Falhas de aquisição preservam a revisão anterior e indicam a próxima ação no recibo.

Há um escritor por projeto. Se um processo for encerrado à força, consulte
`python scripts/documents.py lock-status --json`. Somente com `owner_alive: false`, use
`python scripts/documents.py recover-lock --token UUID --json`, com o token informado, e repita a
ingestão. A recuperação recusa um processo ativo ou token diferente. Fechar uma sessão não apaga
os documentos locais; mantenha seu backup privado.

Para áudio e vídeo, disponibilize `ffmpeg` e `ffprobe` no PATH do cliente ou em
`.operacao-local/docling/bin/`. O setup verifica esses executáveis e registra seus hashes; não os
instala globalmente. A [página do FFmpeg](https://ffmpeg.org/download.html) indica distribuições por
plataforma. No Windows, a prova desta entrega usa os binários Gyan 9.0.2, com o checksum do fornecedor.

```bash
python scripts/documents.py setup --profile media --json
python scripts/documents.py doctor --profile media --json
python scripts/documents.py ingest "caminho/gravação.wav" --json
python scripts/documents.py ingest "caminho/vídeo.mp4" --json
```

O perfil cria `.operacao-local/docling/media/venv` e baixa o Whisper Base multilíngue para CPU.
Identificação de locutores está desativada. No Windows, seu extra opcional é omitido porque exige
compilação C++; transcrição e amostragem usam o pipeline nativo do Docling.
Os pacotes de mídia ficam separados dos documentos; uma falha nessa instalação conserva o ambiente
anterior. Isso ocupa espaço adicional. Depois de trocar FFmpeg/ffprobe, confira o diagnóstico antes
de recriar o perfil. O setup não aceita silenciosamente executáveis diferentes dos registrados.

Áudio aceita WAV, MP3, M4A, AAC, OGG e FLAC; vídeo aceita MP4, MOV, AVI, MKV e WEBM. Cada arquivo
tem teto de 500 MiB e 60 minutos. O conversor dispõe de até 30 minutos e amostra até 200 quadros,
normalmente a cada dez segundos. Formato aceito pelo pipeline não garante qualidade de transcrição.
Áudio é normalizado localmente antes do ASR; o idioma é detectado pelo modelo, sem tradução automática.

O recibo informa intervalos de transcrição e tempos dos quadros efetivamente obtidos. Ausência de áudio,
transcrição vazia, falha parcial ou limite de quadros aparece nos avisos e mantém estado `partial`.
Essas imagens não comprovam interpretação de todas as ações, textos ou telas de um vídeo. Um prazo
esgotado que impeça exportar conteúdo retorna `failed`; uma saída parcial exportável preserva sua nota.
O encerramento por prazo também termina os processos filhos. Confira transcrição e quadros antes de
usar a gravação como evidência.

Para ligar uma revisão a uma feature, decisão ou outra nota, use o ID do frontmatter de destino e
um trecho presente na extração:

```bash
python scripts/documents.py relate --source-id UUID_FONTE --revision REVISAO --target-id ID_NOTA --relation supports --evidence "trecho presente na extração" --json
```

As relações disponíveis são `supports`, `complements`, `contradicts`, `supersedes` e `used-in`.
O vínculo fica na área local e mantém a nota compartilhada intacta. A verificação confirma o trecho;
o sentido da relação precisa de revisão. `contradicts` começa como hipótese.

Para compartilhar uma fonte:

```bash
python scripts/documents.py prepare-review --source-id UUID_FONTE --revision REVISAO --json
python scripts/documents.py review-status --review-id UUID_REVISAO --json
python scripts/documents.py promote --review-id UUID_REVISAO --approved-digest DIGEST_APROVADO --json
```

O primeiro comando prepara uma cópia editável na área privada, com um ID público novo. Revise o
texto e cada imagem nessa pasta, removendo o que não pode sair do ambiente local. Depois de editar,
`review-status` fornece o digest atual e a lista de arquivos. Autorize essa cópia exata antes de
executar `promote`: conhecer o digest não equivale a ter autorização humana.

A promoção verifica todos os nomes e bytes, mantém avisos de extração parcial e recusa links para
arquivos privados ou caminhos absolutos. Cada cópia pode conter uma nota Markdown e imagens raster,
com teto de 2.000 arquivos e 500 MiB. HTML e autolinks fora de exemplos de código são recusados.
Use `[rótulo](destino)` sem envolver o destino em sinais de menor/maior.
O resultado entra em `vault/sources/`; não há `git add`, commit ou push automático.
Só depois disso uma feature compartilhada deve receber um link para a fonte publicada. O mapeamento
com a revisão original fica local. Mudanças posteriores no original não alteram a cópia preparada.

Esse processo não anonimiza o conteúdo: um nome dentro de um parágrafo ou de uma imagem depende da
revisão humana. Confira o diff e execute `vault.py check` antes de versionar.

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Falhas, repetição e manutenção

| Situação | Comportamento e próximo passo |
|---|---|
| Reexecutar | Preserva arquivos existentes; renderiza o nome só nos guias recém-copiados. As regras finais de ignore não crescem em repetições do mesmo modo sem mudanças. |
| `--force` | Substitui templates gerenciados. Preserva vault, `.env`, regras de `.gitignore`, manifesto, skills, agentes, `.mcp.json`, `.codex/config.toml` e hooks existentes. Compare e mescle; revise o diff. |
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

<a id="memoria-pt"></a>

## Memória: consultar notas selecionadas

Num projeto novo, conclua o setup e registre a primeira feature com `personalizer`. Numa migração, audite as notas existentes, preserve suas identidades e use `vault.py check` para reparar a navegação antes de selecionar. O setup mantém configurações de MCPs/hooks existentes; mescle as instruções necessárias sem substituí-las por inteiro.

Na raiz do projeto, escolha notas Markdown do vault que tenham UUID. Os índices existentes ajudam a localizar essas notas. A consulta não amplia a seleção sozinha.

```bash
python3 scripts/memory.py --root . index --note vault/local/features/pagamentos/index.md
python3 scripts/memory.py --root . query "pagamentos"
python3 scripts/memory.py --root . status
```

Troque o caminho pelo de uma nota existente. Repita `--note` para incluir outras notas. O limite inicial é 100 notas, 256 KiB por nota e 8 MiB no conjunto. O índice fica em `.operacao-local/memory/`, excluído do Git; notas e configurações dos clientes são preservadas. A primeira resposta traz até cinco referências. Abra as notas citadas para verificar decisões, publicação e próxima ação.

Mudança ou remoção de uma nota torna o retrato antigo obsoleto. A consulta lê as notas atuais da seleção e avisa que o índice precisa ser reconstruído. Use `rebuild` para reconstruir com as notas sobreviventes ou `index` para trocar a seleção. Sem seleção, o comando oferece os índices do vault para navegação. Graphify é opcional. Para instalá-lo neste projeto, execute o setup com Python 3.12:

```bash
python3.12 scripts/memory.py --root . setup-graphify
python3 scripts/memory.py --root . doctor
python3 scripts/memory.py --root . index --provider graphify --note vault/local/features/pagamentos/index.md
python3 scripts/memory.py --root . query "pagamentos"
```

No Windows, use `py -3.12` ou o caminho do Python 3.12 no primeiro comando, e `python` nos demais. A versão fixada é `graphifyy==0.9.73`, instalada em `.operacao-local/memory/runtime/venv`. O setup registra as versões resolvidas; `doctor` confere o ambiente sem reinstalar. Runtime ausente retorna `pending`, versão incompatível retorna `unsupported` e falha retorna `failed`. A consulta continua disponível pelo Markdown selecionado. Consultar Graphify requer escrita temporária em `.operacao-local/memory/runtime/`; num cliente restrito à leitura, confira os avisos de fallback.

O grafo representa links explícitos entre notas. Sua busca local combina termos e relações; a IA da sessão interpreta as evidências. Esse adaptador não chama modelos, instala MCPs ou registra um grafo global. Em Claude Code ou Codex, peça: “Use retrieve-memory para retomar pagamentos; confira decisões, desenvolvimento, produção e próxima ação.” A mesma skill acompanha o setup para projetos novos e migrações. Ela abre as evidências e registra IDs/revisões no handoff.

Para operar o índice:

```bash
python3 scripts/memory.py --root . rebuild
python3 scripts/memory.py --root . disable
python3 scripts/memory.py --root . clear-index
```

`rebuild` informa quais caminhos deixaram de existir; uma nota renomeada precisa entrar numa nova seleção. `disable` muda a seleção para Markdown. `clear-index` remove apenas gerações derivadas e o ponteiro ativo; preserva notas, seleção e runtime. Repetir uma indexação sem alterações reutiliza a geração. Uma falha de construção preserva o ponteiro anterior; uma consulta sempre confere as revisões atuais antes de usá-lo.

`query`, `doctor` e `clear-index` não criam nem reparam notas ou regras do `.gitignore`. Se a proteção da área privada tiver sido removida, o worker e a limpeza recusam a operação; a consulta recorre ao Markdown. Revise a regra e execute a indexação explicitamente para restaurar a proteção. Um identificador inválido no cache também leva ao Markdown atual e permite `rebuild` ou `disable`.

Memória e ingestão compartilham o lock do projeto. Se uma interrupção deixar `pending`, confira `python3 scripts/documents.py --root . lock-status`. A recuperação exige dono encerrado e o token mostrado: `python3 scripts/documents.py --root . recover-lock --token TOKEN`. Depois execute `rebuild`; não apague o lock manualmente.


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

<a id="vault-check-en"></a>

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Check vault organization

The validator accepts `vault/local/index.md` as a second entry when present. Local notes may link
to shared notes; shared notes must not reference `vault/local/` or `.operacao-local/docling/`.
A `private_reference` finding requires removing or reviewing that reference before publication.
Ignore rules do not encrypt files or replace backups.

Run from the product root after updating memory and before closing a delivery:

```bash
python3 scripts/vault.py check
python3 scripts/vault.py check --json
```

Setup installs this command for Claude Code and Codex. For an existing harness installation,
update the source clone and run setup again without `--force`: it copies the new file and preserves
existing notes. The command uses Python and `scripts/integrations.py`, with no external service.

Output includes the file, issue code and guidance. Exit status is `0` when checks pass, `1` for vault
issues and `2` for invalid arguments. `--json` returns the same diagnostics as structured data,
without note bodies. The command does not repair or create files.

Each Markdown note needs `id`, `type`, `title`, `origin`, `updated` and `index` in frontmatter between
`---` lines. Personalizer and integration commands already create these fields. Values are single-line
strings, unquoted or single/double quoted; `updated` is an ISO date such as `2026-10-01` or an ISO
timestamp. Other Obsidian properties may remain in the header and are not evaluated. Legacy notes
missing these fields are reported for review; new identities are never assigned automatically.

| Issue | Resolution |
|---|---|
| `metadata` / `duplicate_id` | Complete the indicated fields. Keep identity when moving a note; distinct notes need distinct IDs. |
| `invalid_index` / `index_cycle` | Point `index` to a vault `index.md`. The chain must reach `vault/index.md`, which references itself. |
| `missing_index_link` / `unreachable` | Add a note link to its declared index and connect that index to general navigation. |
| `broken_link` / `ambiguous_link` | Fix the destination or reference label. Use the full vault-relative path for ambiguous wikilinks. |
| `unsafe_path` / `unsafe_link` / `unreadable` | Check permissions, UTF-8 and file types. Symlinks, junctions, hardlinks and paths outside the project are rejected. |
| `missing_vault` / `missing_root_index` | Install or restore the vault and its general index before checking navigation. |

The check covers Markdown file and image links, labeled references and wikilinks such as
`[[features/payments/index|Payments]]`. Wiki paths start at the vault root; `./` and `../` start
at the current note. A bare name may resolve to a uniquely named note. Markdown paths start at the
note's directory and may reference code or documentation inside the project. Prefer relative
Markdown links when the notes should also be navigable on GitHub.

Fenced blocks using three or more backticks/tildes, inline code, HTML comments and `.obsidian` are
excluded. Indented lines, including nested lists, are checked: fence code examples to avoid reports
about fictional links. External URLs are not fetched; `#section` fragments are not checked.
This validates required field structure and the link formats
above, without implementing all YAML or Markdown syntax. It does not verify claims, detect secrets,
confirm test outcomes or inspect production. Run it while the vault has no concurrent edits.
Use simple link labels: nested brackets inside labels and escaped openings such as
`\[example](file.md)` still require manual inspection.

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

5. `python3 scripts/integrations.py export --provider example --service payments` prints a YoungCrow envelope with IDs, paths, content and revision hashes. **This is not a vendor import format or automatic synchronization.** Review before transmission; no automatic secret redaction is performed. Follow the [memory reference](../skills/integrate-from-docs/references/memory.md) to check installed tools, project isolation, idempotency and confirmation. Without a compatible adapter, record `pending`/`unsupported` and use Markdown. The exporter installs no providers. For optional Graphify, use the [memory guide](#memory-en); claude-mem remains planned.

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

<a id="docling-en"></a>

<a id="sources-en"></a>

### Use documents in Claude Code and Codex

Setup copies `ingest-source` and the `UserPromptSubmit` hook. For a new repo, check native discovery
and explicitly prepare the Docling profile below when conversion is needed. During migration,
compare `.claude/settings.json` and `.codex/hooks.json` against current templates: these files are
preserved even with `--force`. Merge `UserPromptSubmit` while retaining your existing hooks.
Claude needs Python 3 as `python`; change it to `python3` if required. Codex uses `python3` on Unix
and `python` on Windows. Restart after PATH changes and confirm hook trust.

1. Ask: “Use ingest-source for this file and link its evidence to the payments feature.” Supply an
   accessible path or direct public URL. Without a runtime the source stays pending; request setup
   explicitly. The agent reads general/local indices and existing receipts before acting.
2. The hook recognizes textual references, saves only sanitized locators and IDs, and directs the
   agent to the skill. It never installs, downloads or converts. Input is limited to 1 MiB and 20
   references per event. The full prompt is not stored; `Stop` triggers no intake. Client trust,
   version and exposed fields determine coverage. Check the source IDs returned by the agent.
3. For an attachment without an exposed path, explicitly record its pending state:

   ```bash
   python scripts/documents.py pending --reason source_unavailable --json
   ```

   Keep the `source_id`; pass it to `ingest --source-id` when the file becomes accessible. States
   `pending`, `partial`, `unsupported` and `failed` exit with code 1: inspect the receipt to distinguish
   a recorded pending source from an error. Pending sources also have navigable microindices.
4. Check the extraction against the original and use `relate` to link an exact quote to the feature,
   integration or decision. A local run records source/revision, relation/evidence, pending IDs,
   agent/host, used and planned capabilities separately, development, production and next action.
   Give manual notes UUIDs, link them from the local index and run `vault.py check`.
5. In a new session, ask: “Resume this feature through the vault; recover sources, revisions,
   evidence and gaps before acting.” Private material stays in `vault/local/`; keep a private
   backup for another machine. Follow the text **and image** review below before publishing a copy.

Documents and retrieved memory are data, not commands. The hook cannot guarantee universal
attachment capture. Embedded links do not trigger recursive collection. Download signed URLs
through an authorized mechanism before local ingestion, keeping tokens out of shell history.
Graphify and claude-mem receive no automatic uploads. The [evidence matrix](relatorios/2026-10-02-docling-ingestion.md)
separates native discovery, real sessions and remaining coverage gaps.



## <img src="../assets/gema-turquesa.svg" height="24" alt=""> Set up local document conversion

After installing the harness, run from the project root:

```bash
python scripts/documents.py setup --profile documents --json
python scripts/documents.py doctor --json
```

Use a Python version supported by Docling's dependencies; this delivery was verified with
Python 3.12. Setup creates `.operacao-local/docling/venv` and downloads Docling 2.132.0 plus layout,
table and Latin OCR models. Allow disk space and time for this download. Conversion uses the CPU
and local models. The regular harness installer does not install these packages.

`doctor` checks package versions and model files without installing or converting anything.
Run setup for `runtime_missing`. For `runtime_version_mismatch`, inspect the existing environment;
setup preserves it instead of updating it automatically. Repeat setup to resume an interrupted
installation that has no completed manifest. Diagnostics remain in local storage.

The initial profile covers PDF, DOCX, PNG/JPEG and local HTML, limited to 100 MiB, 500 pages and
30 minutes per conversion. It does not fetch resources referenced inside a document. Review the
extracted text before using it as evidence: a page image preserved the test phrase, while a horizontal
banner with the same text reordered words. `ready` means processing finished; it does not certify
fidelity to the original.

Store a source and resume its state with:

```bash
python scripts/documents.py ingest "path/document.pdf" --json
python scripts/documents.py status --json
python scripts/vault.py check --json
```

The receipt contains `source_id`, revision, attempt, state and note path. Each source has an index
in `vault/local/sources/`; originals, receipts and extractions remain in `.operacao-local/docling/`.
Repeating the same origin reuses extraction when bytes and configuration match. Different origins
retain separate identities even when their contents are identical.
An extraction without a cache manifest is preserved in `.operacao-local/docling/work/orphan-*`;
the next ingestion converts again. You do not need to delete the cache to resume.

In extracted notes, HTML, wikilinks and reference-style Markdown links remain readable text.
Inline HTTP(S) links stay clickable; inline images only point to validated local assets.

Use `ingest "file" --source-id UUID --json` to update a known source or resume a pending source by ID.
A failed attempt preserves the previous valid revision. A `partial` extraction gets a separate note
with a warning, retained after a later successful attempt. Manual note edits are preserved. `status`
separates the current revision from the latest attempt without showing source text or its original
path. A missing file or runtime remains `pending`; an unsupported format returns `unsupported`.

For a direct URL, use the same command:

```bash
python scripts/documents.py ingest "https://example.org/document.pdf" --json
```

Acquisition accepts HTTP(S), at most five redirects, 60 seconds total and 100 MiB. The file type is
checked against the received bytes. Each connection uses a previously validated IP while preserving
TLS hostname verification. Environment proxies and credentials are not inherited. Resources inside
documents do not trigger downloads. A recognized video or audio playback page stays `pending`:
provide an accessible file or transcript. A transcript is a separate source.

The stored locator omits query and fragment. Different full URLs retain distinct IDs through an
opaque local key; pass `--source-id UUID` when renewing a signed link for the same source.
Avoid putting token-bearing links into shell history: download through an authorized tool and
ingest the local copy instead. Receipts never print the access URL.

Private destinations are rejected by default. For an internal server, the operator can create
`.operacao-local/docling/acquisition.json` with `{"allowed_private_hosts":["docs.internal.example"]}`.
This authorizes only the exact listed names, including redirects; review this exception.
Acquisition failures preserve the previous revision and include a next action in the receipt.

Each project has one writer. After a forced process termination, inspect
`python scripts/documents.py lock-status --json`. Only when `owner_alive` is false, run
`python scripts/documents.py recover-lock --token UUID --json` with the reported token, then repeat
ingestion. Recovery rejects a live owner or a different token. Closing a session does not erase local
documents; maintain a private backup.

For audio and video, make `ffmpeg` and `ffprobe` available on the client's PATH or in
`.operacao-local/docling/bin/`. Setup checks these executables and records their hashes; it does not
install them globally. The [FFmpeg download page](https://ffmpeg.org/download.html) lists distributions
by platform. The Windows proof uses Gyan 9.0.2 binaries with the publisher's checksum verified.

```bash
python scripts/documents.py setup --profile media --json
python scripts/documents.py doctor --profile media --json
python scripts/documents.py ingest "path/recording.wav" --json
python scripts/documents.py ingest "path/video.mp4" --json
```

The profile creates `.operacao-local/docling/media/venv` and downloads multilingual Whisper Base for
CPU use. Speaker diarization is disabled. On Windows its optional extra is omitted because it
requires C++ compilation; transcription and sampling use Docling's native pipeline.
Media packages are separate from the document runtime, so a failed install preserves the
existing environment. This needs extra disk space. After replacing FFmpeg/ffprobe, inspect the
diagnostic before recreating the profile. Setup will not silently accept different executables.

Audio accepts WAV, MP3, M4A, AAC, OGG and FLAC; video accepts MP4, MOV, AVI, MKV and WEBM. Each file
is limited to 500 MiB and 60 minutes. Conversion has up to 30 minutes and samples at most 200 frames,
normally ten seconds apart. Pipeline format support does not guarantee transcription quality.
Audio is normalized locally before ASR; the model detects language without automatic translation.

The receipt reports transcript intervals and frame times actually produced. Missing audio, empty
transcripts, partial failure or a frame limit appears in warnings and retains a `partial` state.
These images do not establish understanding of every action, text or screen in a video. A timeout
that prevents any export returns `failed`; an exportable partial result keeps its own note.
Timeout cleanup also terminates child processes. Review transcripts and frames before using the
recording as evidence.

Link a revision to a feature, decision or another note using its frontmatter ID and a quote from
the extraction:

```bash
python scripts/documents.py relate --source-id SOURCE_UUID --revision REVISION --target-id NOTE_ID --relation supports --evidence "quote present in the extraction" --json
```

Available relations are `supports`, `complements`, `contradicts`, `supersedes` and `used-in`.
The relation stays local and leaves the shared note unchanged. Validation confirms the quote;
the relationship's meaning needs review. `contradicts` starts as a hypothesis.

To share a source:

```bash
python scripts/documents.py prepare-review --source-id SOURCE_UUID --revision REVISION --json
python scripts/documents.py review-status --review-id REVIEW_UUID --json
python scripts/documents.py promote --review-id REVIEW_UUID --approved-digest APPROVED_DIGEST --json
```

The first command prepares an editable private copy with a new public ID. Inspect its text and every
image, removing anything that must remain local. After editing, `review-status` reports the current
digest and file list. Authorize that exact copy before running `promote`: knowing a digest does not
establish human permission.

Promotion checks all filenames and bytes, preserves partial-extraction warnings and rejects private
file links or absolute paths. A copy may contain one Markdown note and raster images, up to 2,000 files
and 500 MiB. HTML and autolinks outside code examples are rejected; use `[label](destination)` without
angle brackets around the destination. The result enters `vault/sources/`; the command never stages, commits or pushes it. A shared
feature can then link to the published source. The original-to-copy mapping remains local. Later changes
to the original do not alter the prepared copy.

This process does not anonymize content: a name within a paragraph or image still requires human
review. Inspect the diff and run `vault.py check` before tracking the files.

## <img src="../assets/gema-violeta.svg" height="24" alt=""> Failures and maintenance

Repeated runs preserve existing files and render the project name only in newly copied guides. `--force` replaces managed templates, but preserves vault notes, `.env`, ignore rules, existing manifests, skills, agents, `.mcp.json`, `.codex/config.toml` and hook files. Compare and merge existing configurations. Review changes before using it.

Invalid arguments exit with code 2. Dependency, path, manifest, tracked-env and divergent-skill checks fail before project copies. Existing humanizer must be a clean repository at the manifest commit; changes are preserved and require your decision. Failed downloads/checkouts never activate the incomplete skill. Plugin failures identify their stage and return nonzero. Earlier successful steps remain in place; resolve the cause and retry.

Skipped plugins are reported for `--no-plugins` or missing `claude`. Impeccable and skills without an installable source require manual installation. Existing humanizer-ptbr is preserved without automatic updates. Humanizer's commit is verified; marketplace revisions/versions remain inventory information, not enforced locks. Successful setup does not verify optional plugins, hooks or real MCP access.

Run checks from the harness clone with Python 3.11+:

```bash
python3 -m unittest discover -s tests -v
bash -n setup.sh
git diff --check
```

Tests use local Git, simulated network/plugin calls and an isolated temporary home. See the [verification matrix](../README.md#verification).

<a id="memory-en"></a>

## Memory: query selected notes

From a new or adopted project's root, select Markdown vault notes with UUIDs. Existing indices help locate them. Queries never expand the selection automatically.

```bash
python3 scripts/memory.py --root . index --note vault/local/features/payments/index.md
python3 scripts/memory.py --root . query "payments"
python3 scripts/memory.py --root . status
```

Replace the path with an existing note. Repeat `--note` to include more notes. Initial limits are 100 notes, 256 KiB per note and 8 MiB total. Derived state stays in `.operacao-local/memory/`, excluded from Git; notes and client settings are preserved. The first response includes up to five references. Open cited notes to verify decisions, publication and the next action.

Changed or removed notes make the previous snapshot stale. Queries read current selected notes and report that the index needs rebuilding. Use `rebuild` to rebuild from surviving notes or `index` to change the selection. With no selection, the command offers the vault indices for navigation. Graphify is optional. Install it for this project using Python 3.12:

```bash
python3.12 scripts/memory.py --root . setup-graphify
python3 scripts/memory.py --root . doctor
python3 scripts/memory.py --root . index --provider graphify --note vault/local/features/payments/index.md
python3 scripts/memory.py --root . query "payments"
```

On Windows, use `py -3.12` or the Python 3.12 executable path for setup, and `python` for the other commands. The pinned version is `graphifyy==0.9.73`, installed under `.operacao-local/memory/runtime/venv`. Setup records resolved versions; `doctor` checks them without reinstalling. Missing runtime returns `pending`, incompatible versions return `unsupported`, and errors return `failed`. Selected Markdown remains available for retrieval. Graphify queries need temporary writes under `.operacao-local/memory/runtime/`; in a read-only client, inspect fallback warnings.

The graph represents explicit links between notes. Local search combines terms and relations; the session AI interprets the evidence. This adapter does not call models, install MCPs or register a global graph. In Claude Code or Codex, ask: “Use retrieve-memory to resume payments; check decisions, development, production and the next action.” The same skill ships with setup for new and migrated projects. It opens evidence and records IDs/revisions in the handoff.

To operate the index:

```bash
python3 scripts/memory.py --root . rebuild
python3 scripts/memory.py --root . disable
python3 scripts/memory.py --root . clear-index
```

`rebuild` reports removed paths; renamed notes need a new selection. `disable` switches the selection to Markdown. `clear-index` removes derived generations and the active pointer while preserving notes, selection and runtime. Unchanged indexing reuses the generation. Build failures preserve the previous pointer; queries check current revisions before using it.

`query`, `doctor` and `clear-index` do not create or repair notes or `.gitignore` rules. If private storage protection has been removed, the worker and cleanup reject the operation; retrieval falls back to Markdown. Review the rule and run indexing explicitly to restore protection. An invalid cache identifier also falls back to current Markdown and allows `rebuild` or `disable`.

Memory and ingestion share the project lock. If interruption leaves `pending`, inspect `python3 scripts/documents.py --root . lock-status`. Recovery requires a stopped owner and the displayed token: `python3 scripts/documents.py --root . recover-lock --token TOKEN`. Then run `rebuild`; do not delete the lock manually.


## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Referências oficiais / Official references

- [Codex skills](https://learn.chatgpt.com/docs/build-skills): descoberta no projeto / project discovery.
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli): TOML e confiança / TOML and trust.
- [Codex hooks](https://learn.chatgpt.com/docs/hooks): descoberta, confiança e comandos Windows / discovery, trust and Windows commands.
- [Claude skills](https://code.claude.com/docs/en/skills): skills do usuário e projeto / user and project skills.

<p align="center">
  <img src="../assets/assinatura.svg" alt="☧ Ora et labora ☧ et coda" width="100%">
</p>

- Docling: [formatos e limites do fornecedor](https://docling-project.github.io/docling/usage/supported_formats/) · [versão usada](https://github.com/docling-project/docling/tree/v2.132.0).
