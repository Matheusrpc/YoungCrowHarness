# YoungCrowHarness — contexto completo para continuidade na cloud

Frente: produto YoungCrowHarness, com trabalho ativo no executor isolado.

Data de corte: 7 de outubro de 2026. Este documento foi preparado para que outra sessão consiga continuar sem receber toda a conversa. Reúne decisões do mantenedor, estado do código, resultados observados, falhas, limites e próximos passos. Os caminhos de arquivos, salvo indicação contrária, são relativos à raiz do repositório.

**Estado atual de P06 (9/out):** [memória Claude verificada](relatorios/2026-10-09-p06-offline-review.md)
na sessão Haiku `164e5438`, por reavaliação offline dos eventos e arquivos originais
com o verificador corrigido e revisão semântica. O recibo original de falha permanece;
não repetir a inferência. YC-011 e o executor Docker continuam pendentes.
**YC-011:** [descoberta verificada no Codex/Linux e Claude/Windows](relatorios/2026-10-09-client-skill-discovery.md),
com zero prompts. O operador executou o [roteiro Windows](YC011-CLAUDE-DISCOVERY.md)
às 21h15 de Brasília em 9/out; o JSON enviado registra Claude 2.1.220, quatro skills,
limpeza confirmada e aplicação não verificada. Os oito hashes das skills e o hash
do probe conferem com `058be40`. O CI dessa revisão passou nos oito jobs de push/PR.
Preservar os recibos; não repetir P06 ou a descoberta. Próxima ação: retomar YC-203
quando houver evidência aplicável ao contrato local Docker. Aplicação nativa das
skills, fila e agentes continuam na sequência aprovada, sem habilitação antecipada.
O mantenedor pediu avanço após a explicação do bloqueio; iniciou-se uma
[revisão de alternativas](relatorios/2026-10-09-executor-alternatives.md). Inventário
recebido: Windows 11 Home Single Language, hipervisor detectado, módulo Hyper-V ausente
e 7,69 GiB de RAM total. A função Hyper-V não é suportada nessa edição; candidata
pausada nesse PC. Não repetir inventário, recomendar upgrade ou reprovar sbx/WHP
com esses campos. Nenhuma substituição, instalação ou novo ciclo nativo aprovado.
Falha independente: CI Windows do PR em `136469e`, teste de queda abrupta do
controlador. Mesmo diagnóstico passou no push; causa ainda sem traceback. Próxima
ação: aplicar a adição salva no rascunho de rede e obter o log completo. A leitura
é bloqueada em `productionresultssa3.blob.core.windows.net`; não ajustar prazos ou
reexecutar por suposição. Docker #690 permanece sem resposta no último checkpoint.
Os parágrafos seguintes preservam a sequência histórica e suas decisões na ocasião.

