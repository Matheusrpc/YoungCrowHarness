# Backlog do YoungCrowHarness

Frente: produto completo e sequência de entrega. Atualizado em 2026-10-09.

Checkpoint para continuidade na cloud: `feat/isolated-executor`.
[Contexto e próximos passos](HANDOFF-CLOUD-2026-10-07.md) ·
[verificação da publicação](relatorios/2026-10-07-cloud-checkpoint.md).
YC-203 continua parcial; versionar o progresso não conclui o aceite do executor.

Checkpoint validado: `a0af931`, com oito jobs aprovados entre push e PR, incluindo
Windows. A prévia inicial da fila está publicada; o próximo aceite do executor
depende do contrato sbx local. [Publicação e CI](relatorios/2026-10-09-queue-preview.md#publicação-e-ci-conferidos).
Validated checkpoint: `a0af931`, all eight push/PR jobs passed, including Windows.
The initial queue preview is published; native acceptance still needs the local sbx contract.

**Consulta ao Docker publicada em 9/out:** [issue #690](https://github.com/docker/sbx-releases/issues/690),
aberta pelo mantenedor e conferida pela API. Aguardar resposta aplicável ao sbx local;
a consulta permanece sem comentários na verificação. Novo ciclo nativo continua fora desta etapa.
A entrega independente corrige a orientação de `yc-status`, na preparação
já existente: recibos abertos em qualquer missão do projeto, recuperação integrada e
projeções pendentes/conflitantes passam a orientar a próxima ação. Não habilita 2B.
[Entrega e verificação](relatorios/2026-10-08-mission-status-guidance.md).
**Docker inquiry published on Oct 9:** [issue #690](https://github.com/docker/sbx-releases/issues/690),
opened by the maintainer and verified through the API. Await a response applicable
to local sbx; the issue had no comments when checked. A new native cycle remains outside this step.
Independent work fixes `yc-status` guidance for unresolved
repository runs, integrated recovery and pending/conflicting projections; it does not enable 2B.

Retomada: `missions.py --json list` encontra missões salvas por código, título, UUID,
revisão e estado registrado, inclusive com projeção pendente. `status CODIGO` consulta
os impedimentos atuais. [Entrega e verificação](relatorios/2026-10-09-mission-discovery.md).
Resuming: `missions.py --json list` discovers saved missions by code, title, UUID,
revision and recorded state, including pending projections. `status CODE` checks current blockers.

Preparação antecipada de YC-204: `status` apresenta `queue_preview`, com prioridade,
dependências e primeiro candidato inicial. Usa dados existentes e preserva o bloqueio
de execução; a coordenação, as vagas e a ordem entre etapas ainda não estão implementadas.
Early YC-204 preparation: `status` exposes `queue_preview` with priority, dependencies
and the first initial candidate. Execution stays gated; coordination, slots and
ordering across ongoing stages remain unimplemented.

Revisão de arquitetura em 8/out: proxy fixo entre missões pode reduzir escritas, mas
ainda exige proteção do endpoint e recuperação verificável de credenciais. A instalação
exclusiva já estava aprovada; não iniciar uma reescrita apenas para evitar a consulta
ao fornecedor. A alternativa não foi implementada. [Parecer](relatorios/2026-10-08-executor-lifecycle-review.md).
Architecture review: a fixed proxy between missions could reduce writes, but endpoint
ownership and credential recovery remain unresolved. Exclusive installation was already
approved. No replacement was implemented; a vendor issue remains optional.

Histórico de 8/out: leituras de missão e observação independente de egress, publicado
em `b106bc5`. Passaram 616 testes locais, com 20 pulados; adoção com diagnóstico em
consumidor novo/existente também passou. Os 12 focais Windows passaram no push e no PR;
a suíte completa do PR passou, mas a do push falhou na recusa de rede: sete dos oito
jobs passaram. Em `f3e091d`, os dois Windows confirmaram `ConnectionResetError`
antes de EOF. O controlador agora reserva parte do prazo existente para limpeza
cooperativa; passaram 620 testes locais, com 20 pulados. O CI de `9cb3729` terminou
com sete dos oito jobs aprovados. O Windows do PR passou integralmente; o push
teve timeout v4 antes do primeiro pedido SOCKS registrado. Os testes de EOF e
recusa passaram nos dois Windows. Naquela revisão, restava localizar essa pausa do v4.
[Encerramento e provas](relatorios/2026-10-08-guard-cooperative-close.md).
[Entrega e medição](relatorios/2026-10-08-mission-read-stability.md).
Oct 8 history: mission reads and independent egress observation, published at
`b106bc5`. Local validation passed 616 tests with 20 skips and installed-consumer
diagnostics in new/existing projects. All 12 focused Windows cases passed on push
and PR; the full PR suite passed, while push Windows failed the network refusal
test: seven of eight jobs passed. At `f3e091d`, both Windows runs confirmed a reset
before EOF. The controller now uses part of its existing deadline for cooperative
cleanup; 620 local tests passed with 20 skips. CI at `9cb3729` passed seven of
eight jobs. PR Windows passed fully; push Windows timed out in v4 before the first
recorded SOCKS request. EOF/refusal tests passed on both Windows runs. At that revision,
the next investigation was to locate the v4 delay.
[Shutdown evidence](relatorios/2026-10-08-guard-cooperative-close.md#english-overview).

Histórico da investigação: falha da suíte de missões em `adoption-windows`
no CI de `da28f00`. Push e PR falharam; os outros três jobs passaram. O runner publica
IDs dos testes falhos nas anotações. Em `a9d05ea`, falharam os dois percursos positivos
de `NetworkBindingTests`; o CI do PR também falhou no encerramento abrupto do guard.
O CI de `919b0a4` confirmou `TimeoutError` na sonda B v3. A correção da fixture
usa o prazo restante da fase, sem aceitar timeout como recusa nem ampliar o limite
do supervisor. Em `32960b8`, os cinco casos passaram no push; no PR, v3 e v4
atingiram 15 s. O ledger preservado após timeout passou a orientar a localização
do atraso. Em `e674a83`, os cinco focais passaram
em ambos os runs; naquele checkpoint, o CI completo ainda estava em andamento.
[Evidência e diagnóstico](relatorios/2026-10-07-windows-ci-diagnostics.md).

Em `63bb229`, o ledger localizou os timeouts no encerramento de A2. A verificação
de ignore passa a agrupar três consultas em uma, mantendo todos os caminhos e
checagens atuais. O CI Windows completo de `25ee51d` passou dentro do mesmo limite de 15 s.
[Redução de custo e critérios](relatorios/2026-10-08-git-preflight-cost.md).
At `63bb229`, ledger timelines located timeouts near A2 completion. Ignore preflight
now batches three queries into one while retaining all checks. Full Windows CI at
`25ee51d` passed within the unchanged 15-second supervisor limit.

A correção da seleção concorrente usa o mesmo lock para inventário, leitura e troca.
As provas com processos e barreiras cobrem criação inicial, atualização, consulta e
bootstrap concorrente. A aquisição em lock vazio/somente leitura no Windows passou
nos focais de `b106bc5`; o CI completo do baseline `c8e7f0b` já passou.
[Evidências da correção](relatorios/2026-10-08-selection-concurrency.md).
Concurrent selection now locks inventory, reads and updates together. Process/barrier
regressions cover initial creation, updates and concurrent bootstrap. Empty/read-only
lock cases passed on Windows in the `b106bc5` focal checks; full baseline CI at
`c8e7f0b` also passed.

A recuperação de B (203.8) está conferida: o ZIP privado trouxe as 13 dependências
diretas e as transitivas necessárias aos 26 testes selecionados. Todos passaram na
cloud, com 17 hashes fixados conferidos e os 635 arquivos preservados. A suíte mantém
seus mocks de transporte, guard e efeitos nativos; não houve tentativa de processo ou
rede. Resta integrar a atribuição ao contrato atual e cumprir o aceite nativo,
preservando o bloqueio do contrato sbx local. [Provas e limites](relatorios/2026-10-08-b-source-recovery.md).
B recovery (203.8) is verified: the private ZIP supplied the 13 direct dependencies
and transitive inputs needed by the selected 26 tests. All passed in the cloud;
17 pinned hashes matched and all 635 files remained unchanged. The suite retains
its transport, guard and native-effect mocks; no process or network attempt occurred.
Integration with the current contract and native acceptance remain pending.

A integração interna de 203.6 usa plano v4, guard no mesmo grupo/job e diário anterior
aos efeitos. A/A2 reutilizam a porta; B exige ausência. Recuperação observa proprietário
e porta ausentes e restaura apenas settings sandbox ainda iguais aos valores da operação.
**203.4 interna; 203.5 e 203.6 parciais.** Políticas e credenciais permanecem imutáveis.
[Prova de injeção](relatorios/2026-10-07-injection-proof.md).

A ativação/restauração interna exige escrita atômica condicionada ao setting completo.
Os testes preservam alterações externas feitas depois da intenção, sem reiniciar ou
liberar a reserva na recuperação. O diário continua v3/v4, sem migração.
[Correção atual e bloqueio nativo](relatorios/2026-10-07-conditional-settings.md).

O contrato v4 já exige hash de um valor distinto do placeholder, fixado no plano;
A/B/A2 usam o mesmo placeholder/hash/proxy/CA. O percurso local recusa ausência de
substituição e conserva os contratos antigos para recuperação.
O próximo passo é comprovar, no sbx local 0.46.0, identidade, versão e remoção atômica
condicionada da credencial fictícia. A API Cloud documenta `uid`/`etag`/`If-Match`,
mas seus recursos são separados dos locais. Comparar e depois remover por placeholder
permite uma alteração externa entre as operações. A pesquisa adicional de guias API,
daemon e release 0.46.0 não fechou essa compatibilidade. Também falta comprovar escrita
condicionada dos settings locais. **Adaptador nativo bloqueado por contrato externo:**
obter referência aplicável do fornecedor; não repetir as mesmas buscas nem criar
outro roteiro experimental. Depois: adaptador, pacote e aceite nativo.

The internal 203.6 integration uses a v4 plan, inherited guard containment and a journal
before effects. A/A2 reuse the port; B requires absence. Recovery observes owner and
port absence and restores only sandbox settings still matching this operation.
**203.4 is internal; 203.5 and 203.6 remain partial.** Policies and credentials are immutable.
V4 fixes an expected hash for a value distinct from the placeholder and shares the
placeholder/hash/proxy/CA across A/B/A2. Local tests reject missing substitution;
historical recovery remains supported. Next: establish identity, version and atomic
conditional deletion for local sbx 0.46.0. The Cloud API documents these semantics,
but uses a separate store. Additional API/daemon/release documentation did not establish
local compatibility. Conditional local setting writes also need proof. The native
adapter is blocked on an applicable vendor contract. Internal tests now preserve
changes made after intent persistence using a conditional-write contract, keeping
recovery reserved. Then implement the native adapter and acceptance tests.

A entrada pública `client check` continua em `failed/controller_pending`, com zero
chamadas de modelo. Perfis nativos seguem bloqueados. A sequência é **203.6 e restante
da recuperação → pacote e A/B/A2 nativo → clientes autenticados e adoção → fila/agentes
→ QA → release/operação**. A publicação anterior, com controlador/fixture e correções
AUD-01, AUD-02 e PR24-F2, está no [checkpoint cloud](relatorios/2026-10-07-cloud-publication.md).

Public `client check` still returns `failed/controller_pending` with zero model calls;
native profiles remain blocked. Order: **203.6 and remaining recovery → package and
native A/B/A2 → authenticated clients and adoption → queue/agents → QA → release/operations**.
CI for `da28f00` failed in Windows mission tests on both push and PR runs; the other
three jobs passed. Diagnose this failure before native acceptance. The step now emits
failed test identifiers as annotations. At `a9d05ea`, both positive NetworkBinding
flows failed; the PR run also failed the abrupt controller shutdown test. A focused
step confirmed `TimeoutError` in the v3 B probe at `919b0a4`. The fixture fix uses
the remaining phase deadline while retaining explicit refusal and the supervisor
limit. At `32960b8`, all five cases passed on push, but v3 and v4 hit 15 seconds on
the PR run. Next: locate the delay using the durable ledger after timeout and follow
the full Windows suite. At `e674a83`, all five focused cases passed on both runs;
full CI remains in progress.
[Evidence](relatorios/2026-10-07-windows-ci-diagnostics.md#english-overview).

Este é o índice público do trabalho necessário para entregar a esteira definida na
[especificação aprovada](superpowers/specs/2026-10-03-ai-product-pipeline-design.md).
A base está publicada; a preparação de missões entrou na `main` pelo
[PR #18](https://github.com/Matheusrpc/YoungCrowHarness/pull/18). A execução autônoma ainda precisa
das entregas abaixo. Não há estimativa de prazo ou percentual de conclusão validada.

O público inicial é formado por desenvolvedores individuais e pequenos times com Claude Code
ou Codex. A primeira versão completa deve levar uma missão de uma a N features até uma versão
conjunta em produção verificada, em projeto novo ou migrado, com retomada pelo vault.

## Como acompanhar

- [Base entregue](#base-entregue)
- [Sequência das entregas](#sequência-das-entregas)
- [Pendências de prova da base](#pendências-de-prova-da-base)
- [Frente 2: execução e continuidade](#frente-2-execução-e-continuidade)
- [Frente 3: QA e integração](#frente-3-qa-e-integração)
- [Frente 4: release e operação](#frente-4-release-e-operação)
- [Aceite do produto completo](#aceite-do-produto-completo)
- [Extensões após o núcleo](#extensões-após-o-núcleo)

Os códigos `YC-*` identificam itens deste planejamento público. Eles não são missões ou PBIs
já importados no banco operacional. A decomposição em tarefas de código fica nos planos de cada
entrega. Um item planejado só fica pronto para desenvolvimento depois de ter DoR, DoD, dependências
e plano revisados. Três PBIs ativos é o limite inicial de trabalho em andamento; o backlog pode
ter quantos itens o produto exigir.

## Base entregue

| Capacidade | Estado e evidência |
|---|---|
| Setup e preservação do projeto | Instalador com preflight e testes de preservação; [primeira entrega](relatorios/2026-10-01-primeira-entrega.md) |
| Personalizer para projeto novo e existente | Entrevista retomável, auditoria e perfil; [ensaio](relatorios/2026-10-02-personalizer.md) |
| Vault, índices e integrações | Notas ligadas, especialista em integração e fontes; [integrações](relatorios/2026-10-01-integration-vault.md) e [verificador](relatorios/2026-10-02-vault-check.md) |
| Docling e referências | Documentos, HTML, áudio/vídeo e origem privada; [matriz](relatorios/2026-10-02-docling-ingestion.md) e [Claude](relatorios/2026-10-03-claude-docling.md). Anexos sem caminho exposto exigem registro explícito |
| Memória consultável | Markdown, Graphify opcional e retomada entre sessões/projetos; [isolamento de temas](relatorios/2026-10-02-memory-project-isolation.md) |
| Governança de skills, agentes e MCPs | Catálogo, auditoria e provas delimitadas por cliente; [matriz](relatorios/2026-10-02-capability-governance.md). Auditoria não concede autorização |
| Experimentação reversível | Baseline anterior ao setup e retorno preservando o trabalho do trial; [provas](relatorios/2026-10-02-reversible-adoption.md). Efeitos em serviços externos ficam fora do retorno de arquivos |
| Exemplo público | Quadro de entregas publicado e verificado; [piloto](relatorios/2026-10-03-public-pilot.md). Retomada do piloto no Claude ainda pendente |
| Frente 1: preparação de missões | Configuração, backlog, DoR/DoD, histórico e quatro skills; [provas](relatorios/2026-10-03-mission-foundation.md). Execução dos modelos ainda não verificada |

## Sequência das entregas

As frentes 1–4 preservam a numeração da especificação. A frente 2 tem três incrementos para
permitir verificar o executor antes de lhe dar uma fila de desenvolvimento e transferência.

| Ordem | Entrega | Resultado visível | Situação |
|---|---|---|---|
| 1 | Fundação das missões | Personalizar, configurar, preparar e consultar | Publicada |
| 2A | Executor limitado e adaptadores | Inspecionar o cliente e provar uma execução delimitada, com recibo e recuperação | Parcial: mecanismo implementado; perfis nativos bloqueados. [Provas e pendências](relatorios/2026-10-03-mission-runtime-adapters.md) |
| 2B | Fila e desenvolvimento | Puxar PBIs por prioridade, com três PBIs/três agentes e branches próprias | Planejada; depende de 2A |
| 2C | Continuidade | Pausar, retomar e transferir local/servidor sem duplicar responsabilidade | Planejada; depende de 2B |
| 3 | QA e integração | Revisão independente, testes, Playwright, correções e versão integrada | Planejada; depende de 2B; aceite conjunto inclui 2C |
| 4 | Release e operação | PR protegido, deploy manual/automático e produção verificada | Planejada; depende de 3 e 2C |
| Aceite | Produto completo | Percurso real nas combinações anunciadas, documentação e pacote público | Planejado; depende das frentes anteriores |

A implementação de `YC-201` e `YC-202` está entregue no incremento 2A parcial. O próximo aceite
é concluir `YC-203`, comprovando os perfis nativos antes de habilitar a fila. As provas pendentes
da base exigem acesso e limites explícitos; o backlog não autoriza chamadas por si só.

## Pendências de prova da base

As provas serão organizadas em [lotes controlados](TEST-RUN-2026-10-10.md), com
autorização por pacote definido e avanço entre etapas elegíveis sem confirmação
por teste. O roteiro preserva limites, aceites separados e os bloqueios atuais.
Pending proofs are grouped in controlled batches, with one approval per defined
package. Existing limits, separate acceptance criteria and current blockers remain.

| ID | Entrega | Dependência | Critério de aceite | Estado |
|---|---|---|---|---|
| YC-010 | Retomar o piloto público em sessão nova do Claude | Login válido e tentativa delimitada | Encontrar índices, UUIDs, revisão e produção observada sem receber o histórico inteiro; registrar resultado real | Tentativa de 9/out falhou por OAuth expirado. Login renovado; [13 testes Windows passaram](relatorios/2026-10-09-p06-windows-tests.md). [Pacote r2 preparado](P06-CLAUDE.md#nova-operação-preparada-em-9out) com zero prompts; execução aguarda autorização específica. Aceite de memória pendente |
| YC-011 | Provar as quatro novas skills nos clientes nativos | Instalação atual e sessão autorizada em cada cliente | Descobrir e aplicar `yc-personalizer`, `yc-config`, `yc-missao` e `yc-status`; preservar dados e distinguir preparo de execução | Pendente; integra a prova de YC-203 |

## Frente 2: execução e continuidade

PM responde por objetivo, prioridade e DoR/DoD; Tech Lead detalha interfaces e dependências.
Desenvolvimento implementa; QA produz a prova independente. Os papéis serão agentes na esteira.
Até ela existir, esses ritos são conduzidos nas sessões autorizadas.

| ID | Feature / PBI | Depende de | Critério de aceite | Estado |
|---|---|---|---|---|
| YC-201 | 2A: preflight e compatibilidade dos clientes | Frente 1 | Conferir cliente, versão, modelo/effort, autenticação selecionada e capacidades. Configuração desconhecida fica bloqueada, sem fallback ou chamada de modelo | Implementado; catálogo dinâmico e recusas testados. Perfis nativos continuam sem aceite de execução |
| YC-202 | 2A: execução limitada e recibos duráveis | YC-201 | Reservar operação antes de chamar; impor tempo e quantidade, registrar consumo observado, encerrar processos próprios e conservar resultado incerto sem repetir | Verificado com simuladores: limites, recuperação e recibos; chamadas nativas bloqueadas |
| YC-203 | 2A: instalação, consulta e provas dos adaptadores | YC-202 | Provar cliente autenticado e API explícita quando houver acesso, em matriz por ambiente; consulta sem escrita e adoção preservada. Cada combinação sem prova permanece indisponível | Parcial; inspeção Claude corrigida. Prova local reproduz falha de isolamento do Codex; chamadas reais bloqueadas. [Evidência atual](relatorios/2026-10-03-native-client-verification.md) |
| YC-204 | 2B: coordenador e fila priorizada | YC-203 para despacho | Uma missão ativa por repositório; três PBIs e três execuções como limites distintos; dependências e ordem persistidas. Sem item elegível, persistir espera | Prévia inicial somente leitura implementada; [ordenação aprovada, desenho operacional em refinamento](superpowers/specs/2026-10-09-queue-eligibility-refinement.md). Coordenação e despacho pendentes |
| YC-205 | 2B: branches e worktrees por PBI | YC-204 | Um escritor por checkout, base registrada, alterações do usuário preservadas, limpeza apenas de recursos próprios e recuperação após criação interrompida | Planejado |
| YC-206 | 2B: decisões de PM/Tech Lead e contexto dos agentes | YC-204, YC-205 | Validar propostas estruturadas e revisões; repriorizar somente PBIs não iniciados; avisar líderes uma vez por evento. Contexto reúne referências necessárias, sem ampliar escopo | Planejado |
| YC-207 | 2C: pausa, retomada e cancelamento | YC-206 | Encerrar despachos/processos, persistir consumo e tentativas, reconciliar efeito incerto e retomar sem repetição. Cancelamento explícito libera a vaga e conserva o trabalho | Planejado |
| YC-208 | 2C: pacote privado e troca de responsável | YC-207 | Transferir Git, estado, notas e evidências com hashes; excluir credenciais; importar pausado. Origem perde direito de retomar a geração entregue | Planejado |
| YC-209 | 2C: prova local/servidor nos dois sentidos | YC-208 | Transferência interrompida, repetida e confirmação perdida preservam um único responsável; contadores sobrevivem e sessão nova localiza o histórico | Planejado |

O mantenedor escolheu o ambiente separado após os [controles complementares](relatorios/2026-10-04-native-permission-controls.md).
O [desenho detalhado](superpowers/specs/2026-10-04-isolated-executor-design.md) foi aprovado.
O [plano de implementação](superpowers/plans/2026-10-04-isolated-executor.md) foi aprovado; R1 está em andamento.
Seus três PBIs refinam YC-203: ambiente/prova sem modelo (2A-R1), adaptador/recuperação (2A-R2)
e prova autenticada/adoção nos dois clientes (2A-R3). Não criam novos itens na contagem principal.
Nenhum foi concluído. O início de 2B continua dependente da prova de execução.
Em 7 de outubro, o mantenedor aprovou a [consolidação em três PBIs](superpowers/plans/2026-10-07-executor-consolidation.md).
O diagnóstico compartilhado está em implementação, com evidência privada e 11 consultas
nativas de leitura aprovadas no terminal local. A nova captura remota identificou
conjunto de credenciais indisponível na sessão Windows. A prova integrada e os dois clientes autenticados continuam pendentes;
o inventário Docker observado não tinha credenciais de provedores cadastradas.
O primeiro ciclo de correção trata a recusa `execution_storage_unprotected` no celular:
o diagnóstico confirmou `temporary_evidence` / `owner_mismatch`. O segundo ciclo
protege somente o novo temporário vazio; a confirmação remota passou e registrou a
falha de credenciais. A próxima prova requer uma sessão com acesso ao conjunto de
credenciais. Não há nova prova de rede agendada para a sessão remota que falhou.
O mantenedor retomou o PowerShell local e confirmou as 11 consultas com sucesso,
incluindo credenciais. O contexto local pode seguir para integração; o perfil continua bloqueado.
O preflight de candidato está implementado na mesma entrada `client environment`:
29 consultas locais passaram, cobrindo identidade do processo, políticas e baseline
repetido. O relay restrito está ligado ao guardian/launcher em desenvolvimento,
com 43 testes locais aprovados. Reserva compartilhada entre projetos e filtro do
destino já têm implementação e testes locais; `client environment` consulta a reserva.
Plano, despacho e diário têm integração local; a recuperação interna cobre cargas e VM.
Faltam o egress e sua restauração global, o empacotamento e A/B/A2 nativo; YC-203 permanece aberto. O manifesto v3 aceita somente eco fictício, sem clientes autenticados.
On October 7, the maintainer approved consolidation: shared diagnostics are being
implemented, with 11 native read queries passing locally. Integrated isolation and
both authenticated clients remain pending; no execution profile was enabled.
The first correction cycle addresses the phone session's storage refusal by retaining
its stage and reason. It confirmed a temporary-file owner mismatch; the second cycle
protects only that new empty file. Remote confirmation passed and captured an
unavailable Windows credential set. The next proof requires a session with access
to that credential set; no network trial is scheduled in the failing remote session.
The maintainer then verified all 11 queries in local PowerShell, including credentials.
That local context can proceed to integration; the runtime profile remains blocked.
Candidate preflight is implemented through the same `client environment` entry:
29 local queries passed, covering process identity, policies and repeated baseline
reads. The restricted relay is connected to guardian/launcher in development,
with 43 local tests passing. Shared reservation and destination filtering now have
implementations and local tests; `client environment` reads the reservation.
Plan, dispatch and journal have local integration; internal recovery covers workloads and VM.
Egress and global restoration, packaging and native A/B/A2 remain pending; YC-203 stays open. Manifest v3 accepts only dummy echo, with no authenticated clients.
R1 já tem o diagnóstico de ambiente e sua distribuição em desenvolvimento;
consulte as [provas e pendências](relatorios/2026-10-04-isolated-executor.md).
O host já reiniciou e o login Docker foi concluído. A [prova do supervisor interno](relatorios/2026-10-04-supervisor-spike.md)
passou nos casos sintéticos de privilégios, prazo, descendentes, limites e perda do coordenador.
O [protocolo de despacho único](relatorios/2026-10-04-guardian-protocol.md) passou em seis cenários
sintéticos na microVM, com marcadores duráveis e capabilities do cliente zeradas.
O [launcher](relatorios/2026-10-04-launcher-boundary.md) passou em conclusão, prazo e perda
do transporte, incluindo queda do coordenador e do `sbx` no Windows. O [pacote v3](relatorios/2026-10-04-native-kit-build.md)
foi construído e [criou a sandbox esperada](relatorios/2026-10-04-native-package-proof.md),
com digest, recursos e proteção dos arquivos conferidos. Os três casos do launcher passaram
nessa VM; certificado e exceções foram retirados. O [reinício ativo](relatorios/2026-10-04-shutdown-reserve.md)
falhou na verificação estrita do prazo: 3,8935 ms de atraso. A candidata reserva um segundo
para encerramento e passou em nove cenários sintéticos. Um novo reinício passou com
993,6312 ms de sobra e repetição recusada. O [ensaio de rede](relatorios/2026-10-04-network-boundary.md)
encontrou uma rota MCP pelo proxy; a alternativa com saída direta restrita passou nos casos
testados para OpenAI/Anthropic, com cliente e filho. São provas de transporte, sem autenticação.
A [integração ao launcher](relatorios/2026-10-04-network-launcher.md) passou em oito cenários
nativos e nos dois ensaios de provedor. Cada fase exige recibo privado; falha na preparação
ou regras alteradas impedem o despacho. O reinício v2 falhou na medição; logs mostram
desligamento antes do prazo e novo boot na consulta. A nova prova observou a VM parada
3,756s antes do deadline e recusou repetição após boot; recibo anterior preservado.
Os [endereços observados do gateway e as sentinelas Windows](relatorios/2026-10-05-gateway-endpoints.md)
passaram nos cenários testados: 124 tentativas TCP sem conexão e zero acessos às sentinelas,
com TLS dos provedores acessível. A [investigação de DNS/proxy](relatorios/2026-10-05-proxy-resolution.md)
mediu a proteção do resolvedor, mas deixou o destino final sem comprovação e identificou
a dependência do proxy explícito para injeção de credenciais. A [prova conjunta](relatorios/2026-10-05-auth-egress-spike.md)
encerrou três ciclos; o candidato de origem fixa passou em simulação. A [prova nativa](relatorios/2026-10-05-native-proxy-compatibility.md)
confirmou substituição de credencial por domínio, mas o Docker recusou os túneis por IP
para os serviços de eco. A [prova por domínio/CIDR](relatorios/2026-10-05-hostname-cidr-proof.md)
foi executada: três HTTP 200, inclusive sob negação universal de IP, com substituição
fictícia correta. Combinação reprovada. A [instalação local exclusiva](superpowers/specs/2026-10-05-exclusive-egress-decision.md)
foi aprovada para controlar a saída após a injeção de credenciais. O
[plano aprovado](superpowers/plans/2026-10-05-exclusive-egress-proof.md) tem protótipo
e 60 testes locais passando. O [ensaio nativo](relatorios/2026-10-05-exclusive-egress-proof.md)
parou antes de tráfego por uma origem de setting modelada incorretamente. Código corrigido
e recuperação concluída, incluindo a conferência dos IDs regenerados de uma regra automática.
V2 executada: timeout antes do recibo e de efeitos no Docker; inventários conferidos,
sem recuperação pendente. Ciclo encerrado como inconclusivo e roteiro bloqueado.
Decisão de produto: [execução local por padrão e runner dedicado opcional](superpowers/specs/2026-10-05-local-and-dedicated-execution.md),
com a mesma esteira para Claude Code e Codex. YC-203 mantém as provas por perfil;
YC-208/209 já cobrem transferência e responsável único. O [desenho de setup](superpowers/specs/2026-10-05-execution-setup-design.md)
foi aprovado, incluindo Remote SSH. O [plano](superpowers/plans/2026-10-05-execution-setup.md)
divide a preparação em três PBIs: seleção privada, diagnóstico por etapa e adoção nos
dois destinos. [Setup validado nesta branch](relatorios/2026-10-05-execution-setup.md):
seleção, diagnóstico e guia instalados; oito combinações de adoção/restauração passaram.
Resultados finais: 403 testes aprovados e 11 skips de ambiente, após as correções registradas.
Entrega local, ainda sem publicação na main.
Na [continuação com observação por comando](superpowers/plans/2026-10-06-observed-egress-proof.md),
o ensaio parou antes das GETs por exigir `override` ao gravar um valor padrão. A correção
passou em 75 testes locais; a restauração foi confirmada por leitura, sem limpeza pendente.
A operação está consumida. O timeout histórico permanece sem causa comprovada; essa falha
nova foi uma comparação incorreta no roteiro. Nenhum perfil ou PBI adicional foi concluído.
A [entrada corrigida](relatorios/2026-10-06-corrected-egress-proof.md) foi executada:
A passou, B inconclusiva, A2 não executada; limpeza confirmada, sem recuperação pendente.
Os 80 testes da preparação não substituem o aceite nativo. Diagnóstico posterior:
recusa ao guard registrada no daemon; o coletor não reconheceu a evidência. O
[candidato separado](relatorios/2026-10-06-captured-egress-evidence.md) passou em onze testes
offline. Sua [integração com o controlador](relatorios/2026-10-06-integrated-egress-controller.md)
também foi validada offline, com recuperação sem repetição. A entrada está preparada;
113 testes locais passaram. A tentativa nativa foi consumida sem efeitos no Docker:
proprietário dos arquivos incompatível na sessão remota. O ajuste foi comprovado
nessa sessão. A entrada separada passou pela verificação de proprietário, mas parou
com `JSONDecodeError` no primeiro status do Docker. Sem efeitos ou limpeza pendentes;
a resposta original não foi guardada. A captura remota passou e coincide com a local;
as cinco consultas iniciais passaram daqui. A entrada separada já captura as respostas
de status antes da interpretação e passou em uma suíte de 129 testes. A execução seguinte
guardou quatro respostas válidas, mas parou na comparação literal de um identificador
recriado pela limpeza anterior (`policy_baseline_changed`). Foram 24 consultas, sem
efeitos ou limpeza pendente. A correção foi integrada à captura e ao controlador:
12 testes da sequência inicial completa e 83 do controlador/comparação/fases passaram,
com respostas externas simuladas. A entrada nativa foi executada e parou na consulta
`sbx secret ls --json` (código 1), depois de validar as políticas. Foram 25 consultas,
sem alteração ou limpeza pendente. Duas consultas locais passaram; a causa remota
continua desconhecida porque o stderr não foi retido. Próximo: obter o erro dessa
consulta no contexto remoto, somente leitura, antes de outro ensaio completo.
O [guia](USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor) marca a operação como
consumida; não repetir nem reconciliar. A/B/A2 continua pendente.
[Panorama](relatorios/2026-10-06-panorama-executor.md).
Não iniciar uma v3
automaticamente. R1 continua parcial, sem integração do relay; os dois destinos não estão certificados.
OAuth, isolamento do intermediário,
DNS/redirecionamentos reais, reconstrução do pacote e suspensão continuam pendentes.
O gateway MCP externo exige prova de
inacessibilidade pelo cliente mesmo com a rede do fornecedor liberada.
A prova real de isolamento continua obrigatória para habilitar o executor; R2/R3 não começaram.
QA da rodada: raiz temporária curta e publicação completa do PID passaram nos 17 testes
focados. A nova suíte geral executou 384 testes, sem falhas ou erros, com 11 skips.
O [relatório de QA](relatorios/2026-10-04-qa-fixtures.md)
preserva a rodada anterior com 6 falhas e 2 erros. O launcher v2 passou na suíte de
390 testes, com 11 skips e sem falhas/erros; o aceite de isolamento continua pendente.

Aceite da frente 2: `yc-iniciar`, `yc-pausar`, `yc-retomar` e `yc-transferir` instalados e
verificados nas combinações anunciadas. A etapa 2A isolada fornece o mecanismo de execução e
diagnóstico; o início autônomo de missões depende de 2B. Transferência depende de 2C.

## Frente 3: QA e integração

| ID | Feature / PBI | Depende de | Critério de aceite | Estado |
|---|---|---|---|---|
| YC-301 | Revisão técnica e QA por PBI | YC-206 | Sessões independentes do implementador examinam diff, critérios, testes/build/análise pertinentes e resultados reais; defeito conhecido é reprovado | Planejado |
| YC-302 | QA visual e operacional por Playwright | YC-301 | Testar localhost, teclado, formulários e tamanhos relevantes contra referência aprovada; registrar capturas e ações; zero processos próprios restantes. Projetos sem interface registram não aplicável | Planejado |
| YC-303 | Autocorreção com limite de três ciclos | YC-301 | Implementação inicial mais até três correções; terceira reprovação bloqueia e avisa líderes. Falha operacional tem estado próprio; pausa, transferência ou novo ID não renovam tentativas | Planejado |
| YC-304 | Integração serial e aprovações por revisão | YC-205, YC-301, YC-303 | Integrar um PBI por vez; rejeitar conflito, base alterada e aprovação antiga; vincular pareceres ao commit, árvore, critérios e evidências | Planejado |
| YC-305 | Validação conjunta e aceite da versão | YC-302, YC-304 | Uma ou várias features formam uma versão; PM, Tech Lead e QA aprovam o conjunto. Defeito integrado retorna ao item responsável sem apagar histórico | Planejado |

## Frente 4: release e operação

| ID | Feature / PBI | Depende de | Critério de aceite | Estado |
|---|---|---|---|---|
| YC-401 | PR e promoção pela proteção da main | YC-305 | Respeitar checks/revisões, conferir árvore após merge e ligar artefato à revisão final; mudança de conteúdo invalida aprovações afetadas | Planejado |
| YC-402 | Deploy manual e automático | YC-401 | Manual como padrão e espera persistida; automático explícito usa os mesmos gates. Detectar workflows que publicam ao fazer merge e impedir promessa manual incompatível | Planejado |
| YC-403 | Verificação de produção e fechamento | YC-402 | Conferir revisão, saúde e fluxos críticos numa janela finita; só então marcar missão concluída e registrar timestamp, ambiente e evidências | Planejado |
| YC-404 | Falha de deploy e recuperação autorizada | YC-402 | Consultar operação incerta antes de repetir, respeitar teto de tentativas e provar retorno configurado. Migração de dados exige procedimento próprio | Planejado |
| YC-405 | Avisos e operação por eventos | YC-206, YC-403, YC-404 | Status/terminal expõem decisões e falhas; webhook opcional só para destino autorizado, com deduplicação, limite de tentativas e sem documentos/segredos | Planejado |

## Aceite do produto completo

| ID | Entrega | Depende de | Critério de aceite | Estado |
|---|---|---|---|---|
| YC-501 | Matriz de ponta a ponta | YC-010, YC-011, YC-209, YC-305, YC-405 | Projeto novo/migrado, uma/N features, ambos os clientes, local/servidor e conexões anunciadas percorrem o rito. Login indisponível fica pendente; simulação não vale como prova nativa | Planejado |
| YC-502 | Memória verificável da entrega | YC-501 | Sessão nova encontra tema, fontes, agentes/skills/MCPs, criação/refino/dev/QA/deploy, produção atual e próxima ação. Verificar vínculos/recibos de encerramento; não certificar texto livre como verdade | Planejado |
| YC-503 | Guias, demonstração e processos completos | YC-502 | README e guia PT/EN, exemplo público e diagramas cobrem zero, migração, configuração, missão, falhas, transferência, QA, deploy e saída. Mostrar o que está disponível e seus limites | Planejado |
| YC-504 | Publicação e manutenção do repositório | YC-503 | Versão identificável, notas de release, política de compatibilidade/migração, guia de contribuição e relato privado de vulnerabilidades; licença/créditos e pacotes revisados | Planejado |

DoR comum: objetivo observável; escopo pequeno; dependências conhecidas; referências acessíveis;
critérios testáveis; comandos de validação e autorizações do percurso definidos. Itens sem esses
dados permanecem em refinamento.

DoD comum: código e documentação revisados; testes pertinentes com saídas reais; evidências ligadas
ao item; README/guia/processo coerentes; integração protegida e retomada pelo vault. Para releases,
acrescentar versão, ambiente e produção verificada. Uma prova de biblioteca ou de documentação pode
terminar sem deploy de produto, declarando o alvo que realmente publicou.

Registrar horários UTC de criação, refinamento, desenvolvimento, revisão, QA, deploy e verificação,
preservando cada ocorrência. Etapas ainda não executadas ficam sem timestamp de conclusão.
Cada atualização deste backlog acompanha o PR que mudou seu estado e a prova correspondente.
Os 25 itens obrigatórios incluem o mecanismo 2A implementado e as provas nativas ainda abertas.
A contagem descreve o escopo do backlog, sem equivalência de esforço ou percentual de conclusão.

## Extensões após o núcleo

Estes candidatos permanecem visíveis para a visão de longo prazo. Precisam de desenho e aceite
próprios; não bloqueiam a primeira esteira completa acordada.

| ID | Candidato | Como decidir |
|---|---|---|
| YC-X01 | Avaliar claude-mem como adaptador opcional | Comparar recuperação, custo, privacidade, isolamento e uso nos dois clientes contra Markdown/Graphify. Preservar caminho de volta ao vault e fallback sem dependência obrigatória |
| YC-X02 | Atualização assistida de relações e índices | Propor relações com evidência e revisão; detectar fontes alteradas e reindexar apenas seleção autorizada. Medir melhoria de recuperação e evitar duplicar a verdade do vault |
| YC-X03 | Sincronização contínua entre máquinas | Avaliar somente se a transferência explícita não atender; resolver conflitos, privacidade e responsabilidade antes de automatizar |
| YC-X04 | Revisões imutáveis para plugins de marketplace | Verificar o que cada host permite fixar e provar revogação/atualização; não prometer reprodução com números de versão que o instalador não aplica |
| YC-X05 | Aviário da squad e cockpit local | Desenhar após concluir o roadmap principal (YC-501 a YC-504). Pássaros representam agentes e suas passagens reais de demanda; cockpit lê o vault e apresenta andamento e métricas medidas |

### YC-X05: aviário da squad e cockpit local

Solicitado pelo mantenedor em 2026-10-09. Estado: registrado para desenho após a
conclusão de todo o roadmap principal, incluindo o aceite e a publicação do produto.

**Objetivo:** permitir que o usuário faça o build de um front e o abra no localhost
para acompanhar a squad como um escritório de pássaros, com uma baia para cada agente.
O cockpit deve mostrar o trabalho registrado no vault e seu histórico de entrega.

Escopo a desenhar:

- Mascotes pássaros distintos para os agentes, identificados por papel, incluindo
  PM, Tech Lead, Dev e QA. Mostrar quem trabalha em quê, quem está esperando,
  bloqueado ou concluiu sua participação.
- Comunicações e passagens automáticas de demanda entre agentes: quando um agente
  entrega trabalho a outro, seu mascote vai até a baia do destinatário e entrega a
  demanda. A animação deve corresponder ao evento real e identificar o item envolvido.
- Cockpit com leitura do backlog do vault por épico, feature e PBI, mostrando o que
  ainda não começou, o que está em andamento, bloqueado, em revisão/QA ou concluído,
  além das relações de dependência e do responsável atual.
- Métricas da squad: tempo médio medido por entrega de épico, feature e PBI,
  quantidade de entregas por período, trabalho em andamento e tempo em espera/bloqueio.
  Mostrar período, quantidade de amostras e origem dos dados; ausência de medição
  aparece como indisponível, sem estimar ou tratar como zero.
- No desenho, definir os marcos de início/fim e o tratamento de pausas e paralelismo.
  A duração de uma feature ou épico deve refletir seus próprios marcos; somar tempos
  de PBIs paralelos não equivale ao tempo decorrido da entrega.
- Build e execução locais documentados; ao reabrir o cockpit, reconstruir a visão
  do estado persistido. Eventos repetidos ou históricos não podem parecer novas
  entregas, duplicar contagens ou inventar conversas entre agentes.

Critérios para o aceite futuro: acompanhar uma entrega real entre pelo menos dois
agentes, conferir o item e seus estados no vault, reproduzir uma passagem na animação
e comparar as métricas exibidas com os timestamps e recibos dessa entrega. Reabertura,
ausência de dados e eventos repetidos precisam preservar os mesmos resultados.
Framework, biblioteca de animação, desenho visual e fórmulas finais ficam para o
desenho posterior. Este registro não antecipa implementação nem altera o roadmap principal.

English: YC-X05 is deferred until the full core roadmap is complete. A locally built
frontend will depict agents as bird mascots moving between desks to hand off real
work. A vault-backed cockpit will show epic/feature/PBI status and measured delivery
times, throughput, WIP and waiting time. Metrics must expose source, time window and
sample size; replay and reopening must not duplicate handoffs or counts. Design and
implementation remain deferred.

Histórico durável no vault permite continuar além de uma sessão. Armazenamento, retenção e contexto
dos modelos continuam finitos; as extensões devem melhorar recuperação e navegação de forma mensurável.

## English overview

The foundation and mission preparation are published. Delivery 2A implements client preflight,
bounded execution and durable receipts, with [native isolation proofs still open](relatorios/2026-10-03-mission-runtime-adapters.md).
Both native profiles stay blocked. A separate environment was selected, with the
[detailed design](superpowers/specs/2026-10-04-isolated-executor-design.md) approved and the
[implementation plan](superpowers/plans/2026-10-04-isolated-executor.md) approved; R1 is in progress. Its three
PBIs refine YC-203: environment and unpaid proof, adapter/recovery, then authenticated adoption
with both clients. None is complete. Host restart and Docker sign-in are confirmed.
The [nested supervisor probe](relatorios/2026-10-04-supervisor-spike.md#english-overview) passed synthetic
privilege, deadline, descendant, resource-limit and coordinator-loss cases. The [single-dispatch
protocol](relatorios/2026-10-04-guardian-protocol.md#english-overview) passed six synthetic microVM
scenarios with durable markers and zero client capabilities. The [launcher](relatorios/2026-10-04-launcher-boundary.md#english-overview)
passed completion, deadline and transport-loss cases, including Windows coordinator and
`sbx` loss. The [v3 package](relatorios/2026-10-04-native-kit-build.md#english-overview) was built
with native Buildx and [created the expected sandbox](relatorios/2026-10-04-native-package-proof.md#english-overview).
Digest, resources and file protections were verified; three launcher cases passed in that VM.
Certificate and exceptions were removed. The [active restart](relatorios/2026-10-04-shutdown-reserve.md#english-overview)
failed the strict deadline check by 3.8935 ms. A candidate with one second reserved for shutdown
passed nine synthetic scenarios and a new active restart, finishing 993.6312 ms early and
refusing replay. The [network probe](relatorios/2026-10-04-network-boundary.md#english-overview)
found an MCP route through Docker's proxy; restricted direct egress passed the tested
OpenAI/Anthropic cases for client and descendant. The [launcher integration](relatorios/2026-10-04-network-launcher.md#english-overview)
passed eight native cases and both provider probes. Each phase requires a private receipt;
interrupted setup or changed rules prevent dispatch. The v2 restart failed its
measurement; logs show shutdown before the deadline and another boot on inspection.
The replacement observed the VM stopped 3.756s early and refused replay after boot;
the failed receipt remains. The [observed gateway addresses and Windows sentinels](relatorios/2026-10-05-gateway-endpoints.md#english-overview)
passed the tested cases: 124 unsuccessful TCP attempts, no unexpected sentinel
connections and provider TLS reachable. The [DNS/proxy investigation](relatorios/2026-10-05-proxy-resolution.md#english-overview)
tested resolver protection, left the final destination unverified and identified the
forward-proxy dependency for credential injection. The [joint probe](relatorios/2026-10-05-auth-egress-spike.md#english-overview)
finished three cycles; the fixed-origin candidate passed in simulation. The [native probe](relatorios/2026-10-05-native-proxy-compatibility.md#english-overview)
confirmed hostname-based credential substitution, while Docker rejected IP tunnels for
the echo services. The [hostname/CIDR probe](relatorios/2026-10-05-hostname-cidr-proof.md#english-overview)
completed: three HTTP 200 responses, including under universal IP denial, with correct
dummy substitution. Candidate rejected. An [exclusive local installation](superpowers/specs/2026-10-05-exclusive-egress-decision.md#english-overview)
is approved for enforcement after credential injection. The [approved plan](superpowers/plans/2026-10-05-exclusive-egress-proof.md)
has a prototype and 60 passing local tests. The [native attempt](relatorios/2026-10-05-exclusive-egress-proof.md#english-overview)
stopped before traffic because the setting source was modeled incorrectly. Code is corrected
and recovery is complete, including verification of regenerated IDs in an automatic rule.
V2 ran and timed out before receipt creation or Docker effects; inventories were verified,
with no recovery pending. The cycle is closed as inconclusive and its entry point is blocked.
Next: decide the executor approach before another proof; do not start v3 automatically.
Subsequently, local/dedicated setup was validated. The
[observed proof proposal](superpowers/plans/2026-10-06-observed-egress-proof.md#english-overview)
preserved the closed cycle and recorded the new operation. It stopped before any GET
because the script expected an override for a default value. The correction passed
75 local tests; read-only checks confirmed restoration with no cleanup pending. This
operation is consumed; its local tests do not enable a profile.
The [corrected entry](relatorios/2026-10-06-corrected-egress-proof.md#english-overview)
ran: A passed, B was inconclusive and A2 did not run. Cleanup was verified. Its 80 local
tests do not replace native acceptance. Later analysis found guard-port refusal in the
daemon log. A separate collector passed eleven offline tests. Controller integration was
also validated offline, including recovery without replay. The native entry is prepared;
113 local tests passed. The native attempt was consumed without Docker changes due to
incompatible file ownership. The owner adjustment passed remotely; a separate entry
passed its owner check but failed parsing the first Docker status reply. No Docker
changes or cleanup occurred; the original reply was not retained. Remote capture later
passed and matched the local output; all five preflight queries also passed locally.
The captured entry passed 129 tests. Its native run retained four valid status replies
but stopped on a literal rule-ID mismatch after earlier cleanup, with 24 queries and
no side effects or pending cleanup. The correction is now integrated with capture and
the controller: 12 complete initial-sequence tests and 83 controller/comparison/phase
tests passed with simulated external replies. The corrected native entry was consumed:
`sbx secret ls --json` exited 1 after policy checks passed. All 25 commands were reads,
with no changes or pending cleanup. Two local queries passed; the remote cause remains
unknown because stderr was not retained. Next: capture only that query's error in
the remote context before another full probe. Do not replay or reconcile this attempt.
Native A/B/A2 acceptance remains pending.
R1 remains partial, without relay integration.
OAuth, relay isolation, real DNS/redirects, package rebuilding
and whole-host suspension remain pending.
The outer MCP gateway requires proof that the client cannot reach it even with provider networking enabled.
R2/R3 have not started. Next come the priority queue and isolated workspaces (2B), pause/resume/transfer
(2C), independent QA and integration (3), and protected release with verified production (4).
The short temporary root and complete PID publication passed 17 focused tests; the new full
suite ran 384 tests without failures or errors, with 11 skips. The [QA report](relatorios/2026-10-04-qa-fixtures.md#english-overview) preserves
the earlier 6 failures and 2 errors. Launcher v2 passed the 390-test suite with 11 skips
and no failures/errors. Isolation acceptance remains pending.

The 25 core backlog items include the implemented 2A mechanism, outstanding native proofs and
four final acceptance/public release items. Item counts are not effort estimates or completion percentages.
The tables above retain stable IDs, dependencies, acceptance criteria and status. Optional
claude-mem, assisted indexing, continuous synchronization and immutable marketplace pinning remain
separate candidates. Commands are documented as available only after installation and verification.
