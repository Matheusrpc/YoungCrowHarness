<p align="center">
  <img src="../assets/titulo.svg" alt="YoungCrowHarness — guia de uso / usage guide" width="100%">
</p>

[← README](../README.md) · [Português](#portugues) · [English](#english)

Consulte os [fluxos visuais de uso](../README.md#processo-pt) para localizar sua etapa:
começar do zero, migrar um projeto, operar uma entrega, incorporar fontes ou retomar a memória. O [processo completo](PROCESS.md#portugues)
detalha decisões, pausas e retomada.

See the [usage diagrams](../README.md#process-en) for new projects, adoption, daily work, source intake and memory retrieval.
The [complete process](PROCESS.md#english) includes decisions, pauses and resumption.

Para continuar o desenvolvimento do executor na cloud, use a branch `feat/isolated-executor`
e leia o [contexto de transição](HANDOFF-CLOUD-2026-10-07.md). Credenciais e estado operacional
não acompanham o clone. Os perfis de execução continuam bloqueados até as provas pendentes.
O [registro da publicação cloud](relatorios/2026-10-07-cloud-publication.md) identifica
o checkpoint anterior enviado ao PR #24. O [incremento de reserva e recuperação](relatorios/2026-10-07-reservation-recovery.md)
registra o estado atual e a próxima task 203.6.

To continue executor development in the cloud, use branch `feat/isolated-executor` and read the
[handoff](HANDOFF-CLOUD-2026-10-07.md). Credentials and operational state are not part of the clone.
Execution profiles remain blocked until the pending proofs pass.
The [cloud publication record](relatorios/2026-10-07-cloud-publication.md) identifies
the previous checkpoint pushed to PR #24. The [reservation/recovery increment](relatorios/2026-10-07-reservation-recovery.md)
records current scope and the next task, 203.6.

[Abra a demonstração](https://matheusrpc.github.io/YoungCrowHarness/) ou siga o [roteiro do piloto](../examples/delivery-board/README.md), que reúne esses percursos em um exemplo com
vault próprio. A página e os filtros foram verificados localmente, incluindo teclado e tela estreita.
O roteiro explica início do zero, migração e saída; os dois consumidores passaram pela prova de retorno no Windows e no Linux.
A retomada passou no Codex e foi [confirmada no Claude](relatorios/2026-10-09-p06-offline-review.md) em uma
sessão Haiku. O verificador original recusou a navegação; a reavaliação
offline dos mesmos arquivos passou com a correção e a revisão do conteúdo.
O recibo original permanece intacto. P06 está verificado no piloto; não é preciso
repetir o teste. O [guia](P06-CLAUDE.md) conserva o histórico e os limites.
O README do exemplo explica como gerar e servir somente o pacote permitido, em um destino novo.

[Open the demonstration](https://matheusrpc.github.io/YoungCrowHarness/) or follow the [pilot recipe](../examples/delivery-board/README.md), which brings these paths together in an example
with its own vault. The page and filters were checked locally, including keyboard navigation and a narrow viewport.
The recipe covers a new project, migration and exit; both consumers passed restoration on Windows and Linux.
Retrieval passed in Codex and was [confirmed in Claude](relatorios/2026-10-09-p06-offline-review.md) in one
Haiku session. The original verifier rejected navigation; offline
re-evaluation of the same files passed with the fix and semantic review.
The original receipt remains intact. Pilot P06 is verified; no repeat is needed.
The [guide](P06-CLAUDE.md) preserves the history and limits.
The example README explains how to build and serve only the allowed package, using a new destination.

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

O [tutorial animado](media/youngcrow-guide/README.md) preserva o percurso de 118 segundos
da instalação à missão preparada e acrescenta três minutos de um agente de atendimento de clínica fictício,
com features, vault e troca manual Codex/Claude. Há layouts horizontal e vertical e uma
transcrição com comandos. As telas encenadas não substituem as condições e verificações deste guia.

Downloads em MP4: [16:9](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-16x9.mp4) e [9:16](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-9x16.mp4), ambos com 4min58s.

<a id="adocao-reversivel-pt"></a>

Use `--trial` no primeiro setup para guardar um ponto anterior à adoção. O perfil inicial cobre arquivos comuns, diretórios vazios
e Git independente, incluindo arquivos ignorados e mudanças sem commit. Links, worktrees, submódulos
e metadados que não possam ser preservados são recusados antes da instalação. Sem `--trial`, o setup não cria ponto de retorno.

Encerre os escritores do projeto. O pai do destino deve existir. A base padrão é
`.youngcrow-recovery`, ao lado do destino; escolha outra base com `--backup-root CAMINHO`.
Ela precisa ficar fora de qualquer Git, no mesmo volume, com acesso restrito ao dono.
O modo de teste pula instalações globais, plugins e downloads de skills nos dois clientes.
`--sem-plugins` sozinho ainda instala skills e não oferece essa proteção.

```bash
bash YoungCrowHarness/setup.sh meu-projeto --trial --client both --backup-root ./backups-privados
```

Guarde o caminho `runner` retornado em local privado. Para repetir ou retomar uma instalação
parcial, use o mesmo destino e a mesma base: o ponto inicial não muda. Uma instalação antiga
sem esse ponto não permite reconstruir o estado anterior. Depois de restaurar, o registro é histórico;
uma adoção nova exige outro destino ainda não adotado ou tratamento manual, preservando as cópias anteriores.

A preparação pode ser feita a partir da cópia do harness, antes do setup, com escritores do projeto
encerrados. Escolha uma pasta de backup no mesmo volume, fora de qualquer repo Git:

```bash
python scripts/adoption.py --root /caminho/projeto --backup-root /caminho/backups prepare --json
python scripts/adoption.py --root /caminho/projeto --backup-root /caminho/backups status --json
```

`prepare` recusa instalações YoungCrow reconhecidas sem ponto anterior e preserva um ponto existente.
`status` não cria arquivos. Guarde o caminho `runner` informado: ele fica fora do projeto.
Para retornar, use o runner externo e encerre todos os processos que escrevem no projeto:

```bash
python /caminho/runner/adoption.py --root /caminho/projeto --backup-root /caminho/backups restore --dry-run --json
# Revise o relatório privado; use o digest atual somente após confirmar a saída.
python /caminho/runner/adoption.py --root /caminho/projeto --backup-root /caminho/backups restore --confirm DIGEST --json
```

A confirmação autoriza copiar e verificar o trabalho do teste antes de retirar a pasta atual.
No Windows, também autoriza restringir temporariamente suas permissões durante a troca.
O resultado informa `recovery_path` e `displaced_path`; as duas cópias ficam preservadas.
Se houver interrupção, consulte `status` pelo runner. Com dono e filho encerrados, use
`recover-lock --confirm LOCK_ID` e depois `recover --confirm TRANSACTION_ID`, com os IDs retornados.
Mudanças após a prévia exigem nova revisão. O retorno nunca é um efeito automático do setup.

O armazenamento inclui arquivos ignorados e pode conter segredos: não o publique nem o indexe no
vault, Graphify ou claude-mem. O vault recebe apenas ID da adoção, data, estado e próxima ação.
A captura aceita até 100 mil entradas e 64 GiB. Reserve o tamanho inicial para a captura; na saída,
precisa haver espaço livre para uma cópia do projeto atual, outra do ponto inicial e 64 MiB adicionais.
As cópias não são apagadas automaticamente. Não há garantia contra falha de disco ou energia.

No Windows, o perfil exige ACLs herdadas e o usuário atual como dono. Pastas pertencentes ao grupo
Administradores ficam fora desse perfil. O preflight recusa streams extras, junctions e atributos
não preserváveis. Caminhos derivados precisam ter menos de 248 unidades UTF-16, incluindo o
armazenamento interno. `unsupported_path_length` pede uma base mais curta, por exemplo `C:/yc-backups`;
o setup reserva espaço de caminho para os arquivos distribuídos. Arquivos novos muito longos também
podem bloquear a saída antes da troca. No POSIX, permissões simples do dono atual e grupos dos quais
ele ainda faz parte são preservados; grupos que o processo não pode restaurar são recusados.
ACLs estendidas, xattrs e bits especiais são recusados. As consultas Git do trial ignoram configurações
globais, variáveis Git herdadas e monitores externos desde o preflight. Links, hardlinks, submódulos, Git compartilhado
e worktrees não entram neste perfil. Encerre agentes, editores que salvam e processos Git antes das
operações: o lock coordena o harness, mas não impede um programa externo de escrever.
Plugins globais, serviços, publicações remotas e mudanças fora da pasta ficam fora do retorno.

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
   bash YoungCrowHarness/setup.sh meu-projeto --trial --client both --nome "Meu Projeto"
   cd meu-projeto
   ```

   Guarde o `runner` retornado. O teste pula plugins e downloads; a saída distingue componentes copiados, mantidos e pulados.

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
   bash ../YoungCrowHarness/setup.sh . --trial --client both --nome "Meu Produto"
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

O teste opcional `tests/smoke_clients.py` usa os clientes reais com configuração temporária: valida descoberta de skills/hooks/configuração no Codex e leitura de MCP pendente de aprovação no Claude. O modo completo inclui uma requisição Codex à fixture de modelo em loopback, sem fornecedor pago, plugins reais ou chamadas MCP. Rode com Python 3.11+ e os caminhos dos executáveis:

```bash
python3 tests/smoke_clients.py --codex /caminho/codex --claude /caminho/claude
```

No Windows, use os `.exe` reais, não os wrappers `.ps1`/`.cmd` do npm. O teste termina seus processos e mantém sua configuração pessoal fora da fixture.


Para conferir só a descoberta das quatro skills de missão em um cliente, sem enviar
prompt, use um caminho novo para o recibo. A pasta de destino deve existir:

```bash
python3 -B tests/smoke_clients.py --discovery-only --codex /caminho/codex --report .runtime/descoberta-codex.json
```

Para Claude, troque `--codex` por `--claude` e indique o executável nativo. Também
é possível fornecer ambos; a sequência para na primeira falha. O cliente omitido
fica `not_run`. Um recibo existente é preservado e impede repetir esse comando
sobre o mesmo arquivo. O resultado registra versão, plataforma, hash do binário,
nomes encontrados e hashes das quatro skills e suas entradas instaladas.
`passed` comprova descoberta, não aplicação em uma missão. O teste usa um consumidor
e perfil temporários, sem copiar seu login. [Codex/Linux e Claude/Windows passaram](relatorios/2026-10-09-client-skill-discovery.md).
YC-011 continua parcial pela aplicação nativa pendente.
Para o PC Windows usado na prova P06, siga o [preparo e a consulta sem prompt](YC011-CLAUDE-DISCOVERY.md).
O roteiro usa uma cópia nova e preserva os recibos anteriores.

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
   Curingas de comandos e notas Markdown dentro do vault do projeto são ignorados. URLs e Markdown
   externo ao vault continuam sendo registrados; use `ingest-source` explicitamente se necessário.
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
distingue descoberta nativa, sessão real e cobertura ainda pendente. A [prova no Claude](relatorios/2026-10-03-claude-docling.md)
verificou o hook para um caminho HTML textual, conversão, vínculo com feature e retomada em outra
sessão. A entrada inacessível foi registrada explicitamente; envio binário pela interface não foi testado.
Confira o registro de execução e o recibo atual antes de atualizar o resumo da feature: essa conciliação
continua manual. Descoberta ou autodeclaração de uma skill não comprova que suas instruções foram lidas.



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

Em HTML, links como `/llms.txt`, `../guia` e `file:///arquivo` ficam como referências inativas
no vault. O conversor recebe os bytes do original, sem tomar a pasta da cópia como origem da página.
Ele não segue esses links nem baixa imagens, scripts ou outros recursos externos. Confira a URL
de origem no registro privado da fonte quando precisar localizar uma referência relativa.

Para retomar uma conversão HTML que falhou, atualize os scripts do harness e repita
`ingest "pagina.html" --source-id UUID --json` com o original preservado, ou use a URL original
para obter a versão disponível naquele momento. A mudança do adaptador gera uma nova revisão;
recibos e originais anteriores permanecem guardados. Não é necessário reinstalar o Docling.
Com o ambiente instalado, `python tests/smoke_docling_html.py` verifica texto, tabela, links e
ausência de acesso aos recursos referenciados, usando apenas uma página sintética local.

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

<a id="ci-fixture-diagnostics"></a>

Nos testes de egress executados com `GITHUB_ACTIONS=true`, exceções antes do recibo
normal geram uma anotação `fixture`. O campo `reason` informa a última etapa alcançada:
`fixture_setup`, `fixture_supervise` ou `fixture_cleanup`. `failure` publica uma
categoria permitida ou `other`; nunca a mensagem, traceback ou caminho. Se o supervisor
já retornou, seus estados e contagens permitidos acompanham a anotação.
Uma exceção durante a saída do contexto pode substituir outra anterior: a etapa não
determina a causa. O teste continua falhando; erro de escrita da anotação não substitui
a exceção da fixture. Sem `GITHUB_ACTIONS=true`, não há anotação adicional.
[Prova e limites](relatorios/2026-10-10-ci-fixture-diagnostics.md).

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

Para conferir a passagem entre sessões, salve um handoff com fontes, UUIDs, revisões, decisões,
estado de DEV/produção e próxima ação. Vincule-o ao microíndice e valide o vault. Encerre o escritor
e abra uma sessão nova, sem colar a conversa anterior. Peça a retomada pelos índices e confira se
ela encontrou o mesmo registro e releu as fontes atuais. Um handoff novo não entra automaticamente
na seleção do Graphify; o índice do vault permite encontrá-lo.

Confira o `provider` e os avisos de cada `query`: `status: ready` sozinho não comprova consulta ao
grafo. O adaptador usa o motor de consulta do Graphify 0.9.73 sem gravar o marcador auxiliar da CLI
na geração do índice. A requisição temporária continua restrita ao runtime privado. A
[prova com a instalação atual](relatorios/2026-10-02-memory-current-clients.md) registrou duas
sessões Codex independentes com Graphify, sem timeout ou fallback. A retomada encontrou o handoff
pelo índice e preservou notas e gerações. Antes de testar, confira a revisão dos scripts e
skills da fixture, a autenticação e o limite de sessões. O [ensaio autenticado no Claude](relatorios/2026-10-02-claude-memory-capabilities.md)
passou em três sessões, incluindo revisão alterada, fallback Markdown e retorno ao Graphify após
reconstrução explícita. Registre fallback sem ampliar permissões automaticamente.

Quando dois projetos tiverem o mesmo tema, consulte cada raiz autorizada separadamente com `--root`.
Confira `project_id`, UUID e revisão antes de atribuir uma decisão ou publicação. Títulos e caminhos
relativos iguais podem representar notas diferentes. A [prova em Codex e Claude](relatorios/2026-10-02-memory-project-isolation.md)
preservou essa distinção em dois corpus Markdown; ambos estavam autorizados para leitura.
Em um perfil que permite comandos específicos, execute cada comando na forma autorizada.
Agrupar com variáveis, `cd` ou separadores pode exigir permissões diferentes. Se houver recusa,
registre o que ficou sem verificação; uma revisão não calculada não deve receber um hash inventado.

Para operar o índice:

```bash
python3 scripts/memory.py --root . rebuild
python3 scripts/memory.py --root . disable
python3 scripts/memory.py --root . clear-index
```

`rebuild` informa quais caminhos deixaram de existir; uma nota renomeada precisa entrar numa nova seleção. `disable` muda a seleção para Markdown. `clear-index` remove apenas gerações derivadas e o ponteiro ativo; preserva notas, seleção e runtime. Repetir uma indexação sem alterações reutiliza a geração. Uma falha de construção preserva o ponteiro anterior; uma consulta sempre confere as revisões atuais antes de usá-lo.

`query`, `doctor` e `clear-index` não criam nem reparam notas ou regras do `.gitignore`. Se a proteção da área privada tiver sido removida, o worker e a limpeza recusam a operação; a consulta recorre ao Markdown. Revise a regra e execute a indexação explicitamente para restaurar a proteção. Um identificador inválido no cache também leva ao Markdown atual e permite `rebuild` ou `disable`.

Memória e ingestão compartilham o lock do projeto. Se uma interrupção deixar `pending`, confira `python3 scripts/documents.py --root . lock-status`. A recuperação exige dono encerrado e o token mostrado: `python3 scripts/documents.py --root . recover-lock --token TOKEN`. Depois execute `rebuild`; não apague o lock manualmente.


<a id="governanca-pt"></a>

## Governança: descobrir, revisar e revogar

Num projeto novo, conclua o setup para o cliente escolhido e use `personalizer` para criar a
identidade do vault. Peça: “Use govern-capabilities para revisar as capacidades deste projeto.”
Liste o catálogo, abra o contrato da capacidade necessária e audite o cliente antes de habilitá-la.

Numa migração, inventarie primeiro manifesto, skills, agentes, MCPs e hooks existentes. Rode o
auditor com `--root CAMINHO_DO_PROJETO` antes de aplicar mudanças; se não houver manifesto, registre
a ausência e compare com o catálogo do harness. O setup preserva esses contratos e as configurações
nativas, inclusive com `--force`. Mescle apenas o que o projeto precisa e execute a auditoria novamente.
Use `--client codex` ou `--client claude` quando só houver um cliente.

```bash
python3 scripts/capabilities.py list --json
python3 scripts/capabilities.py describe retrieve-memory --json
python3 scripts/capabilities.py audit --client both --json
python3 scripts/capabilities.py review --id retrieve-memory --client codex --json
python3 scripts/capabilities.py review --check DIGEST --json
```

`review --id` grava um pacote privado; os outros comandos apenas leem. Confira finalidade, origem,
arquivos e acessos propostos. Aplique diferenças pontuais dentro da autorização vigente. Um pacote
antigo serve de histórico: se seus inputs mudaram, gere outra revisão. A skill não amplia permissões
por conta própria nem executa comandos declarados no manifesto.

Para retirar acesso, desabilite o servidor ou remova a permissão na configuração do cliente.
Abra uma sessão nova e tente a operação retirada; confira a recusa e os registros do servidor.
Se restaurar o acesso, faça outra prova positiva. Salve ID, versão, escopo, revisão e resultados
no microíndice local de capacidades, ligado à feature e à execução. Preserve o histórico do vault.

O ensaio sintético passou no Codex 0.158.0-alpha.2.1 pelo despacho local do app-server: uma chamada
permitida, nenhuma chamada proibida, nenhuma chamada após revogação e uma após restauração.
O ensaio mede esse caminho e essa versão; não comprova permissões de todos os plugins, clientes ou
serviços. O [ensaio autenticado no Claude 2.1.220](relatorios/2026-10-02-claude-memory-capabilities.md)
também verificou leitura permitida, escrita recusada e retirada/restauração do MCP em sessões novas.
Essa rodada usou modelo, permissões específicas e `dontAsk`; é separada do comando sem modelo abaixo.
O CI offline não substitui essas provas. Veja a [matriz](relatorios/2026-10-02-capability-governance.md).

No checkout do harness, o ensaio opcional usa `python3 tests/smoke_capabilities.py --client codex
--executable /caminho/absoluto/codex --root /caminho/novo/descartavel` (uma única linha). Ele exige uma
pasta inexistente, cria um ambiente isolado e usa um MCP sintético, sem turno de modelo. No Windows,
passe o `.exe`, não o lançador `.ps1` ou `.cmd`. Resultado pendente retorna 2; falha da prova retorna 1.

<a id="english"></a>

## <img src="../assets/gema-cobalto.svg" height="24" alt=""> Before you start

The [animated tutorial](media/youngcrow-guide/README.md) preserves the 118-second introduction
and adds a three-minute fictional clinic reception agent example, including features, the vault and a manual
Codex/Claude handoff. It is in Portuguese, with landscape and portrait layouts and copyable
commands. The staged screens do not replace the conditions and checks in this guide.

MP4 downloads: [16:9](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-16x9.mp4) and [9:16](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-9x16.mp4), each lasting 4min58s.

<a id="reversible-adoption-en"></a>

Use `--trial` on first setup to save the pre-adoption state. The initial profile covers regular files, empty directories
and standalone Git repositories, including ignored files and uncommitted work. Links, worktrees,
submodules and metadata that cannot be preserved are refused before installation. Setup without `--trial` creates no restore point.

Stop project writers first. The destination's parent must exist. The default base is
`.youngcrow-recovery` beside the destination; override it with `--backup-root PATH`.
It must be outside every Git repository, on the same volume, and accessible only to its owner.
Trial skips global installs, plugins and skill downloads for both clients.
`--no-plugins` alone still installs skills and does not provide this protection.

```bash
bash YoungCrowHarness/setup.sh my-project --trial --client both --backup-root ./private-backups
```

Keep the returned `runner` path private. Repeat setup or resume a partial install with the same
destination and backup base: the first baseline stays unchanged. Older installations without that
baseline cannot reconstruct the pre-adoption state. After restoration, the record is historical;
a new adoption requires another not-yet-adopted destination or manual handling, retaining earlier copies.

Run preparation from the harness checkout before setup, with project writers stopped.
Choose a backup directory on the same volume and outside every Git repository:

```bash
python scripts/adoption.py --root /path/project --backup-root /path/backups prepare --json
python scripts/adoption.py --root /path/project --backup-root /path/backups status --json
```

`prepare` refuses recognized YoungCrow installations without a prior baseline and preserves existing
baselines. `status` creates no files. Keep the returned `runner` path; it is outside the project.
To restore, use the external runner and stop every process that writes to the project:

```bash
python /path/runner/adoption.py --root /path/project --backup-root /path/backups restore --dry-run --json
# Review the private report; use its current digest only after confirming the exit.
python /path/runner/adoption.py --root /path/project --backup-root /path/backups restore --confirm DIGEST --json
```

Confirmation authorizes copying and verifying trial work before moving the current folder.
On Windows it also authorizes temporarily restricting permissions during the exchange.
The result reports `recovery_path` and `displaced_path`; both copies are retained.
After interruption, inspect `status` through the runner. Once the owner and child have stopped, use
`recover-lock --confirm LOCK_ID`, then `recover --confirm TRANSACTION_ID`, with the reported IDs.
Changes after preview require a new review. Setup never triggers restoration automatically.

Storage includes ignored files and may contain secrets: keep it out of Git, the vault, Graphify and
claude-mem. Vault notes contain only adoption ID, date, state and next action. Capture accepts up to
100,000 entries and 64 GiB. Allow the initial size for capture; exit needs free space for a copy of
the current project, another copy of the baseline and 64 MiB of reserve. Copies are never cleaned
up automatically. Disk failure and power-loss durability are not guaranteed.

Windows requires inherited ACLs and the current user as owner; folders owned by the Administrators
group are outside this profile. Extra streams, junctions and unsupported
attributes are refused. Derived paths must remain below 248 UTF-16 units, including internal storage.
For `unsupported_path_length`, choose a shorter base, such as `C:/yc-backups`; setup reserves path
space for bundled files. Long files created later can also block exit before the exchange. POSIX
preserves current ownership, simple modes and groups the process still belongs to; unsupported groups,
extended ACLs, xattrs and special mode bits are refused. Trial Git queries ignore global configuration,
inherited Git variables and external filesystem monitors from the first preflight.
Links, hardlinks, submodules, shared Git metadata and worktrees are outside this profile. Stop agents,
autosaving editors and Git processes first: the harness lock cannot prevent external writers.
Global plugins, services, remote publications and changes outside the folder are excluded.

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
   bash YoungCrowHarness/setup.sh my-project --trial --client both --name "My Project"
   cd my-project
   git init
   git check-ignore --no-index .env
   git ls-files -- .env
   ```

   The ignore check must print `.env`; the tracked-files check must be empty. Setup prepares the ignore rule but does not initialize Git. Keep the returned external `runner`; trial skips plugins and skill downloads.

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
   bash ../YoungCrowHarness/setup.sh . --trial --client both --name "My Product"
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

Optional real-client check (Python 3.11+): `python3 tests/smoke_clients.py --codex /path/to/codex --claude /path/to/claude`. On Windows use actual `.exe` files. It checks Codex skill/hook/config discovery and Claude MCP configuration pending approval, in temporary configuration. Its full mode includes one Codex request to a loopback model fixture, with no paid provider, real plugin execution or MCP connection; it terminates its direct processes.


To check only the four mission skills in one client without sending a prompt, use
a new receipt path whose parent directory already exists:

```bash
python3 -B tests/smoke_clients.py --discovery-only --codex /path/to/codex --report .runtime/codex-discovery.json
```

For Claude, replace `--codex` with `--claude` and supply the native executable.
Both may be supplied; the sequence stops at the first failure. An omitted client
is `not_run`. Existing receipts are preserved and cannot be overwritten. The receipt
records version, platform, executable hash, discovered names and hashes of the four
skills and their installed entries. `passed` proves discovery, not application in
a mission. The disposable consumer/profile does not copy personal login data.
[Codex/Linux and Claude/Windows passed](relatorios/2026-10-09-client-skill-discovery.md).
YC-011 remains partial because native application is still pending.
For the Windows PC used in P06, follow the [preparation and metadata-only probe](YC011-CLAUDE-DISCOVERY.md).
The recipe uses a new checkout and preserves previous receipts.

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
   Command globs and Markdown notes inside the project's vault are skipped. URLs and Markdown
   outside the vault are still recorded; invoke `ingest-source` explicitly when needed.
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
separates native discovery, real sessions and remaining coverage gaps. The [Claude proof](relatorios/2026-10-03-claude-docling.md)
verified the hook for a textual HTML path, conversion, a feature relation and recovery in a fresh
session. The inaccessible input was recorded explicitly; binary uploads through the UI were not tested.
Check the run record and current receipt before updating the feature summary: reconciliation remains
manual. Discovery or self-reported skill use does not prove its instructions were read.



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

In HTML, links such as `/llms.txt`, `../guide` and `file:///file` become inactive references
in the vault. The converter receives the original bytes without treating the copy's folder as
the page's origin. It does not follow these links or fetch images, scripts or other external
resources. Check the source's private origin record when you need to locate a relative reference.

To retry a failed HTML conversion, update the harness scripts and repeat
`ingest "page.html" --source-id UUID --json` with the preserved original, or use the original URL
to obtain the version available at that time. An adapter change creates a new revision; previous
receipts and originals remain stored. You do not need to reinstall Docling. With the runtime
installed, `python tests/smoke_docling_html.py` checks text, a table, links and absence of access
to referenced resources, using only a local synthetic page.

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

With `GITHUB_ACTIONS=true`, egress fixture exceptions before the normal receipt emit a
`fixture` annotation. `reason` identifies the last stage reached: `fixture_setup`,
`fixture_supervise` or `fixture_cleanup`. `failure` is an allowed category or `other`,
never the exception message, traceback or path. Available supervisor results retain
only allowed states and counts. An exception while unwinding may replace an earlier
one, so the stage does not establish root cause. The test still fails, and annotation
output errors do not replace the fixture exception. Without `GITHUB_ACTIONS=true`, no extra annotation is emitted.
[Evidence and limits](relatorios/2026-10-10-ci-fixture-diagnostics.md#english-overview).

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

To check continuity between sessions, save a handoff with sources, UUIDs, revisions, decisions,
development/production status and the next action. Link it from the microindex and validate the
vault. Close the writer and start a fresh session without pasting the previous conversation. Ask
it to resume through the indices; check that it found the same record and reread current sources.
A new handoff does not automatically join the Graphify selection; the vault index makes it discoverable.

Check the `provider` and warnings from each `query`: `status: ready` alone does not prove a graph
query. The adapter uses Graphify 0.9.73's query engine without writing the CLI's auxiliary stamp
in the index generation. Its temporary request still stays within the private runtime. The
[current-installation test](relatorios/2026-10-02-memory-current-clients.md) recorded two independent
Codex sessions using Graphify without timeout or fallback. Recovery found the handoff through
the index and preserved notes and generations. Before testing, check the fixture's script and
skill revisions, authentication and session limit. The [authenticated Claude test](relatorios/2026-10-02-claude-memory-capabilities.md)
passed in three sessions, including a changed revision, Markdown fallback and return to Graphify
after an explicit rebuild. Record fallback without automatically broadening permissions.

When two projects share a topic name, query each authorized root separately with `--root`.
Check `project_id`, UUID and revision before attributing a decision or publication. Identical titles
and relative paths can refer to different notes. The [Codex and Claude test](relatorios/2026-10-02-memory-project-isolation.md)
preserved that distinction across two Markdown corpora; both were authorized for reading.
When a profile allows specific commands, execute each in its authorized form. Grouping commands
with variables, `cd` or separators can require different permissions. If a command is denied,
record what remains unverified; never invent a hash for a revision that was not computed.

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

<a id="governance-en"></a>

## Governance: discover, review and revoke

For a new project, complete setup for the selected client and use `personalizer` to create the
vault identity. Ask: “Use govern-capabilities to review this project's capabilities.” List the
catalog, open the contract for the capability you need and audit the client before enabling it.

For migration, inventory existing manifests, skills, agents, MCPs and hooks first. Run the auditor
with `--root PROJECT_PATH` before changing anything. If there is no manifest, record that absence
and compare with the harness catalog. Setup preserves these contracts and native configurations,
even with `--force`. Merge only what the project needs, then audit again. Use `--client codex` or
`--client claude` for a single-client project.

```bash
python3 scripts/capabilities.py list --json
python3 scripts/capabilities.py describe retrieve-memory --json
python3 scripts/capabilities.py audit --client both --json
python3 scripts/capabilities.py review --id retrieve-memory --client codex --json
python3 scripts/capabilities.py review --check DIGEST --json
```

`review --id` writes a private bundle; the other commands only read. Check purpose, origin, files
and proposed access. Apply targeted changes within current authorization. An old bundle is history:
if its inputs changed, create a new review. The skill never expands access on its own or executes
commands declared in the manifest.

To revoke access, disable the server or remove the permission in the client configuration. Start
a fresh session and attempt the revoked operation; check its rejection and the server records.
If restoring access, run another positive check. Save ID, version, scope, revision and outcomes
in the local capability index, linked to the feature and run. Preserve vault history.

The synthetic probe passed in Codex 0.158.0-alpha.2.1 through local app-server dispatch: one allowed
call, no forbidden calls, no calls after revocation and one after restoration. This verifies that
path and version, not every plugin, client or service. The [authenticated Claude 2.1.220 test](relatorios/2026-10-02-claude-memory-capabilities.md)
also verified allowed reads, denied writes and MCP removal/restoration in fresh sessions. It used
a model, specific permissions and `dontAsk`; it is separate from the model-free command below.
Offline CI cannot replace native proof. See the
[matrix](relatorios/2026-10-02-capability-governance.md).

In the harness checkout, the optional probe is `python3 tests/smoke_capabilities.py --client codex
--executable /absolute/path/codex --root /new/disposable/path` (one line). The directory must not
exist. The probe creates an isolated environment and synthetic MCP with no model turn. On Windows,
select the actual `.exe`, not a `.ps1` or `.cmd` launcher. Pending exits with 2; failed proof exits with 1.

<a id="mission-config"></a>

## Configuração de agentes / Agent configuration

`youngcrow/agents.json` usa `schema_version: 1` e exige objetos para `pm`, `tech_lead`, `developer`
e `qa`; `integration_specialist` é opcional. Cada papel declara `client` (`claude` ou `codex`),
`model`, `effort`, `connection`, `credential_env` e IDs de `capabilities`.
Omitir cliente, modelo ou esforço deixa uma pendência. `effort.level` aceita `low`, `medium`,
`high` ou `native`; só `native` exige `native_value`. A compatibilidade real depende de prova no cliente.

`connection` começa em `authenticated`. Para API, escolha `api` e forneça somente o nome da
variável em `credential_env`, nunca seu valor. A validação não lê credenciais nem chama modelos.
Os padrões de `limits` são `max_active_pbis: 3`, `max_parallel_agents: 3` e
`max_correction_cycles: 3` (fixo nesta versão). Defina `mission_active_seconds`, `agent_seconds`,
`max_agent_runs` e `max_deploy_attempts` como inteiros positivos. API exige também `api_budget_usd`
como string decimal positiva. `deploy_mode` começa em `manual`; `automatic` registra uma intenção.
Substituições de missão alteram só os campos declarados e preservam os padrões do projeto.
O backend desta etapa ainda não executa os limites nem faz deploy.

`youngcrow/agents.json` requires `schema_version: 1` and objects for `pm`, `tech_lead`, `developer`
and `qa`; `integration_specialist` is optional. Each role declares `client` (`claude` or `codex`),
`model`, `effort`, `connection`, `credential_env` and capability IDs. Missing client, model or effort
remains pending. Effort accepts `low`, `medium`, `high` or `native`; only `native` requires
`native_value`. Schema validation does not verify client compatibility.

Connections default to `authenticated`. API access is explicit and accepts an environment variable
name only. Validation never reads its value or calls a model. Limits default to three active PBIs,
three parallel agents and three correction cycles (fixed in this version). Set positive integers for
`mission_active_seconds`, `agent_seconds`, `max_agent_runs` and `max_deploy_attempts`. API use also
requires a positive decimal string in `api_budget_usd`. Deployment defaults to `manual`;
`automatic` records intent. Mission overrides preserve project defaults. This backend does not yet
enforce runtime limits or deploy products.

<a id="mission-backlog"></a>

## Contratos do backlog / Backlog contracts

Novos épicos, features e PBIs ficam em `vault/local/product/{epics,features,pbis}/<uuid>/index.md`.
Cada nota conserva seu UUID e declara o microíndice em `index`. O bloco entre
`<!-- youngcrow:contract:start -->` e `<!-- youngcrow:contract:end -->` contém um único bloco
JSON com `schema_version`, `project_id`, `parent_id`, `owner`, `objective`, `acceptance`, `dor`,
`dod`, `validation`, `dependencies` e `references`. Veja o
[contrato completo](superpowers/plans/2026-10-03-mission-foundation.md#notas-do-backlog-e-leitura-de-contratos).
O PM define objetivo, aceite, DoR e DoD; o Tech Lead detalha PBIs, dependências e validação.
Dependências são UUIDs de PBIs; referências usam `{note_id, path}` e apontam para notas locais.
Acrescente links legíveis na prosa para navegar entre elas.

Uma feature antiga sem contrato continua legível, com a pendência `missing_contract`.
A leitura não reescreve notas, move arquivos nem executa comandos mencionados nos critérios.
Contratos malformados, referências de outro projeto e links públicos para notas privadas são recusados.
Critérios vazios deixam o item em rascunho. Datas históricas desconhecidas continuam desconhecidas.

New epics, features and PBIs live in `vault/local/product/{epics,features,pbis}/<uuid>/index.md`.
Each note keeps its UUID and names its micro-index in `index`. The marked contract contains one
JSON block with the fields above. PM defines objectives, acceptance, DoR and DoD; Tech Lead details
PBIs, dependencies and validation. Dependencies are PBI UUIDs; references use `{note_id, path}`
and point to local notes. Add readable Markdown links for navigation.

Legacy features without a contract remain readable with `missing_contract`. Reading never rewrites
notes, moves files or executes commands mentioned in criteria. Malformed contracts, foreign project
references and public links to private notes are rejected. Empty criteria remain draft; unknown
historical dates stay unknown.

<a id="mission-workflow"></a>

## Preparar uma missão / Prepare a mission

O setup instala quatro entradas: `yc-personalizer` retoma a entrevista; `yc-config` salva escolhas
por agente; `yc-missao` refina o backlog e prepara a missão; `yc-status` consulta sem escrever.
No Claude Code, chame `/yc-personalizer`, `/yc-config`, `/yc-missao` ou `/yc-status`. No Codex,
selecione a skill ou use `$yc-personalizer`, `$yc-config`, `$yc-missao` e `$yc-status` onde disponíveis.
Reabra a sessão após instalar. O catálogo verifica arquivos; a descoberta e o uso pelo cliente
precisam de evidência própria. `yc-iniciar`, `yc-pausar`, `yc-retomar`, `yc-transferir` e `yc-deploy`
ainda não são comandos funcionais.

Setup installs four entries: `yc-personalizer` resumes discovery; `yc-config` saves agent choices;
`yc-missao` refines backlog and prepares a mission; `yc-status` reads without writing. Use `/yc-*`
in Claude Code, or select the skill/use `$yc-*` in Codex where available. Reopen the session after
installation. Catalog checks establish file integrity; native discovery and model use need their
own evidence. `yc-iniciar`, `yc-pausar`, `yc-retomar`, `yc-transferir` and `yc-deploy` are not functional commands yet.

### Primeiro uso em um produto novo

1. Mantenha o checkout do harness separado da pasta do produto. Para experimentar com retorno,
   siga o [setup trial](#adocao-reversivel-pt) antes da primeira nota; escolha `--client claude`,
   `codex` ou `both`. Uma instalação normal não cria ponto de retorno.
2. Abra o produto no cliente escolhido e chame `yc-personalizer`. Ela registra perfil, decisões
   e perguntas pendentes; documentos recebidos seguem `ingest-source` e ficam locais até revisão.
3. Em `yc-config`, defina as escolhas de cada agente uma vez. A configuração vale para o projeto;
   uma missão pode substituir escolhas explicitamente. O instalador não escolhe modelos por você.
4. Em `yc-missao`, peça ao PM que descreva épico, features, DoR/DoD e aceite. O Tech Lead divide
   em PBIs verificáveis. Esses papéis atuam na sessão atual. Registre referências e importe as notas.
5. Selecione uma ou mais features e priorize todos os PBIs selecionados. `yc-status` mostra o
   que falta ou confirma `prepared`; iniciar execução automática pertence à próxima frente.

### Primeiro uso em um produto existente

Faça o trial a partir do checkout separado antes de adaptar o produto. A personalizer deve
primeiro registrar o que existe: instruções, testes, design, integrações e notas. Preserve perfil,
UUIDs e convenções confirmadas. O setup conserva catálogo e skills locais mesmo com `--force`;
compare e mescle versões conscientemente. `incompatible_helper` pede revisão dos scripts
preservados antes de qualquer escrita da CLI de missões. Uma instalação antiga sem baseline
não permite voltar ao estado anterior à adoção original.

O índice geral antigo também é preservado. Durante a adaptação, acrescente apenas os links
faltantes para seções recém-instaladas, como `integrations/index.md` e `capabilities/index.md`.
Execute `python3 -B scripts/vault.py check --json` e concilie pendências antes de entregar a navegação.

Retome em `yc-config` e `yc-missao` usando as respostas existentes. Notas antigas podem ser
importadas no mesmo caminho; ficam em rascunho quando não têm contrato. Crie novos itens no
vault privado e ligue-os aos índices. O guia de [contratos](#mission-backlog) explica essa estrutura.

### First use: new and existing products

Keep the harness checkout separate from the product. For a reversible trial, capture the baseline
through trial setup before writing any notes, selecting `claude`, `codex` or `both`. Normal setup
has no initial return point. Open the product in your client, call `yc-personalizer`, then `yc-config`
to record each role's choices once. Documents go through `ingest-source` and stay local until review.
Use `yc-missao` for PM-owned epics/features, DoR/DoD and acceptance; the Tech Lead splits verifiable
PBIs in the current session. Select one or more features, order all their PBIs and consult `yc-status`.

For an existing product, first audit instructions, tests, design, integrations and notes. Preserve
confirmed answers, profile and UUIDs. Setup preserves local catalogs and skills even with `--force`;
compare and merge intentionally. `incompatible_helper` requires reviewing preserved helper versions
before mission commands can write. An old installation without a baseline cannot restore its original
pre-adoption state. Import old notes at their existing paths; missing contracts remain drafts. New
items belong in the private vault with links from their indexes. `prepared` describes complete planning;
automatic execution is a later delivery.

Setup also preserves the old general index. During adaptation, append missing links to newly installed
sections such as `integrations/index.md` and `capabilities/index.md`, preserving existing text. Run
`python3 -B scripts/vault.py check --json` and reconcile navigation issues before handoff.

Depois do setup e da personalizer, use os comandos abaixo na raiz do produto. No Windows,
`python` pode ser o nome do Python 3. Arquivos de entrada são caminhos relativos ao projeto.
Guarde pedidos e backlog em `vault/local/`; mantenha o mesmo UUID de operação para repetir
um pedido interrompido. Um pedido diferente exige outro UUID.

```bash
python3 -B scripts/missions.py --json config show
python3 -B scripts/missions.py --json config validate --input vault/local/agents-draft.json
python3 -B scripts/missions.py --json config apply --input vault/local/agents-draft.json --expected-digest absent
python3 -B scripts/missions.py --json backlog import --note vault/local/product/epics/EPIC_UUID/index.md --expected-revision 0 --operation-id OPERATION_UUID --actor-id current-session --actor-role pm
python3 -B scripts/missions.py --json prepare --input vault/local/mission-request.json --operation-id OPERATION_UUID --actor-id current-session --actor-role pm
python3 -B scripts/missions.py --json list
python3 -B scripts/missions.py --json status M001
python3 -B scripts/missions.py --json repair M001
```

Substitua os marcadores por UUIDs reais. Importe primeiro o épico, depois features e PBIs;
para PBIs, use `--actor-role tech_lead`. Cada importação tem seu próprio UUID de operação.
O papel é uma atribuição declarada, sem autenticação de identidade. Uma nota importada recebe
código E/F/P e revisão. Importar uma edição exige a revisão atual em `--expected-revision`.
Para alterar os padrões, substitua `absent` pelo digest retornado por `config show`.

Para descobrir o código ao retomar, use `list`. O campo `missions` contém código, UUID,
título, revisão atual salva e estado registrado (`draft` ou `prepared`) de cada missão.
Esse estado não revalida fontes, projeções ou recibos: use `status CODIGO` para consultar
os impedimentos atuais. A listagem lê o banco mesmo se uma projeção da nota falhou;
não repara nem inicializa arquivos. Sem banco ou com banco vazio, retorna `missions: []`.
Armazenamento incompatível ou pertencente a outro projeto continua recusado.

O pedido da missão contém exatamente:

```json
{
  "title": "Entrega definida com o PM",
  "feature_ids": ["FEATURE_UUID"],
  "priority": ["PBI_UUID_1", "PBI_UUID_2"],
  "overrides": {},
  "scope_reference": "Decisão aprovada e registrada no perfil"
}
```

`feature_ids` seleciona uma ou mais features; `priority` ordena todos os PBIs importados dessas
features, sem repetição. Três PBIs ativos é o padrão futuro de execução, não o tamanho total da missão.
Critérios, dependências ou escolhas ausentes produzem `draft`. `prepared` indica planejamento
completo; `runtime_available` e `runnable` continuam `false`. O backend não chama modelos nem
executa as strings em `validation`.

O histórico fica em `vault/local/operations/state.sqlite3`, com notas navegáveis de eventos e
missões. `status` não cria nem repara arquivos. Se fontes mudarem, ele mostra `stale_inputs`;
importe as edições e use `revise M001 --input ... --expected-revision N --operation-id UUID
--actor-id current-session --actor-role pm` para preparar outra revisão. Mudar o padrão global
não altera missões existentes. `revise` herda a configuração congelada e aplica apenas as
substituições explícitas. As datas dos eventos registram importação/refinamento, sem inventar
datas de desenvolvimento, QA ou produção.

Uma falha de projeção mantém o evento confirmado no banco. Repita a mesma operação ou use
`repair`; conflito com edição humana exige conciliar essa nota, sem apagar seu conteúdo.

`next_action` prioriza recibos abertos no repositório, depois conflitos/projeções pendentes,
fontes alteradas e lacunas de planejamento. `blocking_runs` identifica os recibos que impedem
um novo diagnóstico, inclusive de outra missão, com UUID da missão, execução e operação,
revisão e estado. `client_runs` continua limitado à missão consultada.

| Próxima ação | O que fazer em uma operação separada e autorizada |
|---|---|
| `inspect_client_run` | Conferir o recibo reservado/em execução; status não verifica se o processo continua vivo |
| `review_reconciliation` | Revisar a evidência de encerramento e efeito externo antes de `client reconcile` |
| `review_integrated_recovery` | Revisar a recuperação do plano integrado; `client reconcile` não serve para esse recibo e o adaptador nativo continua bloqueado |
| `review_projection_conflict` | Preservar a edição humana e decidir como conciliar a nota |
| `repair_projection` | Pedir reparo explícito da projeção pendente |
| `revise_inputs` / `complete_gaps` | Atualizar as fontes ou completar o planejamento e preparar outra revisão |
| `runtime_not_available` | Aguardar o aceite do executor; planejamento completo não habilita execução |

`check_available=false` sinaliza um desses impedimentos conhecidos. `true` não é autorização
nem confirmação de orçamento, autenticação ou compatibilidade: o manifesto e o preflight
continuam obrigatórios. A consulta não executa nenhuma das ações sugeridas.

`queue_preview` apresenta a entrada inicial do backlog (`scope: initial_backlog`).
`items` segue a prioridade salva e contém UUID, código, título, revisão e UUIDs das
dependências de cada PBI. `first_candidate_id` aponta o primeiro item sem dependências,
somente se a preparação estiver consistente. Lacunas, fontes/revisões alteradas,
projeções pendentes/conflitantes ou recibos abertos deixam esse campo `null`.
A prévia considera que nenhum PBI foi integrado. O [ensaio da fila](#queue-rehearsal)
aparece separadamente em `queue_sessions`. A prévia não calcula vagas disponíveis nem
a ordem entre trabalho em andamento, QA e decisões dos líderes; não reserva ou despacha.
Mesmo com um candidato, `next_action` conserva os impedimentos e a execução segue bloqueada.

Se a nota de missão ou item foi gravada antes da interrupção e houve outra revisão,
o reparo reconhece os bytes exatos da escrita não confirmada pelo histórico durável.
Ele mantém a revisão mais recente, sem criar eventos ou repetir execuções. Alterações
humanas e restauração manual de uma revisão antiga já confirmada continuam em conflito.
Essa recuperação histórica cobre notas agregadas de missão/backlog; não as notas de
execução de clientes, cujo histórico guarda outro formato.
Saída 0 significa pedido válido (inclusive rascunho), 1 conflito ou falha operacional e 2 entrada
inválida. Não edite o banco diretamente; guarde também esse arquivo em seu backup privado.
Após uma interrupção com journal SQLite pendente, `status` pode retornar `invalid_store` sem alterar
arquivos. Um `repair` explícito permite ao SQLite recuperar a transação antes de conferir o esquema
aceito e projetar as notas. Bancos incompatíveis continuam recusados. Uma primeira gravação abortada
que deixou arquivo vazio pode ser repetida. Projeções agregadas acima de 1 MiB usam hash contínuo;
o limite das notas de entrada permanece igual.

After setup and personalization, run the commands above from the product root. Inputs are project-relative
paths. Keep requests and backlog private. Use real UUIDs and a distinct operation UUID for each request;
retry an interrupted request with its original UUID. Import epics, features and then PBIs. PBIs use
`tech_lead`; other items and mission preparation use `pm`. These are declared roles, not authenticated identities.
Updating an item requires its current revision; changing defaults requires the current configuration digest.

Use `list` to discover mission codes when resuming. Its `missions` array contains each
mission's code, UUID, title, latest saved revision and recorded state (`draft` or `prepared`).
It does not revalidate sources, projections or receipts; use `status CODE` for current
blockers. Listing reads the database even when a note projection failed, without repairing
or initializing files. An absent or empty database returns `missions: []`; incompatible
storage or a database belonging to another project remains rejected.

A request selects one or more feature UUIDs and lists every imported PBI in priority order. Empty criteria,
unresolved dependencies or missing choices produce `draft`; complete planning produces `prepared`.
Runtime remains unavailable. Three active PBIs is the future execution default, not a mission size limit.
The backend calls no models and never executes validation strings.

SQLite keeps revisions and events privately, with navigable Markdown projections. `status` is read-only
and reports changed inputs. Import edits, then use `revise` with the current revision and a new operation
UUID. Global defaults never rewrite a mission; revision inherits frozen choices plus explicit overrides.
Event times record import/refinement, without inventing development, QA or production dates.
Retry or `repair` recovers a failed projection. Human edits are preserved and reported as conflicts.

`next_action` prioritizes unresolved repository runs, projection conflicts/pending writes,
changed sources and planning gaps. `blocking_runs` identifies unresolved receipts from any
mission in this repository by mission/run/operation UUID, revision, state and next action;
`client_runs` remains limited to the requested mission. `inspect_client_run` asks for inspection
of a reserved/running receipt without probing process liveness. `review_reconciliation` requires
reviewing termination and external-effect evidence before a separate `client reconcile`.
`review_integrated_recovery` directs review to the integrated plan; legacy reconciliation cannot
close it and native recovery remains gated. Projection actions are `review_projection_conflict`
(preserve human edits) and `repair_projection` (explicit repair). `revise_inputs`, `complete_gaps`
and `runtime_not_available` retain their planning meanings.
`check_available=false` indicates a known blocker; `true` does not authorize a call or validate
budget, authentication or compatibility. Manifest/preflight checks remain mandatory. Status
performs none of the suggested actions.

`queue_preview` describes the initial backlog (`scope: initial_backlog`). The
[queue rehearsal](#queue-rehearsal) is reported separately in `queue_sessions`. Its `items`
follow saved priority and include each PBI's UUID, code, title, revision and dependency
UUIDs. `first_candidate_id` selects the first item without dependencies only when
preparation is current. Gaps, changed sources/revisions, pending/conflicting projections
or unresolved runs leave it null. No PBI is assumed integrated. The preview does not
compute available slots, ongoing-work/QA/leader ordering, reserve resources or dispatch.
An initial candidate does not change `next_action` or enable execution.

If a mission or item note was written before interruption and another revision followed,
repair recognizes the exact unconfirmed bytes from durable history. It keeps the latest
revision without adding events or repeating execution. Human edits and manual restoration
of an older confirmed revision still conflict. This historical recovery covers aggregated
mission/backlog notes; client-run notes use a different history format and are outside its scope.
Exit 0 includes valid drafts; 1 means conflict or operational failure; 2 means invalid input. Include the
database in private backups; do not edit it directly. After an interruption with a pending SQLite
journal, `status` can return `invalid_store` without writing. Explicit `repair` allows SQLite recovery
before validating the supported schema and projecting notes. Incompatible stores remain rejected.
Retry a first write that left an empty database. Aggregated projections over 1 MiB use streaming hashes;
source-note limits remain unchanged.

<a id="mission-client-checks"></a>

## Modelos e diagnóstico / Models and diagnostics

Estado desta entrega: catálogo e mecanismo disponíveis; chamadas reais bloqueadas nos dois
clientes enquanto os perfis de isolamento são comprovados. Os comandos abaixo documentam o
contrato instalado; `client check` retorna `unsupported_policy` nas combinações ainda sem prova.

Current delivery: catalog and mechanism available; live calls blocked in both clients pending
isolation proofs. The commands below document the installed contract; `client check` returns
`unsupported_policy` for combinations without that evidence.

Os adaptadores consultam o catálogo do cliente instalado e os esforços aceitos por modelo.
`latest` seleciona a recomendação atual desse cliente para a conta autenticada. A recomendação
pode diferir do lançamento mais recente do fornecedor. Um nome explícito mantém a escolha fixa;
a execução recusa combinações ausentes no catálogo. `native` permite escolher esforços adicionais
anunciados pelo cliente. `{"level":"native","native_value":"client-default"}` conserva o padrão
do modelo, inclusive quando ele não oferece controle de esforço. Inspeção não comprova uma
chamada ao modelo. A missão permanece com `runnable: false` após qualquer diagnóstico.

Adapters read the installed client's model and effort catalog. `latest` resolves the client's current
account recommendation, which may differ from the provider's newest release. Choose an explicit
model to pin it, and use `native` for additional effort levels advertised by that client. Unsupported
combinations fail without a fallback. `{"level":"native","native_value":"client-default"}` keeps
the model default, including models without effort control. Inspection does not prove model
execution. Missions remain `runnable: false` after every diagnostic.

Recibos do diagnóstico reservam uma tentativa e seu tempo antes do processo. Repetir o UUID
consulta a mesma execução. Estado incerto bloqueia outra prova no projeto; consumo desconhecido
continua desconhecido. O Windows usa um Job Object antes de liberar o cliente; no Linux x86-64,
o grupo de processos usa um filtro herdado que impede sair do grupo. Essas medidas controlam
os processos; o perfil de ferramentas de cada cliente exige prova própria. Notas e microíndices
ficam em `vault/local/missions/<UUID>/runs/`, e edições humanas são preservadas.

Diagnostic receipts reserve one attempt and its time before spawning. Repeating the UUID reads
the same run. Uncertain state blocks another project check; unknown cost stays unknown. Windows
assigns a Job Object before releasing the client. Linux x86-64 uses a process group with inherited
restrictions on leaving that group. Process containment and client tool permissions need separate
proofs. Receipts and indexes live in `vault/local/missions/<UUID>/runs/`; human edits are preserved.

### Inspecionar, escolher e provar / Inspect, choose and check

1. Termine o setup e prepare uma missão pelo [rito de preparação](#mission-workflow).
2. Consulte o executável oficial instalado. No Windows, informe o `.exe` nativo; launchers npm
   `.cmd` não são aceitos. Use `python` onde `python3` não estiver disponível.
3. Escolha modelo e esforço em `youngcrow/agents.json` com `yc-config`. Uma missão já preparada
   conserva as escolhas anteriores; use `revise` para uma alteração explícita naquela missão.
4. Revise os `gaps` e a conexão. Uma pendência impede o diagnóstico. Não troque de conta, modelo
   ou cliente para contornar uma recusa.

```bash
python3 -B scripts/missions.py client inspect --client codex --executable CAMINHO_DO_EXECUTAVEL --json
python3 -B scripts/missions.py client inspect --client claude --executable CAMINHO_DO_EXECUTAVEL --json
```

O catálogo é consultado a cada operação nova. `latest` é resolvido e registrado naquele momento;
não baixa clientes nem garante o lançamento global mais recente. A inspeção usa versão, ajuda,
metadados e status de autenticação oficiais, sem enviar um turno de modelo. Não cria banco ou
recibos do harness. Cada processo de inspeção e seus descendentes usam o mesmo supervisor,
com prazo de 30 segundos e saída limitada. O próprio cliente pode manter caches locais.
O executável precisa ser um arquivo regular, sem link simbólico ou reparse point no caminho.
Hard links usados por instaladores são aceitos para leitura; o hash é conferido novamente antes
da chamada. A inspeção não altera o binário. Backups e arquivos de adoção continuam recusando
hard links. Um catálogo legível pode retornar `native_profile_unverified` e manter a execução bloqueada.

Objetos de resposta e listas de esforços malformados retornam `client_protocol_error`
em JSON, com código 2, sem traceback ou conteúdo bruto do cliente. Confira a versão
e a resposta de descoberta do cliente antes de tentar novamente; campos opcionais
de esforço ausentes continuam representados por lista vazia. `environment show --json`
também classifica falhas de Git na primeira consulta: um timeout retorna
`execution_storage_unprotected`, fase `git_boundary`, motivo `git_query_timeout`.
A consulta conserva o projeto e indica a causa para corrigir o acesso ao Git.

Malformed response objects and effort lists return JSON `client_protocol_error`,
exit code 2, without a traceback or raw client output. Check the installed client
version and discovery response before retrying; missing optional effort fields still
produce an empty list. `environment show --json` also classifies Git failures on the
first query: a timeout returns `execution_storage_unprotected`, phase `git_boundary`,
reason `git_query_timeout`. The query preserves the project and identifies the Git
access failure.

Crie `vault/local/client-check.json` com os UUIDs e a revisão reais. `authorization_ref` registra a
autorização que você concedeu; o texto do modelo não pode concedê-la. Este exemplo usa até 120
segundos, desde que a configuração congelada tenha esse limite. Cada execução nova precisa de
um UUID novo; uma repetição da mesma execução conserva **o manifesto inteiro**.

```json
{
  "schema_version": 1,
  "mission_id": "UUID_DA_MISSAO",
  "mission_revision": 1,
  "role": "pm",
  "operation_id": "UUID_DA_OPERACAO",
  "authorization_ref": "Autorizo um diagnóstico echo-v1 com a conta já autenticada",
  "agent_seconds": 120,
  "max_runs": 1,
  "api_budget_usd": null,
  "fixture_id": "echo-v1"
}
```

```bash
python3 -B scripts/missions.py client check --manifest vault/local/client-check.json --executable CAMINHO_DO_EXECUTAVEL --json
python3 -B scripts/missions.py client runs --mission M001 --json
python3 -B scripts/missions.py --json status M001
```

A prova pede somente a devolução de um identificador JSON. Não aceita prompt, URL, shell ou
capacidade adicional. O recibo separa modelo pedido, resolvido e observado. Esforço observado
fica nulo quando não informado. Custo nulo significa desconhecido; um valor informado pelo
cliente não é confirmação da fatura. Assinatura nunca muda para API implicitamente.

First finish setup and prepare a mission. Inspect the official native executable, then choose
model and effort with `yc-config`; revise an existing mission to change its frozen choices.
Review profile gaps before using the manifest above with real UUIDs and revision. Keep the
entire manifest unchanged when retrying the same operation. A new operation refreshes the
catalog and resolves `latest`; it neither upgrades clients nor guarantees the newest global
release. Inspection sends no model turn and creates no harness database or receipts; the
native client may maintain its own caches.
Each metadata process and its descendants use the supervisor with a 30-second deadline and
bounded output. The executable must be a regular file without symbolic links or reparse points
in its path. Installer hard links are accepted for reading, with the hash rechecked before launch.
Inspection never modifies the binary. Adoption and backup files still reject hard links. A readable
catalog can report `native_profile_unverified` and keep execution blocked.

The check only asks for its JSON nonce back. Arbitrary prompts, URLs, shell and additional
capabilities are rejected. Requested, resolved and observed model values remain separate.
Missing effort or cost stays null. Client-reported cost does not confirm a bill. Subscription
authentication never silently changes to an API connection.

<a id="synthetic-admission"></a>

### Admissão sintética / Synthetic admission

O mesmo `client check` aceita `fixture_id: "isolated-egress-v1"` no manifesto acima.
Todos os demais campos continuam obrigatórios; `api_budget_usd` deve ser `null` e
`max_runs` deve ser `1`. Missão preparada, revisão, autorização, papel e limites são
conferidos antes da gravação. Essa variante entra antes da inspeção de Claude/Codex.

Nesta versão, o resultado é sempre um recibo `purpose: "isolated_egress_check"`,
`state: "failed"`, `reason: "controller_pending"`, `model_calls: 0` e
`effects_allowed: false`. O comando retorna código `1`. Não consulta o executável
informado em `--executable`, que continua obrigatório na sintaxe compartilhada,
nem inicia processos ou reserva o Docker. O recibo não contém observações de modelo,
autenticação, baseline ou candidato.

A tentativa fica em `client runs` e no vault local. Ela consome uma entrada de
`max_agent_runs` e reserva os segundos declarados no orçamento acumulado da missão,
mesmo bloqueada. Repetir o manifesto inteiro devolve o mesmo recibo, sem novo consumo;
alterar seu conteúdo com o mesmo UUID causa `operation_conflict`. Uma versão futura
do controlador não poderá reativar esse UUID.

A admissão não executa A/B/A2. O coordenador interno já persiste esse plano e o baseline
na reserva global. A entrada pública aguarda integração do egress e da restauração
global em 203.6, seguida de prova nativa. Os perfis nativos continuam bloqueados. Consulte o
[handoff](HANDOFF-CLOUD-2026-10-07.md#102-integrar-uma-variante-sintética-em-client-check).

The same `client check` accepts `fixture_id: "isolated-egress-v1"` in the manifest
above. All other fields remain required; `api_budget_usd` must be `null` and
`max_runs` must be `1`. Admission checks the prepared mission, revision, authorization,
role and limits before writing, and branches before Claude/Codex inspection.

This version always returns a receipt with `purpose: "isolated_egress_check"`,
`state: "failed"`, `reason: "controller_pending"`, `model_calls: 0` and
`effects_allowed: false`, with exit code `1`. It does not inspect the executable
passed through the still-required shared `--executable` option, start processes or
reserve Docker. The receipt contains no model, authentication, baseline or candidate
observations.

The attempt appears in `client runs` and the local vault. It consumes one
`max_agent_runs` entry and its declared seconds in the mission's cumulative budget,
even though blocked. Replaying the entire manifest returns the same receipt without
further consumption; changing its contents with the same UUID raises
`operation_conflict`. A future controller cannot reactivate that UUID.

Admission does not execute A/B/A2. The internal coordinator persists this plan and
baseline in the global reservation. Public execution awaits egress and global
restoration integration in 203.6, followed by native proof. Native profiles remain blocked.

<a id="internal-controller"></a>

### Controlador e fixture internos / Internal controller and fixture

`scripts/mission_controller.py` mantém o canal do launcher sob o supervisor existente.
Confere identidade e namespace, registra intenção e autorização antes de cada efeito
e espera `ready` após a inicialização. Aceita somente o comando fixo da fixture e
metadados limitados. A fixture `runtime/sbx/fixture.py` inicializa sem rede e faz uma
GET ao relay local. O contrato v4 confere o hash esperado de um valor fictício distinto
do placeholder; v3 preserva somente a semântica histórica de eco. Está incluída no contexto de build
da imagem; o instalador distribui o controlador e preserva cópias locais existentes.

São componentes internos, sem novo comando público de execução. O `client check`
continua retornando o bloqueio descrito acima. `mission_transaction.py` vincula a
missão ao plano v2, v3 ou v4 no mesmo ledger global. Guarda baseline completo, três identidades
distintas, digests e diário anterior aos efeitos. As fases compartilham até 120 segundos,
limitados pelo orçamento admitido. A execução pública aguarda o contrato de credenciais, adaptador e prova nativa. O controlador retorna sempre
`proof_accepted=false` e `workload_reaped=false`; `observed` indica apenas que o
protocolo da fase foi concluído. Em B, saída 126 continua `blocked_unattributed`;
uma resposta permitida vira `unexpected_allow`.

`scripts/mission_controller.py` keeps the launcher pipe open inside the existing
supervisor. It checks identity and namespace, records intent and authorization before
each effect, and waits for `ready` after initialization. Commands are fixed to the
fixture and results are bounded metadata. `runtime/sbx/fixture.py` initializes without
network and makes one GET through the loopback relay. V4 checks the expected hash of
a dummy value distinct from the placeholder; v3 keeps its historical echo semantics. The
image build context includes it; setup distributes the controller while preserving
existing local copies.

These are internal components with no new public execution command. `client check`
still returns the block above. `mission_transaction.py` binds the mission to a v2, v3 or v4
plan in the same global ledger, storing baseline values, three distinct identities,
digests and a journal before effects. Phases share up to 120 seconds, bounded by
the admitted budget. Public execution awaits the credential contract, native adapter and proof. Controller results always keep `proof_accepted=false` and
`workload_reaped=false`; `observed` only confirms a completed phase protocol. In B,
exit 126 stays `blocked_unattributed`; a successful response becomes `unexpected_allow`.

O plano v3 acrescenta `mission_network.py`, hash do guard e do Python, resolvedor do
sistema e IPs proibidos. O helper recebe configuração somente após persistir seu PID;
os recibos de destino precisam de confirmação durável antes de encaminhar bytes.
Somente `proxy.sandbox` e `no_proxy.sandbox` podem mudar. A recuperação exige cargas/VM
paradas, proprietário e porta ausentes, preserva mudanças externas e observa respostas
perdidas sem repetir mutações. Registros v1/v2 conservam seus contratos.

O adaptador interno deve implementar `setting(key, target, *, expected)` como uma
comparação e escrita indivisíveis. A ativação fornece o setting original completo;
a restauração fornece o setting aplicado, incluindo origem, tipo e default. Se o
estado mudou, a operação deve recusar sem escrita. Uma consulta seguida de `set`
não satisfaz esse contrato. Não há fallback para adaptadores sem `expected`.
A intenção permanece consumida após conflito; observar resposta perdida não repete
a mutação. O suporte atômico do sbx local ainda não foi comprovado, e o adaptador
nativo continua recusando efeitos. [Correção e evidências](relatorios/2026-10-07-conditional-settings.md).

O plano e os manifestos v4 acrescentam `relay.injection_sha256`, recebido pelo
`build_plan(..., injection_sha256=...)` interno junto à configuração de rede.
Placeholder, hash esperado, proxy e CA são iguais em A/B/A2; UUIDs e nonces são
distintos, com prazo compartilhado. Manifesto, argv e recibos contêm apenas o hash do
valor fictício. Não passar credenciais reais a essa interface sintética.

A fixture exige um único header de texto, diferente do placeholder, cujo SHA-256
coincida com o hash imutável. Retorna `schema_version=2`, `injection_matches=true`
e `injected_value_sha256`; não retorna o valor nem o corpo. Hash do próprio placeholder,
comandos alterados ou resposta legada são recusados. O resultado schema 1 de eco
continua válido somente no contrato antigo e não certifica injeção.

Os testes ligam fixture, relay e guard com processos e sockets locais reais; sbx,
TLS e substituição no upstream são simulados. O adaptador nativo recusa set/restart.
A API Cloud documenta `uid`, `etag` e remoção com `If-Match`; ainda falta comprovar
endpoint, armazenamento e operação atômica compatíveis no sbx local 0.46.0. Docker TLS,
MCP e recusa nativa atribuída continuam sem prova; perfis seguem vazios.
[Escopo, fontes e provas](relatorios/2026-10-07-injection-proof.md).

The v3 plan adds `mission_network.py`, guard/Python hashes, the system resolver and
forbidden IPs. Configuration follows the durable helper PID receipt; destination
metadata must be acknowledged before forwarding bytes. Only the two sandbox proxy
settings may change. Recovery requires stopped workloads/VM and absent owner/port,
preserves external changes and observes lost replies without repeating mutations.
Internal `setting(key, target, *, expected)` must compare the complete setting and
write the target indivisibly. Activation supplies the original state; restoration
supplies the applied state, including source, type and default. A mismatch must
refuse without writing. A read followed by `set` is insufficient; adapters without
`expected` receive no unconditional fallback. Intent stays consumed after conflict.
Native atomic support remains unproven, so the native adapter continues to refuse effects.
Legacy v1/v2 contracts remain intact. V4 adds `relay.injection_sha256`, supplied to
internal `build_plan(..., injection_sha256=...)` together with network configuration.
A/B/A2 share placeholder, expected hash, proxy, CA and deadline, keeping separate identities.
Only the hash of the dummy value enters manifests, argv and receipts. This synthetic
interface must not receive real credentials.

The fixture requires exactly one string header, distinct from the placeholder and
matching the immutable hash. Result schema 2 reports `injection_matches=true` and
`injected_value_sha256`, never the value or body. The placeholder's hash, changed
commands and legacy responses are rejected. Schema 1 echo results remain historical.
Tests connect the fixture, relay and guard with real local processes and sockets;
sbx, TLS and upstream substitution are simulated. Native set/restart remains blocked.
The Cloud API documents `uid`, `etag` and `If-Match` deletion, but its endpoint/store
and atomic semantics are unproven for local sbx 0.46.0. Docker TLS, MCP and attributable
native refusal remain unproven; profiles stay empty.

Testes locais / Local tests:

```bash
python3 -B -m unittest discover -s tests -p 'test_mission_controller.py' -v
python3 -B -m unittest discover -s tests -p 'test_mission_transaction.py' -v
python3 -B -m unittest discover -s tests -p 'test_mission_network.py' -v
python3 -B -m unittest discover -s tests -p 'test_mission_egress.py' -v
python3 -B -m unittest discover -s tests -p 'test_isolated_fixture.py' -v
python3 -B -m unittest discover -s tests -p 'test_mission_relay.py' -v
```

Esses testes não usam Docker, fornecedor externo ou modelo. / These tests use no
Docker, external provider or model. [Evidência / Evidence](relatorios/2026-10-07-controller-channel.md).

Para reproduzir a recusa de isolamento encontrada no Codex, consulte a
[prova local](relatorios/2026-10-03-native-client-verification.md). Ela usa uma imagem fictícia
e um fornecedor simulado em loopback, sem conta ou modelo real. Esse teste não libera um perfil.

See the [local probe](relatorios/2026-10-03-native-client-verification.md) to reproduce the Codex
isolation failure with a synthetic image and a loopback provider, without an account or live model.
This test never enables a profile.

Os [controles de permissões](relatorios/2026-10-04-native-permission-controls.md) também testaram
resposta permitida, leitura recusada e gravações internas dos clientes. Um JSON correto ou um
processo com código zero não prova isolamento. Os perfis continuam bloqueados; a proposta de
ambiente separado ainda não tem setup disponível. Não altere a lista de perfis para forçar a execução.

O [desenho aprovado](superpowers/specs/2026-10-04-isolated-executor-design.md) prevê preparação
única do Docker Sandboxes local e login separado. O runtime exige conta Docker; o uso local é
gratuito conforme a documentação consultada, com o consumo dos modelos tratado pela conta escolhida.
No Windows, será necessário Windows 11 x64 e Windows Hypervisor Platform habilitado. A preparação
nunca reinicia o computador automaticamente. O rollback do trial restaura os arquivos do projeto;
runtime do sistema e logins terão um procedimento de remoção separado. Não há comando YoungCrow
de instalação desse executor disponível nesta versão.
O [plano de implementação](superpowers/plans/2026-10-04-isolated-executor.md) organiza a prova
de ambiente, a recuperação e os dois diagnósticos autenticados; foi aprovado e está em execução.

The [permission controls](relatorios/2026-10-04-native-permission-controls.md#english-overview)
also checked an allowed response, denied reads and internal client writes. A correct JSON response
or zero exit code does not prove isolation. Profiles remain blocked; the proposed separate
environment has no setup command yet. Do not edit the profile allowlist to force execution.

The [approved design](superpowers/specs/2026-10-04-isolated-executor-design.md) proposes one-time
local Docker Sandboxes preparation and separate sign-in. It requires a Docker account; the cited
vendor documentation states local runtime use is free, with model usage handled by the chosen account.
Windows requires Windows 11 x64 and Windows Hypervisor Platform. Setup will not restart the host
automatically. Trial rollback restores project files; system runtime and logins will have a separate
removal procedure. This version has no YoungCrow command for installing that executor.
The [implementation plan](superpowers/plans/2026-10-04-isolated-executor.md) covers environment
proof, recovery and both authenticated diagnostics; it is approved and implementation has started.

<a id="sandbox-environment"></a>
### Diagnóstico do ambiente / Environment diagnostic

Para investigar consultas do Docker, acrescente `--preflight` ao comando abaixo.
Essa opção salva evidência sensível em `.operacao-local/execution/sbx-UUID.json`,
com permissões privadas verificadas antes das consultas. Não publique esse arquivo:
ele pode conter valores ou fragmentos de credenciais. O JSON exibido contém apenas
metadados, hashes e categorias de erro; `evidence_path` aponta para a cópia privada.

Cada consulta tem prazo de 15 segundos e limite conjunto de saída de 64 KiB.
O comando para na primeira falha, sem repetir a consulta. `ready: true` significa
que as consultas preparatórias responderam; `effects_allowed: false` mantém o
bloqueio de execução. Se o daemon estiver parado, o preflight para antes das consultas
dependentes. Nenhum comando de criação, reinício, escrita de configuração ou modelo
é emitido. A verificação de permissões do arquivo é separada e pode levar até 120s.

`permission_denied` indica mensagem explícita de permissão; `credential_store_error`
indica referência ao armazenamento de credenciais. `command_failed` exige examinar
a evidência privada antes de concluir a causa. `empty_output`, `invalid_json`,
`contract_incompatible` e `timeout` distinguem os demais casos. Os roteiros antigos
permanecem como evidência e não devem ser reexecutados.

`credential_session_unavailable` reconhece a mensagem de conjunto de credenciais
indisponível na sessão Windows, capturada em `secret ls --json`. O inventário permanece
desconhecido. Execute o mesmo diagnóstico na sessão de desktop do seu usuário quando
ela estiver disponível; confirme o preflight antes de qualquer alteração Docker.
Abrir outro shell dentro do Termius mantém a sessão SSH; a VPN fornece conectividade,
mas não muda o conjunto de credenciais disponível. O tipo de logon observado não foi medido.
O Docker usa o [Gerenciador de Credenciais do Windows](https://docs.docker.com/ai/sandboxes/configuration/credentials/),
cujo conjunto depende da [sessão de logon do token atual](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratea).

Se o servidor já aceitar senha, outra possibilidade é criar uma conexão separada no
Termius com o mesmo host e usuário, usando a senha do Windows e sem selecionar a chave
nessa cópia. Preserve a conexão original. Digite a senha apenas no Termius. Se conectar,
execute somente o preflight; se o login for recusado, pare sem reconfigurar o servidor.
Essa alternativa ainda precisa de prova: o [OpenSSH distingue os contextos de senha e chave](https://github.com/PowerShell/Win32-OpenSSH/wiki/SSH-remote-sessions-on-Windows),
mas essa documentação não garante acesso ao Docker nesse host.

Na prova seguinte, executada diretamente no PowerShell do mantenedor em 7 de outubro,
as 11 consultas passaram: `ready: true`, `effects_allowed: false`, inventário Docker
vazio. Somente `runtime_profile_unverified` permaneceu. Esse resultado resolve o acesso
às consultas naquele contexto; não comprova autenticação Claude/Codex ou isolamento.

Para conferir uma sandbox existente antes da integração, use as duas opções juntas:

```bash
python scripts/missions.py client environment --executable CAMINHO_SBX --preflight --sandbox NOME --json
```

No Windows, esse modo observa PID e criação do daemon, inventário completo de credenciais,
VMs paradas, configurações, políticas e log de política. Confere novamente os dados para
detectar alterações durante a leitura. Saídas brutas ficam no recibo privado. `scope:
candidate_metadata` e `ready: true` confirmam a coleta; `pending` enumera o que ainda
falta para executar. O campo `effects_allowed` continua falso.

`daemon_identity_changed` indica troca do processo; `configuration_changed`, diferença
nos dados comparados. O tempo de atividade do daemon é preservado no recibo, mas não
entra na comparação da inspeção. Campos desconhecidos continuam sendo comparados.
`active_consumer` impede prosseguir com VM em uso. Credenciais personalizadas e fontes
de ambiente também contam no inventário: `secrets: []` sozinho não comprova ausência.
Esse modo passou em 29 consultas locais: 27 do Docker e duas do Windows. A identificação
do processo no runner Linux ainda precisa ser implementada e validada.

O relay de desenvolvimento está ligado ao guardian/launcher e permite um único eco
por operação. Seu manifesto v3 fixa a origem e vincula por hash uma cópia pública
da CA do proxy, guardada no controle privado. A intenção é permitir ao cliente
somente a porta local do relay; o supervisor acessa o endereço exato do proxy.
Os contratos e sockets locais passaram nos testes. Aplicação do firewall Linux,
TLS real e A/B/A2 ainda precisam de prova no novo pacote. `client check` permanece
bloqueado: não há comando adicional de operação nem perfil liberado por esse incremento.

`client environment` também lê `execution_reservation`, sem criar a reserva ou
liberar efeitos. `available` indica ausência de operação pendente nesse registro;
`reserved` ou `consumed` acrescenta `execution_reserved` às lacunas. `unknown`
acrescenta `execution_reservation_unknown`; consulte `reason` e preserve o registro.
O armazenamento é comum aos projetos da conta: `YoungCrowExecution` na pasta local
de dados do Windows obtida pelo sistema, ou na pasta pessoal da conta POSIX.
Não há opção de trocar esse caminho por projeto. Apagar o registro ou alterar suas
permissões não é um procedimento de recuperação.

A reserva v1 consumida permanece bloqueada. O coordenador interno v2 pode recuperar
cargas identificadas e parar a VM, com prazo próprio de até 60 segundos. Observa o
estado após resposta perdida, conserva intenções consumidas e nunca inicia uma VM
parada para inspecioná-la. Uma VM parada sem recibo terminal da carga mantém a reserva.
A recuperação compara configurações e exige identidade do daemon estável durante a
tentativa, aceitando reinício legítimo anterior. Divergência global permanece intacta
e bloqueia encerramento; sua restauração e os helpers/portas entram em 203.6.
Nenhum prazo vencido libera a reserva. [Escopo e provas](relatorios/2026-10-07-reservation-recovery.md).

Se aparecer `execution_storage_unprotected`, consulte `diagnostic.phase` e
`diagnostic.reason`. `temporary_evidence` identifica a verificação do temporário
antes de gravar saídas sensíveis; `existing_storage` identifica a área existente.
`owner_mismatch` aponta proprietário diferente do usuário; `acl_not_private`, acesso
incompatível; `git_exclusion_missing`, exclusão Git ausente. Timeouts distinguem Git
de permissões. Preserve os recibos e informe esses campos; não aplique mudanças
recursivas de proprietário ou permissões para contornar a recusa.

No Windows, o comando define proprietário e ACL privada somente no novo temporário
vazio que ele próprio criou. Confere sua identidade, o diretório e as permissões
antes de gravar dados. Recibos anteriores e o proprietário padrão da sessão são
preservados. Se essa proteção falhar, a operação para sem tentar novamente.

Add `--preflight` to investigate Docker queries. It saves sensitive output under
`.operacao-local/execution/` after checking private permissions; never publish that
file. Displayed results contain metadata, hashes and error categories. Queries have
a 15-second deadline and a combined 64 KiB output limit, stop at the first failure,
and are not retried. File permission checks have a separate 120-second limit.
`ready` describes readable metadata; `effects_allowed: false` keeps execution blocked.
No lifecycle, configuration-write or model command is issued. Preserve historical
proof scripts and receipts instead of rerunning them.

`credential_session_unavailable` identifies the Windows credential-set error captured
from `secret ls --json`. The inventory remains unknown. Run the same diagnostic from
your signed-in Windows desktop session when available; confirm preflight before
changing Docker. Opening another shell in Termius retains the SSH session. VPN
connectivity does not change its available credential set; the logon type was not measured.
Docker uses [Windows Credential Manager](https://docs.docker.com/ai/sandboxes/configuration/credentials/);
its credential set depends on the [current token's logon session](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratea).

If the server already accepts password authentication, another option is a separate
Termius connection to the same host and user, using the Windows password without a
key selected in that copy. Preserve the original connection and enter the password
only in Termius. If login succeeds, run only preflight; if refused, stop without
reconfiguring the server. This option still needs validation: [OpenSSH documents different credential contexts](https://github.com/PowerShell/Win32-OpenSSH/wiki/SSH-remote-sessions-on-Windows),
but does not guarantee Docker access on this host.

The maintainer's subsequent local PowerShell run on October 7 passed all 11 queries:
`ready: true`, `effects_allowed: false`, empty Docker credential inventory. Only
`runtime_profile_unverified` remained. This confirms query access in that context;
Claude/Codex authentication and isolation acceptance remain pending.

Use `--preflight --sandbox NAME` together to inspect a candidate before integration.
On Windows, this adds daemon PID/creation time, complete credential metadata, stopped-VM
inventory, settings, policies and policy-log access. It reads the baseline again to
detect drift. The first local run passed 27 Docker and two Windows queries.
`scope: candidate_metadata` and `ready: true` describe collection only; `pending` lists
the remaining execution gates and `effects_allowed` stays false. Raw output remains
private. Only the observed `daemon_uptime` field is excluded from inspection comparison;
unknown fields still participate. Custom credentials and environment sources count,
so `secrets: []` alone does not establish an empty inventory. Linux daemon identity
still needs implementation and native validation.

The development relay is connected to guardian/launcher and permits one echo per
operation. Its v3 manifest fixes the origin and binds a public proxy-CA snapshot
by hash inside private control storage. The intended boundary permits the client
only the local relay port and the supervisor only the exact proxy address.
Contract and local-socket tests passed. Linux firewall enforcement, real TLS and
A/B/A2 still need proof in the new package. `client check` remains blocked; this
increment adds no operator command and enables no execution profile.

`client environment` also reads `execution_reservation` without creating a reservation
or authorizing effects. `available` means this ledger has no pending operation;
`reserved` or `consumed` adds `execution_reserved` to the gaps. `unknown` adds
`execution_reservation_unknown`; inspect `reason` and preserve the ledger.
Storage is shared across the account's projects: `YoungCrowExecution` under the
Windows local application-data folder resolved by the OS, or the POSIX account's
home directory. Projects cannot override that location. Deleting the ledger or
changing its permissions is not a recovery procedure.

A consumed v1 reservation remains blocked. The internal v2 coordinator can recover
identified workloads and stop the VM within a separate deadline of up to 60 seconds.
It observes state after lost replies, preserves consumed intents and never starts a
stopped VM to inspect it. A stopped VM without a terminal workload receipt retains
the reservation. Recovery compares configuration and requires a stable daemon identity
during the attempt while accepting a legitimate earlier restart. Global drift remains
untouched and blocks closure; restoration and helper/port recovery belong to 203.6.
An expired deadline never releases ownership.

For `execution_storage_unprotected`, inspect `diagnostic.phase` and `diagnostic.reason`.
`temporary_evidence` identifies the temporary-file check before sensitive output is
written; `existing_storage` identifies the existing area. Reasons distinguish owner
mismatch, non-private ACLs, missing Git exclusions and Git or permission timeouts.
Preserve receipts and report those fields. Do not recursively change ownership or
permissions to bypass the refusal.

On Windows, the command sets private ownership and ACLs only on its newly created,
empty temporary file. Identity, directory and permissions are checked before data
is written. Existing receipts and the session's default owner remain unchanged.
A protection failure stops the operation without an automatic retry.

Na raiz do projeto, indique o caminho absoluto do `sbx` instalado:

```bash
python3 -B scripts/missions.py client environment --executable /caminho/absoluto/sbx --json
```

No Windows, use `python` e o caminho do `sbx.exe`, entre aspas se houver espaços.
O comando consulta a versão e o hash do executável e os pré-requisitos do sistema.
Não instala componentes, altera configurações, cria VM, faz login ou chama modelos.
O resultado inclui `gaps` com as pendências e retorna código 1 enquanto houver alguma.
`runtime_missing` indica binário ausente; `whp_disabled` indica o recurso do Windows
desabilitado. `whp_unknown` indica que a consulta não confirmou seu estado.
Se a ativação do recurso retornar `RestartNeeded: True`, salve o trabalho e reinicie
o Windows antes da prova real, mesmo que `whp_state` já seja 1.
Esse campo confirma a configuração do recurso, não uma VM em funcionamento.
`runtime_profile_unverified` permanece em todos os ambientes nesta etapa: versão
detectada e pré-requisitos presentes não comprovam isolamento ou prazo de execução.
Completar `sbx login` também não remove essa pendência. A [prova sintética do supervisor](relatorios/2026-10-04-supervisor-spike.md)
usou uma microVM sem workspace e um contêiner interno, com prazo de cinco segundos.
Ela confirmou parte dos controles; ainda não habilita `client check` com modelos reais.
O ensaio foi preparação manual de desenvolvimento, fora do setup dos projetos consumidores.
O [protocolo do guardian](relatorios/2026-10-04-guardian-protocol.md) já tem prova sintética
em Python: descoberta e diagnóstico compartilham o mesmo prazo, com consumo persistido antes
de cada fase. Uma operação consumida não deve ser reaberta apagando seus marcadores.
Não há novo comando de produção nesta etapa. No checkout de desenvolvimento do harness,
verifique a lógica sem Docker ou modelo:

```bash
python -B -m unittest discover -s tests -p test_mission_guardian.py -v
```

No Windows, esse teste não comprova permissões ou sincronização de diretórios Linux.
O relatório descreve a prova separada na microVM e os controles ainda pendentes.
Para inspecionar uma sandbox existente sem iniciá-la, acrescente `--sandbox NOME`:

```bash
python3 -B scripts/missions.py client environment --executable /caminho/absoluto/sbx --sandbox NOME --json
```

A versão observada usa `ls/inspect/ls` para conferir UUID, nome, imagem e executável.
`mcp_isolation_unverified` significa que ainda falta provar a inacessibilidade do gateway
pelo cliente, inclusive com rede de fornecedor permitida. Nenhum perfil é liberado por
esse comando. A [prova do launcher](relatorios/2026-10-04-launcher-boundary.md) registra
três cenários dentro da VM e duas provas de queda no Windows: coordenador e transporte
`sbx`. O [build nativo](relatorios/2026-10-04-native-kit-build.md) produziu e importou a
imagem sem depender do builder gerenciado que falhou. O resolvedor ainda exige um registry
HTTPS confiável para criar a sandbox; importar o arquivo não basta, mesmo com `--pull never`.
O ensaio com `--pull missing` [criou a sandbox pelo digest esperado](relatorios/2026-10-04-native-package-proof.md),
com 2 CPUs/4 GiB e sem montagem do projeto. O certificado temporário foi retirado e o
inventário original restaurado; origem e portas também voltaram ao estado anterior.
Arquivos protegidos, recusa sem coordenador e três casos do launcher foram comprovados
nessa VM. O [reinício durante trabalho sintético](relatorios/2026-10-04-shutdown-reserve.md)
terminou 3,8935 ms após o limite e permanece reprovado. A candidata reserva um segundo do
prazo para encerramento; recusa criação, início e despacho quando resta apenas essa janela.
O prazo original e o teto de 120 segundos permanecem. Nove cenários sintéticos passaram;
um novo reinício com a candidata terminou 993,6312 ms antes do limite e recusou outro início.
O [ensaio de rede](relatorios/2026-10-04-network-boundary.md) encontrou uma rota MCP pelo
proxy do Docker. A alternativa com saída direta restrita ao IP público do provedor passou
nos casos testados para OpenAI e Anthropic, incluindo processos filhos. Isso comprova
transporte TLS, sem autenticação ou chamada de modelo. A [integração no launcher](relatorios/2026-10-04-network-launcher.md)
passou em oito cenários nativos e nos dois ensaios de provedor. O reinício ativo v2
foi executado e a verificação de prazo falhou. A reconciliação encontrou desligamento
da VM antes do limite e novo boot durante a consulta. A nova prova deve registrar
`ls`/`inspect` com identidade, imagem e horário antes de qualquer `exec`, que pode
iniciar uma VM parada. Um `FinishedAt` recuperado com saída 255 não comprova sozinho
quando a tarefa terminou. O recibo anterior permanece reprovado. O novo ensaio
observou a VM parada 3,756s antes do deadline, conferiu PID0 e recusou repetição após
a retomada. Ambos estão consumidos; não repita nem apague seus recibos. Rotas restantes,
pacote e suspensão continuam pendentes.
O perfil continua bloqueado; não substitua esse gate por uma liberação manual de rede.
Recibos consumidos não devem ser apagados nem reexecutados. As duas provas de
reinício estão preservadas; a candidata usa código separado do pacote anterior.
As exceções de confiança usadas no diagnóstico ficam fora do setup consumidor. A receita em `runtime/sbx/`
continua restrita ao desenvolvimento do harness; não está no setup dos projetos consumidores.
No Windows avaliado, iniciar o serviço pelo PowerShell normal permitiu criar as VMs após
falhas nos sockets quando o serviço partia pelo terminal do agente. Essa comparação não
prova recuperação automática. Não repita login, instalação ou reinício do Windows para
resolver `runtime_profile_unverified`: consulte as pendências do relatório.
Ao migrar, o setup preserva um `mission_sandbox.py` existente, inclusive com `--force`.
Se aparecer `incompatible_helper`, compare os helpers preservados com a versão do harness
e mescle as alterações antes de repetir o diagnóstico.
A CLI verifica o contrato de observação do helper de sandbox antes de consultar o host,
inclusive quando o helper anterior ainda fornece uma função de diagnóstico utilizável.

From the project root, pass the absolute path to the installed `sbx` executable.
On Windows, use `python` and the path to `sbx.exe`, quoted if it contains spaces.
The command reads the executable version and hash and checks system prerequisites.
It does not install components, change settings, create a VM, sign in or call models.
The result lists pending checks in `gaps` and exits with code 1 while any remain.
`runtime_missing` means the binary is absent; `whp_disabled` means the Windows feature
is disabled; `whp_unknown` means its state could not be confirmed.
If enabling the feature returns `RestartNeeded: True`, save your work and restart
Windows before the real proof, even when `whp_state` already reports 1.
That field confirms feature configuration, not a working VM.
Every environment currently reports `runtime_profile_unverified`: discovering a version
and prerequisites does not prove isolation or enforcement of the execution deadline.
Completing `sbx login` does not clear that gap either. The [synthetic supervisor probe](relatorios/2026-10-04-supervisor-spike.md#english-overview)
used a mountless microVM and a nested container with a five-second deadline.
It confirmed some controls; it does not enable `client check` with real models.
This was manual development preparation, separate from consumer-project setup.
The [guardian protocol](relatorios/2026-10-04-guardian-protocol.md#english-overview) now has a
synthetic Python proof: discovery and diagnostics share one deadline, with consumption persisted
before each phase. Do not reopen a consumed operation by deleting its markers.
There is no new production command at this stage. Run the unit-test command above from the
harness development checkout, without Docker or model calls. On Windows, it does not prove Linux permissions
or directory synchronization; the report records the separate microVM proof and remaining checks.
Add `--sandbox NAME`, as shown above, to inspect an existing sandbox without starting it.
The observed runtime uses `ls/inspect/ls` to check UUID, name, image and executable.
`mcp_isolation_unverified` means client access to the gateway still needs to be ruled out,
including with provider networking enabled. This command never enables a profile.
The [launcher proof](relatorios/2026-10-04-launcher-boundary.md#english-overview) records three
in-VM scenarios and two Windows crash cases: coordinator and `sbx` transport loss.
The [native build](relatorios/2026-10-04-native-kit-build.md#english-overview) produced and imported
the image without the failing managed builder. Sandbox creation still requires a trusted HTTPS
registry; loading the archive is insufficient, even with `--pull never`. Using `--pull missing`
[created the sandbox from the expected digest](relatorios/2026-10-04-native-package-proof.md#english-overview),
with 2 CPUs/4 GiB and no project mount. Certificate inventory, source settings and ports were
restored. Protected files, refusal without the coordinator and three launcher cases passed
in that VM. The [active restart test](relatorios/2026-10-04-shutdown-reserve.md#english-overview)
recorded termination 3.8935 ms past the deadline and remains failed. The candidate reserves
one second within that deadline for shutdown and refuses creation, start or dispatch when
only this window remains. The original deadline and 120-second ceiling stay unchanged.
Nine synthetic scenarios passed. During a new restart, the candidate finished 993.6312 ms
early and refused another start. The [network probe](relatorios/2026-10-04-network-boundary.md#english-overview)
found an MCP route through Docker's proxy. Restricted direct egress passed the tested
OpenAI and Anthropic cases, including child processes. This proves TLS transport without
authentication or model calls. The [launcher integration](relatorios/2026-10-04-network-launcher.md#english-overview)
passed eight native cases and both provider probes. Its active restart failed the
deadline check. Host logs show shutdown before the limit and another boot during
inspection. The replacement proof must capture `ls`/`inspect`, identity, image and
time before any `exec`, which may start a stopped VM. Recovered exit 255 and
`FinishedAt` alone cannot establish the task termination time. Preserve the failed
receipt. The replacement observed the VM stopped 3.756s before the deadline, verified
PID0 and refused replay after boot. Both scripts are consumed; do not replay or erase
their receipts. Remaining routes, package rebuilding and suspension still need proof. The profile stays blocked; do not replace
this gate with a manual network allowance. Keep all consumed receipts; the candidate uses
code separate from the earlier package. Global trust changes are outside consumer setup.
The recipe under `runtime/sbx/`
remains limited to harness development and is not installed in consumer projects.
On the tested Windows host, starting the daemon from ordinary PowerShell allowed VM
creation after socket failures when the daemon was launched by the agent terminal.
That comparison does not prove automatic recovery. Do not repeat sign-in, installation
or a Windows reboot to resolve `runtime_profile_unverified`; consult the report's remaining checks.
During migration, setup preserves an existing `mission_sandbox.py`, including with `--force`.
If `incompatible_helper` appears, compare preserved helpers with the harness version
and merge the changes before repeating the diagnostic.
The CLI checks the sandbox helper's observation contract before querying the host,
including when the older helper still exports a working diagnostic function.

### Rede do launcher em desenvolvimento / Development launcher networking

O manifesto v1 usa `network none`. No v2, `network` contém um único `host` e `ipv4`
público fixados por operação. O controlador confiável prepara e inicia o contêiner,
executa `launcher.py network OPERATION_ID NONCE initialize` e só então envia a mensagem
`initialize`. Antes de enviar `dispatch`, executa o mesmo comando com a fase `dispatch`.
Esse segundo passo confere as regras existentes; não as repara.

Ambos os comandos exigem root na VM e gravam um claim antes do efeito. O guardian
recusa iniciar o cliente sem recibo privado correspondente à identidade, fase e namespace.
Uma tentativa interrompida fica consumida: preserve os registros para reconciliação.
Esses comandos pertencem ao teste do runtime, sem liberação de perfil ou instalação
no projeto consumidor. Não reutilize IPs de relatórios como configuração permanente.

No checkout do harness, `python3 -m unittest discover -s tests -p 'test_mission_launcher.py' -v`
verifica o contrato sem Docker ou chamadas de modelo. `tests/smoke_mission_network.py`
exige Linux, root, imagem e launcher previamente preparados numa VM própria; seus oito
casos não alteram a política `sbx` nem chamam provedores. A medição registra as provas
externas separadamente. Testes unitários no Windows não certificam permissões Linux.

A [prova com sentinelas Windows](relatorios/2026-10-05-gateway-endpoints.md) cobriu os
endereços observados do gateway/host com os provedores acessíveis. Foram 124 tentativas
TCP sem conexão e zero acessos às sentinelas; as portas temporárias foram fechadas e
as políticas restauradas. Falha de DNS e erro genérico IPv6 não certificam filtragem.
Esses recibos estão consumidos. A [investigação seguinte](relatorios/2026-10-05-proxy-resolution.md)
mediu DNS direto e proteção dos arquivos de resolução, mas não comprovou o destino final.
O caminho atual também não usa a injeção de credenciais do proxy explícito. Autenticação
e bloqueio de MCP precisam ser resolvidos juntos; perfis continuam bloqueados. A [prova conjunta](relatorios/2026-10-05-auth-egress-spike.md)
passou somente em simulação, com credenciais falsas e destinos locais. Na [prova com o proxy real](relatorios/2026-10-05-native-proxy-compatibility.md),
a substituição funcionou por domínio; o caminho por IP foi recusado em dois serviços de eco.
O candidato ainda não pode ser integrado. A [prova A/B/A](relatorios/2026-10-05-hostname-cidr-proof.md)
recebeu HTTP 200 com credencial fictícia nas três etapas, inclusive com negação de
todos os IPs. O Docker documenta essa separação entre domínio e CIDR. Regras CIDR
não suprem o controle do endereço resolvido nesse caminho. O [desenho do modo exclusivo](superpowers/specs/2026-10-05-exclusive-egress-decision.md)
documenta ativação e retorno para uma instalação do Docker Sandboxes reservada ao
YoungCrow; quem precisar compartilhá-la usaria um runner dedicado. O modo local foi
aprovado, assim como o [plano da prova](superpowers/plans/2026-10-05-exclusive-egress-proof.md).
O [ensaio nativo](relatorios/2026-10-05-exclusive-egress-proof.md) parou na ativação, antes de
GETs ou partidas de VM: a origem real do setting é `override`, enquanto o código esperava `user`.
A suíte passou em 60 testes. A recuperação foi concluída após um reinício pelo mantenedor
e uma conferência final somente leitura: configurações restauradas, cinco VMs paradas,
guard ausente e permissões preservadas. Dois IDs de uma regra automática do kit mudaram
no reinício; essa diferença está registrada. Não há outro comando de recuperação pendente.
`run-exclusive-egress-proof.ps1 -Reconcile` recupera somente a operação existente, sem GET;
seu sucesso não aprova a prova de rede. O recibo permanece consumido. Uma nova prova precisa
de operação e autorização próprias; não há comando de ativação no produto. OAuth, DNS final
e isolamento seguem pendentes.
O operador executou v2; houve `TimeoutExpired` antes da criação do recibo e das alterações
no Docker. A consulta exata que excedeu o prazo não ficou registrada. A conferência posterior
encontrou o mesmo daemon, cinco VMs paradas e configurações, políticas e credenciais preservadas.
Não há recibo v2 para `-Reconcile` recuperar. O roteiro `run-exclusive-egress-v2.ps1` e sua
entrada Python estão bloqueados pelo encerramento do ciclo; nenhum modo inicia uma nova prova.
Não execute outro comando desse ensaio. O resultado de rede permanece inconclusivo.
Não repita os scripts consumidos nem use a fixture como executor.

A [prova observada](relatorios/2026-10-06-observed-egress-proof.md) foi executada e parou
antes das GETs em `settings_readback_failed`. O roteiro exigia `override` ao gravar o
valor padrão de `no_proxy.sandbox`; o Docker remove o override nesse caso. A correção
passou em 75 testes locais. Configurações, regras, inventário de credenciais e porta
temporária foram conferidos após a restauração. Não há limpeza pendente: não repita
`-RunApprovedProbe` nem execute `-Reconcile` para essa saída. Os recibos e a fonte executada
foram preservados. Os hashes do roteiro consumido não foram atualizados; uma operação
futura precisa de escopo e autorização próprios. A prova de rede permanece pendente.

A [continuação corrigida](relatorios/2026-10-06-corrected-egress-proof.md) foi executada.
A passou com HTTP 200 e credencial fictícia correspondente. B recebeu `RemoteDisconnected`,
sem evidência suficiente da recusa do upstream; A2 não foi executada. Limpeza confirmada
por leitura independente. Preserve `corrected-egress-proof/`; não repita o roteiro nem use
`-Reconcile` para essa saída. Não há limpeza pendente. A análise posterior encontrou a recusa na porta do guard no
log do daemon, com sandbox e horário correspondentes. O coletor não reconheceu essa
evidência; A2 continua não executada. Um [coletor separado](relatorios/2026-10-06-captured-egress-evidence.md)
passou em onze testes offline, com snapshots completos e a mensagem real do daemon.
A [ligação com o controlador](relatorios/2026-10-06-integrated-egress-controller.md) foi
validada offline: o fluxo grava B, condiciona A2 ao aceite e recupera sem repetir trabalho.
A entrada da nova prova está preparada, com hashes conferidos e 113 testes locais
aprovados. O resultado nativo continua pendente. Não execute os roteiros consumidos.
[Panorama consolidado](relatorios/2026-10-06-panorama-executor.md).

#### Entrada do ensaio integrado: somente mantenedor

A tentativa `integrated-egress-proof/` está consumida. As cinco consultas iniciais
passaram, mas `unsupported_permissions` interrompeu a execução antes de criar
`control.json` ou alterar o Docker. A pasta tinha o usuário como proprietário;
os três arquivos criados pela sessão remota tinham o grupo Administradores.
A validação exige o usuário também nos arquivos. Não repita o roteiro, não altere
as permissões dos recibos e não execute `-Reconcile`: não há restauração do Docker
pendente para essa tentativa.

O contexto pelo terminal remoto foi conferido com o comando abaixo. Não é necessário repeti-lo:

```cmd
C:\Python314\python.exe -I -B "C:\Users\rmfon\YoungCrowHarness-review-20261001\.superpowers\sdd\2026-10-04-isolated-executor\check_mobile_owner.py" --check
```

Esse diagnóstico privado reutiliza `tests/windows_fixture_runner.py`. O auxiliar
ajusta o proprietário padrão do processo para o usuário atual e restaura esse valor
no `finally`. Cria um arquivo temporário, exige as mesmas validações de permissão e
remove o arquivo e sua pasta vazia. Os hashes dos auxiliares e dos três registros
anteriores são conferidos antes e depois. Não há comando Docker, requisição externa,
reinício ou chamada de IA; as ACLs existentes e a política do Windows são preservadas.

O operador confirmou `owner_context_verified` com `adjusted: true` na sessão do
celular. A verificação local também passou, com `adjusted: false`. Esse resultado
comprova a criação de arquivos privados nesse contexto; a prova de rede continua pendente.

A entrada `run-mobile-egress-proof.ps1` passou pela verificação de proprietário, mas a
tentativa `mobile-egress-proof/` foi consumida por `JSONDecodeError` na primeira consulta
`sbx daemon status --json`. O comando retornou zero; o registro não guardou sua resposta.
Não existem `control.json` ou `receipt.json`; a falha ocorreu antes de alterar o Docker.
Não repita essa entrada nem execute `-Reconcile`: não há limpeza pendente nessa tentativa.

O diagnóstico concluído consultou somente esse status, uma vez, com prazo de 15 segundos.
Reutiliza o contexto de proprietário, salva stdout/stderr originais em uma pasta privada
e registra o resultado da interpretação. Não inicia a prova A/B/A2, não faz GETs nem
reinicia o serviço. A consulta passou localmente com e sem o auxiliar. O operador também
confirmou a captura no terminal remoto: 180 bytes, JSON válido, daemon em execução e
stderr vazio. Os bytes são idênticos aos locais. Comando já executado, sem necessidade de repetir:

```cmd
C:\Python314\python.exe -I -B "C:\Users\rmfon\YoungCrowHarness-review-20261001\.superpowers\sdd\2026-10-04-isolated-executor\check_mobile_status.py" --check
```

O JSON final informa `evidence_dir`, onde ficam `status.stdout`, `status.stderr` e
`status-observation.json`. São registros privados de diagnóstico; preserve a saída.
O auxiliar de proprietário mantém suas verificações de ACL com timeout de 120 segundos.
A etapa inicial original, com seu registrador de comandos, passou depois nas cinco
consultas somente leitura executadas daqui. Todas as sandboxes estavam paradas.
A falha anterior não foi reproduzida; sua resposta original não pode ser recuperada
desses recibos. A nova entrada `captured_mobile_egress.py` integra a captura ao ensaio:
guarda stdout/stderr do comando exato de status antes de devolvê-los ao interpretador.
Cada resposta fica vinculada ao identificador do comando em `status-responses/`.
Os arquivos ficam privados. Comandos de credenciais e outros comandos continuam sem
argumentos ou conteúdo das respostas no registro. JSON inválido e timeout continuam
recusados, sem repetição automática. Respostas maiores que 64 KiB por fluxo deixam
prefixo e hash registrados e interrompem a execução.

A preparação passou em 129 testes, incluindo nove novos. A revisão daquela entrada
não encontrou defeitos acionáveis, mas não cobriu a divergência de identificador no
controlador. **A operação `captured-mobile-egress-proof/` já foi consumida. Não repita
o roteiro.** Suas 24 consultas terminaram antes de qualquer GET, reinício ou alteração
no Docker. Quatro respostas de status foram guardadas e interpretadas corretamente.
O resultado `policy_baseline_changed` veio da comparação literal de um identificador
recriado pela limpeza anterior; as permissões da regra continuavam iguais.
`cleanup.restored=true`, sem erros: não há recuperação por `-Reconcile` pendente.

A correção está ligada à captura e ao controlador por `policy_egress_entry.py`, uma
entrada usada por importação nos testes, com execução direta bloqueada. A sequência
inicial completa passou por status, sete configurações, identidade da VM, políticas e
inventário fictício de credenciais até a primeira ação com efeito externo. As respostas
externas foram simuladas; nenhum comando Docker foi executado. Passaram 12 testes dessa
entrada e 83 do controlador, comparação e fases seguintes. A entrada nativa abaixo
liga essa integração ao adaptador Windows. O aceite real A/B/A2 continua pendente.
O [relatório](relatorios/2026-10-06-integrated-egress-controller.md#comparação-da-política-falha-do-controlador)
separa a causa confirmada do aceite A/B/A2 que continua pendente.

**Entrada consumida em 06/10, às 21h50:** `run-policy-egress-proof.ps1`
chegou ao inventário de credenciais e parou porque `sbx secret ls --json` retornou 1.
A operação `policy-mobile-egress-proof/` registrou 25 consultas e nenhuma alteração,
GET externo, reinício ou chamada de IA. Proprietário, configurações e comparação de
políticas passaram. `cleanup.restored=true`, sem erros: não há limpeza pendente.
Preserve os arquivos; não execute novamente nem use `-Reconcile` nessa operação.

A consulta isolada passou duas vezes no terminal local, uma delas pelo mesmo auxiliar
Windows e diretório temporário privado. Isso não reproduz a sessão remota: o auxiliar
registrou `adjusted=False` aqui e `adjusted=True` no celular. O roteiro não guardou
o stderr da consulta de credenciais; os registros existentes não explicam a causa.
O próximo diagnóstico deve capturar somente o erro dessa consulta no contexto
remoto, sem rodar A/B/A2 ou alterar o Docker. Não há novo comando de ensaio preparado.

Os 102 testes anteriores continuam como evidência da preparação com respostas
simuladas. O aceite nativo e a habilitação do executor permanecem pendentes.
[Diagnóstico](relatorios/2026-10-06-integrated-egress-controller.md#consulta-de-credenciais-falhou-na-sessão-remota) ·
[Medição atualizada](medicoes/native-policy-egress-entry.json).

Os limites da operação consumida eram: até três GETs para `postman-echo.com`, com
credencial fictícia, e até dois reinícios do serviço Docker Sandboxes, com VMs paradas.
O preflight faz até cinco consultas de 15 segundos. Preparação e limpeza têm 180
segundos cada; o ensaio tem 120 segundos, com até 10 por GET. Antes disso, o auxiliar
verifica o contexto Windows; suas verificações de ACL têm timeout próprio de 120 segundos.
Não há chamada de IA, certificado novo ou reinício do Windows.

Só `viable_within_probe` aceita um ensaio nativo; esse aceite não libera o executor do
produto. Esta operação não recebeu esse aceite e já confirmou sua restauração.
Preserve a saída e a pasta; não repita o roteiro nem use `-Reconcile` neste caso.
O auxiliar restaura o proprietário padrão do processo ao sair; a pasta privada de
arquivos temporários permanece como artefato local. O roteiro não integra o setup distribuído.

Manifest v1 uses `network none`. Version 2 binds one public IPv4 and hostname to the
operation. After preparing and starting the container, the trusted controller runs
`launcher.py network OPERATION_ID NONCE initialize` before sending `initialize`.
It runs the same command with phase `dispatch` before dispatching; that phase verifies
existing rules without repairing them. Both root-only commands consume a durable claim
before effects, and the guardian requires the matching private receipt. Interrupted
attempts stay consumed. These are development commands, with no profile activation
or consumer installation. Never reuse report IPs as permanent configuration.

The unit command above runs without Docker or models. The native smoke requires a
prepared owned Linux VM and image; it neither changes `sbx` policy nor calls providers.
The [report](relatorios/2026-10-04-network-launcher.md#english-overview) distinguishes
unit tests, native cases, external transport checks and remaining proof.

The [Windows sentinel proof](relatorios/2026-10-05-gateway-endpoints.md#english-overview)
covered observed gateway/host addresses while provider TLS remained reachable:
124 TCP attempts did not connect and no unexpected connection reached a sentinel.
Temporary listeners closed and policies were restored. DNS failure and generic IPv6
errors do not prove filtering. These receipts are consumed. The [next investigation](relatorios/2026-10-05-proxy-resolution.md#english-overview)
tested direct DNS and resolver-file protection but did not establish the final destination.
The current path also lacks forward-proxy credential injection. Authentication and MCP
isolation need a joint solution; native profiles remain blocked. The [joint probe](relatorios/2026-10-05-auth-egress-spike.md#english-overview)
passed only in simulation with fake credentials and local destinations. In the [real-proxy probe](relatorios/2026-10-05-native-proxy-compatibility.md#english-overview),
substitution worked through hostname CONNECT, while the IP path was rejected on two echo
services. The candidate is not ready for integration. The [A/B/A probe](relatorios/2026-10-05-hostname-cidr-proof.md#english-overview)
returned HTTP 200 with the dummy credential in all three phases, including under
universal IP denial. Docker documents this separation between hostname and CIDR.
CIDR rules do not enforce the resolved address on this path. The [exclusive-mode design](superpowers/specs/2026-10-05-exclusive-egress-decision.md#english-overview)
describes activation and teardown for a Docker Sandboxes installation reserved for
YoungCrow; shared local use would require a dedicated runner. Exclusive local scope
and the [proof plan](superpowers/plans/2026-10-05-exclusive-egress-proof.md) are approved.
The [native attempt](relatorios/2026-10-05-exclusive-egress-proof.md#english-overview) stopped during
activation, before GETs or VM starts: Docker reports `override`, while the code expected `user`.
The suite passed 60 tests. Recovery completed after one maintainer-initiated restart and
final read-only verification: settings restored, five VMs stopped, guard absent and permissions
preserved. Two IDs in an automatic kit rule changed during restart; that difference is recorded.
No recovery command remains pending. `run-exclusive-egress-proof.ps1 -Reconcile` only recovers
the existing operation, without a GET; its success does not approve the network proof. The receipt
remains consumed. A new proof needs its own operation and authorization; no product activation
command is available. OAuth, final DNS and isolation remain unverified. Do not repeat consumed
scripts or use the fixture as an executor.
The operator ran v2; `TimeoutExpired` occurred before receipt creation or Docker changes.
The exact timed-out query was not recorded. Follow-up observation found the same daemon,
five stopped VMs and unchanged settings, policies and credentials. No v2 receipt needs
`-Reconcile`. Both `run-exclusive-egress-v2.ps1` and its Python entry point are blocked by
cycle closure; no mode starts another proof. No further command is required. Network results
remain inconclusive; the closed probe must not be replayed.

The [observed proof](relatorios/2026-10-06-observed-egress-proof.md#english-overview) ran
and stopped before any GET with `settings_readback_failed`. The script expected an
override when assigning the default `no_proxy.sandbox` value; Docker removes the override.
The correction passed 75 local tests. Settings, rules, credential inventory and the
temporary port were checked after restoration. No cleanup remains: do not repeat
`-RunApprovedProbe` or run `-Reconcile` for this result. Receipts and executed source were
preserved; the consumed wrapper was not repinned. A future operation needs its own scope
and authorization. Network enforcement remains unverified.

The [corrected continuation](relatorios/2026-10-06-corrected-egress-proof.md#english-overview)
ran once. A passed with HTTP 200 and the matching dummy credential. B received
RemoteDisconnected without enough evidence of upstream refusal; A2 did not run. Cleanup
was independently verified. Preserve `corrected-egress-proof/`; do not repeat the script
or run `-Reconcile` for this result. No cleanup remains. Later daemon-log analysis attributed the disconnect to guard-port
refusal in the same sandbox and time window. A2 did not run. A [separate collector](relatorios/2026-10-06-captured-egress-evidence.md#english-overview)
passed eleven offline tests with full snapshots and the real daemon event.
[Controller integration](relatorios/2026-10-06-integrated-egress-controller.md#english-overview)
was validated offline, including persistent B evidence, conditional A2 and recovery without
replay. Its 113 local tests passed, but the native attempt stopped after five metadata
queries because its files were owned by Administrators rather than the current user.
No control record, GET, Docker restart or settings change occurred. Preserve the consumed
attempt; no Docker reconciliation is needed. The earlier `check_mobile_owner.py` diagnostic
checked current-user file creation through the existing process-owner fixture adapter,
without Docker or network calls. It retained permission checks and restored the process
token's default owner on exit. Local verification passed with `adjusted: false`; the operator
confirmed `adjusted: true` in the remote session. The separate native entry reused this
adapter, verifies a private file before reservation and keeps existing controller and
cleanup behavior. It records a new single-use `mobile-egress-proof/` operation. Bounds:
three dummy GETs, two service restarts with stopped VMs, five initial queries of 15 seconds,
180 seconds each for preparation and cleanup, and 120 seconds for the probe with 10 per
GET. The preceding owner adapter retains its own 120-second ACL helper timeouts.
Preserve output and receipts; reconcile only pending cleanup. Native acceptance remains
pending and product profiles stay disabled. The subsequent mobile attempt passed the
owner check but failed while parsing the first daemon-status reply, despite exit code
zero. The raw reply was not retained. No control record, Docker changes or cleanup
occurred. Do not repeat that attempt or reconcile it. The current command above captures
one read-only status reply, with a 15-second timeout, under the owner adapter. Both local
status queries passed. The remote capture then passed too: 180 bytes, valid JSON,
running daemon and empty stderr, matching the local output byte for byte. All five
original preflight queries also passed locally through the command recorder, with
every sandbox stopped. No replay of the diagnostic is needed. The historical failure
remains unexplained. The separate captured entry now retains exact daemon-status replies
before parsing, correlated by command ID under private `status-responses/`. Other command
payloads remain unrecorded. Timeout and JSON failures still refuse; there are no automatic
retries. A 64 KiB limit per stream preserves a prefix/hash and refuses oversized replies.
The preparation suite passed 129 tests, including nine new cases. That entry's review
did not cover the controller's rule-ID mismatch. The operation has now been consumed:
24 queries, four valid captured status replies, no GET, restart or Docker changes.
It stopped on `policy_baseline_changed` because earlier cleanup regenerated a rule ID
without changing its permissions. Cleanup is verified; no replay or reconciliation
is needed. The correction is now connected to capture and recovery through an import-only
entry; its direct CLI remains disabled. Twelve tests exercise the full initial sequence
through seven settings, VM identity, policies and a synthetic credential inventory,
stopping at the first external-effect boundary. Another 83 controller/comparison/phase
tests passed. External replies were simulated; no Docker command was executed. The new
`run-policy-egress-proof.ps1` entry now connects this integration to the Windows owner
adapter and the separate `policy-mobile-egress-proof/` operation. It pins Python, sources
and prior receipts; SHA-256 uses .NET rather than requiring `Get-FileHash`. The actual
owner adapter reached the full initial sequence in tests with simulated Docker replies.
The operator has now consumed this entry. It stopped when `sbx secret ls --json`
exited 1 after ownership, settings and policy checks passed. All 25 commands were
read-only, with no external GET, restart or Docker mutation. Cleanup is verified;
do not replay or reconcile this operation. Two local queries passed, one through
the existing owner helper, but the local owner required no adjustment whereas the
remote owner did. The controller did not retain the failed query's stderr, so its
cause remains unknown. The next diagnostic must obtain only that query's error in
the remote context before another full probe is prepared. No new probe command is available.
Native A/B/A2 acceptance is still pending.
[Consolidated overview](relatorios/2026-10-06-panorama-executor.md#english-overview).

### Destinos de execução previstos / Planned execution locations

O [escopo aprovado](superpowers/specs/2026-10-05-local-and-dedicated-execution.md) mantém
duas opções: execução local como padrão para quem abre o projeto no VS Code e runner
dedicado opcional, em outra máquina ou servidor. A mesma esteira deve atender Claude Code
e Codex em ambos. O setup aceita `--execution-location local|dedicated`; omitir a flag
preserva uma escolha anterior e usa local apenas quando não há registro.
O [desenho aprovado](superpowers/specs/2026-10-05-execution-setup-design.md) usa o VS Code
Remote SSH para abrir o projeto do runner e executar o harness naquele host. O
[plano](superpowers/plans/2026-10-05-execution-setup.md) foi implementado nesta branch.
As oito combinações de adoção/restauração passaram; consulte o
[relatório e os limites da prova](relatorios/2026-10-05-execution-setup.md). O
[guia instalado PT/EN](../skills/personalizer/references/execution.md) cobre projeto novo,
migração, troca autorizada por digest e diagnóstico com limites por etapa.

O destino local depende da disponibilidade da máquina do desenvolvedor. O runner exige
ambiente e autenticação próprios; a transferência prevista em YC-208/209 conserva um
único responsável e exclui credenciais. Dev Container será uma opção de padronização de
dependências, sem substituir as provas de isolamento. Nenhum perfil autônomo foi liberado.

The [approved scope](superpowers/specs/2026-10-05-local-and-dedicated-execution.md#english-overview)
retains two locations: local execution by default for VS Code users, and an optional
dedicated machine or server. The same pipeline must support Claude Code and Codex in both.
Setup accepts `--execution-location local|dedicated`. Omitting it preserves an existing
choice and defaults to local only when no record exists.
The [approved design](superpowers/specs/2026-10-05-execution-setup-design.md#english-overview)
uses VS Code Remote SSH to open the runner's workspace and run the harness on that host.
The [plan](superpowers/plans/2026-10-05-execution-setup.md) is implemented on this branch.
All eight adoption/restore combinations passed; see the
[evidence and limitations](relatorios/2026-10-05-execution-setup.md#english-overview). The
[installed guide](../skills/personalizer/references/execution.md#english) covers new/existing
projects, authorized digest-based changes and bounded phase diagnostics.

Local execution requires the developer's machine to remain available. A runner needs its
own environment and authentication. Planned YC-208/209 transfer preserves a single owner
and excludes credentials. An optional Dev Container can standardize dependencies without
replacing isolation evidence. No autonomous execution profile has been enabled.

### Interrupção e recuperação / Interruption and recovery

Consulte primeiro a seleção e o diagnóstico / Read selection and diagnostics first:

```bash
python3 -B scripts/missions.py environment show --json
python3 -B scripts/missions.py environment configure --location dedicated --expected-digest DIGEST --json
python3 -B scripts/missions.py client environment --executable /path/to/sbx --json
```

Use o digest de `show`; `none` vale só para arquivo ausente. Consulta não cria arquivo,
banco ou nota. Mudança de preferência não transfere missões. Um lock ocupado exige nova
consulta, sem apagar estado. Use the current digest; `none` applies only to an absent
record. Read-only queries create no state. Selection changes do not transfer missions.

A consulta e a troca do destino usam o mesmo lock da seleção. Se outra operação
estiver usando esse lock, `environment show` ou `configure` retorna
`execution_selection_busy`; consulte novamente depois que ela terminar. Não apague
`reclaim.lock`: o arquivo permanece após a liberação pelo sistema operacional.
Um digest antigo retorna `execution_selection_conflict`, sem uma segunda gravação.
A consulta aceita lock vazio ou somente leitura e não o modifica. Proteção inválida
continua sendo recusada; esse controle cobre a seleção, não todos os recibos da área.

Selection reads and updates use the same lock. If another operation holds it,
`environment show` or `configure` returns `execution_selection_busy`; query again
after that operation finishes. Keep `reclaim.lock`: its file persists after the OS
releases the lock. A stale digest returns `execution_selection_conflict` without a
second write. Queries leave empty or read-only locks unchanged. Unsafe storage is
still rejected. This coordination covers selection, not every receipt in the area.

Exemplo abreviado de fixture sintética / Abbreviated synthetic fixture example:

```json
{"id":"virtualization","started_at":"2026-10-05T00:00:00+00:00","ended_at":"2026-10-05T00:00:30+00:00","elapsed_seconds":30.01,"timeout_seconds":30,"output_limit_bytes":8388608,"state":"timeout","reason":"timeout"}
```

A consulta de versão ainda pode passar; `runtime_profile_unverified` mantém o bloqueio.
Essa saída não comprova falha de rede nem execução em runner real. As fases não incluem
stdout, ambiente ou credenciais. Helpers preservados incompatíveis exigem comparação e
mesclagem. Um trial com restaurador antigo incompatível deve ser encerrado pelo runner
original antes de uma nova adoção, sem substituir seus arquivos.

The independent version query can still pass; `runtime_profile_unverified` keeps execution
blocked. This fixture proves neither network failure nor a real runner. Phases omit raw
stdout, environment and credentials. Preserved incompatible helpers need comparison and
merging. Exit an incompatible older trial using its original restore runner before adopting
again; keep its files unchanged.

`client runs` e `status` só leem. Não migram o banco, não corrigem notas nem iniciam processos.
O primeiro diagnóstico autorizado migra o esquema 1 para 2 numa transação aditiva. Uma falha
na projeção deixa `pending`; repetir o mesmo manifesto recupera a nota sem repetir o modelo.
`conflict` preserva uma edição humana e requer comparação manual.

Se o coordenador cair, consulte os recibos e repita **o mesmo manifesto**. Depois de liberar o
cliente, timeout, cancelamento, queda ou saída inválida ficam `uncertain` quando não há resultado
conclusivo validado. Encerrar os processos não confirma o efeito no fornecedor. Nenhum UUID novo
permite contornar esse bloqueio. Confira término dos processos e efeito externo antes de
reconciliar. Guarde a análise em arquivos privados e referencie seus bytes exatos num JSON,
por exemplo `vault/local/client-evidence.json`. Notas Markdown precisam dos metadados do vault;
use `.txt` para evidência em texto simples.

```json
{
  "authorization_ref": "Revisão do operador: processo encerrado e efeito externo conferido",
  "termination": {"path": "vault/local/termination.md", "sha256": "SHA256_REAL"},
  "external_effect": {"path": "vault/local/external-effect.md", "sha256": "SHA256_REAL"}
}
```

```bash
python3 -B scripts/missions.py client reconcile --run UUID_DO_RUN --evidence vault/local/client-evidence.json --expected-revision REVISAO_ATUAL --operation-id UUID_DA_RECONCILIACAO --json
```

Runs ligadas ao plano global v2 recusam esse comando com `integrated_recovery_required`;
seu encerramento exige observação interna e preserva os limites reservados.

Hash prova a identidade do arquivo, não a veracidade do relato. A reconciliação exige também
que o processo registrado esteja encerrado; nunca mata um PID fornecido pelo operador. O
resultado é `interrupted`, conservando tentativa, reserva de tempo e custo desconhecido.
Os limites contam reservas anteriores, inclusive falhas. Criar outro UUID não renova o orçamento.

Runs bound to a global v2 plan reject this command with `integrated_recovery_required`;
closure requires internal observations and preserves reserved limits.

`client runs` and `status` only read: no migration, repair or process launch. The first authorized
check migrates schema 1 to 2 atomically. Repeating a manifest repairs a pending projection without
calling the model again; human edits produce a preserved conflict. After a crash, read receipts
and retry the same manifest. `uncertain` blocks new operations until operator reconciliation.
After releasing the client, timeout, cancellation, a crash or invalid output remains uncertain
without a validated conclusive result. Reaping processes does not prove the provider's outcome.
Review process termination and external effects, then bind private evidence files by SHA-256
using the command above. Hashes identify bytes, not truth. Reconciliation also requires the
recorded process to be gone; it never kills an operator-supplied PID. It records `interrupted`
without resetting attempts, reserved time or unknown cost. Failed runs still consume limits.
Markdown evidence requires vault metadata; use `.txt` for plain text.

No Windows, prefira um caminho curto para `--backup-root` ao testar o harness. Os recibos
aninhados de missão também entram no snapshot de retorno e podem exceder o limite conservador
de caminhos da adoção. O runner recusa esse caso antes da troca; preserve o snapshot e resolva
o caminho indicado pelo diagnóstico.

On Windows, use a short `--backup-root` when trying the harness. Nested mission receipts also
enter the return snapshot and can exceed adoption's conservative path limit. The runner rejects
that case before swapping directories; preserve the snapshot and resolve the reported path.

| Código / Code | Ação / Action |
|---|---|
| `unsupported_policy` | Confira a matriz de perfil; não contorne o bloqueio / check the profile matrix; do not bypass it |
| `unsupported_combination` | Escolha modelo/effort presente no catálogo / choose an advertised model/effort |
| `connection_conflict` | Resolva a conexão configurada; não imprima credenciais / resolve the selected connection without printing credentials |
| `stale_observation` | Binário ou política mudou; uma nova operação exige nova inspeção / binary or policy changed; a new operation requires inspection |
| `unresolved_run` | Retome o recibo pendente antes de outra prova / recover the existing receipt before another check |
| `operation_conflict` | O UUID já pertence a outro conteúdo / the UUID already identifies different input |
| `limit_exceeded` | A reserva supera o limite congelado / the reservation exceeds frozen limits |
| `insufficient_evidence` | Processo ativo ou evidência incompleta: mantenha o bloqueio / active process or incomplete evidence: retain the block |

Saída 0: consulta sem pendência ou diagnóstico concluído. Saída 1: `gaps`, execução interrompida,
falha, incerteza ou conflito de projeção; uma reconciliação para `interrupted` também retorna 1.
Saída 2: entrada/combinação recusada. Confira sempre o JSON. Perfis são verificados por cliente,
sistema, versão e hash do executável; atualizar o cliente pode exigir nova prova de isolamento.
API, macOS e outras arquiteturas sem prova continuam bloqueados. Veja a
[matriz da entrega](relatorios/2026-10-03-mission-runtime-adapters.md).

Exit 0 means a query without gaps or a successful check. Exit 1 includes profile gaps, interrupted,
failed or uncertain runs and projection conflicts; reconciliation to `interrupted` also returns 1.
Exit 2 means rejected input/combination. Always read the JSON. Profiles bind the client, OS, version
and executable hash; a client update can require a new isolation proof. API, macOS and unverified
architectures remain blocked. See the [delivery matrix](relatorios/2026-10-03-mission-runtime-adapters.md).

<a id="tests-windows"></a>

### Testes do harness no Windows / Harness tests on Windows

No checkout de desenvolvimento, use o runner de testes para conferir proprietário e permissões
das fixtures. Python, Git e Git Bash precisam estar instalados. Escolha um diretório curto,
gravável e fora de qualquer repositório Git para `RUNNER_TEMP`; o runner cria uma subpasta privada
exclusiva e imprime o caminho. Não use a raiz do projeto como pasta temporária.

In the development checkout, use the test runner to verify fixture ownership and permissions.
Install Python, Git and Git Bash. Set `RUNNER_TEMP` to a short writable directory outside Git;
the runner creates a unique private child and prints its path. Do not use the project root.

```powershell
# Exemplo / Example: perfil curto, fora de Git / short profile path, outside Git.
$previousTestTemp = $env:RUNNER_TEMP
try {
    $env:RUNNER_TEMP = $env:USERPROFILE
    python -X utf8 -B tests/windows_fixture_runner.py -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Harness tests failed' }
} finally {
    $env:RUNNER_TEMP = $previousTestTemp
}
```

Se o perfil também tiver caminho longo, escolha outro diretório existente com permissão de escrita.
No host avaliado, a reserva de trial projetava 256 unidades UTF-16 usando o TEMP padrão e 237
com a raiz curta; a adoção exige menos de 248. O runner mantém a validação de ACL e o produto
continua recusando caminhos excessivos antes da escrita. Nenhuma política global do Windows é alterada.

A fixture MCP publica o PID depois de fechar sua gravação, sem substituir registro existente.
Se houver publicação pendente, a limpeza fica incompleta. Esses testes são sintéticos e não
chamam modelos. Resultados e limites: [relatório de QA](relatorios/2026-10-04-qa-fixtures.md).

If the profile path is also long, choose another existing writable directory. On the evaluated
host, the projected trial path measured 256 UTF-16 units under the default TEMP and 237 under
the short root; adoption requires fewer than 248. ACL checks and path refusal before writes
remain active. No global Windows policy changes. The synthetic MCP fixture publishes its PID
after closing the write, without replacing an existing record. Pending publication means
incomplete cleanup. These tests make no model calls. See the [QA evidence](relatorios/2026-10-04-qa-fixtures.md#english-overview).

### Diagnóstico de testes no GitHub Actions / Test diagnostics in GitHub Actions

A etapa de missões Windows usa o wrapper de ACL existente e a entrada abaixo:

```powershell
python -B tests/windows_fixture_runner.py tests/ci_unittest.py discover -s tests -p "test_mission*.py" -v
```

Com `GITHUB_ACTIONS=true`, `ci_unittest.py` publica um identificador por teste falho,
com erro ou sucesso inesperado nas anotações da etapa. Subtestes usam o ID do teste pai;
mensagens de exceção e valores de parâmetros não entram nessas anotações. IDs fora do
formato convencional viram `test_identifier_unavailable`. A saída normal e o código de
saída continuam sob controle do unittest; localmente, sem essa variável, não há anotações.

As anotações exigem a conclusão da suíte. Cancelamento, timeout ou falha no wrapper
antes do unittest exigem consultar o log da etapa com acesso ao GitHub. O CI de
`da28f00` falhou nessa etapa; a causa ainda está em diagnóstico. Veja a
[evidência](relatorios/2026-10-07-windows-ci-diagnostics.md). Essa suíte usa fixtures;
não executa um ciclo de aceite nativo do sbx.

The Windows mission step keeps the existing ACL wrapper and uses the entry point
above. With `GITHUB_ACTIONS=true`, it annotates failure/error/unexpected-success test
IDs, deduplicating subtests under their parent and excluding exception messages and
parameter values. Nonstandard IDs become `test_identifier_unavailable`. Standard
unittest output and exit status remain unchanged; local runs emit no annotations
without that variable. Annotations require suite completion, so cancellation, timeout
or earlier wrapper failure still requires access to step logs. CI at `da28f00` failed
in this step and remains under diagnosis. These fixture tests do not run a native
sbx acceptance cycle.


Os testes integrados de rede também publicam uma anotação por caso com estados e
códigos de uma lista fixa, duração, código de saída e contagens. Saída dos processos,
texto de exceções, caminhos e identidades ficam fora da projeção. Valores desconhecidos
viram `other`. A anotação roda depois que a fixture restaura o ambiente do chamador.
O workflow executa primeiro os quatro casos `NetworkBindingTests` e o caso de encerramento
abrupto; a suíte completa permanece depois deles. Se o diagnóstico falhar, os passos
seguintes ficam pulados e o job continua falho. Não interpretar a rodada focal como
execução de toda a suíte Windows.

Integrated network tests also publish one notice per case with allowlisted states,
elapsed time, exit code and counts. Process output, exception text, paths and identities
are excluded; unknown codes become `other`. The notice runs after fixture environment
restoration. The workflow first runs the four NetworkBinding cases and the abrupt
shutdown case, retaining the full suite afterwards. A focused failure skips later
steps and keeps the job failed; focused execution is not full Windows coverage.


A sonda local de B registra apenas a classe de uma exceção inesperada em arquivo da
fixture e a propaga. A anotação aceita nomes de uma lista fixa; não inclui mensagem,
endereço ou conteúdo de processo. Uma exceção continua falhando o teste.
The local B probe records only an unexpected exception class in its fixture and
re-raises it. Annotations allow only fixed class names, excluding messages, addresses
and process content. The exception still fails the test.


No percurso local v3, B só é reconhecida quando a conexão recebe
`ConnectionRefusedError`. O CI confirmou que o corte anterior de um segundo podia
produzir `TimeoutError` no Windows. A sonda usa agora o prazo restante do manifesto,
com a reserva de encerramento do controlador. Timeout e conexão bem-sucedida
continuam falhando. Os limites do supervisor (15 s) e do plano (30 s) permanecem.

In the local v3 flow, B is recognized only after `ConnectionRefusedError`. CI confirmed
that the previous one-second cutoff could produce `TimeoutError` on Windows. The
probe now uses the manifest's remaining deadline, preserving the controller's shutdown
reserve. Timeout and successful connection still fail. Supervisor (15 s) and plan
(30 s) limits remain unchanged.


Mesmo sem stdout após timeout, o diagnóstico tenta ler o ledger persistido. Publica
contagens e listas de tempos relativos ao início do supervisor para cada fase, em
milissegundos. Aceita no máximo 60 inteiros de 0 a 3.600.000 por lista; não publica
timestamps absolutos, payloads ou identidades. Falha na coleta preserva o assert original.

After a timeout with no stdout, diagnostics still attempt to read the durable ledger.
Per-phase lists report event times relative to supervisor start in milliseconds. Each
list accepts at most 60 integers from 0 to 3,600,000, excluding absolute timestamps,
payloads and identities. Collection failures preserve the original assertion.


Checkpoint `e674a83`: suíte pública local com 618 testes, 598 aprovados e 20 pulados;
cinco focais Windows passaram nos runs de push e PR. A suíte Windows completa ainda
estava em andamento. Um focal verde não encerra a investigação dos timeouts anteriores.

Checkpoint `e674a83`: 618 local public tests, 598 passes and 20 skips; all five focused
Windows cases passed on push and PR. Full Windows CI was still running. A focused
pass does not resolve the earlier intermittent timeout investigation.


### Verificação das regras privadas / Private ignore verification

As consultas de missão e memória verificam novamente os caminhos privados antes
de ler o armazenamento. O preflight consulta as três regras de ignore em uma só
chamada Git e exige correspondência para todas. Remover uma regra, rastrear um
arquivo privado ou receber erro do Git continua bloqueando a operação. A consulta
não corrige `.gitignore` e não reutiliza resultados de chamadas anteriores.

Mission and memory queries recheck private paths before reading storage. Preflight
checks all three ignore rules in one Git invocation and requires every path to
match. Removing a rule, tracking a private file or receiving a Git error still
blocks the operation. Verification neither repairs `.gitignore` nor caches earlier
results. See the [measurement](relatorios/2026-10-08-git-preflight-cost.md#english-overview).

Para uma missão existente, `missions.py status` faz três leituras do banco: missão, revisões/eventos/projeções
e execuções do cliente. As consultas SQL adjacentes compartilham uma conexão; cada
leitura mantém o preflight atual. O banco é reaberto após os arquivos de entrada.
Remover o banco nesse intervalo retorna `invalid_store`; trocar o banco ou mudar
uma revisão pode marcar `stale_inputs`. A consulta continua sem escrita e sem cache.

Nos testes de rede, o observador fica no controlador. A recusa recebe um payload
antecipado e precisa comprovar zero bytes até EOF, após encerrar o guard e coletar
a thread. O controle positivo exige 13 bytes. Essa prova usa sockets locais e não
substitui o aceite nativo do executor. [Relatório](relatorios/2026-10-08-mission-read-stability.md).
Uma observação incompleta continua reprovando o teste. No CI, a anotação expõe
somente os booleanos `accepted`, `eof`, `complete`, a contagem limitada de bytes
e um código de erro permitido. O negativo faz oito tentativas independentes para
exercitar o encerramento concorrente do helper.
O controlador fecha a entrada do helper e permite até 100 ms para limpeza
cooperativa. Essa espera usa o saldo dos 200 ms já destinados a `terminate` e
respeita o prazo restante. Com prazo expirado, segue direto ao encerramento
forçado; `kill` e a coleta da árvore continuam disponíveis.

For an existing mission, `missions.py status` reads the database three times: mission, item revisions/events/
projections, and client runs. Adjacent SQL queries share a connection; each read
retains current preflight checks. The database reopens after input files. Removal
during that interval returns `invalid_store`; replacement or a changed item revision
can mark `stale_inputs`. Status remains read-only and uncached.

Network tests keep the observer in the controller. Refusal receives an early
payload and must establish zero bytes through EOF after guard shutdown and thread
collection. The positive control requires 13 bytes. This local socket proof does
not replace native executor acceptance. [Report](relatorios/2026-10-08-mission-read-stability.md#english-overview).
Incomplete observations still fail the test. CI annotations expose only the
`accepted`, `eof`, `complete` booleans, a bounded byte count and an allowed error
code. The negative case performs eight independent attempts to exercise concurrent
helper shutdown.
The controller closes helper input and allows up to 100 ms for cooperative cleanup.
This wait uses the remaining portion of the existing 200 ms termination stage and
respects the execution deadline. Expired deadlines skip grace; forced shutdown,
`kill` and process-tree collection remain available.

<a id="queue-rehearsal"></a>
## Ensaio persistente da fila / Persistent queue rehearsal

O ensaio usa os PBIs de uma missão preparada, na prioridade congelada dessa missão.
Ele registra etapas e resultados no SQLite privado. Executa um PBI por vez: prioriza
seu QA e suas correções e então escolhe o primeiro item pendente cujos
predecessores concluíram o ensaio na mesma sessão. Ciclos ou dependências ausentes
continuam impedindo o preparo válido da missão.
O executor determinístico calcula um resultado local; o QA simulado confere seu hash.
Não há chamada de modelo, edição de código, worktree ou aprovação real de entrega.

Use `list` e `status M001` para escolher a missão e conferir sua revisão. Para cada
novo comando de escrita, gere um UUID (por exemplo, `python3 -c "import uuid; print(uuid.uuid4())"`).
Guarde o UUID junto com os argumentos. No Windows, use `python` no lugar de `python3`.
Substitua os nomes em maiúsculas abaixo pelos valores obtidos:

```bash
python3 -B scripts/missions.py --json queue start M001 --expected-revision 1 --operation-id UUID_INICIO --actor-id operador
python3 -B scripts/missions.py --json status M001
python3 -B scripts/missions.py --json queue step UUID_SESSAO --expected-revision 1 --operation-id UUID_DEV --actor-id operador
python3 -B scripts/missions.py --json queue step UUID_SESSAO --expected-revision 2 --operation-id UUID_QA --actor-id operador
python3 -B scripts/missions.py --json status M001
```

O exemplo acima cobre um PBI. Com vários, continue `queue step` usando a revisão
retornada após cada comando até a sessão atingir `fixture_completed` ou `waiting`.
Em `waiting`, consulte os bloqueios e cancele o ensaio quando necessário. No cenário padrão,
são dois avanços por PBI. O QA de um item pode devolver `dev_pending` com o próximo PBI selecionado.

Para exercitar reprovações, escolha `--fixture-scenario` no comando `queue start`:

| Cenário | Comportamento do primeiro PBI elegível |
|---|---|
| `pass` (padrão) | Aprova o primeiro QA |
| `qa-retry` | Reprova o primeiro QA e aprova após uma correção |
| `qa-exhaust` | Reprova o primeiro QA e as três correções; bloqueia o PBI |

O cenário e o PBI alvo ficam congelados na sessão. Os demais PBIs usam aprovação inicial.
A opção só existe em `start`; ela não permite fornecer um resultado ou executar comandos.
Um cenário diferente exige outro ensaio, não uma alteração no ensaio em curso.

`correction_pending` pede outro `step` para despachar a correção simulada. O campo
`items[].correction_cycles` começa em zero e aumenta nesse despacho, não na reprovação.
Cada ciclo inclui a correção e seu QA. Após a terceira correção reprovada, o item vira
`blocked`; os independentes podem avançar. Se não houver item elegível e restarem itens
não concluídos, a sessão vira `waiting`. O status orienta `inspect_rehearsal_blockers`
com motivo `correction_limit_reached`. A espera ocupa a vaga da sessão, recusa `step`
e permite `cancel`; nenhum processo fica suspenso esperando uma resposta.

O contador pertence à sessão sintética: reinício, replay e falha transacional não o
renovam. Novos ensaios são independentes. Este incremento não implementa o ledger real
de autocorreção entre missões, revisões ou IDs; YC-303 continua pendente.

O primeiro `--expected-revision` é a revisão da missão. Nos avanços, é a revisão da
sessão retornada em `session.revision`. O UUID da sessão está em `session.id`.
`status.queue_sessions` mostra escopo, resultados, histórico de recibos, próximo papel
e `next_action`. Em sessões v2/v3, `items` lista estado e `waiting_on` de cada PBI,
na prioridade congelada. Os campos `pbi_id`, `pbi_code` e `pbi_revision` identificam
o candidato atual e ficam nulos ao concluir todos os itens ou entrar em espera.
`dependency_basis: rehearsal_results` limita a liberação de dependências à simulação.
Por exemplo, prioridade `[C(depende de B), D, B(depende de A), A]` executa
`D → A → B → C`, com Dev e QA de cada um. `fixture_completed` conclui apenas o ensaio; desenvolvimento, QA,
integração e produção reais conservam seus estados anteriores.

Após perder a resposta ou interromper o processo, repita o comando com os mesmos
argumentos e UUID. A mesma operação devolve o recibo original, mesmo que a sessão já
esteja mais adiantada; consulte `status` para o estado atual. UUID com pedido diferente
ou revisão antiga em uma nova operação é conflito. Uma queda antes do commit pode
repetir cálculo puro, mas não cria dois resultados persistidos. Isso não demonstra
execução externa exatamente uma vez.

Há uma sessão ativa por repositório e uma sessão por revisão da missão. Para encerrá-la
antes do fim, use `queue cancel UUID_SESSAO --expected-revision REVISAO_SESSAO
--operation-id UUID_CANCELAMENTO --actor-id operador` com os mesmos prefixos dos comandos
acima. O cancelamento mantém o histórico e funciona mesmo se a missão mudou.
Outro ensaio da mesma missão exige uma revisão nova, preparada explicitamente.

Lacunas, fontes alteradas, projeções pendentes/conflitantes e diagnósticos nativos abertos
impedem avançar. A orientação aparece na própria sessão. `cancel_stale_rehearsal` pede
encerrar um ensaio ligado à revisão anterior da missão. O cancelamento não altera ou
libera diagnósticos nativos. A prévia `initial_backlog` continua independente dos resultados
sintéticos; nenhum deles satisfaz uma dependência integrada.

A primeira nova escrita aceita da fila migra bancos antigos para o esquema 5, sem criar
novas tabelas nesse incremento. Quando o banco já está no esquema 6, ele é preservado. O índice de sessão ativa passa a incluir correções e espera.
Leituras e replay exato conservam o esquema anterior. Sessões v1/v2
continuam pelo fluxo original; seus recibos não são reescritos. Atualize em conjunto
`missions.py`, `mission_store.py`, `mission_runs.py` e `mission_queue.py`; o instalador
preserva helpers existentes para comparação e conciliação. Uma mistura incompatível
retorna `incompatible_helper`. Versões antigas do harness não devem abrir o banco migrado.
Leituras de status nunca migram o banco. O arquivo permanece em
`vault/local/operations/state.sqlite3` e precisa acompanhar o backup privado do projeto.

The commands above run a persistent deterministic rehearsal. Multiple PBIs run
serially: QA of the active item precedes new development; saved priority selects
the next item whose predecessors completed this same rehearsal. `items` exposes
per-PBI state and `waiting_on`. This simulated dependency basis never grants real
integration. Repeat `step` with the returned session revision until `fixture_completed`
or `waiting`. In `waiting`, inspect blockers and cancel the rehearsal when needed.
The default scenario takes two steps per PBI. `start` expects
the mission revision; `step` and `cancel` expect the session revision. Each new command
needs its own operation UUID. Repeating the exact request recovers its original receipt;
`status` reports the current state, next role, blockers and receipt history.

Choose `--fixture-scenario pass|qa-retry|qa-exhaust` only at `queue start`. The scenario
and first eligible PBI are frozen in the session; all other PBIs pass their initial QA.
`qa-retry` rejects initial QA and passes one correction. `qa-exhaust` rejects initial QA
and all three corrections. A rejected QA schedules `correction_pending`; the next
`step` dispatches the pure fixture correction and increments `items[].correction_cycles`.
Each cycle includes revalidation. Exhaustion marks the PBI `blocked` and permits
independent PBIs to continue without releasing the blocked item's dependents.
When no eligible item remains, incomplete work enters `waiting`, holds the session slot,
and allows cancel but not step. Status reports `inspect_rehearsal_blockers` and
`correction_limit_reached`. Counts survive restart, replay and crashes within the same
synthetic session. New rehearsals are independent; the real correction ledger across
missions, revisions and IDs remains YC-303 roadmap work.

The fixture hashes frozen input and its simulated QA checks that result. It invokes no
model and changes no worktree. `fixture_completed` grants no real development, QA,
integration or production acceptance. A crash before commit can repeat pure computation,
but cannot duplicate the persisted transition. External exactly-once execution is unproven.
Only one rehearsal may be active per repository; one session is allowed per mission
revision. Cancel preserves history and remains available after mission revision changes.

New accepted queue writes migrate older private SQLite stores to schema 5 (retaining schema 6 when present) while retaining native
client diagnostics and blockers. Update the four helpers named above together; existing
helpers are preserved by the installer for explicit comparison and reconciliation. Reads
and exact replay never migrate storage. Existing v1/v2 sessions keep their original
behavior and receipts. The active-session index includes correction and waiting states;
schema 5 prevents old writers from misinterpreting v3 sessions. Native dispatch remains
gated by YC-203. Concurrent scheduling, leader decisions, real agents and product release/deployment remain roadmap work.
Explicit local worktree preparation is available through the [separate workspace commands](#pbi-workspaces).

<a id="pbi-workspaces"></a>

## Diretório Git por PBI / PBI Git workspaces

**PT:** YC-205 oferece preparo local explícito. Use uma missão preparada e atual,
o UUID de um PBI selecionado e o SHA completo de um commit disponível no repositório.
O pedido fixa essas revisões e cria uma branch `youngcrow/pNNN-UUID` com worktree em
`.runtime/workspaces/UUID`. Até três PBIs podem manter reservas; o mesmo PBI não recebe
uma segunda reserva ativa. Esse teto limita diretórios preparados; não consome os limites
de PBIs em execução ou agentes. Isso organiza diretórios Git; não isola permissões nem inicia agentes.
A fila determinística continua independente.

Execute na raiz original do projeto com Python 3 (`python` no Windows):

```bash
python3 -B scripts/missions.py --json workspace prepare M001 --pbi PBI_UUID --base SHA_COMPLETO --expected-revision 1 --operation-id UUID_PREPARO --actor-id operador
python3 -B scripts/missions.py --json workspace status UUID_PREPARO
python3 -B scripts/missions.py --json workspace release UUID_PREPARO --expected-revision 1 --operation-id UUID_LIBERACAO --actor-id operador
```

Substitua os exemplos pelos valores reais. Guarde o UUID e o pedido antes de executar.
`prepare` espera a revisão da missão; `release`, a revisão retornada do workspace.
`status M001` também lista `workspaces`. A consulta lê o estado salvo, sem inspecionar
novamente a integridade Git. `prepared` significa diretório preparado, com desenvolvimento,
QA e produção ainda sem aceite. Nenhum modelo é chamado por esses comandos.

O retorno de preparo informa `path`, `branch`, `base`, `id` e `revision`. Abra o caminho
retornado para trabalhar. Ele contém os arquivos do commit fixado. Alterações staged,
unstaged e arquivos novos do checkout original permanecem lá; configurações locais não versionadas,
credenciais e a instalação local do cliente não são copiadas para o novo diretório.

Para liberar, encerre editores e outros clientes que escrevam nesse worktree. Preserve
mudanças por commit ou outra ação deliberada antes de chamar `release`. O comando recusa
arquivos alterados, staged, não rastreados ou ignorados; também recusa HEAD destacado,
branch trocada, flags de índice que escondam alterações e identidade divergente. A remoção
usa `git worktree remove` sem força e mantém branch/commits, registrando `last_commit`.
O lock coordena apenas estes comandos do harness: não existe exclusão global de outros
clientes Git. O uso exige ausência de escritores externos durante preparo/liberação.

Após interrupção, repita **o mesmo pedido, UUID e revisão**. A intenção é persistida antes
do Git; branch e referência de propriedade são criadas na mesma transação Git. A retomada
verifica identidade do diretório, metadados, branch e checkout completo. Uma operação de
preparo já admitida mantém sua revisão congelada mesmo que a missão seja revisada depois.
O replay concluído devolve o recibo original; não recria um workspace liberado.

Uma queda entre criar o diretório vazio e salvar sua identidade permanece ambígua. Checkout
parcial, recurso substituído ou lock nativo remanescente também exigem diagnóstico. Preserve
os recursos e recibos; não use `--force`, `reset`, `clean`, `prune` ou novo UUID para contornar
uma reserva. A recuperação só continua automaticamente quando consegue confirmar o recurso.

Perfil coberto: repositório Git local independente, checkout completo, Linux x86-64 ou Windows
com o supervisor disponível. Links/hardlinks em destinos Git, submódulos, shallow/partial clone,
sparse checkout, includes e filtros externos configurados são recusados. Hooks, fsmonitor,
fetch implícito e manutenção automática ficam desativados nos comandos desta operação.
`.runtime/workspaces/` precisa estar ignorado e sem arquivos rastreados; o setup atualizado
acrescenta essa regra. O comando não altera `.gitignore` para corrigir uma instalação antiga.

Worktree ativo impede o dry-run de retorno do trial. Libere os worktrees próprios e limpos,
conserve as branches e peça o preview novamente. Worktrees alheios continuam impedindo retorno;
a restauração genérica não foi ampliada. Um retorno completo ao baseline reverte o repositório
inteiro, incluindo branches posteriores: preserve entregas que deseja manter antes de aprová-lo.

Atualize juntos `missions.py`, `mission_store.py`, `mission_runs.py`, `mission_queue.py` e
`mission_workspace.py`, além das instruções/catálogo do pacote. O instalador preserva helpers
existentes para comparação. A primeira reserva aceita migra SQLite para esquema 6; leitores
antigos recusam o banco. Filas/diagnósticos anteriores permanecem legíveis. Status e replay
concluído não migram nem reparam o armazenamento. Não há integração, push ou aceite nativo.

**EN:** YC-205 now supports explicitly requested local preparation for a PBI in a current
prepared mission. Use its PBI UUID, full local commit SHA, mission revision and a saved operation
UUID with `workspace prepare` above. `workspace status` reads the stored record;
`workspace release` expects the workspace revision and a new operation UUID. Replace the
Portuguese placeholders with actual values. On Windows use `python` for Python 3.

The result identifies the dedicated branch, directory, base and revision. Up to three PBIs can
hold workspace reservations, with one active reservation per PBI. This preparation cap is
separate from active-PBI and agent execution limits. The directory contains the pinned commit;
uncommitted work, untracked local client setup and credentials stay in the original checkout. No agent runs,
QA, integration or production acceptance follow from preparing it. Worktrees are not security sandboxes.

Stop external writers before prepare/release. Release refuses staged/unstaged, untracked and
ignored content, hidden index flags, detached HEAD, changed branch or ownership. It uses native
non-force worktree removal and retains branch/commits, recording the last commit. The coordinator
lock does not exclude other Git clients; this is not a globally atomic deletion guarantee.

After interruption, repeat the exact request, UUID and expected revision. Pending preparation
uses its frozen intent even after mission changes. Recovery verifies ownership and a complete
checkout; completed replay returns the original receipt and never recreates a released workspace.
A crash between directory creation and identity persistence, partial checkout, replacement or
leftover native locks requires diagnosis. Keep the files and receipts; do not force removal,
reset/clean/prune or bypass a reservation with a new UUID. Status reports saved state only.

Supported profile: standalone full local Git checkout on Linux x86-64 or Windows with the existing
process supervisor. Redirected metadata, submodules, shallow/partial clones, sparse checkout,
config includes and external filters are refused. Hooks, fsmonitor, lazy fetch and automatic
maintenance are disabled. Setup adds an ignore rule for `.runtime/workspaces/`; preparation
requires this directory to be ignored and untracked, without repairing old installation rules.

An active worktree blocks trial return preview. Release clean owned worktrees first; foreign ones
still block return. Generic restore is unchanged. A full return to the baseline also reverts later
branches, so preserve any deliveries you intend to keep before approving that return.
Update the five helpers listed above and the matching instructions/catalog together. The installer
preserves existing helpers for comparison. Accepted workspace reservation migrates SQLite to schema 6;
old readers refuse it, while current queue and diagnostic readers retain their history. Status and
completed replay do not migrate or repair storage. Queue simulation remains independent; worker
execution, integration and native acceptance are still pending.
