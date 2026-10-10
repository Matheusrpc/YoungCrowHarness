# Prévia inicial do backlog da missão

Frente: preparação antecipada de YC-204. Base: `6d6d7a5`.

O mantenedor autorizou adiantar a parte que não depende do executor. `status` agora
retorna `queue_preview`, com os PBIs na prioridade salva, código, título, revisão e
UUIDs das dependências. O primeiro candidato é o primeiro item sem dependências,
somente quando a preparação está consistente. A leitura reutiliza o snapshot e as
checagens existentes, sem schema, comando ou acesso adicional ao ambiente.

A regressão com quatro PBIs coloca o item de maior prioridade à espera de uma cadeia
de dependências. A prévia aponta outro PBI independente, conforme a prioridade da
missão, e acompanha sua revisão. Gaps, fontes alteradas, projeções pendentes/conflitantes
e recibos abertos, inclusive de outra missão, deixam o candidato nulo.

## Limites

O escopo é `initial_backlog`: nenhum PBI é presumido integrado. Os dados atuais não
registram ocupação de vagas ou prontidão de etapas. A sequência de importação não
é usada como FIFO. Continuação, correção, QA e decisões dos líderes preservam a
política aprovada para implementação futura; esta prévia não a executa.
`runtime_available=false`, `runnable=false` e a orientação de `next_action` permanecem.
Não houve despacho, Docker/sbx ou inferência pelos clientes nativos; contador 2/3,
`proof_accepted=false`. O aceite de YC-203 continua necessário para o despacho de 2B.

## Verificação

Três regressões novas e duas ampliadas falharam por ausência do campo antes da
implementação e passaram depois. O smoke instalado passou em consumidores novo e
existente, com entradas para Claude e Codex, conferindo prévia, preservação e bloqueio
com projeção pendente. Isso não comprova uma conversa nos clientes nativos.
A suíte completa executou 651 testes em 322,429 s: 631 aprovados e 20 pulados,
sem falhas ou erros. O smoke instalado levou 18,423 s. As provas locais usam Linux;
CI desta revisão e aceites nativos permanecem separados.

O catálogo recebeu dez hashes de conteúdo atualizados, com contratos e permissões
preservados. Revisão independente de código e documentação sem achados materiais.
Veja os comandos, resultados e hashes na [medição](../medicoes/2026-10-09-queue-preview.json).

## Publicação e CI conferidos

O commit `a0af931b8200c3b1c9416e0eba395ed3a5791016` está publicado no PR #24.
O [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37884519194)
e o [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37884523562)
concluíram com sucesso os quatro jobs: `installer`, `public-pilot`,
`adoption-windows` e `graphify-smoke`. A API confirmou oito jobs aprovados em 9/out.

Isso encerra a espera pelo CI desta entrega. Os timeouts Windows de revisões
anteriores permanecem no histórico, sem causa final comprovada; não constituem
falha atual reproduzida. O aceite nativo continua pendente. Na consulta de 9/out,
a issue Docker #690 permanecia aberta e sem comentários. A próxima entrega do
executor depende de evidência aplicável ao contrato local; a prova de memória no
Claude mantém o horário combinado, 10/out às 18h30 em America/Sao_Paulo.

## Visão posterior registrada

O pedido adicional está no [YC-X05](../BACKLOG.md#yc-x05-aviário-da-squad-e-cockpit-local):
front local com pássaros representando agentes e passagens de demanda entre baias,
cockpit do vault e métricas medidas por épico, feature e PBI. Desenho e implementação
ficam para depois de todo o roadmap principal. Nenhum front ou componente gráfico
foi implementado neste incremento.

## English overview

Mission status now exposes an initial backlog preview from its frozen snapshot.
Saved priority and dependencies identify the first initial candidate only when
preparation is current. No integration, available slots or ongoing-stage ordering
are inferred. Native execution gates remain unchanged. YC-X05 records a future
local bird-mascot squad cockpit, deferred until the complete core roadmap is delivered.
Commit `a0af931` passed all four CI jobs on both push and PR, including Windows.
Earlier timeouts remain historical observations with no final established cause;
native acceptance and the local Docker contract remain pending.

ATRASO: PR #24 publicado | CI de a0af931 aprovado | aceite nativo pendente | YC-X05 após roadmap.