Checkpoint conferido em 9/out: `a0af931` passou nos oito jobs de push e PR, incluindo
Windows. [Publicação e CI](relatorios/2026-10-09-queue-preview.md#publicação-e-ci-conferidos).
A prévia inicial da fila está entregue; execução nativa aguarda o contrato local da
issue Docker #690. A tentativa de memória Claude reportada em 9/out falhou por OAuth
expirado; renovar login e reconciliar a tentativa antes de outra execução.
Falhas anteriores abaixo são histórico, não resultados desse checkpoint.

O mantenedor pediu aprovação por lote para as próximas provas. Usar a
[campanha controlada](TEST-RUN-2026-10-10.md): não pedir confirmação por teste dentro
de um pacote autorizado. Os dois fontes privados de P06 foram recuperados e
[auditados](relatorios/2026-10-09-p06-runner-review.md). O [runner corrigido](P06-CLAUDE.md)
admite ferramentas antes de executá-las, reutiliza o prazo/árvore do supervisor
existente e verifica os artefatos Claude. O recibo enviado pelo operador em 9/out
confirma preparo no Windows, inicialização do cliente real, zero prompts e limpeza
dos processos e da cópia temporária de autenticação. Na execução seguinte, em
9/out às 12:30 UTC, o runner registrou um prompt, saída 1 e árvore encerrada;
Claude informou OAuth expirado e tokens zerados. Preservar esse pacote e os
marcadores de 3/out. A retomada não passou; o pacote Docker permanece bloqueado.
A aprovação original previa uma sessão em 10/out às 18h30; o horário não concede
outra tentativa após essa reserva usada. Renovar login e revisar a repetição
antes de qualquer chamada adicional. Nenhum novo ciclo Docker foi iniciado.

Atualização posterior de 9/out: o operador renovou o login por assinatura.
A saída de 13 testes no PC identificou duas suposições de plataforma nos testes,
[corrigidas em duas linhas](relatorios/2026-10-09-p06-windows-tests.md).
Os 13 casos passaram no PC Windows em 9,373 s, na revisão `6481a91`.
O [pacote r2](P06-CLAUDE.md#nova-operação-preparada-em-9out) foi preparado em
13,889191 s, com zero prompts e limpeza confirmada. Operação
`323ef492-4967-4d13-bd71-8afe0bc2ed00`: pacote com modelo padrão preservado.
O mantenedor aprovou uma nova sessão/300 s/24 ferramentas, seguida de revisão
semântica, e exigiu o modelo mais barato antes de executá-la. Preparar outro pacote
com [Haiku 5.5 explícito](P06-CLAUDE.md#modelo-econômico-autorizado) e vincular
operação/hash à aprovação já dada. Não executar r2 nem pedir aprovação novamente
para aplicar essa restrição. Preservar a revisão `6481a91` e os pacotes anteriores.
O CI do PR `37984416730` passou integralmente, incluindo P06; o push `37984411482`
mantém a falha histórica de diagnóstico anterior ao P06.

Atualização posterior: a [tentativa Haiku](relatorios/2026-10-09-p06-haiku.md) foi
executada, operação `4c9999a6-8c3a-4ec7-abc8-b187360d0b35`. O preparo passou;
o run terminou em 4,102774 s por OAuth expirado sem renovação. Inicialização em
`claude-haiku-5-5`, um prompt, zero tokens reportados e limpeza confirmada. A
autorização ficou consumida. O próximo passo é conferir a origem e os metadados
do login, sem novo prompt, troca de modelo ou atualização automática do cliente.

Metadados recebidos depois: arquivo atualizado às 09h51min56s e validade encerrada
às 17h51min56s (America/Sao_Paulo). O preparo começou cerca de 20 s após o
vencimento; o run, 25 s depois. A [checagem de validade](relatorios/2026-10-09-p06-expiry-guard.md)
agora recusa `expiresAt` sem mais de 360 s antes de criar pacote/reserva e reconfere
a cópia temporária. 17 testes focados passaram; suíte completa com 648 aprovados
e 20 pulados, sem falhas. O operador confirmou os 17 testes Windows em 12,776 s na
revisão `47a8150`. Após novo login, o preparo Haiku passou em 4,968794 s com zero
prompts e limpeza confirmada. Operação `164e5438-0cac-4089-845c-f1e3cc60db04`, hash
`45ec8706433bbe3866c17d79d963df7e3617eaaf224ca15f4c27a24e87ea8ac4`.
O mantenedor aprovou essa operação: uma sessão/um prompt/300 s/24 ferramentas.
Execução realizada: um prompt, 39,351451 s, exit 0, limpeza confirmada e resposta
Haiku. O verificador recusou `missing_memory_navigation`: skills lidas por
`.claude/skills/`, `project.json` consultado por Grep segundo a resposta e JSON
final com cerca Markdown. Seis UUIDs e hashes CRLF conferem com as notas. Recolher
contexto e eventos para análise offline; não repetir run. A reserva está consumida.
Pacotes antigos preservados; renovação OAuth e aceite de memória não comprovados.
CI push `37996841986` falhou antes de P06 no teste de encerramento abrupto do guard;
PR `37996847736` terminou com os quatro jobs aprovados, incluindo P06 Windows.
Esse resultado não substitui a inferência real nem apaga a falha do run de push.

Navegação: [entregas](#4-o-que-já-foi-desenvolvido-no-produto) · [executor atual](#6-estado-atual-do-executor-componente-por-componente) · [testes](#7-o-que-os-testes-já-demonstraram) · [falhas](#8-falhas-históricas-causas-e-tratamento) · [próximos passos](#10-próximos-passos-de-implementação-em-ordem) · [backlog](#11-backlog-restante-até-o-produto-completo) · [transferência para cloud](#12-o-que-levar-para-a-cloud) · [evidências](#14-evidências-e-identidade-da-implementação).

## 1. Leia isto primeiro

O YoungCrow já tem base de instalação, personalização, documentação, memória, governança, adoção reversível e preparação de missões. **A esteira autônoma completa ainda não está entregue.** Estamos concluindo a execução isolada que permitirá habilitá-la.

O diagnóstico local do Docker passou. Guardian, launcher, relay, reserva compartilhada e filtro de saída têm implementações e provas com escopos definidos. Plano, reserva, controlador e recuperação de cargas/VM têm integração local. Egress e restauração dos settings sandbox têm integração local. Falta fechar o contrato de credenciais e o adaptador nativo, provar A/B/A2 no mesmo candidato e executar Claude Code e Codex autenticados por assinatura. Os perfis de execução continuam bloqueados.

**Para continuar esta frente, clone a branch `feat/isolated-executor`.** O checkpoint reúne código, testes e relatórios revisados que estavam somente no checkout local. A `main` permanece na base anterior. VMs, logins e estado operacional continuam fora do Git. Veja a [verificação da publicação](relatorios/2026-10-07-cloud-checkpoint.md).

```bash
git clone --branch feat/isolated-executor https://github.com/Matheusrpc/YoungCrowHarness.git
cd YoungCrowHarness
```

O próximo passo de 203.6 é comprovar identidade, versão e remoção atômica condicionada da credencial fictícia no sbx local 0.46.0. A API Cloud documenta esse contrato, mas usa recursos separados. O contrato v4 de injeção distinta do placeholder já tem prova local; faltam adaptador, pacote e aceite nativos. Não reiniciar a investigação do zero, não produzir outro roteiro experimental de PowerShell e não repetir operações históricas consumidas.

A [revisão de simplificação em 8/out](relatorios/2026-10-08-executor-lifecycle-review.md)
avaliou manter o proxy configurado entre missões. Isso pode retirar escritas de settings
das missões, mas não resolve sozinho propriedade do endpoint e recuperação de credenciais.
A instalação exclusiva já estava aprovada. Não reimplementar esse fluxo antes de fechar
essas condições; a alternativa não está implementada nem aprovada como substituta.
O contrato e os bloqueios atuais permanecem.

**Consulta publicada em 9/out:** [Docker #690](https://github.com/docker/sbx-releases/issues/690).
O mantenedor publicou o texto revisado pela própria conta. A API confirmou autor,
título, corpo e estado aberto; a issue não tinha comentários na verificação.
O acesso a `api.github.com` passou após aplicar a configuração do ambiente, revisão 5.
A integração ainda recusou criar a issue, por `Resource not accessible by integration`;
a publicação manual resolveu essa etapa. Não criar duplicata nem solicitar novamente
a liberação de rede. Próxima ação: acompanhar a resposta e conferir sua aplicabilidade
ao sbx local antes de alterar o adaptador. Novo ciclo nativo não faz parte desta etapa.

A entrega independente corrigiu `yc-status`, usando recibos e projeções existentes
para indicar o impedimento real e a próxima ação. A fila 2B permanece indisponível.

Em 9/out, a preparação ganhou `scripts/missions.py --json list` para descobrir
missões salvas sem conhecer seu código. A consulta lê resumos do banco; depois,
`status CODIGO` confere fontes, projeções e recibos atuais. A listagem não repara
notas nem habilita execução. [Entrega e verificação](relatorios/2026-10-09-mission-discovery.md).

A preparação independente inclui a [matriz de elegibilidade de YC-204](superpowers/specs/2026-10-09-queue-eligibility-refinement.md).
Ela explicita espera, capacidade de PBIs/execuções e recuperação ainda a detalhar.
O mantenedor aprovou em 2026-10-09 a preferência por etapas elegíveis do trabalho iniciado,
ordenadas pela sequência em que ficaram prontas, antes de admitir novos PBIs.
Essa escolha está encerrada; o desenho operacional permanece em refinamento.
O mantenedor autorizou antecipar o que não depende do executor: `status` agora expõe
`queue_preview`, somente para a entrada inicial do backlog. Não usa eventos de
importação como sequência de prontidão, não reserva vagas e não inicia agentes.
Coordenação e despacho continuam dependentes do aceite de YC-203.
A prova de retomada no Claude está verificada no piloto por reavaliação offline
e revisão semântica; não substitui o aceite isolado de YC-203.

Visão posterior registrada: [YC-X05, aviário e cockpit local](BACKLOG.md#yc-x05-aviário-da-squad-e-cockpit-local).
Desenhar somente depois de concluir todo o roadmap principal: mascotes pássaros por
agente, passagens de demanda entre baias e métricas reais de épicos, features e PBIs
a partir do vault. O pedido atual é de backlog; não iniciar esse front agora.

### Recuperação dos fontes de B em 8/out

Os quatro fontes/testes de captura e integração e os dois recibos B chegaram por
transferência privada. Os seis hashes coincidem com os registros históricos; os
originais estão preservados fora do Git. O ZIP recebido depois trouxe as 13 dependências
diretas e as transitivas necessárias à suíte. Os 26 testes passaram em cópia privada
na cloud Linux, com 17 hashes fixados conferidos e os 635 arquivos preservados.
[Inventário e reprodução](relatorios/2026-10-08-b-source-recovery.md).
Esta atualização supera as referências anteriores à ausência dos fontes e dependências.
Transporte, guard e efeitos nativos usam os mocks originais; nenhum evento de processo
ou rede ocorreu. A execução usa cinco auxiliares públicos do commit `9b27c8a`, com
hashes na medição; não reproduz o ambiente Windows inteiro. A integração da atribuição
ao contrato atual continua pendente, assim como o contrato nativo externo.
Permanecem 2/3 ciclos consumidos, `proof_accepted=false` e perfis nativos bloqueados.

### Continuidade na cloud em 7/out

**Checkpoint anterior publicado:** os incrementos de admissão, controlador e auditoria chegaram ao PR #24 no commit
`a06986f58aaab503438685b1e0c5e3f2d79bd886`. A branch e a ref do PR foram conferidas
no remoto; a `main` permanece em `932b775`. O pacote público exato passou em 516
testes, com 20 pulados. O CI continua sem consulta por `Forbidden` da API.
Veja o [registro desse checkpoint de publicação](relatorios/2026-10-07-cloud-publication.md).
Os relatórios anteriores conservam o estado local observado na data de cada medição.

O checkout recebeu originalmente o PR #24 em `b801bec`. O incremento acrescenta a admissão sintética
bloqueada em `client check` e corrige a criação privada do lock POSIX. Veja o
[relatório e a medição](relatorios/2026-10-07-synthetic-admission.md).

O §10.2 continua parcial: a entrada pública permanece bloqueada. A integração interna
de plano A/B/A2, baseline, missão e reserva global está implementada no incremento abaixo.
Nenhuma nova tentativa Docker ou chamada de modelo ocorreu. O contador histórico
permanece em dois ciclos usados de três. Os hashes da seção 14 identificam o
checkpoint anterior; a medição do incremento registra as fontes alteradas.

### Controlador, fixture e correções anteriores

O controlador interno (`mission_controller.py`) e a fixture fixa (`runtime/sbx/fixture.py`)
estão implementados. Os testes exercitam canal aberto, gates, contenção de processos,
replay após falha de gravação e fixture com relay real local. O setup distribui o
controlador; o contexto de build inclui a fixture. Nenhuma imagem foi reconstruída
nem perfil liberado. Veja [escopo e provas](relatorios/2026-10-07-controller-channel.md).

As correções seguintes trataram AUD-01 (projeção interrompida seguida de revisão),
AUD-02 (catálogo malformado) e PR24-F2 (falha Git na primeira leitura do ambiente).
Passaram nas regressões locais e na revisão independente; nenhuma migração de banco
foi necessária. PR24-F1 já estava corrigido. Use o [relatório das correções](relatorios/2026-10-07-audit-fixes.md)
como estado mais recente desses achados; os relatórios anteriores preservam o histórico.
A recuperação histórica adicionada cobre missão/backlog; não generalizá-la a
`project_run`, cujos eventos guardam deltas e não os retratos completos anteriores.

### Incremento anterior: reserva e recuperação

Publicado no PR #24 em `ea2ff60`; branch e ref do PR conferidas no GitHub.
Suíte: 547 aprovados e 20 pulados; 23 transacionais passaram novamente após ajuste
de fixture. CI continua não verificado; main preservada.

`mission_transaction.py` grava o plano imutável v2, valores/hashes de baseline, digests,
três UUIDs/nonces, revisão/autorização e vínculo bilateral com a missão. O diário é
persistido antes de cada efeito; as três fases compartilham até 120 segundos dentro
do orçamento admitido. Testes locais executam A/B/A2 sob o supervisor existente.

A recuperação interna observa e para somente cargas identificadas, confere a VM e
as configurações e projeta o encerramento na missão sem devolver limites. Tem prazo
próprio de até 60 segundos. Recusa troca de CID, deriva e identidade do daemon instável
durante a tentativa. Resposta perdida exige observação, não repetição da mutação.
VM parada sem recibo terminal da carga mantém a reserva.

**203.4 implementada internamente; 203.5 parcial.** O incremento seguinte integra settings sandbox, helpers e portas localmente; o aceite nativo permanece pendente. Nenhum perfil nativo foi liberado; B continua
sem atribuição nativa. [Relatório e medição desse incremento](relatorios/2026-10-07-reservation-recovery.md).
Os dois revisores confirmaram as correções de CID, histórico, daemon e prazo com regressões.
Nenhum Docker ou modelo foi executado; o contador permanece em **2/3** ciclos nativos.

### Incremento anterior: integração de rede

Publicado no PR #24 em `7d1031c`; branch e ref do PR conferidas.

Plano/registro v3 adiciona guard, hashes de código/Python, resolvedor do sistema e IPs
proibidos. DNS e helper herdam a contenção existente. PID precede configuração; destino
precede bytes por confirmação durável. Um escritor serializa os recibos do pipe e da fase.
A/A2 usam a mesma porta; B exige ausência. Recuperação restaura somente settings sandbox
que continuam iguais aos valores da operação, depois de cargas/VM paradas e proprietário
/porta ausentes. Intenções consumidas nunca são repetidas. V1/v2 permanecem legíveis.

**203.5 e 203.6 seguem parciais.** Políticas e credenciais são imutáveis.
Naquele incremento, a documentação CLI consultada não fechava a identidade/remoção
da credencial. A pesquisa da API e a correção do eco constam no incremento abaixo.
O adaptador nativo recusa set/restart. Não promover testes locais a prova Docker
TLS, MCP, bypass do host, assinatura ou atribuição de B. Contador nativo **2/3**.
Suíte pública: 574 aprovados e 20 pulados, zero falhas/erros.
[Relatório e medição desse incremento](relatorios/2026-10-07-network-integration.md).

### Incremento anterior: prova interna de injeção

Publicado no PR #24 em `61bdc7b`; branch e ref do PR conferidas.

Plano/registro e manifestos v4 fixam `relay.injection_sha256`. A resposta precisa
conter um único valor diferente do placeholder e com esse hash. Resultado schema 2
contém somente metadados; o eco schema 1 não satisfaz v4. A/B/A2 compartilham
placeholder, hash esperado, proxy e CA. Guardian confere argv completos; launcher
revalida o contrato antes de consultar Docker. V2/v3 continuam legíveis para recuperação.

O teste percorre fixture, relay e guard reais com processos e sockets locais, observa
A/A2 e B sem saída e recupera o registro. Sem substituição, A falha e B não é despachado.
Docker, TLS e injeção no upstream são fronteiras simuladas. Não houve Docker, login,
modelo ou novo ciclo nativo; permanecem **2/3**, perfis vazios e `proof_accepted=false`.
Suíte pública: 607 testes, 587 aprovados e 20 pulados, zero falhas/erros em 250.427 s.
[Relatório, fontes e medição desse incremento](relatorios/2026-10-07-injection-proof.md).

Pesquisa oficial: a API Cloud define `uid`/nome imutáveis, `etag` forte e DELETE com
`If-Match`, recusando versão obsoleta. A documentação separa os recursos local/cloud;
a referência genérica a Unix socket não comprova endpoint nem armazenamento do daemon
local 0.46.0. A proveniência aponta código proprietário sem fonte pública acessível.
Comparar e depois chamar `secret rm` permite uma alteração externa entre as etapas.
Próxima evidência: contrato compatível com o armazenamento local e remoção condicionada
atômica, incluindo rotação e recusa de versão antiga. Não implementar esse adaptador
com base somente no schema Cloud nem repetir consultas já sem resposta.

### Incremento anterior: settings condicionais

Publicado no PR #24 em `2f4e47a`; branch e ref do PR conferidas.

A revisão reproduziu perda de uma alteração externa entre a consulta e a escrita,
na ativação e na recuperação. `backend.setting(key, target, *, expected)` agora
recebe o estado completo esperado e exige comparação/escrita indivisíveis. A fixture
modela essa operação; mudança após persistir intenção é preservada, impede reinício
e mantém a reserva na recuperação. Não há fallback para escrita incondicional.
Intenções consumidas e respostas perdidas continuam sem replay; schema v3/v4 preservado.
Suíte pública: 612 testes, 592 aprovados e 20 pulados, sem falhas/erros em 251.364 s.
[Relatório e medição atuais](relatorios/2026-10-07-conditional-settings.md).

A pesquisa adicional no guia API, conceitos de endpoint, comandos de daemon e release
0.46.0 não demonstrou o contrato do armazenamento local. A nota do release distingue
exclusão do store de revogação em sandboxes ativos; excluir não certifica revogação.
**A implementação nativa está bloqueada por contrato externo**, tanto para identidade/
remoção da credencial quanto para escrita condicional dos settings. Obter uma
referência aplicável do fornecedor antes do adaptador. Não repetir as mesmas buscas,
baixar/executar binário como tentativa de desbloqueio ou consumir novo ciclo sem a
prova exigida. Docker/modelos continuam sem execução nesta cloud; contador **2/3**.

### Incremento atual: leituras de missão e observação de egress

O CI completo de `c8e7f0b` passou nos oito jobs de push/PR. Os percursos Windows
v3/v4 da suíte ficaram entre 9,734 e 13,078 segundos; as falhas históricas continuam
intermitentes. No incremento atual, `mission_status` agrupa consultas SQL adjacentes:
15 processos Git por chamada passam a nove, com reabertura após inputs e leitura
final independente. Os testes preservam recusa de regras privadas alteradas,
detecção de revisões concorrentes e remoção/substituição do banco.

A fixture egress mede bytes no controlador, fora do helper encerrado. O negativo
oferece 13 bytes antes da resposta SOCKS e exige zero bytes até EOF; o positivo
comprova a contagem de 13 bytes. A observadora conclui depois de `guard.close` e
é coletada antes de consumir o recibo. Não atribuir esse mecanismo à falha histórica
Windows sem o traceback original. Os prazos do produto continuam iguais.

[Relatório e validação desta revisão](relatorios/2026-10-08-mission-read-stability.md).
Suíte local: 616 aprovados e 20 pulados; 12 focais e 11 testes de catálogo passaram.
Adoção com diagnóstico passou em consumidor novo e existente, perfis Claude/Codex,
com fixtures e zero chamadas de modelo. Apenas hashes de conteúdo do catálogo foram atualizados.
CI de `b106bc5`: sete dos oito jobs passaram. O Windows do PR passou integralmente;
o do push falhou em `test_failed_destination_receipt_forwards_zero_upstream_bytes`
com exit 1, stdout vazio e 445 bytes de stderr. O HTML público não expôs a exceção.
O diagnóstico de `f3e091d` confirmou reset antes de EOF nos dois Windows: oito
observações incompletas continuaram reprovadas. `Channel.close` agora permite até
100 ms para EOF cooperativo, dentro do estágio existente de 200 ms e do Deadline.
Persistência recusada continua sem ACK; terminate/kill e contenção permanecem.
Em `9cb3729`, os testes de EOF e as oito recusas passaram nos dois Windows; o PR
passou integralmente, incluindo os 14 focais, a suíte de missões e a adoção final.
Resultado: sete dos oito jobs aprovados. O push falhou por timeout v4,
com 7.098 ms entre autorização e primeiro pedido SOCKS registrado, antes do close.
Naquela revisão, a próxima investigação era comparar `guard_request.payload.at_ms`
com a hora do registro para localizar essa pausa. Não atribuir causa nem ampliar
prazos sem evidência. [Relatório](relatorios/2026-10-08-guard-cooperative-close.md).
Contratos sbx, fontes nativas de B, perfis bloqueados e contador 2/3 preservados.

### Incremento anterior: concorrência da seleção

A seleção local/dedicada agora adquire o lock existente sem criar ou escrever bytes,
antes de inspecionar o armazenamento. A primeira configuração mantém os gates antes
da criação e revalida sob o lock. Leitura e escrita usam uma leitura interna comum;
a consulta não adquire o lock recursivamente. Se o lock surgir durante o preflight,
a operação refaz a validação uma vez sob proteção. Nenhum temporário é ignorado.

As seis regressões de concorrência falham no baseline e passam na correção. A bateria
local da seleção tem 18 aprovados e uma junction Windows pulada; os sete focais locais
passaram. Suíte completa: 610 aprovados e 20 pulados em 249,942 s. O CI passa a testar cedo lock vazio/somente leitura
e leitor durante gravação, mantendo a suíte integral. [Relatório](relatorios/2026-10-08-selection-concurrency.md).

Próximo passo: consultar o CI desta revisão no PR #24, começando pelos sete focais
e depois pela suíte Windows completa. O CI completo de `25ee51d` já passou no push
e no PR; os oito percursos positivos medidos ficaram entre 8,625 e 10,656 s. O código coordena seleção;
recibos de `Sbx.persist` não participam desse lock. Contratos sbx e fontes originais de B
continuam bloqueados, perfis sem aceite nativo e contador 2/3 preservado.

### Histórico: custo do preflight Git

O CI de `63bb229` confirmou timeout no fim de A2, após A/B completos; casos irmãos
terminaram em 14,781 s e 14,891 s. A mudança publicada em `25ee51d` agrupa os três `check-ignore` de
`verify_private_storage`, exigindo todos os probes na saída. Mantém verificações
de caminhos, rastreamento, regras atuais e todos os prazos. Medição real Linux:
cinco processos Git por consulta passaram a três. Testes de armazenamento e os
cinco focais passaram; suíte geral confirmada com 602 aprovados e 20 pulados
em 240,982 s. Naquele checkpoint, Windows ainda estava pendente; depois os dois jobs
completos de `25ee51d` passaram. A falha de seleção concorrente identificada nessa
bateria é tratada pelo incremento atual.
[Relatório atual](relatorios/2026-10-08-git-preflight-cost.md).
Os cinco focais Windows passaram no push `37724707270` e no PR `37724712042`,
42 s por etapa. Às 00:57 de 8/out (America/Sao_Paulo), seis jobs Linux aprovados e
dois Windows ainda em armazenamento/recuperação. Essa consulta foi sucedida pela
confirmação dos dois jobs completos. O incremento atual de concorrência está descrito acima. Dependências nativas e contador 2/3 preservados.

### Histórico: diagnóstico do CI Windows

Checkpoint atualizado em 8/out: código publicado `e674a83`, branch/ref do PR
conferidas. Suíte pública local: 618 testes, 598 aprovados e 20 pulados em 255,268 s.
Os cinco focais passaram nos runs `37722035973` (push) e `37722040460` (PR);
a suíte Windows completa ainda estava em andamento na última consulta.
Esse checkpoint foi sucedido por `63bb229` e pelo incremento de custo descrito acima.
Naquele incremento, as fontes de produto não mudaram.
O MCP GitHub não está exposto nesta sessão; Git HTTPS permitiu publicar. Uma falha
401 transitória foi seguida por push e leitura de refs bem-sucedidos, sem alteração
de autenticação/configuração.

A consulta às páginas públicas do GitHub confirmou que `da28f00` falhou em
`adoption-windows` nos runs de push `37702748727` e PR `37702753288`. Os jobs
`public-pilot`, `installer` e `graphify-smoke` passaram em ambos. A etapa falha é
`Verify mission diagnostics and process recovery`, saída 1. Logs detalhados exigem
login nessa consulta; a página não identifica o teste responsável.

`tests/ci_unittest.py` mantém a execução/saída do unittest e acrescenta anotações com
IDs de falhas, erros e sucessos inesperados, sem traceback nem parâmetros de subteste.
O workflow usa essa entrada dentro do wrapper de ACL já existente. Timeout, cancelamento
ou falha anterior ao unittest podem impedir as anotações. No CI de `a9d05ea`, falharam os dois percursos positivos de `NetworkBindingTests`;
a execução do PR também falhou em
`test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`. Uma etapa focal
executa esses casos primeiro e acrescenta estados/códigos permitidos, duração e
contagens às anotações. Em `919b0a4`, os dois runs confirmaram `TimeoutError` na
sonda B v3 antes dos eventos finais. A fixture agora usa o prazo restante da fase
em lugar do corte fixo de um segundo. Exige `ConnectionRefusedError`; timeout
continua falhando. Supervisor 15 s e plano 30 s permanecem inalterados.
[Relatório e medição](relatorios/2026-10-07-windows-ci-diagnostics.md).

Em `32960b8`, o focal passou no push `37721430256`; o PR `37721434176` falhou
com timeout externo de 15 s em v3 e v4, ambos sem stdout e com árvore recolhida.
O diagnóstico agora lê o ledger mesmo sem envelope e publica tempos relativos.
O passo seguinte era localizar o atraso pelo ledger e acompanhar a suíte
Windows completa; a localização em A2 consta no incremento de 8/out. V4 e encerramento abrupto passaram nas rodadas focais anteriores,
mas isso não explica suas falhas na execução longa de `a9d05ea`. A transferência de B
e a reprodução de seus 26 testes offline foram concluídas em 8/out. A integração
ao contrato atual continua pendente. Não substituir a prova nativa por essa suíte
nem repetir operações consumidas.
O contador nativo permanece **2/3**, sem Docker/sbx ou modelos executados nesta cloud.

Para continuar, seguir esta ordem sem reabrir decisões anteriores:

| Etapa | Próxima entrega verificável |
|---|---|
| CI Windows | Concluído para `a0af931`: push e PR passaram integralmente. Timeout anterior preservado como histórico, sem causa final comprovada; nova investigação exige falha reproduzida |
| Executor: 203.6 | Bloqueio externo: comprovar identidade/versão/remoção atômica da credencial e escrita condicional dos settings locais 0.46.0; depois adaptador e aceite v4 |
| Executor: restante de 203.5 | Comprovar recuperação nativa de settings/serviço/credencial e demais políticas necessárias, preservando alterações externas |
| Executor: aceite | Reconstruir candidato exato; provar A/B/A2 com B atribuível; Claude e Codex por assinatura; adoção |
| Fila e agentes | Retomar os itens da frente 2 dependentes do aceite YC-203 |
| QA e publicação | Frentes 3 e 4, depois da execução e continuidade comprovadas |

A reserva v1 consumida não pode ser reaberta ou ter arquivos soltos acrescentados.
O plano v2 conserva valores de baseline para recuperação sem depender do checkout,
além dos hashes; a identidade histórica permanece separada da comparação de
configuração após reinício legítimo. Não encadear outro `supervise`
dentro do controlador: os filhos devem herdar o mesmo grupo/job. O resolvedor de egress usa filho direto, herdando a contenção do controlador.

### Estado Git antes do checkpoint de publicação

| Campo | Valor |
|---|---|
| Repositório | `https://github.com/Matheusrpc/YoungCrowHarness` |
| Checkout de trabalho no Windows | `C:/Users/rmfon/YoungCrowHarness-review-20261001` |
| Branch | `feat/isolated-executor` |
| HEAD | `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95` |
| Último commit local | `docs: define isolated executor for Claude and Codex (#23)` |
| Referência local `origin/main` | Mesmo SHA do HEAD; não houve `fetch` nesta exportação |
| Diferença entre commits locais HEAD e origin/main | 0/0 |
| Estado do checkout antes de criar este documento | 27 arquivos rastreados alterados e 225 arquivos não rastreados |
| Publicação antes deste checkpoint | Os incrementos estavam sem commit/push; foram reunidos na branch `feat/isolated-executor`, sem promover a implementação à main |

Essas contagens não incluem arquivos ignorados e não significam que os 225 arquivos devam ser publicados. Há relatórios, fontes, fixtures e resíduos a revisar. O marcador histórico `ATRASO: main 1` indicava esta frente ainda não publicada; não era uma medição de “um commit atrás”. O estado remoto atual não foi consultado nesta exportação.

## 2. Visão de produto acordada

O objetivo é transformar o YoungCrow em um repositório público reutilizável para desenvolvimento assistido por IA. O público inicial são desenvolvedores individuais e pequenos times com Claude Code e Codex.

O harness deve servir tanto para começar do zero quanto para incorporar um projeto existente, auditando código, documentação e instruções antes de personalizar o processo. Deve preservar o trabalho do adotante e permitir experimentar e voltar ao estado anterior ao início do YoungCrow, dentro do escopo coberto pelo mecanismo de retorno.

### Decisões que não precisam ser perguntadas novamente

| Tema | Decisão do mantenedor |
|---|---|
| Clientes | Claude Code e Codex; assinatura autenticada como padrão, API apenas por escolha explícita |
| Papéis da squad | PM, Tech Lead, desenvolvimento, QA e especialista em integração são agentes de IA |
| Personalizer | Entrevista profunda, inspirada no Grill Me, reaproveitando respostas e contexto anteriores |
| Configuração de agentes | Configurar uma vez por projeto; permitir substituições explícitas por missão |
| Provedor/modelo/effort | Escolha do desenvolvedor, conforme disponibilidade real; tradução determinística para cada cliente |
| JEV/roteador por modelo | Descartado para evitar custo adicional |
| Modelos recentes | Descobrir catálogo atual; não fixar uma lista antiga nem prometer execução segura de qualquer versão futura |
| Comandos | Entradas separadas, com sintaxe nativa documentada para cada cliente |
| Missão | Início, limites e fim definidos; de uma a N features; uma missão ativa por repositório |
| PM | Épicos, features, prioridade, DoR e DoD |
| Tech Lead | PBIs, dependências, contratos técnicos e revisão |
| Priorização | PM pode repriorizar itens ainda não iniciados dentro do escopo aprovado |
| Paralelismo inicial | Três PBIs ativos e três execuções simultâneas; são limites separados e configuráveis |
| Branches | Um escritor por checkout; isolamento por branch/worktree de PBI; integração serial |
| QA | Por PBI, revisão técnica independente e validação integrada |
| Frontend | Playwright em localhost para validação operacional/visual quando houver interface |
| Correções | Até três ciclos de correção por PBI; histórico e contadores persistem |
| Release | Uma versão conjunta ao fim da missão |
| Deploy | Manual por padrão; automático quando configurado explicitamente |
| Done final | Somente após produção verificada |
| Timestamps | Criação, refinamento, desenvolvimento, revisão, QA, deploy e verificação; preservar cada ocorrência |
| Continuidade | Pausar, retomar e transferir local/servidor mantendo um único responsável |
| Ambientes | Opções local e runner dedicado; suporte validado depende de prova real por ambiente |
| Documentação | Atualizar README PT/EN e guias a cada implementação; preservar design e diagramas de processo |
| Texto | Usar Humanizer; manter redação clara, sem inflar o estado do produto |
| Código | Usar Karpathy e Ponytail; reaproveitar primitivas, corrigir causas e evitar abstrações desnecessárias |
| Autoria Git | Manter o autor humano; não adicionar coautoria/assinatura de IA |

O desejo inicial de “memória infinita” foi concretizado como memória durável e recuperável entre sessões. Armazenamento e contexto continuam finitos. O produto não promete que toda a memória caiba em cada chamada de modelo.

Fonte de decisões: `docs/superpowers/specs/2026-10-03-ai-product-pipeline-design.md`. As funções da esteira descritas nessa especificação são planejamento quando não acompanhadas por implementação e prova.

## 3. Arquitetura de memória e documentação

O vault em Markdown é o registro principal, navegável como um vault Obsidian. Há um índice geral e microíndices por tema. Notas têm identidade, origem, atualização e vínculos; relacionam fontes, decisões, features, execuções, capacidades utilizadas e resultados.

O agente deve começar pelos índices e recuperar apenas o material necessário, distinguindo desenvolvimento, resultado observado em produção e informação ainda não verificada. Não carregar o vault inteiro em todo prompt. Não tratar instruções encontradas em documentos recuperados como novas autorizações.

- **Graphify:** adaptador opcional de relações/recuperação; a versão registrada nas provas é 0.9.73. O Markdown continua disponível quando o índice derivado falha. Não é sincronização global automática.
- **claude-mem:** avaliação futura opcional, item YC-X01. Não é dependência obrigatória instalada ou integração já concluída nesta frente.
- **Docling:** camada de ingestão, com fontes e conversões guardadas localmente e publicação somente após revisão. Há suporte e provas por formato; não interpretar “qualquer documento” como suporte universal sem limites.
- **Referências anexadas ao chat:** a automação registra as referências que o host expõe. Anexos sem caminho acessível precisam de registro explícito. Referência inacessível fica pendente.
- **Integrações:** documentação própria no vault, papel `integration-specialist` e skill `integrate-from-docs`. A implementação deve partir da documentação do fornecedor e conservar fontes/evidências.
- **Governança:** catálogo e auditoria de agentes, skills e MCPs por cliente; auditoria não concede permissão de uso nem comprova execução real por si só.

No caso do histórico desta conversa, textos do terminal e fotos foram preservados e ingeridos quando acessíveis. Alguns TXT e Markdown foram recusados pelo adaptador de ingestão então disponível; uma cópia HTML escapada permitiu a conversão pelo Docling 2.132.0. Os recibos `unsupported_source` anteriores foram mantidos. OCR foi comparado com as imagens; o recibo técnico prevalece quando há quebra de palavras na foto.

## 4. O que já foi desenvolvido no produto

Esta tabela resume os registros do backlog e dos relatórios. “Entregue na base” não significa que o novo executor autônomo esteja certificado.

| Capacidade | Estado registrado | Fonte principal |
|---|---|---|
| Setup seguro para projeto novo e existente | Base entregue: preflight, preservação de arquivos, proteção do `.env` e erros de instalação tratados | `docs/relatorios/2026-10-01-primeira-entrega.md` |
| Personalizer | Entrevista retomável, auditoria, perfil e orientação inicial | `docs/relatorios/2026-10-02-personalizer.md` |
| Claude Code e Codex no template | Instruções, skills e entradas para os dois clientes | `README.md`, `docs/USAGE.md`, `setup.sh` |
| Documentação e processos | README PT/EN, guias de zero/migração/operação e SVGs inspirados em BPMN | `docs/PROCESS.md`, `assets/process-*.svg` |
| Vault e integrações | Índices, vínculos, especialista e verificador de notas | `docs/relatorios/2026-10-01-integration-vault.md`, `docs/relatorios/2026-10-02-vault-check.md` |
| Docling | Ingestão local, origem/revisão, pendências, revisão e publicação controlada | `docs/relatorios/2026-10-02-docling-ingestion.md`, `docs/relatorios/2026-10-03-claude-docling.md` |
| Memória consultável | Markdown e Graphify opcional; provas de retomada e isolamento de temas/projetos | `docs/relatorios/2026-10-02-memory-project-isolation.md` |
| Capacidades | Catálogo, auditoria e provas delimitadas de skills, agentes e MCPs | `docs/relatorios/2026-10-02-capability-governance.md` |
| Adoção reversível | Baseline anterior ao setup, trial e retorno preservando o trabalho realizado durante a experiência | `docs/relatorios/2026-10-02-reversible-adoption.md` |
| Piloto público | Quadro publicado/verificado no checkpoint; retomada Codex e Claude verificadas, esta por reavaliação offline | `docs/relatorios/2026-10-09-p06-offline-review.md` |
| Preparação de missões | Configuração, backlog, DoR/DoD, histórico e quatro skills; registrada como publicada pelo PR #18 | `docs/relatorios/2026-10-03-mission-foundation.md` |
| Adaptadores e execução limitada | Mecanismo e simuladores implementados; perfis nativos sem aceite | `docs/relatorios/2026-10-03-mission-runtime-adapters.md` |
| Seleção local/dedicado | Implementada e testada localmente em oito adoções; conexão e execução reais em runner ainda não certificadas | `docs/relatorios/2026-10-05-execution-setup.md` |
| Executor isolado | Implementação local parcial descrita nas seções seguintes | `docs/relatorios/2026-10-07-executor-consolidation.md` |

O rollback de adoção cobre os arquivos/estado previstos no seu contrato. Não desfaz deploys, alterações em serviços externos ou migrações de dados automaticamente. O baseline deve existir antes da primeira escrita; não se cria uma cópia retroativa e a chama de estado anterior.

### Limites das provas já realizadas na base

- O Personalizer cria e conserva os registros da entrevista/auditoria conduzida pelo agente; não é, sozinho, o coordenador autônomo da esteira.
- A integração de exemplo foi validada com fornecedor fictício e mocks. O export fica `pending`; não comprova envio automático para um serviço de memória.
- O validador do vault confere estrutura, identidades e vínculos. Não verifica a verdade do conteúdo, a existência de segredos ou o estado atual das URLs e da produção.
- Houve provas reais de Docling com PDF, DOCX, HTML, imagem de página, PDF por URL, WAV e MP4. Vídeo sem áudio e conversões interrompidas têm resultado parcial explícito; transcrição/OCR não garantem fidelidade absoluta.
- Houve sessões reais de Claude e Codex recuperando memória. No corpus fixo registrado, Markdown acertou 4/4 consultas e Graphify 3/4. Isso não demonstra vantagem geral de Graphify; preservar o fallback e o escopo das consultas.
- Separação de projetos por UUID/revisão e distinção DEV/produção foram demonstradas na recuperação. Isso não comprova isolamento de filesystem entre projetos.
- A governança de MCP foi exercitada com servidor sintético: leitura permitida, escrita recusada, revogação e restauração. Não certifica qualquer MCP de fornecedor nem substitui isolamento de sistema operacional.
- O piloto `examples/delivery-board` teve publicação e seis hashes públicos conferidos em 3/out. A retomada posterior pelo Claude foi verificada na sessão Haiku de 9/out, por reavaliação offline com correção do verificador e revisão semântica. O recibo original de falha foi preservado.

Os diagramas de processo são Mermaid/SVG inspirados em BPMN, não um motor executável BPMN 2.0. As provas reais dos clientes nas frentes anteriores continuam válidas no seu escopo; o que falta é o aceite autenticado dentro do novo executor isolado.

### Entradas disponíveis e planejadas

As quatro skills da preparação são `yc-personalizer`, `yc-config`, `yc-missao` e `yc-status`. Sua prova de descoberta/aplicação nos clientes nativos atuais ainda aparece no backlog como YC-011.

`yc-iniciar`, `yc-pausar`, `yc-retomar`, `yc-transferir` e `yc-deploy` fazem parte do desenho da esteira. Não anunciá-las como execução autônoma já entregue. O usuário pediu comandos separados; não substituir tudo por uma única entrada genérica.

Na operação técnica já existem `scripts/missions.py client environment`, `client inspect`, `client check`, `client runs` e `client reconcile`. `check` não está liberado para inferência nativa. O `reconcile` atual não comprova, sozinho, a restauração completa do Docker isolado.

## 5. Por que passamos a trabalhar em isolamento

O diagnóstico inicial de 1º de outubro encontrou um template com regras úteis, mas controles ainda declarativos. Foram reproduzidas falhas de instalação: `.env` sem exclusão efetiva, erros não propagados, checkout de skill incompleto e alteração de guias que deveriam ser preservados. A base foi sendo corrigida e testada.

Na frente de execução dos clientes, testes locais mostraram que flags e diretório de trabalho não bastavam para cumprir o contrato mais restritivo do YoungCrow:

| Descoberta | Resultado e decisão |
|---|---|
| Claude instalado com hard links | A inspeção herdava uma regra dos backups e recusava o executável. O leitor foi corrigido para aceitar a instalação oficial, verificando identidade/conteúdo sem relaxar backups |
| Codex 0.146.0 e 0.160.0, `tools.view_image=false` | Um fornecedor simulado recebeu a imagem fictícia situada fora da pasta de trabalho. O perfil falhou no requisito do harness |
| Codex com perfil mais restrito | Também falhou no caso permitido por problema de preparação do sandbox Windows; recusa no caso proibido não comprovou isolamento funcional |
| Saída zero com conteúdo inválido | Um caso de modelo/Code Mode retornou zero e trouxe erro; o decoder recusou. Código de saída não é aceite suficiente |
| Claude safe mode | Mantém políticas administrativas. Catálogo vazio de ferramentas não prova ausência de efeitos dessas políticas |
| Claude `--bare` na versão observada | Exigia API; não atendia à exigência de assinatura |
| Estado interno das CLIs | Ambas gravam arquivos em seus diretórios próprios; flags de sessão não isolam o estado do coordenador |

Os testes usaram arquivos fictícios e fornecedor local nos casos citados. Não demonstraram vazamento de documentos pessoais. As versões registradas são históricas, não uma declaração sobre todas as versões futuras.

O mantenedor escolheu **Docker Sandboxes** e depois aprovou manter essa escolha na consolidação. A alternativa de executar desprotegido no host não foi adotada. A prova por assinatura não pode virar API silenciosamente.

## 6. Estado atual do executor, componente por componente

| Componente | Implementado e comprovado | Falta |
|---|---|---|
| `mission_sbx.py` | Adaptador compartilhado de consultas permitidas, hash/versão, prazo, captura privada, classificação, preflight e adaptador de recuperação com comandos fechados | Prova nativa dos comandos de recuperação e integração de mutações globais |
| `mission_environment.py` | Seleção privada local/dedicado, preservação, diagnóstico de armazenamento | Validação real no ambiente cloud escolhido |
| `mission_sandbox.py` | Metadados e inspeção sem iniciar a VM; exposição da reserva compartilhada | Perfil aprovado e observação nativa suficiente para os novos aceites |
| `mission_process.py` | Supervisão de árvore de processos, limites e recibos; controlador testado dentro da mesma contenção | Prova nativa de encerramento da carga aninhada |
| `mission_controller.py` | Canal aberto, identidade, gates e intenção antes do efeito, protocolo limitado e fixture fixa | Adaptador de despacho nativo e aceite do percurso de rede |
| `runtime/sbx/guardian.py` | Processo supervisor, privilégios limitados, prazo, repetição recusada, gates de rede e comandos v4 completos | Prova integrada do candidato v4 atual |
| `runtime/sbx/launcher.py` | Preparação única, identidade, rede por fase, recibos e recuperação por CID, incluindo resposta de create perdida | Prova nativa dos novos comandos `observe/stop` e pacote exato |
| `runtime/sbx/relay.py` | Relay restrito no guardian: destino fixo, CA vinculada por hash, parser limitado, JSON/streaming e fechamento | Docker TLS real e clientes autenticados nesse percurso |
| `runtime/sbx/fixture.py` | Inicialização sem rede e uma GET ao relay; eco fictício e metadados limitados, teste com relay local | Imagem reconstruída e prova A/B/A2 do candidato |
| `mission_execution.py` | Reserva privada compartilhada por conta, lock, ledger atômico, intenção antes do retorno e recusa de repetição | Restauração nativa pendente; registros v1 consumidos permanecem bloqueados |
| `mission_transaction.py` | Planos v2/v3/v4, vínculo missão/reserva, diário A/B/A2 e recuperação de cargas/VM/configuração com prova local | Recuperação e aceite nativos |
| `mission_network.py` | Guard A/A2, ausência em B, settings sandbox e recuperação com intenção durável | Contrato de credencial, adaptador e prova nativa |
| `mission_egress.py` | Filtro após o proxy, DNS herdado, dial numérico único, peer conferido, helper com PID/recibos duráveis | Provar percurso Docker TLS e recusas nativas |
| `mission_runs.py` | Recibos, admissão sintética bloqueada, vínculo interno global e projeção após recuperação | Habilitação pública após contrato de credenciais e aceites nativos |

`REVIEWED_PROFILES` e o registro de perfis nativos continuam vazios. Não preenchê-los com uma flag `verified=true`, arquivo fornecido pelo chamador ou conclusão de testes simulados.

### Caminho de rede previsto para a integração

```mermaid
flowchart LR
  C[Coordenador YoungCrow] --> R[Reserva global e diário durável]
  R -->|integração local| L[Launcher confiável]
  L --> G[Guardian da operação]
  U[Cliente sem privilégios] --> Q[Relay restrito no guardian]
  G --> U
  Q -. prova nativa pendente .-> P[Proxy Docker e credencial retida fora do trabalho]
  P -.-> F[Filtro de destino no host]
  F -.-> E[Origem autorizada]
```

O manifesto v4 exige hash de um valor fictício distinto do placeholder; v3 conserva o eco histórico. O cliente UID1000 deve alcançar apenas o relay em loopback; UID0 deve alcançar apenas o IPv4 observado do proxy na porta 3128. IPv6 e encaminhamento permanecem negados. As regras, namespace e ausência de remapeamento de UID/GID precisam ser conferidos em cada fase.

O snapshot da CA fica no controle privado e é vinculado por hash ao manifesto. Os testes locais não certificam seu handshake real com o Docker. O gateway MCP pode existir no gerenciador, conforme decisão aprovada, desde que a inacessibilidade pelo cliente seja demonstrada mesmo com a saída necessária liberada.

### Reserva compartilhada

O banco de missão por projeto não impedia dois repositórios de disputar o mesmo Docker. A nova reserva é comum à conta e tem caminho obtido pela identidade do sistema, sem override por projeto, variável de ambiente ou PID do daemon. O teto deliberado é uma operação por conta nesse fluxo.

Ela usa um único `registry.json` com lock do sistema operacional. Falta/corrupção do ledger em armazenamento existente bloqueia o uso. Intenções são persistidas antes de devolver controle ao futuro dispatcher. Repetição do ID retorna o registro existente, sem autorizar outro efeito. Perda do coordenador e expiração do prazo não liberam a reserva.

O abandono v1 atende somente uma reserva sem intenções, após observar baseline idêntico. O plano v2 pode encerrar a reserva após comprovar carga terminal, VM parada, proprietário ausente e configurações inalteradas. Divergência mantém bloqueio. As fases v2 compartilham até 120 segundos; recuperação usa até 60 segundos próprios, sem estender ou repetir o despacho. V3 acrescenta restauração local dos settings sandbox; credenciais/políticas e aceite nativo continuam pendentes.

## 7. O que os testes já demonstraram

Os números abaixo são checkpoints diferentes, com sobreposição. Não somá-los como se fossem uma suíte única ou uma contagem de requisitos entregues.

| Prova/checkpoint | Resultado | Limite da conclusão |
|---|---|---|
| Reserva/recuperação cloud de 7/out | 567 testes: 547 aprovados, 20 pulados; depois 23 transacionais passaram após ajuste de fixture | Fontes de produto idênticas às da suíte; fronteira Docker simulada, Windows nativo e 203.6 pendentes |
| Guardian/launcher de candidatos anteriores | Conclusão, prazo, transporte perdido, PID final zero e repetição recusada em cenários sintéticos/nativos | Pertencem às versões/digests registrados, não aprovam automaticamente o v4 atual |
| Reserva antecipada de encerramento | Nove cenários nativos da candidata passaram; reinício ativo posterior terminou antes do prazo | Suspensão completa do host e candidato atual ainda exigem seus aceites |
| Launcher v2 com rede | Oito cenários nativos passaram, incluindo ausência de gates, regras alteradas e perda do transporte | Não inclui autenticação de modelo |
| Transporte de provedores no launcher v2 | TLS verificado em cliente e filho; HTTP 421 OpenAI e 404 Anthropic; 40 tentativas negativas recusadas | Resposta TLS não é prova de inferência nem de login |
| Endereços de gateway/Windows | 124 tentativas TCP sem conexão e zero acessos às sentinelas no ensaio registrado | Escopo de destinos e candidato do ensaio; não prova ausência universal de rotas |
| Setup local/dedicado | Oito combinações novo/migrado × Claude/Codex × local/dedicado preservaram escolha e retorno | `dedicated` validou configuração local, sem execução real em servidor |
| Diagnóstico local básico em 7/out | 11 consultas passaram, incluindo inventário de credenciais Docker | Inventário vazio não significa que as CLIs no host estejam deslogadas; login Docker não autentica provedores |
| Preflight de candidato em 7/out | 29 consultas passaram: 27 Docker e duas de identidade de processo Windows; baseline repetido estável | Somente leitura; `effects_allowed=false` |
| Relay anterior | 43 testes: guardian 17, launcher 15, relay 11 | Sockets locais/upstream fictício e contratos Linux/TLS controlados; sem aprovação nativa |
| Contrato de injeção v4 | Hash esperado, ausência de substituição recusada, A/B/A2 e recuperação em sockets/processos locais | Docker, TLS e substituição simulados; [medição atual](medicoes/2026-10-07-injection-proof.json) |
| Último incremento conjunto | **74 testes passaram, zero falhas e zero skips**, em 65,004 s | Reserva 13, filtro 8, adaptador 29, inspeção 22 e setup 2; não certifica toda a aplicação |
| Armazenamento da reserva | Um dos 13 testes usa permissões reais do Windows em fixture privada e reabre o registro | Não criou reserva no armazenamento real da conta nem alterou Docker |
| Vault no fim do incremento | 407 notas, zero problemas no verificador | Comprova estrutura/vínculos verificados, não a veracidade de todo texto |

No último incremento não houve comando Docker, reinício, GET externo ou chamada a modelo. Isso se refere ao incremento do executor, não a todo o histórico do projeto: outras frentes registram provas reais de uso dos clientes e do Docling.

As 29 respostas do preflight foram capturadas antes de pequenas correções finais do validador. O replay offline dessas respostas passou, mas não representa outra coleta nativa com o código corrigido. A nova operação integrada terá seu próprio preflight, no contexto e na versão exatos que executarão os efeitos.

### A suíte geral não está aprovada na árvore atual

Existem checkpoints antigos em que a suíte geral passou, além de rodadas com falhas/erros e rodadas interrompidas. Não usar um resultado antigo para certificar o checkout atual.

Uma rodada foi descartada porque os temporários estavam dentro do checkout e houve edição de fontes durante a execução. Outra encontrou falha de observação do supervisor e foi interrompida; o caso passou isoladamente sem alteração de prazo. A rodada geral do relay foi interrompida durante adoção; a suíte focada posterior passou.

Já foram corrigidos problemas das fixtures Windows de caminhos longos e leitura prematura de PID. Preservar limites de caminho e identidade do processo; não relaxar proteções para deixar o teste verde. Antes da liberação final, executar QA geral pertinente com fontes estáveis e temporários privados fora do Git.

## 8. Falhas históricas, causas e tratamento

| Falha ou descoberta | Causa/evidência | Estado e orientação |
|---|---|---|
| `& foi inesperado neste momento` | Comando PowerShell colado em `cmd.exe` no Termius | Problema de shell, não do executor; usar a sintaxe da shell real |
| WHP desabilitado/reinício necessário | Pré-requisito Windows ainda não ativo | Habilitado e reinício observado no histórico; não instalar/reiniciar novamente por hábito |
| Daemon iniciado pelo terminal do agente com erro de socket | Falha observada naquele contexto; serviço iniciado pelo PowerShell do operador funcionou | Não generalizar a causa nem tratar login como correção de socket; diagnosticar o contexto antes de reiniciar |
| Kit não encontrado com `pull_policy=never` | Imagem do registry local ainda não estava em cache | Tentativa posterior com política apropriada criou o pacote antigo; não repetir scripts nem certificados antigos |
| Limpeza de certificado com timeout | Remoção anterior não confirmou em 15 s | Tentativa posterior removeu e confirmou inventário restaurado; não há autorização para instalar outro certificado automaticamente |
| Término 3,8935 ms depois do prazo | Encerramento era armado no deadline, sem reserva para processar sinal e finalizar | Correção reservou um segundo dentro do prazo original; prova posterior passou, sem acrescentar tolerância |
| Medição de término após reinício parecia atrasada | `sbx exec` iniciou a VM parada para inspecioná-la; recuperação alterou a leitura de estado | Nova prova observou a VM antes de iniciar inspeção; medição anterior continua reprovada |
| Repetição com `Existing receipt`/`start_consumed` | Operação já consumida | Recusa esperada; preservar recibo. Novo nome de script não deve contornar a regra |
| MCP alcançável pelo proxy do gerenciador | Existência da VM e deny-all não bastaram para a fronteira desejada | Arquitetura passou a exigir cliente isolado e inacessibilidade demonstrada; gateway somente no gerenciador foi aceito sob essa condição |
| Simulação de autenticação: CONNECT/SNI autorizados, mas `Host` desviava a chamada | Primeiro modelo de filtro não vinculava todas as identidades da requisição | Corrigido no spike; o ciclo seguinte ainda permitiu substituição DNS para IP privado. O terceiro usou destino numérico fixo e passou nos casos loopback, sem comprovar OAuth ou isolamento nativo |
| Domínio autorizado funcionou mesmo negando todos os CIDRs | Semântica da política Docker observada no ensaio; as três GETs retornaram HTTP 200 | Hipótese “allow domínio + deny IP” reprovada. Validar destino após o proxy |
| TLS funcionou, mas credencial não era injetada via IP | Caminho por domínio e caminho por IP têm comportamento diferente no proxy | Transporte por domínio com filtro posterior aprovado para investigação; não expor credencial ao cliente para contornar |
| `settings_readback_failed`/`cleanup_incomplete` | Houve erros nos contratos/leitura de settings dos roteiros | Restaurações foram reconciliadas nos checkpoints. Adaptador compartilhado substitui lógica repetida; conferir cada recibo, não tratar todas as ocorrências como iguais |
| `TimeoutExpired` antes do recibo | Tentativa v2 terminou antes de iniciar o efeito registrado; consulta exata não ficou estabelecida naquele roteiro | Preservar inconclusão. Não inventar causa nem executar automaticamente outra versão |
| `JSONDecodeError` no celular | Roteiro não trouxe observação suficiente da saída original | Diagnóstico separado capturou `daemon status` com JSON válido; isso não identifica retroativamente a causa do JSON anterior |
| `policy_baseline_changed` | Comparação de política precisou de correção no caminho experimental | Baseline deve comparar semântica relevante, mantendo identidade e conteúdo; não ignorar toda divergência para passar |
| `sbx_command_failed` | Roteiro descartava causa útil do fornecedor | Novo adaptador guarda saída limitada em área privada e classifica fase, código e erro |
| `unsupported_permissions`/`execution_storage_unprotected` | Arquivo temporário criado com proprietário diferente do usuário no contexto remoto | Diagnóstico identificou `temporary_evidence/owner_mismatch`; proteção passou a atuar somente no temporário novo e vazio, verificando identidade/ACL |
| `secret ls --json` falhou pelo Termius com chave SSH | Mensagem capturada: conjunto de credenciais indisponível naquela sessão Windows | Classificado como `credential_session_unavailable`. O terminal remoto funciona, mas essa sessão não ofereceu o acesso exigido ao gerenciador de credenciais |
| Mesma consulta no PowerShell local | Inventário e demais consultas passaram, com mesmo executável | Restrição do contexto remoto ficou separada de falha geral do Docker; não repetir o diagnóstico remoto sem mudança de contexto |
| `RemoteDisconnected` na fase B | Resposta do proxy não bastava para provar o bloqueio no destino | Rodada inconclusiva; A2 não executada. Correlacionar log nativo com VM, endpoint e janela da operação |
| Reserva por projeto | Dois projetos poderiam disputar o mesmo Docker | Registro comum por conta implementado; ligação ao dispatcher ainda pendente |
| Recibo removido aparentava histórico vazio | Primeira versão da reserva varria arquivos individuais | Ledger obrigatório único corrigiu o caso; ausência em área existente bloqueia |
| Inicialização concorrente apagava o ledger | Helper Windows podia retornar sucesso a dois criadores do diretório | Sob lock, preservar/validar ledger existente; regressão passou |
| Relay: cancelamento, socket em connect, chunk truncado e thread parcial | Quatro defeitos encontrados por revisão independente | Corrigidos com regressões antes do checkpoint de 43 testes |
| Erro bruto poderia aparecer no relatório do filtro | Texto livre de `ValueError` era aceito como razão | Lista de razões permitidas; regressão com marcador fictício passou |

### O caso A/B/A2 que mais importa

Em 6 de outubro, a fase A da prova corrigida passou: HTTP 200, TLS verificado, credencial fictícia correspondente e peer público observado. A fase B, com guard ausente, terminou em `RemoteDisconnected`. A2 não rodou.

A análise posterior encontrou uma recusa explícita ao upstream nos logs HTTP do daemon, correlacionada com sandbox, porta e horário. O coletor procurava no histórico de decisões de política, esperava outra redação de erro e havia guardado apenas hashes de alguns snapshots. Foi produzido um coletor capaz de correlacionar a evidência preservada e testado offline.

**O recibo da rodada permanece inconclusivo.** A prova integrada precisa obter A, B atribuível e A2 na mesma operação nova, com restauração. A investigação posterior explica B, mas não fabrica A2 nem promove o aceite antigo. As 190 chamadas registradas nessa rodada incluíam consultas/limpeza; não eram 190 testes independentes.

A restauração daquela rodada foi confirmada: settings e política preservados, inventário conservado, cinco VMs paradas e porta fechada no checkpoint. Não repetir nem reconciliar uma rodada cuja limpeza já foi comprovada.

## 9. Plano aprovado que continua valendo

Plano: `docs/superpowers/plans/2026-10-07-executor-consolidation.md`.

### PBI 1 — Diagnóstico confiável

Consolidar consultas no adaptador comum, registrar fase/argumentos sanitizados/contexto/versão/prazo/retorno e preservar saídas sensíveis localmente. Diferenciar timeout, recusa, JSON inválido, contrato incompatível e divergência. Todas as consultas preparatórias devem passar no contexto da operação antes de alterar Docker.

**Estado:** caminho de diagnóstico implementado e comprovado localmente, incluindo causa da falha remota. Não há necessidade de refazer o brainstorming nem de repetir o mesmo preflight sem uma razão nova.

### PBI 2 — Isolamento, rede e recuperação

Reutilizar guardian, launcher, reservas e recibos; intenção durável antes do efeito; identidade antes do despacho; credenciais reais fora da VM de trabalho; MCP/host/arquivos privados inacessíveis. Primeiro usar fixture sintética. Configuração global Docker exige uso exclusivo, baseline e restauração comprovada.

**Estado:** plano, controlador e recuperação de cargas/VM integrados em testes locais; egress, restauração global e pacote atual ainda pendentes. O aceite exige isolamento, prazo, não repetição, bloqueio e restauração juntos, no mesmo candidato.

### PBI 3 — Ambos os clientes e adoção

Integrar `client check` aos recibos de missão. Uma execução mínima por cliente, até 120 segundos, com assinatura, modelo/effort escolhido, resultado válido e encerramento observado. Liberar perfil só depois de ambos passarem. Validar projeto novo/migrado, preservação e interrupção.

**Estado:** aceite autenticado do executor ainda não realizado. A seleção de runner dedicado existe; execução nesse ambiente não está certificada.

### Limites da consolidação

Sequência: contratos determinísticos → diagnóstico somente leitura → prova sintética integrada → Claude autenticado → Codex autenticado → adoção.

Limite aprovado: até três ciclos de correção desta consolidação. O ledger registra **dois utilizados**. Não zerar a contagem ao mudar de sessão ou para cloud. Os ciclos de outras investigações históricas e os três ciclos futuros por PBI são contadores distintos.

Cada nova correção deve ter causa identificada, ajuste localizado e regressão antes de nova prova nativa. Os incrementos mais recentes só fizeram testes locais e não consumiram nova tentativa Docker. Incompatibilidade estrutural demonstrada ou esgotamento do limite exige decisão arquitetural; não gera outro roteiro nem afrouxa requisitos.

## 10. Próximos passos de implementação, em ordem

### 10.1 Preservar a implementação antes da mudança de ambiente

Conferir quais arquivos atuais chegaram à cloud. Verificar branch, commit, modificações e os hashes da seção 14. Um checkout que tenha somente o commit `932b775` não contém a implementação local completa. Não começar a reescrever componentes apenas porque não apareceram no clone.

### 10.2 Integrar uma variante sintética em `client check`

Usar o comando existente, com manifesto explicitamente sintético e resultado separado
de inferência. `fixture_id=isolated-egress-v1` agora tem admissão implementada:
valida missão/revisão/autorização/limites e grava `failed/controller_pending`,
`model_calls=0`, antes de qualquer inspeção de cliente. A tentativa consome os limites
da missão uma vez; replay conserva o bloqueio e seu UUID. O ramo ainda não consulta
Docker nem cria reserva global. O [guia](USAGE.md#synthetic-admission) detalha o contrato.

O ramo sintético precisa ocorrer antes de `inspect_client/build_check`, que dependem de perfil, autenticação e modelo reais. Preservar missão, revisão, autorização e limites. Registrar `model_calls=0`; não produzir uma observação fictícia de Claude/Codex para contornar os perfis vazios.

O coordenador interno já reserva antes dos efeitos e vincula manifesto, baseline, executável, imagem externa/interna, hashes de código, autorização e IDs/manifestos de A/B/A2. Cada fase tem UUID e nonce próprios, persistidos antes de começar. Preservar esse contrato ao ligar egress e a entrada pública. Uma transação com três fases HTTP não equivale a três chamadas de IA.

### 10.3 Implementar o controlador de canal aberto

Componente interno implementado em `scripts/mission_controller.py`, testado com
processos locais sob `mission_process`. A integração nativa ainda depende do §10.2
e §10.4; não há novo comando público ou liberação de `client check`. O retorno de
fase nunca certifica recuperação, parada da VM ou aceite nativo.

O `mission_process.supervise` atual escreve o stdin e fecha. O protocolo do launcher precisa manter o canal aberto e receber duas autorizações externas de rede. O modo existente de `exchange_requests` espera JSON-RPC e não corresponde aos eventos `kind` do guardian.

A menor ponte identificada é um modo interno fixo do controlador, executado sob o mesmo supervisor/job, que mantém o pipe do launcher e conduz os gates. Reutilizar a contenção e o registro de proprietário. Não transportar Python arbitrário por stdin nem importar `guardian_vm.execute(source)` dos experimentos.

Contrato interno observado, a validar na integração e no pacote exato:

```text
launcher.py prepare sha256:<imagem-interna>
launcher.py run <uuid-fase> <nonce>
launcher.py network <uuid-fase> <nonce> initialize
launcher.py network <uuid-fase> <nonce> dispatch
launcher.py observe <uuid-fase> <nonce>
launcher.py stop <uuid-fase> <nonce>
```

Sequência por fase: preparar → aguardar `listening` → aplicar/conferir gate de initialize → autorizar initialize → aguardar `ready` → conferir gate de dispatch → autorizar fixture fixa → consumir eventos limitados → conferir encerramento. Comandos nativos devem ter formato fechado e identidade verificada, sem uma função genérica de execução arbitrária.

### 10.4 Completar recuperação antes de habilitar efeitos

A recuperação v2 cobre cargas identificadas, VM e configuração inalterada com testes locais. V3 acrescenta guard e restauração dos settings sandbox; v4 conserva essa recuperação com o contrato de injeção. Antes da habilitação, completar contrato local de credenciais, adaptador e recuperação nativa de 203.6/203.5. A reserva v1 consumida continua bloqueada.

- Observar contêiner/carga enquanto a VM já estiver legitimamente ativa, quando necessário.
- Depois de queda, não usar `sbx exec` para “consultar” uma VM parada: ele pode iniciá-la.
- Parar somente recursos próprios e identificados.
- Restaurar somente valores que ainda correspondam às alterações da operação.
- Preservar mudanças externas; divergência mantém bloqueio.
- Conferir settings, políticas, credencial fictícia removida, inventário, porta e processos.
- Vincular os hashes dessas observações ao encerramento da reserva.
- `new:false`, timeout ou PID desaparecido não autorizam replay.

O `client reconcile` por arquivos de evidência recusa runs integradas com `integrated_recovery_required`. A API interna projeta a missão somente após fechamento observado da reserva global; ainda não restaura configurações globais. `observe_stop` mantém explicitamente `workload_reaped=false` quando a prova não existe.

### 10.5 Empacotar fixture e provar o candidato atual

Fixture implementada em `runtime/sbx/fixture.py` e incluída no Dockerfile e na
allowlist do contexto. O teste com relay real usa apenas sockets locais e upstream
fictício. Reconstrução da imagem e provas nativas abaixo permanecem pendentes.

Fixture fixa, executada sem privilégios: inicialização sem rede, uma GET ao relay local no caminho exato, validação v4 pelo hash esperado de um valor distinto do placeholder e emissão de metadados limitados. Não aceitar URL/código/comando livre.

Reconstruir a imagem que inclui guardian, launcher, relay e fixture; registrar digest e versões. Um pacote antigo que passou em parte das provas não aprova este novo pacote.

Executar A/B/A2 com intenção durável e limite aprovado:

1. A: requisição permitida funciona, TLS/eco/peer conferidos.
2. B: guard ausente na mesma porta, bloqueio atribuído a evidência nativa da operação; desconexão ou retorno 126 isolado não bastam.
3. A2: guard restaurado e requisição volta a funcionar.
4. Encerramento/restauração: todos os controles anteriores conferidos antes do aceite.

### 10.6 Provar Claude e Codex

Só depois do aceite sintético integrado. Usar os binários oficiais, autenticação do próprio usuário, modelos/efforts realmente disponíveis e até 120 segundos por chamada mínima. Registrar resolução efetiva, resultado e encerramento. Não substituir modelo, effort, provedor ou cobrança sem decisão explícita.

Testar a adoção nova/existente e a recuperação; fazer revisão independente do conjunto; atualizar README/guia/backlog/diagramas/vault. Compatibilidade deve ficar vinculada às versões testadas. Concluir YC-203 antes de habilitar a fila.

## 11. Backlog restante até o produto completo

Fonte: `docs/BACKLOG.md`. IDs são planejamento público; não são PBIs automaticamente importados no banco operacional.

| ID | Entrega | Estado resumido |
|---|---|---|
| YC-010 | Retomar piloto público em nova sessão Claude | Verificado no piloto: sessão real, reavaliação offline e revisão semântica; recibo original preservado |
| YC-011 | Provar as quatro skills de preparação nos clientes atuais | Descoberta Codex/Linux e Claude/Windows verificadas; aplicação em ambos pendente, ligada a YC-203 |
| YC-201 | Preflight, catálogo e compatibilidade | Mecanismo implementado; execução nativa não certificada |
| YC-202 | Limites, recibos e recuperação de processo | Simuladores verificados; integração isolada pendente |
| YC-203 | Perfis nativos, instalação e provas autenticadas | Frente ativa, parcial |
| YC-204 | Coordenador e fila por prioridade | Depois de YC-203 |
| YC-205 | Branches/worktrees por PBI | Depois da fila |
| YC-206 | Decisões dos agentes PM/Tech Lead e contexto de trabalho | Depois de fila e worktrees |
| YC-207 | Pausar, retomar e cancelar | Planejado |
| YC-208 | Pacote privado e transferência de responsabilidade | Planejado |
| YC-209 | Prova local/servidor nos dois sentidos | Planejado |
| YC-301 | Revisão técnica e QA por PBI | Planejado |
| YC-302 | Playwright visual/operacional quando aplicável | Planejado |
| YC-303 | Autocorreção limitada a três ciclos | Planejado |
| YC-304 | Integração serial com aprovações ligadas à revisão | Planejado |
| YC-305 | QA integrado e aceite da versão conjunta | Planejado |
| YC-401 | PR e promoção respeitando proteção da main | Planejado |
| YC-402 | Deploy manual/automático com os mesmos critérios | Planejado |
| YC-403 | Verificação de produção e encerramento | Planejado |
| YC-404 | Recuperação de deploy autorizada e limitada | Planejado |
| YC-405 | Avisos por eventos; webhook opcional autorizado | Planejado |
| YC-501 | Matriz ponta a ponta nos percursos anunciados | Planejado |
| YC-502 | Retomada verificável de toda a entrega pelo vault | Planejado |
| YC-503 | Guias, demonstração e processos completos | Planejado |
| YC-504 | Release pública, manutenção, contribuição e compatibilidade | Planejado |

Os 25 itens não têm esforço equivalente. Não transformar essa lista em percentual de produto pronto. Extensões posteriores: claude-mem opcional (YC-X01), relações/reindexação assistidas (YC-X02), sincronização contínua (YC-X03) e revisões imutáveis de plugins quando suportadas (YC-X04).

```mermaid
flowchart LR
  B[Base e preparação entregues] --> E[2A: executor isolado — atual]
  E --> F[2B: fila e desenvolvimento]
  F --> C[2C: continuidade e transferência]
  F --> Q[3: QA e integração]
  C --> R[4: release e operação]
  Q --> R
  R --> A[Aceite ponta a ponta e publicação]
```

## 12. O que levar para a cloud

### Código e documentos que precisam acompanhar a transição

O checkpoint da branch reúne os arquivos selecionados e revisados abaixo. Antes de transferir alterações posteriores, conferir o diff e os arquivos novos. Não executar `git add .` indiscriminadamente: o estado local também contém material de diagnóstico e resíduos.

Itens essenciais desta frente:

```text
scripts/mission_clients.py
scripts/mission_process.py
scripts/mission_runs.py
scripts/missions.py
scripts/mission_environment.py
scripts/mission_sandbox.py
scripts/mission_sbx.py
scripts/mission_execution.py
scripts/mission_egress.py
scripts/adoption.py
scripts/adoption_fs.py
scripts/adoption_acl.ps1
runtime/sbx/
tests/test_mission_*.py
tests/test_execution_storage_diagnostics.py
tests/test_setup.py
tests/windows_fixture_runner.py
tests/fixtures/guardian_attack.py
tests/fixtures/guardian_network_attack.py
tests/fixtures/legacy_mission_sandbox.py
tests/smoke_mission_guardian.py
tests/smoke_mission_launcher.py
tests/smoke_mission_network.py
tests/smoke_execution_setup.py
setup.sh
skills-lock.json
skills/personalizer/
skills/yc-personalizer/
README.md
docs/USAGE.md
docs/BACKLOG.md
docs/superpowers/specs/
docs/superpowers/plans/
docs/relatorios/
docs/medicoes/
```

Essa lista identifica o núcleo; não substitui a revisão completa do diff. Há mudanças adicionais em testes de adoção/capacidades e `.gitignore`. Não descartar arquivos fora da lista automaticamente.

`docs/medicoes/` na lista significa somente os arquivos selecionados e revisados. Os diretórios `setup-audit-*`, o reprodutor histórico `reproduce_setup.py`, `tracked-files.txt` e `github-metadata.json` foram mantidos locais. O reprodutor pressupõe defeitos da versão inicial e não deve ser executado contra o código atual.

### Material local que um clone não inclui

| Local | Conteúdo e tratamento |
|---|---|
| `.superpowers/sdd/2026-10-04-isolated-executor/` | Experimentos e recibos históricos consumidos. Preservar como evidência; não alterar, executar novamente nem importar no fluxo normal do produto |
| `.superpowers/sdd/2026-10-07-executor-consolidation/progress.md` | Ledger da consolidação, decisões e limites; selecionar cópia revisada para continuidade privada |
| `.superpowers/sdd/2026-10-07-executor-consolidation/*tests.log` | Evidência local dos testes; revisar antes de transferir |
| `.operacao-local/execution/` | Recibos privados, saídas brutas limitadas e seleção local; não publicar em Git |
| `vault/local/` | Notas, fontes ingeridas e histórico privado; clone não leva esta memória |
| `.runtime/` e ambientes Python | Dependências locais; reconstruir conforme guia, não presumir portabilidade binária |
| `YoungCrowExecution` fora do projeto | Registro compartilhado por conta; estado operacional, não template nem autorização para nova máquina |
| Docker Sandboxes no Windows | VMs, imagens, credenciais e políticas locais; não viajam no Git |

Não copiar tokens, senhas, caches de login ou credenciais do host para a cloud. Autenticar cada ambiente pelos mecanismos oficiais. Uma cópia de recibo preserva evidência; não concede permissão de repetir sua operação.

Há um diretório não rastreado de nome literal `%SystemDrive%/` no checkout, a revisar antes da publicação. Há também uma fixture antiga privada fora do repositório, `C:/Users/rmfon/yc-abab9951`, preservada após a revisão automática recusar sua remoção recursiva. Não houve tentativa alternativa de exclusão. Isso não é uma limpeza Docker pendente nem motivo para bloquear o trabalho documental; não transportar resíduos por padrão.

### Cloud de desenvolvimento versus runner validado

Pode-se continuar leitura, implementação e testes determinísticos na cloud. Isso não transforma automaticamente o ambiente em runner aprovado.

O caminho Linux do projeto observa Ubuntu 24.04 e acesso a KVM; a identidade do daemon no runner Linux ainda precisa de implementação/prova. A disponibilidade de virtualização e as permissões reais devem ser medidas no destino. Um ambiente de edição com Docker comum não é, por esse fato, o Docker Sandboxes isolado do contrato.

Windows ACL/Job Objects, logon local e Credential Manager são diferentes dos mecanismos POSIX. Revalidar os controles no ambiente escolhido. A preferência `dedicated` e o uso de VS Code Remote SSH já foram documentados; a transferência operacional certificada de missão continua planejada em YC-208/209.

As skills pessoais Karpathy, Ponytail, Humanizer e Superpowers estão instaladas na conta local e podem não existir no ambiente cloud. Levar suas instruções/referências pelos mecanismos permitidos e conferir a disponibilidade, sem pressupor que caminhos `C:/Users/rmfon/.codex/...` funcionem no Linux.

O núcleo documentado usa Python 3.11+, Bash e Git; no Windows, Git Bash e helpers PowerShell 5.1. macOS e instalação sem Bash não foram validados. Graphify e Docling têm dependências próprias: reconstruir seus ambientes no destino, sem copiar um venv Windows para Linux.

## 13. Checklist de retomada para a próxima sessão

1. Ler este arquivo, `AGENTS.md`, `CLAUDE.md`, `docs/BACKLOG.md` e o plano de consolidação de 7/out.
2. Conferir `git status`, branch, HEAD e presença dos arquivos novos; distinguir clone parcial de componente não implementado.
3. Conferir os hashes e a medição atual; divergência de fonte não herda automaticamente a aprovação antiga.
4. Ler o microíndice e a nota de consolidação se as notas privadas tiverem sido transferidas; usar este documento e os relatórios sanitizados quando não estiverem disponíveis.
5. Registrar o novo ambiente e quais evidências podem ser reproduzidas nele. Começar com contratos determinísticos; não rodar antigos scripts nativos.
6. Retomar 203.6 somente com nova evidência do contrato local 0.46.0: identidade/versão/remoção atômica da credencial e escrita condicional dos settings. A pesquisa oficial disponível está registrada; não repetir buscas idênticas. Depois implementar adaptador nativo e provar o candidato v4; coordenador, injeção interna e preservação de mudanças após intenção têm testes locais.
7. Revalidar a preparação no contexto real antes da nova prova Docker. Respeitar dois ciclos já consumidos e o teto aprovado.
8. Só então testar A/B/A2, ambos os clientes por assinatura e adoção. Manter o perfil bloqueado enquanto faltar qualquer aceite obrigatório.

### Comandos de consulta do checkout

```bash
git status --short
git branch --show-current
git rev-parse HEAD
python -B scripts/vault.py check --json
python -B scripts/missions.py --root . environment show --json
```

Use o Python suportado pelo projeto; na máquina original os testes desta frente usaram Python 3.14. Instalação Docling tem ambiente e dependências próprios.

### Reprodução da última suíte focada no Windows

Este comando é de testes com fixtures, não inicia uma prova Docker. Execute a partir da raiz do checkout; ajuste caminhos para a nova localização. O runner usa temporários privados fora do Git. A execução validada mais recente aparece na seção 14.

```powershell
$env:RUNNER_TEMP = 'C:/Users/rmfon'
$env:YC_NATIVE_RESERVATION = '1'
$env:PYTHONPATH = 'C:/Users/rmfon/YoungCrowHarness-review-20261001/tests'
C:/Python314/python.exe -X utf8 -B tests/windows_fixture_runner.py -m unittest test_mission_execution test_mission_egress test_mission_sbx test_mission_sandbox test_setup.SetupTests.test_sandbox_environment_installs_without_activating_runtime test_setup.SetupTests.test_runtime_helpers_preserve_existing_install -v
```

Na cloud Linux, não rodar o wrapper Windows nem declarar seus aceites a partir de skips. Os testes determinísticos de transporte podem ser selecionados pelo unittest, por exemplo `python -B -m unittest discover -s tests -p 'test_mission_egress.py' -v`. Testes nativos exigem suas pré-condições e não equivalem entre plataformas.

### Diagnóstico Docker disponível, quando houver motivo para nova coleta

Forma do comando, com valores do novo ambiente:

```text
python -B scripts/missions.py --root . client environment --executable <caminho-absoluto-sbx> --preflight --sandbox <sandbox-existente> --json
```

Não colar os placeholders literalmente. O comando observa uma sandbox existente, não a cria nem certifica a execução. O relatório apresenta lacunas e `effects_allowed=false`. Não é necessário repeti-lo apenas para produzir mais evidência idêntica.

## 14. Evidências e identidade da implementação

### Checkpoints principais

| Evidência | Identificação |
|---|---|
| Preflight nativo de candidato | 7/out, 05:26:54–05:29:25 UTC; 29 consultas |
| Recibo privado desse preflight | `.operacao-local/execution/sbx-64d5dab18db144818a7a62c478ee6012.json` |
| SHA-256 do recibo | `3acd4bd3c0e4f08fcf12f797f8b6c1f0f65b1c76740e75553ae4ec0b5044b190` |
| sbx observado | 0.46.0 |
| SHA-256 do sbx observado | `a2c8d68f3a16851a65e1d43f7330ae6860c5a2f07df8f22fab5dae7a4a232780` |
| Sandbox antiga usada nas provas | `yc-package-471e336723f7`, ID `3a4a47a2-6dbd-4196-a7a8-a481f65bdd85` |
| Digest do pacote antigo | `sha256:3e6a380a46840656b9e724694ef2964e2d13471bc3dd0fe92ae66492217dfe2f` |
| Log dos 43 testes do relay | `.superpowers/sdd/2026-10-07-executor-consolidation/relay-final-tests.log` |
| SHA-256 do log do relay | `7c59b8ed57f7a8cefaecc2a4568e72ef5fa70ba1efb5fb9f6f614300e0b3fa38` |
| Log dos 74 testes finais | `.superpowers/sdd/2026-10-07-executor-consolidation/reservation-egress-final-tests.log` |
| SHA-256 desse log | `a16d82eae02bc117c36914dbcd5b7063fbd425d35b0caba2550bbce97f454a12` |
| Medição sanitizada | `docs/medicoes/executor-consolidation.json`, seção `shared_reservation_and_egress` |

IDs e digests históricos identificam evidência, não autorizam iniciar esses recursos na cloud. O pacote antigo não contém automaticamente as mudanças atuais de relay/reserva/filtro.

### Hashes conferidos ao preparar este arquivo

| Arquivo | SHA-256 |
|---|---|
| `scripts/mission_execution.py` | `7663eb7c1f4156e66d9c97277fc9a62a7d0b6de2c95da1f108e56ed126975ffd` |
| `scripts/mission_egress.py` | `20b27afc0186a2f9c2a610afdb7b4c1ce58a7253eaa6f2e23a475795a9f27928` |
| `scripts/mission_sbx.py` | `e425f06c75ddc7b20d9bd374443adbde0caf3f2d02e1bfe6e996c258cd9bc83e` |
| `scripts/mission_sandbox.py` | `44756ecbf3c3806159962743bd8e1d3f7b37560d72f99c98c1af3376d3ba3858` |
| `runtime/sbx/guardian.py` | `136b00f154508180707e2353251796d0af142900c3bc5cb647c9416e36d5c2e1` |
| `runtime/sbx/launcher.py` | `8ece607c94eb30940afbfaebccc7516e49a5a8313cd19c3e154f5d4f3b650906` |
| `runtime/sbx/relay.py` | `c0bf304c53ed0b60014cf0dccee30283cc93c7f237efe04b670d1c258aa08316` |
| `runtime/sbx/youngcrow.dockerfile` | `e2043b3bc9e8c8cf54ded5ddc0c916b32b3558c0ce05443f64f3ddf6d23cb7f9` |
| `docs/superpowers/plans/2026-10-07-executor-consolidation.md` | `d3b7c787dd339661b09a81c77e66c8167c0625358c328630a603d66b0df3028e` |

Hashes são dos bytes locais. Normalização de finais de linha ou alteração de fonte muda o hash; investigar a diferença e revalidar em vez de trocar o valor e herdar um aceite.

### Mapa de leitura por assunto

- Visão e contratos da esteira: `docs/superpowers/specs/2026-10-03-ai-product-pipeline-design.md`.
- Backlog e dependências: `docs/BACKLOG.md`.
- Operação, setup e recuperação: `docs/USAGE.md` e `docs/PROCESS.md`.
- Diagnóstico inicial: `docs/relatorios/2026-10-01-diagnostico-youngcrowharness.md`.
- Limites dos clientes: `docs/relatorios/2026-10-03-native-client-verification.md` e `docs/relatorios/2026-10-04-native-permission-controls.md`.
- Arquitetura isolada: `docs/superpowers/specs/2026-10-04-isolated-executor-design.md`.
- Decisão MCP: `docs/superpowers/specs/2026-10-04-mcp-boundary-decision.md`.
- Decisão do filtro após proxy: `docs/superpowers/specs/2026-10-05-exclusive-egress-decision.md`.
- Provas de prazo/reinício: `docs/relatorios/2026-10-04-shutdown-reserve.md` e `docs/relatorios/2026-10-04-network-launcher.md`.
- CIDR e credenciais: `docs/relatorios/2026-10-05-hostname-cidr-proof.md` e `docs/relatorios/2026-10-05-native-proxy-compatibility.md`.
- A/B/A2 inconclusivo: `docs/relatorios/2026-10-06-corrected-egress-proof.md`.
- Captura do bloqueio: `docs/relatorios/2026-10-06-captured-egress-evidence.md` e `docs/relatorios/2026-10-06-integrated-egress-controller.md`.
- Consolidação atual: `docs/relatorios/2026-10-07-executor-consolidation.md` e `docs/medicoes/executor-consolidation.json`.
- Memória privada atual, se transferida: `vault/local/integrations/docker/sandboxes/index.md` e `vault/local/integrations/docker/sandboxes/runs/2026-10-07-consolidation.md`.

No vault original, projeto UUID `9865926d-6293-4c63-a8ff-c8441674a043`; nota de consolidação UUID `7a9dcf35-353e-42bf-bff3-cc00f97bbfeb`. Não usar apenas nomes de diretório para associar memória de projetos diferentes.

Revisores dos incrementos recentes: `storage_diagnostic_review`, `exclusive_egress_review` e `audit_executor_foundations`, sempre em leitura. O escritor principal concentrou as alterações. As revisões não substituem execução dos testes nem provas nativas. Nenhum MCP novo foi ativado para esses incrementos.

## 15. Regras de continuidade e critério de encerramento

O mantenedor se incomodou com o número de roteiros, confirmações e tentativas semelhantes. A consolidação foi aprovada para resolver isso. Trabalhar pela causa observável, usar o fluxo do produto e preservar a evidência existente. Não pedir novamente decisões já registradas. Solicitar participação do usuário somente quando faltar acesso ou houver uma ação nova que realmente dependa dele.

Não alterar testes para aceitar desconexão sem causa, aumentar prazos para esconder atraso, apagar recibos, reparar permissões existentes recursivamente, iniciar VM parada durante recuperação, copiar credenciais nem liberar fallback no host/API.

Conclusão desta frente exige: diagnóstico confiável; isolamento e A/B/A2 integrados no candidato exato; restauração/recuperação comprovadas; Claude e Codex por assinatura com resultado verificável; adoção preservada; documentação e pacote correspondentes. Só então liberar os perfis cobertos pela prova.

Conclusão do produto exige, além disso, fila, branches, agentes de produto, QA, integração, release, produção verificada e retomada pela memória. Não anunciar essa esteira como pronta ao concluir somente o executor.

O contexto histórico foi produzido por leitura dos registros e do checkout. A preparação do checkpoint acrescentou testes locais e duas correções de empacotamento/catalogação, detalhadas no relatório de publicação; não executou novo ensaio Docker, autenticação, inferência ou migração operacional. O estado atual das proteções do GitHub e dos contribuidores não foi reconsultado; preservar a decisão de autoria humana e validar as proteções antes de promover uma release.

ATRASO: main 1
