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

**Continuidade do executor:** a branch `feat/isolated-executor` reúne o código em desenvolvimento,
testes e relatórios revisados para continuar em outro ambiente. Comece pelo
[contexto completo](docs/HANDOFF-CLOUD-2026-10-07.md) e pela
[verificação deste checkpoint](docs/relatorios/2026-10-07-cloud-checkpoint.md).
O executor ainda depende de prova integrada de rede e dos dois clientes autenticados; seus perfis permanecem bloqueados.

O pacote privado da captura de B foi recuperado na cloud. Seus 26 testes offline
passaram com 17 hashes fixados conferidos e os 635 arquivos preservados. A suíte
usa transporte e efeitos nativos simulados; o aceite nativo continua pendente.
[Recuperação e reprodução da suíte](docs/relatorios/2026-10-08-b-source-recovery.md).

A [revisão do ciclo de configuração](docs/relatorios/2026-10-08-executor-lifecycle-review.md)
identificou uma alternativa com proxy fixo entre missões. Ela pode reduzir escritas,
mas ainda depende de proteção do endpoint e recuperação das credenciais; não foi
implementada. O contrato atual e os bloqueios permanecem.
A [comparação das alternativas](docs/relatorios/2026-10-09-executor-alternatives.md)
recebeu o inventário do PC: a candidata via função Hyper-V fica pausada no Windows
Home. Isso não reprova o sbx/WHP existente nem resolve o contrato Docker. Nenhum
novo backend foi implementado.

