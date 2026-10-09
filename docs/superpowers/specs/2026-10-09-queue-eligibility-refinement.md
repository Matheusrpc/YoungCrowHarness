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
3. Fixar a ordenação entre continuação, correção, revisão/QA e novos PBIs. A prioridade
   aprovada dos PBIs não resolve sozinha a disputa de todos os papéis por uma vaga.
4. Revisar o desenho e então elaborar o plano de implementação com provas de queda,
   concorrência e preservação. Esta matriz é uma entrada desse trabalho, não seu aceite.

## English overview

This draft refines YC-204 into observable queue decisions: dependency waits, separate
PBI/execution capacity, blocked-item release, reacquisition, empty queues and replay.
PM/Tech Lead proposals, worktrees and QA execution remain separate backlog items.
YC-203 acceptance remains mandatory before implementing 2B. The current account-wide
reservation allows one isolated operation; three configured agent slots do not override it.
Cross-store recovery, persisted transitions and scheduling among roles still need a reviewed
design and implementation plan. No runtime behavior or execution gate changed.

ATRASO: YC-204 em refinamento | aceite do executor pendente.
