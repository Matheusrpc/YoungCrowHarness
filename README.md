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

Um harness reutilizável para desenvolvedores e pequenos times que trabalham com Claude Code e Codex.
Reúne instruções de trabalho, skills, configurações de MCP e um vault em Markdown para levar uma
ideia até uma entrega verificada. Pode iniciar um projeto ou ser adotado em código existente.

O `personalizer` ajuda a definir o produto e registrar a primeira feature. O especialista em
integrações consulta a documentação do fornecedor e mantém o histórico da implementação. As notas
ligam decisões, capacidades usadas e evidências para outra sessão conseguir continuar o trabalho.
O `ingest-source` conduz documentos e mídia até o vault local, com origem, revisão e vínculos de evidência.

**Navegue:** [arquitetura](#arquitetura-pt) · [começar ou migrar](#setup-pt) · [processo](#processo-pt) ·
[memória](#memoria-pt) · [próximas entregas](#evolucao-pt).

<a id="arquitetura-pt"></a>

## <img src="assets/gema-turquesa.svg" height="24" alt=""> Arquitetura e estado atual

Os dois clientes usam instruções e skills compartilhadas, com entradas próprias para cada ambiente.
O agente consulta o vault, executa o trabalho autorizado e registra o resultado. Os comandos locais
organizam e verificam as notas; credenciais, confiança e permissões continuam sob controle do cliente
e do ambiente em que ele opera.

![Arquitetura: Claude Code e Codex usam instruções e skills compartilhadas, registram entregas no vault e acessam MCPs configurados. Docling guarda documentos, áudio, vídeo e revisões; Graphify consulta notas selecionadas em um grafo local opcional; claude-mem continua planejado.](assets/architecture-pt.svg)

[Abrir diagrama](assets/architecture-pt.svg) · [Decisões de arquitetura](docs/superpowers/specs/2026-10-01-youngcrow-foundation-design.md)

| Camada | Responsabilidade | Estado |
|---|---|---|
| Claude Code e Codex | Ler as regras, descobrir skills e usar a configuração do cliente escolhido | Instalador e descoberta verificados; veja a [matriz de testes](#verificacao) |
| Personalização | Entrevistar, auditar um projeto existente e preparar perfil e primeira feature | `personalizer` e registros locais disponíveis; entrevista conduzida pelo agente |
| Skills, agentes e MCPs | Encontrar capacidades, comparar acesso e registrar o que cada execução usou | Catálogo, auditoria offline e revisão privada; prova nativa registrada por cliente |
| Integrações | Consultar fontes oficiais e documentar implementação, testes e operação | `integration-specialist` e `integrate-from-docs` disponíveis nos dois clientes |
| Vault | Guardar contexto, índices, referências e estados de desenvolvimento/produção | Markdown, criação de notas e validador disponíveis; conteúdo mantido pelo agente |
| Ingestão com Docling | Receber referências, converter fontes acessíveis e ligar evidências ao trabalho | CLI e skill compartilhada disponíveis; hook curto nos dois clientes; [cobertura real](docs/relatorios/2026-10-02-docling-ingestion.md) |
| retrieve-memory + Graphify | Consultar notas selecionadas com origem, revisão e relações | Markdown disponível; Graphify 0.9.73 opcional. claude-mem planejado |

O [catálogo de capacidades](vault/capabilities/index.md) reúne as entradas das skills e do especialista.
O `skills-lock.json` registra origens; o setup verifica o commit de `humanizer`, mas ainda não fixa
versões dos plugins de marketplace. MCPs exigem revisão de configuração e acesso. Uma capacidade
instalada não comprova autorização nem uso; cada execução deve registrar as capacidades utilizadas.

<a id="setup-pt"></a>

## <img src="assets/gema-rubi.svg" height="24" alt=""> Começar em um comando

```bash
git clone https://github.com/Matheusrpc/YoungCrowHarness.git
bash YoungCrowHarness/setup.sh meu-projeto --trial --client both --nome "Meu Projeto"
```

**Passo a passo:** [repo do zero](docs/USAGE.md#zero-pt) · [migrar repo existente](docs/USAGE.md#migrar-pt) · [como operar](docs/USAGE.md#operar-pt).

Requer Bash, Git e `python3` funcionando no mesmo terminal. No Windows, use Git Bash.
Para experimentar, use `--trial`: ele guarda um ponto privado antes da primeira escrita,
fora de qualquer repo Git, no mesmo volume. Instala arquivos e skills próprios do projeto e pula
plugins e downloads de skills. O ponto original permanece nas próximas execuções. Veja
[como consultar, sair e recuperar uma interrupção](docs/USAGE.md#adocao-reversivel-pt).
As consultas Git do trial desativam monitores externos desde a primeira verificação. No Linux,
o retorno preserva também os grupos dos arquivos, dentro do perfil de permissões aceito.
No Windows, o perfil exige o usuário atual como dono e permissões herdadas da pasta pai.

Sem `--trial`, a instalação normal não cria ponto de retorno e segue o comportamento abaixo.
O `setup.sh` copia o harness preservando os arquivos existentes e acrescenta proteção ao `.gitignore`.
Cria um `.env` local a partir do `.env.example`, com permissão 600 onde suportada, para você preencher à mão.
Instala a skill `humanizer` do upstream (commit pinado) e a `humanizer-ptbr`: em `~/.claude/skills/` para Claude
e `.agents/skills/` no projeto para Codex. Use `--client claude`, `--client codex` ou `--client both` (padrão). E,
se o Claude Code estiver instalado, adiciona os marketplaces e instala os plugins listados em
`skills-lock.json`. Rode com `--sem-plugins` para pular essa última parte, ou com `--force` para trocar
os templates que já existem. Vault, `.env`, regras de `.gitignore` e configurações de clientes/MCPs
são preservados mesmo com `--force`. Compare as configurações com os novos templates e mescle as entradas desejadas.
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

### 4. Incorporar documentos e retomar suas fontes

![Fontes: receber referência, recuperar índices, converter quando acessível, guardar pendência quando não, conferir extração e ligar evidência à feature. Publicação exige revisão e aprovação da cópia exata.](assets/process-sources-pt.svg)

[Preparar Docling e operar nos clientes](docs/USAGE.md#fontes-pt) · [Abrir diagrama](assets/process-sources-pt.svg)

Cada entrega atualiza o README com revisão de texto por `humanizer`. O vault guarda fontes, decisões,
capacidades usadas, testes e próximo passo. Produção exige evidência do ambiente. Uma publicação
fora do escopo fica como não aplicável; se faltar autorização, salve a pendência para a próxima sessão.

<a id="memoria-pt"></a>

## <img src="assets/gema-violeta.svg" height="24" alt=""> Memória que continua entre sessões

A entrada é [vault/index.md](vault/index.md). Dela, o agente segue o microíndice do tema e abre apenas
as notas necessárias. Produto, features, decisões e operação são criados conforme o uso; integrações
têm uma área própria para fontes, implementação e execuções. Os mesmos Markdowns podem ser lidos
no repositório ou abertos como um vault no Obsidian.

Uma feature deve ligar o problema às fontes, decisões, pequenas entregas e evidências. O registro de
execução informa agentes, skills e MCPs realmente usados, o resultado e a próxima ação. Desenvolvimento
e produção têm estados separados: código presente ou teste local não comprovam uma publicação.
O validador confere a estrutura dessas referências; ele não certifica a veracidade das notas.

Peça ao Claude Code ou Codex: **“Use retrieve-memory para retomar esta feature.”** A skill confere
as notas selecionadas, abre suas evidências e registra um handoff com projeto, UUIDs e revisões.
Sem índice atual, a consulta usa o Markdown da seleção. Sem seleção, comece pelos microíndices.

![Memória: salvar no vault, selecionar notas, validar, construir retrato, conferir revisão, consultar, abrir evidências e registrar próxima ação. Grafo ausente ou antigo retorna ao Markdown; falhas preservam o vault.](assets/process-memory-pt.svg)

[Setup e operação da memória](docs/USAGE.md#memoria-pt) · [Abrir diagrama](assets/process-memory-pt.svg)

O retrato fica em `.operacao-local/memory/`, fora do Git. Graphify 0.9.73 é opcional, usa Python 3.12
e representa links explícitos entre notas. Sua busca usa títulos e relações; o Markdown também
busca no corpo das notas. A IA do cliente interpreta os resultados na conta e nas condições de
uso já existentes. O adaptador não contrata outra API nem instala um MCP de memória.

No corpus sintético, a referência esperada apareceu em 3 de 4 consultas Graphify e em 4 de 4
consultas Markdown. O grafo não demonstrou vantagem geral nesse teste pequeno. Veja a
[medição e os limites](docs/relatorios/2026-10-02-memory-discovery.md).

![Governança: descobrir, auditar, revisar diferenças, aplicar mudanças autorizadas, provar no cliente e registrar no vault.](assets/process-governance-pt.svg)

[Operar a governança](docs/USAGE.md#governanca-pt)


A ingestão com Docling guarda documentos convertidos, imagens e índices em `vault/local/`, ignorada
pelo Git. Originais e recibos ficam em
`.operacao-local/docling/`. Uma cópia revisada pode entrar na área compartilhada
`vault/sources/`. O validador já reconhece o índice local e recusa referências públicas a arquivos
privados. O helper de armazenamento prepara e verifica o ignore antes de escrever. O ambiente
Docling tem [setup opt-in e diagnóstico local](docs/USAGE.md#docling-pt). A conversão foi verificada com
PDF, DOCX, HTML e uma imagem de página, além da aquisição e conversão de um PDF público por URL.
Cada conexão valida o destino; downloads têm limites de tamanho e tempo. A revisão do texto extraído continua necessária.
Na nota extraída, referências Markdown por rótulo viram texto legível; imagens ativas precisam ser
arquivos locais validados. A cópia pública recusa HTML e autolinks. Se a gravação do cache for
interrompida, a próxima ingestão preserva a extração incompleta e tenta novamente.

O perfil opcional de mídia usa Whisper Base local. A prova com WAV e MP4 preservou a frase falada,
os intervalos da transcrição e três quadros amostrados. Um vídeo sem áudio manteve as imagens e
o aviso de extração parcial. Os formatos, limites e comandos estão no [guia de uso](docs/USAGE.md#docling-pt).

Os vínculos locais registram a revisão usada e um trecho de evidência para relacionar a fonte a features
ou decisões. Contradições começam como hipóteses; o sentido da relação precisa ser revisado.
O hook `UserPromptSubmit` registra referências textuais e chama a atenção do agente para `ingest-source`.
Ele não baixa nem converte documentos. A skill recupera fontes anteriores, executa a ingestão e registra
relações, capacidades usadas e próxima ação. Anexos sem caminho exposto ficam pendentes; invoque a skill
explicitamente quando o cliente não entregar a referência ao hook. O [contrato de ingestão](docs/superpowers/specs/2026-10-02-docling-ingestion-design.md)
define esse comportamento. Material local não acompanha clones e precisará de backup privado para
uso entre máquinas. Graphify aponta de volta às notas e revisões; claude-mem continua planejado.

### 7. Experimentar e voltar

![Adoção reversível: validar, guardar o ponto inicial, experimentar e decidir continuar ou revisar a saída. A confirmação vem antes das cópias verificadas e da restauração. Interrupções têm recuperação externa.](assets/process-adoption-pt.svg)

[Comandos, limites e recuperação](docs/USAGE.md#adocao-reversivel-pt) · [Abrir diagrama](assets/process-adoption-pt.svg)

<a id="evolucao-pt"></a>

## <img src="assets/gema-ambar.svg" height="24" alt=""> Entregas e próximos passos

A [adoção reversível](docs/USAGE.md#adocao-reversivel-pt) salva o projeto antes do primeiro setup
com `--trial`. Para sair, revise a prévia e confirme o retorno pelo executor externo. O controlador
verifica as cópias antes da troca e guarda o trabalho do teste em uma área privada.
Repetir o setup mantém o ponto inicial; uma troca interrompida pode ser retomada pelo mesmo executor.
O trial instala arquivos do projeto, sem alterar o perfil global dos clientes. Serviços e publicações
externas exigem tratamento separado. Instalações antigas sem ponto inicial não têm retorno retroativo.
O [relatório de validação](docs/relatorios/2026-10-02-reversible-adoption.md) registra ambientes,
revisão e limites; o [plano executado](docs/superpowers/plans/2026-10-02-reversible-adoption.md) preserva as decisões.

O desenho do Docling foi aprovado. O [plano de execução](docs/superpowers/plans/2026-10-02-docling-ingestion.md)
registra quatro entregas e sua cobertura:

1. Verificado: documentos locais, Markdown, origem, revisões e retomada após interrupção, com proteção contra versionamento acidental.
2. Verificado: vínculos com evidência, cópias para revisão e publicação local sem expor a proveniência privada.
3. Verificado: URLs diretas, áudio e vídeo, com intervalos de transcrição, quadros, limites e falhas registrados.
4. Codex: ingestão e retomada verificadas em duas sessões reais. Claude Code: descoberta verificada; conversa real pendente de login. Veja a [matriz e os limites](docs/relatorios/2026-10-02-docling-ingestion.md).

A consulta Markdown, o Graphify opcional e a skill compartilhada estão implementados. O
[plano de memória](docs/superpowers/plans/2026-10-02-memory-discovery.md) mantém a prova de cada
cliente separada: Codex recuperou o handoff e reconheceu uma revisão alterada; a consulta Graphify
no sandbox somente leitura recorreu ao Markdown. Claude Code tem descoberta verificada e conversa
real pendente de login. M04 permanece parcial.
O [relatório](docs/relatorios/2026-10-02-memory-discovery.md) registra o estado atual de M01–M04.
A [governança de skills, agentes e MCPs](docs/superpowers/specs/2026-10-02-capability-governance-design.md)
entrega catálogo verificável, auditoria offline, pacotes privados e uma skill comum aos dois clientes.
No ensaio sintético nativo, o Codex permitiu a ferramenta prevista, recusou a proibida e confirmou
revogação/restauração em sessões novas. A prova equivalente no Claude permanece pendente. Veja a
[matriz de evidências](docs/relatorios/2026-10-02-capability-governance.md). O catálogo já pode ser consultado
com `python scripts/capabilities.py list` e `describe ID`. `audit --client both --json` compara arquivos
e configurações sem iniciar MCPs. `review --id ID` prepara um pacote privado; `review --check DIGEST`
confere se os arquivos continuam iguais. O pacote não concede autorização nem ativa a capacidade.
Peça **“Use govern-capabilities para revisar as capacidades deste projeto.”** O setup instala a skill
nos clientes escolhidos e preserva manifesto, skills e agentes existentes, mesmo com `--force`.
Consultas e diagnóstico preservam as notas e o `.gitignore`. Se o índice estiver corrompido,
a consulta usa o Markdown atual; a reconstrução fica explícita no [guia de uso](docs/USAGE.md#memória-consultar-notas-selecionadas).
claude-mem, sincronização entre máquinas e orquestração autônoma de papéis continuam na
[evolução do produto](docs/superpowers/specs/2026-10-01-youngcrow-foundation-design.md).

## <img src="assets/gema-ambar.svg" height="24" alt=""> O que vem dentro

| Arquivo | Para que serve |
|---|---|
| `CLAUDE.md` | O guia que o Claude Code lê no início de cada sessão: dez leis de trabalho, alvos de publicação, comandos e fronteiras. Em português. |
| `docs/CLAUDE.en.md` | O mesmo guia em inglês. Fique com um dos dois. |
| `AGENTS.md` | A entrada do Codex: lê o `CLAUDE.md` primeiro, um executor escreve por vez, revisores só leem, e o navegador fecha ao terminar. |
| `.claude/settings.json` | Entrada curta para referências de documentos; hooks de design de `impeccable` quando instalado. |
| `.codex/hooks.json` | Os mesmos hooks, no formato do Codex. |
| `.codex/config.toml` | MCPs do Codex no escopo do projeto. Exemplos desativados até revisão; exige confiança do projeto. |
| `.mcp.json` | Atalhos de MCP com URLs de exemplo. Nunca ponha token aqui; o token vai por variável de ambiente. |
| `.env.example` | Os nomes das variáveis que o projeto espera, com valores falsos. O `.env` real nasce daqui e nunca entra no git. |
| `.gitignore` | Segredos, caches, evidência pesada e estado local fora do repositório. |
| `skills-lock.json` | Inventário dos plugins e origem das skills. O instalador verifica o commit de humanizer; versões dos plugins de marketplace ainda não são fixadas por este manifesto. |
| `skills/humanizer-ptbr/` | Juiz de texto em português: 25 padrões de escrita de máquina e como reescrever. |
| `skills/retrieve-memory/` | Retomada com notas selecionadas, evidências e revisões. |
| `scripts/memory.py` | Seleção, consulta, Graphify opcional e recuperação do índice. |
| `skills/personalizer/` | Entrevista retomável, auditoria guiada e adaptação do projeto. |
| `skills/integrate-from-docs/` | Documentação oficial, implementação e histórico de integrações. |
| `skills/ingest-source/` | Recuperação de fontes, ingestão, vínculos com evidência e publicação revisada. |
| `scripts/documents.py` | Setup opcional do Docling, conversão local, recibos e revisão de cópias. |
| `scripts/source_prompt.py` | Registra referências recebidas pelo hook, sem rede ou conversão. |
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

A reusable harness for developers and small teams working with Claude Code and Codex. It combines
working instructions, skills, MCP configuration and a Markdown vault to take an idea through a
verified delivery. Use it for a new product or adopt it in an existing codebase.

The `personalizer` helps define the product and record its first feature. The integration specialist
consults vendor documentation and keeps an implementation history. Notes link decisions, capabilities
used and evidence so another session can continue the work.
The `ingest-source` skill brings documents and media into the local vault with source identity, revisions and evidence links.

**Navigate:** [architecture](#architecture-en) · [setup and adoption](#setup-en) · [process](#process-en) ·
[memory](#memory-en) · [next deliveries](#roadmap-en).

<a id="architecture-en"></a>

## <img src="assets/gema-turquesa.svg" height="24" alt=""> Architecture and current state

Both clients use shared instructions and skills through their own native entries. The agent reads
the vault, performs authorized work and records the result. Local commands organize and check notes;
credentials, trust and permissions remain controlled by the client and its execution environment.

![Architecture: Claude Code and Codex use shared instructions and skills, record deliveries in the vault and access configured MCPs. Docling stores documents, audio, video and revisions; Graphify queries selected notes in an optional local graph; claude-mem remains planned.](assets/architecture-en.svg)

[Open diagram](assets/architecture-en.svg) · [Architecture decisions](docs/superpowers/specs/2026-10-01-youngcrow-foundation-design.md)

| Layer | Responsibility | State |
|---|---|---|
| Claude Code and Codex | Read rules, discover skills and use the selected client's configuration | Installer and discovery verified; see the [test matrix](#verification) |
| Personalization | Interview, audit an existing project and prepare its profile and first feature | `personalizer` and local records available; the agent conducts the interview |
| Skills, agents and MCPs | Discover capabilities, compare access and record actual use | Catalog, offline audit and private review; native proof recorded per client |
| Integrations | Consult official sources and document implementation, tests and operation | `integration-specialist` and `integrate-from-docs` available in both clients |
| Vault | Keep context, indices, references and development/production states | Markdown, note creation and validation available; the agent maintains content |
| Docling ingestion | Receive references, convert accessible sources and link evidence to work | CLI and shared skill available; short hook in both clients; [observed coverage](docs/relatorios/2026-10-02-docling-ingestion.md) |
| retrieve-memory + Graphify | Query selected notes with origin, revision and relations | Markdown available; Graphify 0.9.73 optional. claude-mem planned |

The [capability catalog](vault/capabilities/index.md) links to the skills and integration specialist.
`skills-lock.json` records sources; setup verifies the `humanizer` commit but does not yet pin
marketplace plugin versions. MCPs require configuration and access review. An installed capability
does not prove authorization or use; each run should record the capabilities actually used.

<a id="setup-en"></a>

## <img src="assets/gema-rubi.svg" height="24" alt=""> Start with one command

```bash
git clone https://github.com/Matheusrpc/YoungCrowHarness.git
bash YoungCrowHarness/setup.sh my-project --trial --client both --name "My Project"
```

**Step by step:** [new repository](docs/USAGE.md#new-en) · [adopt an existing repo](docs/USAGE.md#migrate-en) · [daily operation](docs/USAGE.md#operate-en).

Requires Bash, Git and a working `python3` in the same terminal. On Windows, use Git Bash.
For a first try, use `--trial`: it saves a private baseline before the first write, outside every
Git repository and on the same volume. It installs bundled project files and skills, skipping
plugins and skill downloads. Repeated setup preserves the original baseline. See
[status, exit and interruption recovery](docs/USAGE.md#reversible-adoption-en).

Trial Git queries disable external filesystem monitors from the first check. On Linux, restoration
also preserves file groups within the supported permission profile.
Windows requires the current user as owner and permissions inherited from the parent folder.

Without `--trial`, normal installation creates no restore point and behaves as described below.
`setup.sh` preserves existing project files and appends protection to `.gitignore`.
It creates a local `.env` from `.env.example`, with permission 600 where supported, for you to fill in
by hand. It installs the `humanizer` skill from upstream (pinned commit) and `humanizer-ptbr` into
`~/.claude/skills/` for Claude and project-local `.agents/skills/` for Codex. Choose `--client claude`,
`--client codex` or `--client both` (default). For Claude, it adds the marketplaces and installs the plugins
listed in `skills-lock.json`. Run it with `--no-plugins` to skip that last part, or with `--force` to
replace existing templates. Vault notes, `.env`, ignore rules and client/MCP configurations are
preserved even with `--force`. Compare configurations with the new templates and merge the desired entries.
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

### 4. Bring in documents and recover their sources

![Sources: receive a reference, recover indices, convert accessible input, keep inaccessible input pending, check extraction and link evidence to the feature. Publication requires review and approval of the exact copy.](assets/process-sources-en.svg)

[Prepare Docling and use it in both clients](docs/USAGE.md#sources-en) · [Open diagram](assets/process-sources-en.svg)

Each delivery updates the README with `humanizer` prose review. The vault keeps sources, decisions,
capabilities used, tests and the next action. Production requires environment evidence. Mark a
release outside scope as not applicable; when authorization is missing, save it as pending for a later session.

<a id="memory-en"></a>

## <img src="assets/gema-violeta.svg" height="24" alt=""> Memory across sessions

Start at [vault/index.md](vault/index.md), follow the topic index and open only the notes needed for
the task. Product, feature, decision and operation records are created as needed. Integrations have
their own area for sources, implementation and runs. Read the same Markdown in the repository or
open the folder as an Obsidian vault.

A feature should link its problem to sources, decisions, small deliveries and evidence. Its run
record names the agents, skills and MCPs actually used, the result and the next action. Development
and production have separate states: code or a local test does not prove a release. The validator
checks reference structure; it does not certify the truth of a note.

Ask Claude Code or Codex: **“Use retrieve-memory to resume this feature.”** The skill checks
selected notes, opens their evidence and records a handoff with project identity, UUIDs and revisions.
Without a current index, queries use the selected Markdown. Without a selection, start with topic indices.

![Memory: save in the vault, select notes, validate, build a snapshot, check revisions, query, open evidence and record the next action. Missing or stale graphs fall back to Markdown; failures preserve the vault.](assets/process-memory-en.svg)

[Memory setup and operation](docs/USAGE.md#memory-en) · [Open diagram](assets/process-memory-en.svg)

Snapshots stay in Git-ignored `.operacao-local/memory/`. Optional Graphify 0.9.73 uses Python 3.12
and represents explicit links between notes. Its search uses titles and relations; Markdown also
searches note bodies. The client AI interprets results under the existing account and data settings.
The adapter does not purchase another API or install a memory MCP.

In the synthetic corpus, the expected reference appeared in 3 of 4 Graphify queries and 4 of 4
Markdown queries. The graph showed no general advantage in this small test. See the
[measurement and limits](docs/relatorios/2026-10-02-memory-discovery.md).

![Governance: discover, audit, review drift, apply authorized changes, prove in the client and record in the vault.](assets/process-governance-en.svg)

[Operate governance](docs/USAGE.md#governance-en)


Docling ingestion stores converted documents, images and indices in the Git-ignored `vault/local/`
area. Originals and receipts live in `.operacao-local/docling/`.
A reviewed copy can enter the shared `vault/sources/` area. The validator recognizes the local
index and rejects public references to private files. The storage helper prepares and verifies
ignore rules before writing. Docling has [opt-in setup and local diagnostics](docs/USAGE.md#docling-en);
conversion was verified with PDF, DOCX, HTML and a page image, plus acquisition and conversion of a
public PDF URL. Each connection validates its destination; downloads have size and time limits.
Extracted text still needs review.
In extracted notes, reference-style Markdown links become readable text; active images must be
validated local files. Public copies reject HTML and autolinks. If a cache write is interrupted,
the next ingestion preserves the incomplete extraction and retries.

The optional media profile uses local Whisper Base. WAV and MP4 tests preserved the spoken phrase,
transcript intervals and three sampled frames. A video without audio retained its images and a
partial-extraction warning. See the [usage guide](docs/USAGE.md#docling-en) for formats, limits and commands.

Local relations record the source revision and a supporting quote to link it to features or decisions.
Contradictions start as hypotheses; the meaning of a relationship still needs review.
The `UserPromptSubmit` hook records textual references and directs the agent to `ingest-source`.
It does not download or convert documents. The skill recovers prior sources, performs ingestion and
records relations, actual capabilities and the next action. Attachments without an exposed path stay
pending; invoke the skill explicitly when the client does not pass a reference to the hook. The [ingestion contract](docs/superpowers/specs/2026-10-02-docling-ingestion-design.md)
defines that behavior. Local material does not travel with clones and needs a private backup for use
across machines. Graphify points back to source notes and revisions; claude-mem remains planned.

### 7. Try and return

![Reversible adoption: validate, save the baseline, try the harness, then continue or review the exit. Confirmation precedes verified copies and restoration. Interruptions recover through an external runner.](assets/process-adoption-en.svg)

[Commands, limits and recovery](docs/USAGE.md#reversible-adoption-en) · [Open diagram](assets/process-adoption-en.svg)

<a id="roadmap-en"></a>

## <img src="assets/gema-ambar.svg" height="24" alt=""> Deliveries and next steps

[Reversible adoption](docs/USAGE.md#reversible-adoption-en) saves the project before the first
setup with `--trial`. To leave, review the preview and confirm restoration through the external runner.
The controller verifies both copies before exchanging directories and keeps trial work in private storage.
Repeated setup retains the baseline; the same runner can resume an interrupted exchange.
Trial installs project files without changing global client profiles. External services and publications
require separate handling. Existing installations without a baseline cannot be restored retroactively.
The [validation report](docs/relatorios/2026-10-02-reversible-adoption.md) records environments,
review and limits; the [implementation plan](docs/superpowers/plans/2026-10-02-reversible-adoption.md) preserves the decisions.

The Docling design is approved. The [implementation plan](docs/superpowers/plans/2026-10-02-docling-ingestion.md)
records four deliveries and their coverage:

1. Verified: local documents, Markdown, origin, revisions and resumption after interruption, protected against accidental tracking.
2. Verified: evidence-backed relations, review copies and local publication without private provenance.
3. Verified: direct URLs, audio and video, with transcript intervals, frames, limits and failures recorded.
4. Codex: ingestion and recovery verified in two real sessions. Claude Code: discovery verified; live conversation pending login. See the [matrix and limits](docs/relatorios/2026-10-02-docling-ingestion.md).

Markdown retrieval, optional Graphify and the shared skill are implemented. The
[memory plan](docs/superpowers/plans/2026-10-02-memory-discovery.md) tracks each client separately:
Codex recovered the handoff and recognized a changed revision; Graphify queries in its read-only
sandbox fell back to Markdown. Claude Code discovery is verified; model conversation awaits login.
M04 remains partial. The
[report](docs/relatorios/2026-10-02-memory-discovery.md) records current M01–M04 evidence.
[Skill, agent and MCP governance](docs/superpowers/specs/2026-10-02-capability-governance-design.md)
provides a verifiable catalog, offline auditing, private review bundles and a shared skill.
The native synthetic Codex probe allowed the intended tool, rejected the forbidden tool and verified
revocation/restoration in fresh sessions. Equivalent Claude proof remains pending. See the
[evidence matrix](docs/relatorios/2026-10-02-capability-governance.md). The catalog can be queried
with `python scripts/capabilities.py list` and `describe ID`. `audit --client both --json` compares files
and configuration without starting MCPs. `review --id ID` prepares a private bundle; `review --check DIGEST`
checks whether its inputs are unchanged. A bundle grants no authorization and activates nothing.
Ask **“Use govern-capabilities to review this project's capabilities.”** Setup installs the skill in
selected clients and preserves existing manifests, skills and agents, even with `--force`.
Queries and diagnostics preserve notes and `.gitignore`. If the index is corrupt, retrieval
uses current Markdown; rebuilding is explicit in the [usage guide](docs/USAGE.md#memory-query-selected-notes).
claude-mem, cross-machine synchronization and autonomous role orchestration remain in the
[product roadmap](docs/superpowers/specs/2026-10-01-youngcrow-foundation-design.md).

## <img src="assets/gema-ambar.svg" height="24" alt=""> What is inside

| File | What it is for |
|---|---|
| `CLAUDE.md` | The guide Claude Code reads at the start of every session: ten working laws, publication targets, commands and boundaries. In Portuguese. |
| `docs/CLAUDE.en.md` | The same guide in English. Keep one of the two. |
| `AGENTS.md` | The Codex entry point: read `CLAUDE.md` first, one writer at a time, reviewers only read, and the browser closes when the task ends. |
| `.claude/settings.json` | Short document-reference intake hook; `impeccable` design hooks when installed. |
| `.codex/hooks.json` | The same hooks, in Codex format. |
| `.codex/config.toml` | Project-scoped Codex MCP servers. Examples start disabled for review; project trust is required. |
| `.mcp.json` | MCP shortcuts with example URLs. Never put a token here; tokens travel through environment variables. |
| `.env.example` | The names of the variables the project expects, with fake values. The real `.env` is born from it and never enters git. |
| `.gitignore` | Secrets, caches, heavy evidence and local state stay out of the repository. |
| `skills-lock.json` | Plugin inventory and skill sources. The installer verifies the humanizer commit; this manifest does not yet pin marketplace plugin versions. |
| `skills/humanizer-ptbr/` | A text judge for Brazilian Portuguese: 25 patterns of machine writing and how to rewrite them. |
| `skills/retrieve-memory/` | Resume selected notes with evidence and revisions. |
| `scripts/memory.py` | Selection, retrieval, optional Graphify and index recovery. |
| `skills/personalizer/` | Resumable interview, agent-led audit and project adoption. |
| `skills/integrate-from-docs/` | Official sources, implementation and integration history. |
| `skills/ingest-source/` | Source recovery, ingestion, evidence links and reviewed publication. |
| `scripts/documents.py` | Optional Docling setup, local conversion, receipts and copy review. |
| `scripts/source_prompt.py` | Records hook references without network access or conversion. |
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
| Windows + Git Bash + Python 3.11 | CI de adoção: ACLs nativas, instalação trial e retorno por executor externo / adoption CI: native ACLs, trial setup and external-runner restoration. [Provas / evidence](docs/relatorios/2026-10-02-reversible-adoption.md). |
| Linux | Suíte automática a cada push/PR, incluindo symlinks / automated suite on every push/PR, including symlinks — [execuções / runs](https://github.com/Matheusrpc/YoungCrowHarness/actions). |
| macOS / setup sem Bash | Não verificados / not verified. O setup exige Bash; o helper Windows usa PowerShell 5.1 / setup requires Bash; the Windows helper uses PowerShell 5.1. |

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