A consulta ao Docker está publicada na [issue #690](https://github.com/docker/sbx-releases/issues/690),
aberta pelo mantenedor em 9/out. A publicação e o texto foram conferidos pela API;
aguardamos resposta sobre o contrato local. O aceite do executor e a fila 2B continuam pendentes.

A entrega independente melhora `yc-status`: mostra o recibo que bloqueia novos diagnósticos, inclusive de outra
missão do projeto, e indica revisão de recuperação ou reparo de notas antes de refinar
entradas. A consulta permanece somente leitura. [Uso e limites](docs/USAGE.md#mission-workflow).
[Verificação da entrega](docs/relatorios/2026-10-08-mission-status-guidance.md).

Para retomar sem lembrar o código, `python3 -B scripts/missions.py --json list` lista
as missões salvas com título, código, UUID, revisão e estado registrado. Depois use
`status CODIGO` para consultar impedimentos atuais. A listagem funciona mesmo quando
a projeção da nota está pendente e não altera arquivos.
[Uso](docs/USAGE.md#mission-workflow) · [Verificação](docs/relatorios/2026-10-09-mission-discovery.md).

O [refinamento da fila YC-204](docs/superpowers/specs/2026-10-09-queue-eligibility-refinement.md)
detalha decisões de prioridade, espera e capacidade. A política aprovada para a futura
fila prioriza etapas elegíveis do trabalho iniciado antes de admitir novos PBIs,
com ordem de entrada compartilhada por todos os papéis. O desenho operacional está
em refinamento; o despacho nativo continua dependente do aceite do executor.

Já é possível antecipar a leitura da fila: `status CODIGO` retorna `queue_preview`
com PBIs na prioridade salva, dependências e o primeiro candidato inicial quando a
preparação está consistente. Essa consulta usa o snapshot da missão e não executa agentes.
[Contrato e limites](docs/USAGE.md#mission-workflow).

O coordenador oferece um [ensaio persistente com vários PBIs](docs/USAGE.md#queue-rehearsal):
`queue start`, `queue step` e `queue cancel` registram etapas simuladas e recibos.
`status` mostra a etapa, o próximo papel e as dependências ainda pendentes no ensaio.
A fila prioriza QA e correções do PBI ativo. O ensaio pode reprovar QA, aprovar após
uma correção ou esgotar o limite de três. Itens bloqueados conservam seus dependentes
em espera; os independentes seguem pela prioridade salva. O contador sobrevive a reinícios
da mesma sessão sintética. A autocorreção de agentes reais continua no roadmap.
Repetir uma operação recupera seu recibo. O ensaio não chama modelos nem aprova entrega real.
[Provas e limites](docs/relatorios/2026-10-10-queue-corrections.md).

O [preparo de um diretório Git por PBI](docs/USAGE.md#pbi-workspaces) já está disponível:
`workspace prepare/status/release` fixa o commit de base e mantém recibos para retomada.
O checkout original conserva suas alterações. A liberação exige um worktree próprio e limpo,
preserva branch/commits e permite pedir novamente o preview de retorno do trial.
É preparo local explícito; agentes reais e integração seguem pendentes.

O [contexto por PBI](docs/USAGE.md#pbi-context) reúne critérios, feature, épico e fontes
explicitamente vinculadas, com UUIDs, revisões e hashes. `context` consulta o vault do
checkout original e retorna JSON privado, sem alterar notas ou iniciar agentes.
Fontes divergentes são recusadas; lacunas de planejamento aparecem no resultado.

O PM pode [propor outra ordem para os PBIs selecionados](docs/USAGE.md#pbi-priority).
`reprioritize --dry-run` mostra a mudança sem escrever; a aplicação guarda motivo,
autor e revisão, preservando escopo e configuração. Fila ativa bloqueia a mudança;
PBIs com histórico de workspace conservam suas posições. É uma decisão de planejamento.

O Tech Lead pode [selecionar o plano técnico de um PBI](docs/USAGE.md#technical-plan)
entre suas referências diretas. A escolha registra motivo, revisão e hash da nota;
`context` entrega esse plano junto aos critérios, preservando o contrato do PBI.

O preparo também confere se os hashes congelados correspondem às notas e referências
importadas. Divergência deixa a missão em rascunho; `status` bloqueia snapshots antigos
inconsistentes e orienta importar as edições e revisar a missão. [Detalhes](docs/USAGE.md#mission-input-consistency).

Para retomar um diretório de trabalho, [consulte pelo UUID do workspace](docs/USAGE.md#workspace-context).
`workspace context` confere a identidade Git e reúne o contexto do PBI na revisão
fixada pelo preparo. Preserva o trabalho em andamento e retorna JSON privado no terminal.

O checkpoint `77f6e37` passou nos oito jobs de CI entre push e PR, incluindo Windows.
[Resultados conferidos](docs/relatorios/2026-10-10-workspace-context.md).
Em `44cd90f`, o CI Windows expôs um corte de 15 s no teste de rede, cujo plano admite
30 s. O supervisor da fixture agora usa esse prazo; [prova e confirmação pendente](docs/relatorios/2026-10-10-network-fixture-budget.md).
O aceite nativo do executor continua pendente.

As próximas provas estão reunidas em uma [campanha com aprovação por lote](docs/TEST-RUN-2026-10-10.md),
com sequência, limites e critérios de parada. Os bloqueios nativos permanecem.

**Checkpoint anterior de 7/out:** admissão sintética, controlador/fixture e correções da auditoria
chegaram ao [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
O pacote público passou em 516 testes, com 20 pulados; naquela rodada, o CI não pôde ser consultado.
Veja o [registro da publicação](docs/relatorios/2026-10-07-cloud-publication.md).

`client check` reconhece o manifesto `isolated-egress-v1` e registra um bloqueio
`controller_pending`, com `model_calls=0`. A tentativa conserva os limites e o UUID da
missão, sem consultar clientes ou Docker. Veja o [contrato e seus limites](docs/USAGE.md#synthetic-admission)
e a [continuidade na cloud](docs/relatorios/2026-10-07-synthetic-admission.md).

O plano v4 exige que a resposta contenha um valor fictício diferente do placeholder,
com o hash esperado fixado antes da execução. A prova interna usa fixture, relay e
guard com processos e sockets locais; também recusa o percurso sem substituição.
A/B/A2 compartilham a configuração e mantêm identidades próprias. Planos v2/v3
continuam legíveis para recuperação, sem transformar eco antigo em prova de injeção.
**203.6 permanece parcial:** a API Cloud documenta remoção condicionada à versão da
credencial, mas falta comprovar esse contrato no `sbx` local 0.46.0. O adaptador e
os perfis nativos seguem bloqueados; B ainda exige atribuição nativa.
Veja a [prova de injeção](docs/relatorios/2026-10-07-injection-proof.md).

A ativação e a recuperação agora exigem escrita condicionada ao estado completo do
setting. Nos testes, uma mudança externa após a intenção é preservada e impede o
reinício; a recuperação mantém a reserva bloqueada. O contrato atômico do sbx local
continua sem prova. Validação local: 592 testes aprovados e 20 pulados.
[Correção e bloqueio nativo](docs/relatorios/2026-10-07-conditional-settings.md).

O CI de `da28f00` falhou em `adoption-windows`, na suíte de missões, tanto no push
quanto no PR. Os outros três jobs passaram. O runner dessa etapa agora publica
identificadores e estados permitidos dos testes nas anotações do GitHub, preservando
a saída e o resultado do unittest. O CI identificou dois percursos de rede e um caso
de encerramento do controlador. A rodada focal confirmou `TimeoutError` na sonda B
v3, que limitava a conexão a um segundo. A fixture agora usa o prazo restante da fase
e continua exigindo recusa explícita. Os cinco casos focais passaram no push; no PR,
v3 e v4 atingiram o limite externo de 15 s. Com o diagnóstico de tempos em `e674a83`,
os cinco casos passaram em ambos os runs. A suíte completa local passou com 598
aprovados e 20 pulados; naquele checkpoint, o CI Windows completo ainda estava em andamento.
O CI seguinte, em `63bb229`, registrou novos timeouts no fim de A2.
[Estado do CI e próxima ação](docs/relatorios/2026-10-07-windows-ci-diagnostics.md).

A verificação de armazenamento consulta as três regras de ignore em uma chamada
Git e exige confirmação de todas. Isso reduz de cinco para três os processos por
verificação, mantendo a leitura atual das regras em cada etapa. A confirmação local
passou com 602 testes aprovados e 20 pulados. Em `25ee51d`, os cinco focais Windows
passaram no push e no PR; os dois jobs Windows completos também passaram. [Medição e regressões](docs/relatorios/2026-10-08-git-preflight-cost.md).

A seleção do destino agora protege consultas e alterações com o mesmo lock. Um
processo concorrente recebe `execution_selection_busy`; depois da gravação, um digest
antigo continua sendo recusado. Consultar a seleção não cria nem inicializa o lock.
[Correção e provas de concorrência](docs/relatorios/2026-10-08-selection-concurrency.md).

A consulta de uma missão existente agrupa leituras SQL adjacentes e usa nove processos Git,
mantendo a reabertura do banco após os arquivos de entrada e a leitura final
independente. O teste de recusa de rede mede bytes em um observador que permanece
ativo após encerrar o guard. [Medição e regressões](docs/relatorios/2026-10-08-mission-read-stability.md).
O diagnóstico Windows confirmou reset durante o encerramento do helper. O
controlador agora permite até 100 ms para ele fechar após EOF, dentro dos 200 ms
já reservados antes de `kill`. Filhos resistentes continuam sujeitos ao encerramento
forçado. [Correção e validação](docs/relatorios/2026-10-08-guard-cooperative-close.md).
O CI de `9cb3729` passou em sete dos oito jobs: Windows do PR completo aprovado,
com timeout v4 no push daquela revisão. Os testes de EOF e recusa passaram nos dois.

As correções da auditoria recuperam notas de missão/backlog interrompidas
mesmo após outra revisão, preservando edições humanas. Catálogos malformados e falhas
de Git na primeira consulta de ambiente retornam JSON sanitizado.
Veja [correções e regressões](docs/relatorios/2026-10-07-audit-fixes.md).

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

[Tutorial animado em PT-BR](docs/media/youngcrow-guide/README.md): dois capítulos com o visual
de vitrais, lettering e movimentos em Three.js. Inclui layouts 16:9 e 9:16, apresentação
interativa e exportação local de MP4. O tutorial é seguido por um agente de atendimento de clínica fictício:
features, vault, Codex, checkpoint e retomada no Claude. As telas são encenadas e a coordenação
das sessões é manual; a execução autônoma segue em desenvolvimento.

Baixar o vídeo completo: [16:9 para computador](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-16x9.mp4) · [9:16 para celular](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-9x16.mp4).

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
HTML é convertido a partir dos bytes preservados, sem usar a pasta local como origem dos links.
Referências como `/llms.txt` e `../guia` permanecem legíveis e inativas no vault; links HTTP(S)
explícitos continuam clicáveis. A conversão não abre arquivos nem baixa recursos indicados pela página.
Veja a [recuperação das cinco páginas de documentação](docs/relatorios/2026-10-02-docling-html.md).
Na nota extraída, referências Markdown por rótulo viram texto legível; imagens ativas precisam ser
arquivos locais validados. A cópia pública recusa HTML e autolinks. Se a gravação do cache for
interrompida, a próxima ingestão preserva a extração incompleta e tenta novamente.

O perfil opcional de mídia usa Whisper Base local. A prova com WAV e MP4 preservou a frase falada,
os intervalos da transcrição e três quadros amostrados. Um vídeo sem áudio manteve as imagens e
o aviso de extração parcial. Os formatos, limites e comandos estão no [guia de uso](docs/USAGE.md#docling-pt).

Os vínculos locais registram a revisão usada e um trecho de evidência para relacionar a fonte a features
ou decisões. Contradições começam como hipóteses; o sentido da relação precisa ser revisado.
O hook `UserPromptSubmit` registra referências textuais e chama a atenção do agente para `ingest-source`.
Ele ignora curingas de comandos e notas Markdown do próprio vault para evitar cadastros durante uma retomada.
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

O [piloto público](https://matheusrpc.github.io/YoungCrowHarness/) demonstra o rito numa aplicação estática:
um quadro de entregas para acompanhar projeto novo, migração, testes, memória e publicação.
O [exemplo](examples/delivery-board/README.md) tem página com filtros, critérios e um vault próprio.
O percurso local foi verificado por teclado e em tela estreita. No Windows e no Linux, projeto novo e migração
passaram pelo setup real e voltaram ao estado inicial, preservando o trabalho do trial. O site publicado teve revisão, hashes e uso conferidos. A retomada passou no Codex e foi
[confirmada no Claude](docs/relatorios/2026-10-09-p06-offline-review.md): uma sessão
Haiku recuperou a memória em 39,35 s. O verificador original recusou a navegação;
a correção foi conferida offline sobre os mesmos eventos e arquivos, seguida de
revisão do conteúdo, sem outra chamada ao modelo. O recibo de falha foi preservado.
Essa prova do piloto não libera o executor Docker nem comprova descoberta automática de skills.
Veja as [provas e limites](docs/relatorios/2026-10-03-public-pilot.md).
O pacote usa uma lista explícita de arquivos e um manifesto de hashes; o CI do piloto valida dados, testes e navegação do vault.

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
4. Claude Code e Codex: ingestão de HTML, vínculo com feature, fonte inacessível pendente e retomada verificadas em sessões reais independentes. No Claude, o hook também registrou o caminho textual. Veja a [prova do Claude](docs/relatorios/2026-10-03-claude-docling.md) e a [matriz por cliente](docs/relatorios/2026-10-02-docling-ingestion.md); anexos sem caminho exposto exigem registro explícito.

A consulta Markdown, o Graphify opcional e a skill compartilhada estão implementados. As provas
de [Codex](docs/relatorios/2026-10-02-memory-current-clients.md) e
[Claude](docs/relatorios/2026-10-02-claude-memory-capabilities.md) verificaram retomada por índices,
UUIDs/revisões e consulta sem alterar notas ou gerações. Fontes alteradas usam Markdown enquanto
o grafo está obsoleto; a reconstrução é explícita. Na [prova entre projetos](docs/relatorios/2026-10-02-memory-project-isolation.md),
os dois clientes separaram temas de mesmo nome por raiz, `project_id`, UUID e revisão, sem misturar
evidências de publicação. O roteiro e seus limites estão documentados: ambos os projetos estavam
autorizados para leitura; não é uma prova de bloqueio de acesso pelo sistema operacional.
M01–M04 estão verificados nos cenários do [relatório](docs/relatorios/2026-10-02-memory-discovery.md)
e do [plano de memória](docs/superpowers/plans/2026-10-02-memory-discovery.md).
A [governança de skills, agentes e MCPs](docs/superpowers/specs/2026-10-02-capability-governance-design.md)
entrega catálogo verificável, auditoria offline, pacotes privados e uma skill comum aos dois clientes.
Nos ensaios sintéticos nativos, Codex e Claude permitiram a ferramenta prevista, recusaram a
proibida e confirmaram revogação/restauração em sessões novas. Veja a
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
O [desenho da esteira com agentes de IA](docs/superpowers/specs/2026-10-03-ai-product-pipeline-design.md)
detalha personalizer, missões, três PBIs simultâneos por padrão, QA e produção verificada.
O desenho foi aprovado e a [primeira entrega](docs/superpowers/plans/2026-10-03-mission-foundation.md)
está publicada na `main` pelo [PR #18](https://github.com/Matheusrpc/YoungCrowHarness/pull/18).
A base valida configurações de agentes offline em `youngcrow/agents.json`:
três PBIs e três agentes simultâneos por padrão, três ciclos de correção e deploy manual.
Modelo e esforço ficam pendentes até a escolha do usuário. Veja o
[contrato de configuração](docs/USAGE.md#mission-config). A CLI `scripts/missions.py` configura,
importa o backlog, prepara missões e consulta o histórico. O setup instala `yc-personalizer`, `yc-config`, `yc-missao` e `yc-status` nos clientes selecionados.
No Claude, use `/yc-*`; no Codex, use o seletor de skills ou `$yc-*`, conforme o cliente.
O backlog usa contratos Markdown com UUID, DoR, DoD e referências verificadas por hash.
Novas notas começam em `vault/local/product/`; features existentes mantêm seus caminhos e conteúdo.
Missões guardam a configuração e as revisões usadas no preparo. O status aponta fontes alteradas;
`repair` recupera projeções pendentes, permite a recuperação do journal SQLite após interrupção
e preserva edições humanas. Projeções agregadas grandes são conferidas por hash em leitura contínua. Desenvolvimento, QA e deploy
automáticos pertencem às próximas entregas. Veja o [passo a passo](docs/USAGE.md#mission-workflow).

![Preparar uma missão: personalizer, configuração dos agentes, backlog, seleção de features, refinamento e consulta. Execução automática ainda indisponível.](assets/process-mission-planning-pt.svg)

[Abrir o processo de preparação em tamanho completo](assets/process-mission-planning-pt.svg)

[Provas da entrega](docs/relatorios/2026-10-03-mission-foundation.md): 296 testes no Linux, 36 testes
de missões no Windows e percurso de adoção/retorno nos dois sistemas. O ensaio usa a CLI instalada;
não comprova uma conversa nativa com os modelos configurados.

O [diagnóstico dos clientes](docs/USAGE.md#mission-client-checks) consulta modelos e esforços no
catálogo nativo. O desenvolvedor escolhe um nome explícito ou `latest`, que usa a recomendação
atual do cliente para a conta. `client-default` conserva o esforço padrão do modelo. Uma prova
autorizada reserva a tentativa antes de chamar e guarda o resultado no vault. Repetir o UUID
consulta o mesmo recibo; resultado incerto bloqueia outra chamada até reconciliação.
Timeout ou saída incompleta após liberar o cliente conservam esse bloqueio, mesmo com os
processos encerrados. A inspeção do catálogo também supervisiona seus processos e descendentes.

O [backlog completo](docs/BACKLOG.md) acompanha dependências e critérios de aceite. A entrega
[2A: executor e adaptadores](docs/relatorios/2026-10-03-mission-runtime-adapters.md) está parcial:
o mecanismo existe, mas os perfis de permissões de Codex e Claude ainda bloqueiam chamadas reais.
Descobrir um modelo não comprova sua execução. API permanece indisponível nesta etapa.
O [executor isolado](docs/superpowers/specs/2026-10-04-isolated-executor-design.md) usa
Docker Sandboxes local, uma microVM sem montagem do projeto e um contêiner interno para
separar o cliente do coordenador. O [plano aprovado](docs/superpowers/plans/2026-10-04-isolated-executor.md)
tem três PBIs: prova do ambiente, adaptador/recuperação e adoção autenticada nos dois clientes.
R1 está em desenvolvimento; R2/R3 ainda não começaram.

O guardian grava o consumo antes de iniciar cada fase, recusa repetição e conserva um
prazo independente do coordenador. O [launcher com rede restrita](docs/relatorios/2026-10-04-network-launcher.md)
exige recibos privados antes de inicializar ou despachar. Ele instala a negação de rede
antes de conectar a interface e limita o destino TCP dentro do contêiner ao IP público
e à porta selecionados. Isso não comprova o destino final depois dos proxies externos.
O cliente e seus filhos ficam sem privilégios para alterar essa fronteira.

Oito cenários nativos passaram nesta versão, incluindo preparação interrompida, regras
alteradas, repetição, perda de transporte e prazo. OpenAI e Anthropic responderam aos testes
TLS, com 40 tentativas negativas de rede no cliente e nos filhos. Foram requisições HEAD,
sem autenticação ou inferência. A suíte geral executou 390 testes: 379 passaram, 11 foram ignorados por requisitos de ambiente, sem falhas ou erros.
Consulte as [provas e limitações](docs/relatorios/2026-10-04-network-launcher.md) e o
[guia de testes Windows](docs/USAGE.md#tests-windows).

O diagnóstico `client environment --executable CAMINHO --json` verifica o binário e os
pré-requisitos. A opção `--preflight` registra consultas do Docker e preserva suas saídas
em arquivo privado local, com etapa, prazo e erro classificados. As 11 consultas passaram
no terminal local em 7 de outubro. No celular, o diagnóstico confirmou que a sessão
do Windows não disponibilizou seu conjunto de credenciais ao Docker.
Esse resultado não libera execução de IA. Veja a [consolidação do executor](docs/relatorios/2026-10-07-executor-consolidation.md).
Uma consulta posterior pelo celular foi recusada na proteção do armazenamento.
O diagnóstico confirmou proprietário divergente no temporário. No Windows, o comando
agora protege esse arquivo ainda vazio antes de gravar evidências; arquivos e permissões
existentes são preservados. A correção passou na sessão remota e permitiu capturar a
falha de credenciais. `credential_session_unavailable` orienta usar uma sessão do
Windows com acesso ao Gerenciador de Credenciais; o inventário permanece desconhecido.
No PowerShell local do mantenedor, as 11 consultas passaram, com o mesmo binário.
O inventário Docker estava vazio; autenticação e execução isolada continuam pendentes.
Com `--preflight --sandbox NOME`, o diagnóstico também confere políticas, imagem,
recursos e a identidade do serviço antes e depois da coleta. A primeira execução
local passou nas 29 consultas. O resultado descreve metadados estáveis; a reserva
exclusiva e a prova integrada de rede ainda são necessárias para executar clientes.
O relay restrito já está ligado ao guardian e ao launcher em desenvolvimento.
Ele reconstrói o destino autorizado, preserva respostas em streaming e encerra a
conexão no prazo da operação. Passaram 43 testes locais, com revisão independente.
O contrato v4 acrescenta verificação por hash de um valor diferente do placeholder.
Docker integrado e Claude/Codex autenticados ainda precisam de prova. Consulte a
[prova interna atual](docs/relatorios/2026-10-07-injection-proof.md).
O diagnóstico também mostra `execution_reservation`, compartilhada pelos projetos
da mesma conta. A reserva persiste após queda do coordenador; recibo ausente ou
corrompido mantém o bloqueio. O filtro de saída já confere DNS e IP antes de conectar,
com destino sintético limitado a `postman-echo.com:443`. Esses componentes passaram
nos testes locais; sua ligação ao despacho e à recuperação do Docker ainda está pendente.
Veja [reserva e saída](docs/relatorios/2026-10-07-executor-consolidation.md#reserva-compartilhada-e-filtro-de-saída).
`--sandbox NOME` observa uma VM existente sem iniciá-la. O [passo a passo](docs/USAGE.md#sandbox-environment)
explica os resultados. O [reinício ativo](docs/relatorios/2026-10-04-network-launcher.md#reinício-ativo-e-reconciliação)
comprovou a VM parada 3,756 segundos antes do prazo e recusou repetir a operação após
a retomada para inspeção. O recibo anterior, com falha de medição, foi preservado.
R1 ainda depende das rotas restantes, pacote, suspensão e autenticação. Os perfis continuam bloqueados.
Os [ensaios dos endereços do gateway e do Windows](docs/relatorios/2026-10-05-gateway-endpoints.md)
registraram 124 tentativas TCP sem conexão, com TLS dos provedores acessível e nenhum
acesso às sentinelas Windows. A [investigação de DNS e proxy](docs/relatorios/2026-10-05-proxy-resolution.md)
confirmou a proteção dos arquivos de resolução, mas não comprovou o destino final.
A saída atual também não oferece a injeção de credenciais prevista. A [prova conjunta](docs/relatorios/2026-10-05-auth-egress-spike.md)
encerrou três ciclos e encontrou um candidato com IP e identidade do fornecedor fixos.
A [prova nativa](docs/relatorios/2026-10-05-native-proxy-compatibility.md) confirmou TLS nos provedores,
mas a credencial descartável funcionou somente por domínio; o Docker recusou o caminho por IP
nos serviços de eco. A [prova de negação CIDR](docs/relatorios/2026-10-05-hostname-cidr-proof.md)
confirmou que o domínio permitido continua acessível mesmo com todos os IPs negados,
conforme documentado pelo Docker. Essa combinação foi reprovada para o nosso requisito;
a [arquitetura aprovada](docs/superpowers/specs/2026-10-05-exclusive-egress-decision.md)
coloca esse controle após a injeção de credenciais, em uma instalação do Docker Sandboxes
reservada ao YoungCrow. O [plano da prova](docs/superpowers/plans/2026-10-05-exclusive-egress-proof.md)
foi aprovado. O protótipo passou em 60 testes locais. O [ciclo nativo](docs/relatorios/2026-10-05-exclusive-egress-proof.md)
terminou inconclusivo: a primeira operação foi recuperada; a v2 excedeu o prazo antes
de criar o recibo e alterar o Docker. Configurações e permissões foram conferidas,
com cinco VMs paradas. Não há recuperação pendente. O roteiro v2 está bloqueado;
o produto seguirá com [execução local por padrão e runner dedicado opcional](docs/superpowers/specs/2026-10-05-local-and-dedicated-execution.md).
O setup aceita a própria máquina ou um runner aberto pelo VS Code Remote SSH. A seleção
é privada e preservada na reinstalação. A saída de rede ainda depende de aceite e os perfis
de execução seguem bloqueados.
Na [retomada de R1](docs/relatorios/2026-10-06-observed-egress-proof.md), a prova parou
antes das GETs: o roteiro esperava `override` ao gravar um valor padrão, mas o Docker
remove esse override. A correção passou em 75 testes locais. A restauração foi confirmada
por leitura, sem pendência de limpeza. A operação foi consumida; a rede segue sem aceite.
A [prova corrigida](docs/relatorios/2026-10-06-corrected-egress-proof.md) passou no acesso
permitido, mas a falha com o controlador desligado ainda não comprovou o bloqueio esperado.
O diagnóstico posterior encontrou a recusa no log do daemon; o coletor não a reconheceu.
A2 não executada, conjunto inconclusivo e limpeza confirmada. Veja o [panorama de resultados](docs/relatorios/2026-10-06-panorama-executor.md).
Um [coletor separado](docs/relatorios/2026-10-06-captured-egress-evidence.md) passou em onze
testes offline com a mensagem real. Ele preserva os snapshots completos e verifica
origem, porta e horário da recusa. A [integração com o controlador](docs/relatorios/2026-10-06-integrated-egress-controller.md)
também foi validada offline, incluindo A/B/A2 e recuperação sem repetição. A entrada
nativa passou em uma suíte de 120 testes, incluindo sete da entrada remota. O
[guia do ensaio](docs/USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor) registra
a execução pelo mantenedor. A tentativa parou por proprietário incompatível dos
arquivos, após cinco consultas e antes de alterar o Docker. O ajuste de proprietário
passou na sessão remota. A entrada separada passou pela verificação de proprietário,
mas parou ao interpretar o primeiro status do Docker (`JSONDecodeError`). Não houve
alteração no Docker nem limpeza pendente. A captura posterior passou no celular,
com resposta idêntica à local; as cinco consultas iniciais também passaram daqui.
A causa histórica continua sem comprovação. A entrada com captura passou em 129 testes;
na execução seguinte, guardou quatro respostas válidas e parou por `policy_baseline_changed`.
O roteiro confundiu um identificador recriado pela limpeza anterior com mudança de
permissão. Houve 24 consultas, sem GET, reinício ou alteração no Docker. A correção
agora está integrada a uma entrada local, com captura e recuperação. Passaram 102 testes:
sete da entrada Windows, 12 da sequência inicial e 83 do controlador, comparação e fases.
As respostas externas foram simuladas; isso não certifica a rede real.
A entrada corrigida foi executada e parou na consulta `sbx secret ls --json`, com
código 1. Foram 25 consultas, sem GET, reinício ou alteração no Docker; a limpeza foi
confirmada. A mesma consulta passou localmente, inclusive com o auxiliar Windows,
mas a causa da falha remota continua desconhecida: sua mensagem não foi capturada.
O [guia registra a tentativa encerrada](docs/USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor).
Não há novo ensaio completo preparado. O aceite real de A/B/A2 continua pendente.
O [desenho aprovado de setup](docs/superpowers/specs/2026-10-05-execution-setup-design.md) detalha
seleção, diagnóstico por etapa e acesso ao runner pelo VS Code Remote SSH. O
[plano com três PBIs](docs/superpowers/plans/2026-10-05-execution-setup.md) foi implementado nesta branch.
A [validação do setup](docs/relatorios/2026-10-05-execution-setup.md) cobriu oito combinações
de adoção/restauração e 414 testes: 403 aprovados e 11 skips por requisitos do ambiente.
Os resultados finais incluem a repetição do módulo guardian após corrigir sua fixture de relógio.
Use `--execution-location local|dedicated` no setup e
`python3 -B scripts/missions.py environment show --json` para consultar a escolha.
O [guia instalado](skills/personalizer/references/execution.md) explica primeiro uso, migração
e diagnóstico por etapa. Configurar o destino não habilita agentes autônomos.
Os limites de três PBIs e três agentes serão aplicados pela fila da entrega seguinte.

| Próxima entrega | O que falta para a esteira completa |
|---|---|
| 2A. Executor e adaptadores | Completar as provas nativas nas combinações anunciadas; cada perfil sem prova continua bloqueado |
| 2B. Fila e branches | Puxar PBIs por prioridade, aplicar limites e isolar cada desenvolvimento |
| 2C. Continuidade | Pausar, retomar e transferir entre máquina local e servidor |
| 3. QA e integração | Revisão independente, Playwright quando aplicável, três correções e validação conjunta |
| 4. Release e operação | PR protegido, deploy manual/automático, recuperação e produção verificada |
| Aceite do produto | Provar o percurso nos dois clientes, retomar pela memória e publicar guias/demonstração |

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

**Executor handoff:** branch `feat/isolated-executor` contains the work in progress, tests and
reviewed reports for continuing in another environment. Start with the
[full context](docs/HANDOFF-CLOUD-2026-10-07.md) and the
[checkpoint verification](docs/relatorios/2026-10-07-cloud-checkpoint.md).
Integrated network proof and both authenticated clients are still pending; execution profiles remain blocked.

The private B capture bundle was recovered in the cloud. All 26 offline tests passed,
17 pinned hashes matched, and all 635 files remained unchanged. The suite mocks
transport and native effects; native acceptance is still pending.
[Recovery and suite replay](docs/relatorios/2026-10-08-b-source-recovery.md#english-overview).

The [configuration lifecycle review](docs/relatorios/2026-10-08-executor-lifecycle-review.md#english-overview)
identified a fixed proxy between missions as a way to reduce writes. Endpoint ownership
and credential recovery remain unresolved; the alternative is not implemented.
The current contract and gates remain.
The [alternatives review](docs/relatorios/2026-10-09-executor-alternatives.md#english-overview)
received the PC inventory: the Hyper-V role candidate is paused on Windows Home.
This does not establish an existing sbx/WHP incompatibility or resolve Docker's
local contract. No new backend has been implemented.

The maintainer published the Docker inquiry as [issue #690](https://github.com/docker/sbx-releases/issues/690)
on Oct 9. Publication and body were verified through the API; a response about the
local contract is pending. Executor acceptance and the 2B queue remain pending.

The independent delivery improves `yc-status`: it identifies receipts blocking new diagnostics, including other
missions in the project, and directs recovery review or note repair before input
refinement. Status remains read-only. [Usage and limits](docs/USAGE.md#mission-workflow).
[Delivery verification](docs/relatorios/2026-10-08-mission-status-guidance.md#english-overview).

To resume without remembering a code, `python3 -B scripts/missions.py --json list`
shows saved missions with title, code, UUID, revision and recorded state. Then use
`status CODE` to check current blockers. Listing also finds missions with pending
note projections and leaves files unchanged.
[Usage](docs/USAGE.md#mission-workflow) · [Verification](docs/relatorios/2026-10-09-mission-discovery.md#english-overview).

The [YC-204 queue refinement](docs/superpowers/specs/2026-10-09-queue-eligibility-refinement.md#english-overview)
details priority, waiting and capacity decisions. The approved policy serves eligible
ongoing stages before new PBIs, with the same readiness order for every role.
Operational design remains in refinement; native dispatch depends on executor acceptance.

The initial backlog can already be inspected: `status CODE` returns `queue_preview`
with saved PBI priority, dependencies and the first initial candidate when preparation
is current. This read-only view uses the mission snapshot and does not execute agents.
[Contract and limits](docs/USAGE.md#mission-workflow).

The coordinator supports a [persistent multi-PBI rehearsal](docs/USAGE.md#queue-rehearsal):
`queue start`, `queue step` and `queue cancel` record simulated stages and receipts.
`status` shows the stage, next role and pending rehearsal dependencies. QA and corrections
of the active PBI take precedence. The rehearsal can reject QA, pass after one correction,
or exhaust three corrections. Blocked items keep their dependents waiting while independent
items follow saved priority. Counts survive restarts of the same synthetic session.
Correction by real agents remains roadmap work.
Replaying an operation recovers its receipt. No models or real delivery acceptance are involved.
[Evidence and limits](docs/relatorios/2026-10-10-queue-corrections.md#english-overview).

[Explicit PBI Git workspace preparation](docs/USAGE.md#pbi-workspaces) is now available through
`workspace prepare/status/release`, with a pinned base and recoverable receipts. Original checkout
changes are preserved. Release requires a clean owned worktree and retains its branch/commits,
allowing a new trial return preview. Real workers and integration remain pending.

The [PBI context query](docs/USAGE.md#pbi-context) collects criteria, feature, epic and
explicitly linked sources with UUIDs, revisions and hashes. `context` reads the original
checkout's vault and returns private JSON without changing notes or launching agents.
Changed sources are refused; planning gaps remain visible in the result.

The PM can [propose a new order for selected PBIs](docs/USAGE.md#pbi-priority).
`reprioritize --dry-run` previews without writing; applying records the reason,
actor and revision while preserving scope and configuration. An active queue blocks
the change; PBIs with workspace history retain their positions. This is a planning decision.

The Tech Lead can [select a PBI's technical plan](docs/USAGE.md#technical-plan) from
its direct references. The choice records a reason, revision and note hash;
`context` delivers that plan alongside the criteria while preserving the PBI contract.

Preparation also checks frozen hashes against imported notes and references. A mismatch
leaves a draft; `status` blocks inconsistent older snapshots and directs explicit import
and mission revision. [Details](docs/USAGE.md#mission-input-consistency).

To resume a working directory, [query its workspace UUID](docs/USAGE.md#workspace-context).
`workspace context` verifies Git identity and returns the PBI context at the revision
pinned during preparation. Existing work is preserved; the private JSON goes to the terminal.

Checkpoint `77f6e37` passed all eight push/PR CI jobs, including Windows.
[Verified results](docs/relatorios/2026-10-10-workspace-context.md).
On `44cd90f`, Windows CI exposed a 15-second network-test cutoff despite its 30-second
plan. The fixture supervisor now uses that budget; [evidence and pending CI confirmation](docs/relatorios/2026-10-10-network-fixture-budget.md).
Native executor acceptance remains pending.

Upcoming proofs are grouped in a [campaign with batch approval](docs/TEST-RUN-2026-10-10.md),
with ordered stages, limits and stop conditions. Native blockers remain in place.

**Previous Oct 7 checkpoint:** synthetic admission, controller/fixture and audit fixes
are now in [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
The public package passed 516 tests, with 20 skipped; CI could not be queried in that round.
See the [publication record](docs/relatorios/2026-10-07-cloud-publication.md).

`client check` recognizes `isolated-egress-v1` manifests and records a
`controller_pending` block with `model_calls=0`. The attempt preserves mission limits
and its UUID without querying clients or Docker. See the [contract and limits](docs/USAGE.md#synthetic-admission)
and the [cloud continuation report](docs/relatorios/2026-10-07-synthetic-admission.md).

The v4 plan requires a dummy value different from the placeholder, checked against
a hash fixed before execution. The internal proof uses the fixture, relay and guard
with real local processes and sockets; the path without substitution is rejected.
A/B/A2 share configuration with distinct identities. V2/v3 plans remain readable for
recovery without turning historical echo results into injection proof.
**203.6 remains partial:** the Cloud API documents version-conditional credential
deletion, but that contract is unproven for local `sbx` 0.46.0. The native adapter and
profiles remain blocked; B still requires native attribution.
See the [injection proof](docs/relatorios/2026-10-07-injection-proof.md#english-overview).

Activation and recovery now require a write conditional on the full setting state.
Tests preserve an external change made after intent persistence and prevent restart;
recovery keeps the reservation blocked. The local sbx atomic contract remains unproven.
Local validation: 592 tests passed and 20 were skipped.
See the [fix and native blocker](docs/relatorios/2026-10-07-conditional-settings.md#english-overview).

CI for `da28f00` failed in `adoption-windows`, during mission tests, on both push
and PR runs. The other three jobs passed. That step's runner now publishes
test identifiers and allowlisted fixture states in GitHub annotations, preserving
unittest output and status. CI identified two network flows and one controller
shutdown case. Focused execution confirmed `TimeoutError` in the v3 B probe, which
limited its connection to one second. The fixture now uses the remaining phase
deadline and still requires explicit refusal. All five focused cases passed on push;
v3 and v4 hit the outer 15-second limit on the PR run. With event timing diagnostics
at `e674a83`, all five cases passed on both runs. The full local suite passed with
598 successes and 20 skips; full Windows CI was still running at that checkpoint.
Subsequent CI at `63bb229` recorded further timeouts near A2 completion.
[CI evidence and next action](docs/relatorios/2026-10-07-windows-ci-diagnostics.md#english-overview).

Private-storage verification checks all three ignore rules in one Git invocation
and requires every path to match. This reduces processes per check from five to
three while reading current rules at each boundary. Local confirmation passed
602 tests with 20 skips. At `25ee51d`, all five focused Windows cases passed on
push and PR; both full Windows jobs also passed.
[Measurements and regressions](docs/relatorios/2026-10-08-git-preflight-cost.md#english-overview).

Execution-location reads and updates now use the same lock. A competing operation
receives `execution_selection_busy`; after publication, a stale digest is still
rejected. Reading the selection never creates or initializes its lock.
[Concurrency fix and evidence](docs/relatorios/2026-10-08-selection-concurrency.md#english-overview).

Status for an existing mission groups adjacent SQL reads into nine Git processes per query,
while reopening the database after input files and keeping the independent final
read. The network refusal test measures bytes with an observer that survives
guard shutdown. [Measurement and regressions](docs/relatorios/2026-10-08-mission-read-stability.md#english-overview).
Windows diagnostics confirmed a reset during helper shutdown. The controller now
allows up to 100 ms for EOF cleanup within its existing 200 ms stage before `kill`.
Unresponsive children remain subject to forced shutdown.
[Fix and validation](docs/relatorios/2026-10-08-guard-cooperative-close.md#english-overview).
CI at `9cb3729` passed seven of eight jobs: PR Windows passed fully, while a v4
timeout occurred on that push. EOF/refusal tests passed on both Windows runs.

Audit fixes recover interrupted mission/backlog notes even after another
revision, preserving human edits. Malformed catalogs and Git failures during the
first environment query return sanitized JSON.
See [fixes and regressions](docs/relatorios/2026-10-07-audit-fixes.md).

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

[Animated tutorial in Brazilian Portuguese](docs/media/youngcrow-guide/README.md): two
chapters with stained glass artwork, animated lettering and Three.js motion. Includes 16:9
and 9:16 layouts, interactive playback and local MP4 export. It covers current preparation;
the appended fictional clinic reception agent example shows features, the vault, Codex, a checkpoint and
continuation in Claude. Screens are staged and sessions are manually coordinated;
autonomous execution remains under development.

Download the complete video: [16:9 landscape](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-16x9.mp4) · [9:16 mobile](https://github.com/Matheusrpc/YoungCrowHarness/raw/refs/heads/feat/isolated-executor/docs/media/youngcrow-guide/downloads/YoungCrow-9x16.mp4).

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
HTML conversion uses the preserved bytes without treating the local folder as the origin of links.
References such as `/llms.txt` and `../guide` remain readable and inactive in the vault; explicit
HTTP(S) links stay clickable. Conversion does not open files or fetch resources referenced by the page.
See the [recovery of five documentation pages](docs/relatorios/2026-10-02-docling-html.md).
In extracted notes, reference-style Markdown links become readable text; active images must be
validated local files. Public copies reject HTML and autolinks. If a cache write is interrupted,
the next ingestion preserves the incomplete extraction and retries.

The optional media profile uses local Whisper Base. WAV and MP4 tests preserved the spoken phrase,
transcript intervals and three sampled frames. A video without audio retained its images and a
partial-extraction warning. See the [usage guide](docs/USAGE.md#docling-en) for formats, limits and commands.

Local relations record the source revision and a supporting quote to link it to features or decisions.
Contradictions start as hypotheses; the meaning of a relationship still needs review.
The `UserPromptSubmit` hook records textual references and directs the agent to `ingest-source`.
It skips command globs and Markdown notes inside the project's vault to avoid new source records during recovery.
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

The [public pilot](https://matheusrpc.github.io/YoungCrowHarness/) demonstrates the workflow in a static application:
a delivery board covering a new project, adoption, tests, memory and publication.
The [example](examples/delivery-board/README.md) has a page with filters, acceptance criteria and its own vault.
The local flow was checked with keyboard navigation and a narrow viewport. On Windows and Linux, new and existing
projects passed real setup and returned to their initial state while retaining trial work. The published site passed revision, hash and interaction checks. Retrieval passed in Codex and was
[confirmed in Claude](docs/relatorios/2026-10-09-p06-offline-review.md): one Haiku
session retrieved memory in 39.35 seconds. The original verifier rejected navigation;
the fix was checked offline against the same events and files, followed by semantic
review, without another model call. The failed receipt is preserved. This pilot
proof does not enable the Docker executor or prove automatic skill discovery.
See the [evidence and limits](docs/relatorios/2026-10-03-public-pilot.md).
The package uses an explicit file list and hash manifest; the pilot CI checks data, tests and vault navigation.

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
4. Claude Code and Codex: HTML ingestion, a feature relation, an inaccessible-source record and recovery verified in fresh real sessions. The Claude hook also recorded the textual path. See the [Claude proof](docs/relatorios/2026-10-03-claude-docling.md) and [per-client matrix](docs/relatorios/2026-10-02-docling-ingestion.md); attachments without exposed paths need explicit intake.

Markdown retrieval, optional Graphify and the shared skill are implemented. The
[Codex](docs/relatorios/2026-10-02-memory-current-clients.md) and
[Claude](docs/relatorios/2026-10-02-claude-memory-capabilities.md) tests verified recovery through
indices, UUIDs/revisions and queries that preserve notes and generations. Changed sources use
Markdown while the graph is stale; rebuilding is explicit. In the [cross-project test](docs/relatorios/2026-10-02-memory-project-isolation.md),
both clients separated identically named topics by root, `project_id`, UUID and revision,
without mixing publication evidence. The instructions and limits are documented: both projects
were authorized for reading; this does not prove operating-system access restrictions.
M01–M04 are verified in the scenarios covered by the [report](docs/relatorios/2026-10-02-memory-discovery.md)
and [memory plan](docs/superpowers/plans/2026-10-02-memory-discovery.md).
[Skill, agent and MCP governance](docs/superpowers/specs/2026-10-02-capability-governance-design.md)
provides a verifiable catalog, offline auditing, private review bundles and a shared skill.
The native synthetic Codex and Claude tests allowed the intended tool, rejected the forbidden tool
and verified revocation/restoration in fresh sessions. See the
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
The [AI product pipeline design](docs/superpowers/specs/2026-10-03-ai-product-pipeline-design.md),
written in Portuguese, covers the personalizer, missions, three concurrent PBIs by default, QA
and verified production. The design is approved and the
[first delivery](docs/superpowers/plans/2026-10-03-mission-foundation.md) is published on `main`
through [PR #18](https://github.com/Matheusrpc/YoungCrowHarness/pull/18).
Offline agent configuration in `youngcrow/agents.json` defaults to three active PBIs, three parallel
agents, three correction cycles and manual deployment. Model and effort remain pending until chosen.
See the [configuration contract](docs/USAGE.md#mission-config). `scripts/missions.py` configures agents,
imports backlog notes, prepares missions and reads history. Setup installs `yc-personalizer`, `yc-config`, `yc-missao` and `yc-status` for the selected clients.
Use `/yc-*` in Claude and the skill selector or `$yc-*` in Codex, as supported by your client.
Backlog Markdown contracts carry UUIDs, DoR, DoD and references checked by hash.
New notes start in `vault/local/product/`; existing features keep their paths and content.
Missions freeze their configuration and source revisions. Status reports changed inputs; `repair`
recovers pending projections and interrupted SQLite journals while preserving human edits.
Large aggregated projections use streaming hash checks. Automated development, QA and deployment
belong to later deliveries. See the [walkthrough](docs/USAGE.md#mission-workflow).

![Prepare a mission: personalizer, agent configuration, backlog, feature selection, refinement and status. Automatic execution remains unavailable.](assets/process-mission-planning-en.svg)

[Open the preparation process at full size](assets/process-mission-planning-en.svg)

[Delivery evidence](docs/relatorios/2026-10-03-mission-foundation.md): 296 Linux tests, 36 Windows
mission tests and adoption/restoration scenarios on both systems. The smoke uses the installed CLI;
it does not establish a native conversation with the configured models.

[Client diagnostics](docs/USAGE.md#mission-client-checks) read models and efforts from the native
catalog. The developer chooses an explicit name or `latest`, the client's current recommendation
for the account. `client-default` keeps the model's default effort. An authorized check reserves
its attempt before calling and stores the result in the vault. Repeating its UUID reads the same
receipt; an uncertain result blocks another call until reconciliation.
Timeout or incomplete output after releasing the client retains that block, even after its
processes exit. Catalog inspection also supervises its processes and descendants.

The [full backlog](docs/BACKLOG.md#english-overview) tracks dependencies and acceptance criteria.
[2A: executor and adapters](docs/relatorios/2026-10-03-mission-runtime-adapters.md) is partial:
the mechanism exists, but Codex and Claude permission profiles still block live calls.
Discovering a model does not verify execution. API connections remain unavailable in this stage.
The [isolated executor](docs/superpowers/specs/2026-10-04-isolated-executor-design.md)
uses local Docker Sandboxes, a microVM without a project mount and an inner container
separating the client from its coordinator. The [approved plan](docs/superpowers/plans/2026-10-04-isolated-executor.md)
has three PBIs: environment proof, adapter/recovery and authenticated adoption with both
clients. R1 is in development; R2/R3 have not started.

The guardian persists consumption before each phase, refuses replay and keeps a deadline
independent of the coordinator. The [restricted-network launcher](docs/relatorios/2026-10-04-network-launcher.md#english-overview)
requires private receipts before initialization or dispatch. It installs deny rules before
connecting the interface and limits TCP destinations inside the container to the selected
public IP and port. This does not establish the final destination beyond external proxies.
The client and its descendants lack privileges to change that boundary.

Eight native cases passed with this version, including interrupted setup, changed rules,
replay, transport loss and the deadline. OpenAI and Anthropic responded to TLS probes,
with 40 negative network attempts across client and child processes. These were HEAD
requests without authentication or inference. The full suite ran 390 tests: 379 passed and 11 were skipped for environment requirements, with no failures or errors.
See the [evidence and limits](docs/relatorios/2026-10-04-network-launcher.md#english-overview)
and the [Windows test guide](docs/USAGE.md#tests-windows).

The `client environment --executable PATH --json` diagnostic checks the binary and local
prerequisites. Adding `--preflight` records Docker queries and preserves their output in a
private local file, with stage, deadline and classified errors. All 11 queries passed in
the local terminal on October 7. On the phone, the diagnostic confirmed that the Windows
logon session did not provide its credential set to Docker.
This does not enable AI execution. See the [consolidation report](docs/relatorios/2026-10-07-executor-consolidation.md).
A later query from the phone was refused at the storage protection check.
The diagnostic confirmed an owner mismatch on the temporary file. On Windows, the
command now protects that empty file before writing evidence, preserving existing
files and permissions. The correction passed remotely and captured the credential
failure. `credential_session_unavailable` directs the operator to a Windows session
with Credential Manager access; the credential inventory remains unknown.
All 11 queries then passed in the maintainer's local PowerShell session with the same
binary. The Docker credential inventory was empty; authentication and isolation acceptance remain pending.
With `--preflight --sandbox NAME`, the diagnostic also checks policies, image,
resources and the daemon's process identity before and after collection. The first
local run passed all 29 queries. This establishes stable metadata; exclusive reservation
and the integrated network proof are still required before running clients.
The restricted relay is connected to guardian and launcher in development.
It reconstructs the authorized destination, preserves streaming responses and closes
connections within the operation deadline. All 43 local tests passed, with independent
review. The v4 contract adds hash verification of a value distinct from the placeholder.
Integrated Docker and authenticated Claude/Codex still need proof. See the
[current internal proof](docs/relatorios/2026-10-07-injection-proof.md#english-overview).
The diagnostic also reports `execution_reservation`, shared across projects using
the same account. Reservations survive coordinator loss; missing or corrupt records
keep execution blocked. The destination guard checks DNS and IPs before connecting,
currently limited to synthetic `postman-echo.com:443` traffic. These components passed
local tests; wiring them to Docker dispatch and recovery remains pending.
See [reservation and egress](docs/relatorios/2026-10-07-executor-consolidation.md#reserva-compartilhada-e-filtro-de-saída).
`--sandbox NAME` observes an existing VM without starting it. The [walkthrough](docs/USAGE.md#sandbox-environment)
explains results. The [active restart](docs/relatorios/2026-10-04-network-launcher.md#english-overview)
confirmed the VM stopped 3.756 seconds before the deadline and refused another run
after booting for inspection. The earlier measurement failure remains recorded.
Remaining routes, package rebuilding, suspension and authentication still need
validation. Native profiles remain blocked.
The [gateway-address and Windows probes](docs/relatorios/2026-10-05-gateway-endpoints.md#english-overview)
recorded 124 unsuccessful TCP attempts while provider TLS remained reachable and
Windows sentinels received no unexpected connections. The [DNS and proxy investigation](docs/relatorios/2026-10-05-proxy-resolution.md#english-overview)
confirmed resolver-file protection but did not establish the final destination.
The current egress path also lacks the planned credential-injection mechanism. The [joint probe](docs/relatorios/2026-10-05-auth-egress-spike.md#english-overview)
finished three cycles and found a candidate with fixed provider IP and identity. The [native probe](docs/relatorios/2026-10-05-native-proxy-compatibility.md#english-overview)
confirmed provider TLS, but disposable credential injection worked only through hostname
CONNECT; Docker rejected the IP path on the echo services. The [CIDR-deny probe](docs/relatorios/2026-10-05-hostname-cidr-proof.md#english-overview)
confirmed that the allowed hostname remains reachable when all IPs are denied, as
Docker documents. This combination fails our requirement. The [approved design](docs/superpowers/specs/2026-10-05-exclusive-egress-decision.md#english-overview)
places enforcement after credential injection, in a Docker Sandboxes installation
reserved for YoungCrow. The [proof plan](docs/superpowers/plans/2026-10-05-exclusive-egress-proof.md)
is approved. The prototype passed 60 local tests. The [native cycle](docs/relatorios/2026-10-05-exclusive-egress-proof.md#english-overview)
ended inconclusively: the first operation was recovered; v2 timed out before creating its
receipt or changing Docker. Settings and permissions were verified, with five VMs stopped.
No recovery remains pending. The v2 entry point is blocked. The product will offer
[local execution by default and an optional dedicated runner](docs/superpowers/specs/2026-10-05-local-and-dedicated-execution.md#english-overview).
VS Code users will be able to run the same pipeline on their own machine or a selected
machine/server. Setup now records a private selection and preserves it on reinstallation.
Network egress still requires acceptance and product profiles stay blocked.
The [R1 continuation](docs/relatorios/2026-10-06-observed-egress-proof.md#english-overview)
stopped before any GET: the script expected an override when assigning a default value,
but Docker removes that override. The correction passed 75 local tests. Restoration was
verified through read-only checks, with no cleanup pending. The operation is consumed;
network enforcement remains unverified.
The [corrected proof](docs/relatorios/2026-10-06-corrected-egress-proof.md#english-overview)
passed its positive control; the disconnect with the guard absent did not establish the
intended refusal automatically. Later daemon-log analysis attributed the disconnect to
upstream refusal; A2 did not run. Overall inconclusive, cleanup verified. See the [results overview](docs/relatorios/2026-10-06-panorama-executor.md#english-overview).
A [separate collector](docs/relatorios/2026-10-06-captured-egress-evidence.md#english-overview)
passed eleven offline tests using the real event. It preserves full snapshots and checks
the refusal source, endpoint and time. [Controller integration](docs/relatorios/2026-10-06-integrated-egress-controller.md#english-overview)
was also validated offline, including A/B/A2 and recovery without replay. The native
entry passed 120 tests, including seven remote-entry tests. The
[probe guide](docs/USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor) covers the
maintainer's execution. The attempt stopped on incompatible file ownership after
five queries and before Docker changes. The owner adjustment passed in the remote
session. The separate entry passed its owner check but stopped while parsing the first
Docker status reply (`JSONDecodeError`). No Docker changes or cleanup were needed.
The later remote capture matched the local response byte for byte; all five initial
queries also passed locally. The original failure remains unexplained. The captured
entry passed 129 tests; its subsequent native run retained four valid status replies
but stopped on `policy_baseline_changed`. The controller mistook a rule ID regenerated
by earlier cleanup for a permission change. It made 24 queries, with no GET, restart
or Docker change. The correction is now integrated into an import-only entry with capture
and recovery. All 102 tests passed: seven for the Windows entry, 12 for the full initial
sequence and 83 for the controller, comparison and downstream phases. External replies were simulated;
this does not certify real networking. The corrected native entry was consumed and
stopped when `sbx secret ls --json` exited 1. All 25 commands were reads, with no
external GET, restart or Docker mutation; cleanup was verified. The same query passed
locally, including through the Windows helper. The remote cause remains unknown
because its error message was not captured. The [guide records the closed attempt](docs/USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor).
No new full probe is prepared. Native A/B/A2 acceptance remains pending.
The [approved setup design](docs/superpowers/specs/2026-10-05-execution-setup-design.md#english-overview)
details selection, phase-specific diagnostics and VS Code Remote SSH access to the runner.
Its [three-PBI implementation plan](docs/superpowers/plans/2026-10-05-execution-setup.md)
is implemented on this branch. [Setup validation](docs/relatorios/2026-10-05-execution-setup.md#english-overview)
covered eight adoption/restore combinations and 414 tests: 403 passed and 11 were skipped
for environment requirements. Final results include a guardian-module rerun after its
test clock was corrected. Use `--execution-location local|dedicated` during setup and
`python3 -B scripts/missions.py environment show --json` to read the choice.
The [installed guide](skills/personalizer/references/execution.md#english) covers first use,
migration and phase diagnostics. Selection does not enable autonomous agents.
The following queue delivery will enforce the separate limits of three PBIs and three agents.

| Next delivery | Remaining work for the complete pipeline |
|---|---|
| 2A. Executor and adapters | Complete native proofs for advertised combinations; unverified profiles stay blocked |
| 2B. Queue and branches | Pull PBIs by priority, enforce limits and isolate each development workspace |
| 2C. Continuity | Pause, resume and transfer between a local machine and a server |
| 3. QA and integration | Independent review, Playwright where applicable, three corrections and joint validation |
| 4. Release and operations | Protected PR, manual/automatic deployment, recovery and verified production |
| Product acceptance | Prove the flow in both clients, recover context from memory and publish guides/demo |

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

O CI de egress também anota exceções durante o preparo, supervisor e limpeza da fixture,
com a última etapa alcançada e a categoria do erro. Mensagens e caminhos ficam fora da anotação.
[Como interpretar / How to interpret](docs/USAGE.md#ci-fixture-diagnostics).
Egress CI also annotates fixture setup, supervision and cleanup exceptions, reporting the
last stage reached and an error category. Annotations exclude exception messages and paths.

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
Com `--discovery-only`, pode consultar um cliente por vez e salvar recibo sem prompt.
As quatro skills de missão foram [descobertas no Codex/Linux e Claude/Windows](docs/relatorios/2026-10-09-client-skill-discovery.md),
com zero prompts. A aplicação nativa continua pendente em YC-011.
O [roteiro Windows](docs/YC011-CLAUDE-DISCOVERY.md) prepara uma cópia pequena e consulta
o Claude sem prompt, preservando os pacotes P06.
No modo completo, o Codex envia uma requisição a um modelo fictício em loopback; o Claude carrega metadados pelo SDK.
Não há chamada de modelo pago, execução de plugins reais ou conexão MCP. Confira o
[guia dos clientes](docs/USAGE.md#clientes-pt) para confiança e ativação.

Tests cover installation, preservation, paths, indices and resumption. Symlink cases run on Linux;
the native junction test runs on Windows. The optional smoke check uses real client loaders, a
loopback model fixture for Codex and SDK metadata initialization for Claude. It makes no paid model
calls or MCP connections and does not prove third-party plugin execution.
`--discovery-only` checks one client at a time and saves a receipt without a prompt.
The four mission skills were [discovered in Codex/Linux and Claude/Windows](docs/relatorios/2026-10-09-client-skill-discovery.md),
with zero prompts. Native application remains pending under YC-011.
The [Windows recipe](docs/YC011-CLAUDE-DISCOVERY.md) prepares a small checkout and queries
Claude without a model prompt, preserving P06 packages.

<p align="center">
  <img src="assets/assinatura.svg" alt="☧ Ora et labora ☧ et coda &lt;/&gt;" width="100%">
</p>
