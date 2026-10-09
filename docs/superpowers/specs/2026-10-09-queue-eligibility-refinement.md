# Refinamento de YC-204: elegibilidade e reservas

Frente: preparação da fila de desenvolvimento. Estado: rascunho técnico para revisão.
Este documento não habilita 2B nem substitui o aceite de YC-203. Não há implementação,
migração, novo comando ou chamada de modelo nesta entrega.

## Objetivo e base

Detalhar como a fila decide entre iniciar um PBI, continuar trabalho ativo ou esperar.
A [especificação aprovada](2026-10-03-ai-product-pipeline-design.md#fila-paralelismo-e-branches)
já define prioridade, uma missão ativa por repositório e limites distintos de PBIs e
execuções. O [backlog](../../BACKLOG.md#frente-2-execução-e-continuidade) condiciona
YC-204 ao aceite de YC-203. Esta matriz transforma essas regras em cenários verificáveis.

PM define prioridade e critérios; Tech Lead define dependências e decomposição.
Dev implementa e corrige; QA valida em contexto independente. O coordenador aplica
as condições de avanço. Propostas dos líderes pertencem a YC-206, worktrees a YC-205
e execução do QA a YC-301. Aqui não se desenham novos agentes ou prompts desses papéis.

## Matriz proposta para a implementação futura

Os nomes das decisões abaixo descrevem comportamento; não são novos estados de esquema.
Cada decisão deverá vincular missão, revisão, PBI quando houver, motivo e operação.

| Situação observada | Decisão | Efeito que precisa ficar persistido antes de despacho |
|---|---|---|
| YC-203 sem aceite ou perfil necessário sem prova | Recusar início | Informar a pré-condição ausente; nenhuma execução ou vaga ativa adquirida |
| Outra missão ocupa o repositório, inclusive pausada ou aguardando deploy | Recusar ativação | Preservar missão proprietária e recusar a concorrente |
| PBI prioritário tem dependência não integrada | Procurar o próximo elegível | Preservar prioridade e motivo da espera; não reservar o PBI impedido |
| Limite de PBIs ativos atingido | Impedir entrada de novo PBI | Manter ocupação atual; desenvolvimento, correção, revisão/QA e espera de integração continuam contando |
| Há PBI elegível e vaga de PBI, mas faltam vagas de execução | Esperar capacidade | Não iniciar PBI novo nem invocar cliente; trabalho já ativo mantém sua vaga de PBI |
| PBI já ativo precisa de outra execução autorizada | Avaliar capacidade de execução | Não adquirir uma segunda vaga de PBI; reservar execução antes de invocar cliente |
| PBI fica bloqueado | Liberar sua vaga de PBI | Conservar trabalho, tentativas e bloqueio dos dependentes; execução incerta continua reservada |
| PBI bloqueado torna-se retomável | Revalidar e disputar vaga | Reabrir somente com DoR, dependências e capacidade válidos; preservar consumo anterior |
| Nenhum item elegível | Persistir espera | Registrar impedimentos observados e encerrar o ciclo; não chamar um modelo para escolher trabalho |
| Mesma operação é recebida após interrupção | Consultar a intenção e o resultado duráveis | Não duplicar reserva, tentativa ou despacho; incerteza exige reconciliação |

Entre PBIs ainda não iniciados e elegíveis, a ordem é a prioridade persistida da missão.
PBI bloqueado não autoriza alteração de escopo ou redução de critérios. Uma resposta de
agente não confirma integração; a evidência de integração deverá vir de YC-304.

## Proposta de ordem entre etapas e papéis

Política proposta para revisão: dar preferência a trabalho já iniciado, depois abrir
novos PBIs pela prioridade persistida. Essa preferência ainda não está definida na
especificação geral e não deve ser tratada como comportamento implementado.

1. Conferir missão, revisão, autorização, dependências, limites e capacidade do executor
   antes de escolher. Uma tarefa bloqueada não ganha preferência por estar esperando.
2. Reunir etapas elegíveis de continuação, correção, revisão técnica e QA, além de
   decisões de PM/Tech Lead exigidas por um evento concreto do trabalho em curso.
   Uma decisão dos líderes sem PBI consome vaga de execução, sem criar um PBI fictício.
3. Ordenar essas candidaturas pela sequência durável em que ficaram prontas, sem peso
   especial por papel. Cada etapa nova recebe sequência própria. Repetir o mesmo
   evento, alvo, revisão e papel conserva a candidatura e sua ordem; não cria outra.
4. Se não houver candidatura desse grupo elegível, escolher um PBI ainda não iniciado
   pela prioridade persistida da missão. Não é necessário terminar todos os PBIs ativos
   para admitir outro: basta respeitar as condições e os limites de capacidade.
5. Um PBI bloqueado que possa retomar volta como continuação, após revalidar o trabalho
   e adquirir novamente uma vaga de PBI. A espera preserva suas tentativas anteriores.
6. Não interromper execução válida para atender uma candidatura posterior. Antes de cada
   novo despacho, revalidar a revisão e as reservas. Um resultado de revisão antiga não
   autoriza a etapa seguinte da revisão atual.

Uma nova etapa de correção exige os critérios de YC-303; a política não cria tentativas
extras. Esperar integração ou aplicar uma integração mecânica não cria candidatura de
modelo. Conflitos ou decisões de produto seguem seus responsáveis e autorizações.
Chamadas aos líderes precisam de motivo e contexto; não servem para sondar se há trabalho.

| Caso proposto | Escolha esperada, se os demais requisitos estiverem válidos |
|---|---|
| Correção pronta na sequência 118, QA na 120, novo PBI com prioridade máxima | Correção 118; QA não perde a vez para uma nova etapa de correção registrada depois |
| Decisão necessária de PM pronta na sequência 117 e correção na 118 | Decisão 117, sujeita ao mesmo limite de execuções |
| Trabalho ativo aguarda dependência; há novo PBI elegível e vagas disponíveis | Novo PBI pela prioridade persistida |
| PBI bloqueado pode retomar, mas o limite de PBIs já está ocupado | Retomada aguarda vaga; outra candidatura elegível pode avançar |
| Mesmo evento de conclusão é entregue novamente | Mesma candidatura e ordem, sem segunda chamada |
| Todas as candidaturas estão impedidas | Persistir motivos e encerrar o ciclo sem chamada de modelo |

Os casos acima são critérios propostos, não testes executados. Continuidade constante
pode adiar novos PBIs até os limites da missão; a política não promete prazo máximo
de espera. Não há pesos, escalonamento por idade ou configuração adicional nesta proposta.

## Capacidade do executor

Os padrões de três PBIs e três execuções continuam sendo limites separados. A capacidade
comprovada do executor também precisa permitir o despacho. A reserva atual de
`scripts/mission_execution.py` admite uma operação por conta no fluxo isolado; configurar
três agentes não autoriza ignorar essa reserva nem promete três chamadas nativas simultâneas.

Não há transação única entre o SQLite do projeto e a reserva compartilhada da conta.
O desenho detalhado deverá definir intenção durável, aquisição, recusa e recuperação
entre essas fronteiras, reaproveitando YC-203. Uma reserva com efeito incerto não pode
ser liberada só porque o PBI saiu do limite de trabalho ativo.

## O que falta para um plano implementável

1. Após YC-203, fixar quais fatos comprovados do executor a fila pode consumir e como
   tratar uma reserva compartilhada ocupada ou incerta, sem escrever duas vezes após queda.
2. Definir o registro de tentativas da fila e suas transições no SQLite existente,
   com revisão esperada e recuperação entre intenção local e reserva da conta.
3. Revisar a preferência por trabalho iniciado e a ordem por sequência propostas acima.
   A prioridade aprovada dos PBIs não decide sozinha a disputa entre etapas e papéis.
4. Revisar o desenho e então elaborar o plano de implementação com provas de queda,
   concorrência e preservação. Esta matriz é uma entrada desse trabalho, não seu aceite.

## English overview

This draft refines YC-204 into observable queue decisions: dependency waits, separate
PBI/execution capacity, blocked-item release, reacquisition, empty queues and replay.
PM/Tech Lead proposals, worktrees and QA execution remain separate backlog items.
YC-203 acceptance remains mandatory before implementing 2B. The current account-wide
reservation allows one isolated operation; three configured agent slots do not override it.
The proposed dispatch order favors eligible ongoing work and necessary leader decisions,
ordered by their durable readiness sequence, before admitting new PBIs by saved priority.
Replayed events retain their candidate and order; new stages get new sequences. A resumed
blocked PBI must reacquire its PBI slot. Leader decisions without a PBI use an execution slot.
Blocked ongoing work does not prevent eligible new work when capacity exists. Six proposed
cases describe the policy, without claiming executed tests or bounded waiting for new PBIs.
Cross-store recovery, persisted transitions and this scheduling proposal still require a
reviewed design and implementation plan. No runtime behavior or execution gate changed.

ATRASO: YC-204 em refinamento | aceite do executor pendente.
