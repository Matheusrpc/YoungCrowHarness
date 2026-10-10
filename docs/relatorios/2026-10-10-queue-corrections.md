# QA reprovado e correções limitadas no ensaio

Frente: YC-204, continuação do ensaio serial autorizado. Base: `00cd0df`.

O coordenador trata reprovação de QA dentro da sessão determinística. A implementação
inicial pode receber até três correções. O contador aumenta quando `step` despacha a
correção simulada; a reprovação apenas agenda essa etapa. Cada correção inclui seu QA.
Reinício, replay e queda transacional conservam o contador e os resultados confirmados.

`queue start --fixture-scenario` aceita `pass`, `qa-retry` ou `qa-exhaust`. O cenário e
o primeiro PBI elegível ficam congelados; os demais PBIs passam no primeiro QA.
Essa entrada fechada permite provar reprovação, recuperação e esgotamento sem modelos.

Depois da terceira correção reprovada, o item fica `blocked`. Seus dependentes continuam
pendentes; os independentes seguem a prioridade salva. Se restar trabalho sem candidato
elegível, a sessão persiste `waiting`. Ela ocupa a vaga única e permite cancelamento,
mas recusa novos avanços. Não há processo suspenso durante a espera.

## Persistência e compatibilidade

Sessões novas usam formato v3. O banco privado migra para esquema 5 na primeira nova
escrita aceita; a migração ajusta o índice de sessão ativa e conserva as tabelas.
Leituras e replay exato não migram. Sessões v1/v2 mantêm comportamento, candidatos,
resultados e recibos. Atualizar `missions.py`, `mission_queue.py`, `mission_store.py`
e `mission_runs.py` juntos. Escritores anteriores recusam o banco migrado.

A candidatura distingue PBI, revisão, papel e ciclo. O QA confere o resultado do
desenvolvedor da tentativa atual; um resultado válido de tentativa anterior é recusado.
O contador e o resultado da fixture pura são confirmados na mesma transação que o recibo.
Diagnósticos nativos abertos continuam visíveis e impedem avanços.

## Provas

- Antes da implementação, a bateria com os seis novos casos terminou com cinco falhas
  e um erro pela ausência do cenário no CLI/API; os 18 casos anteriores passaram.
- Bateria final da fila: 25 testes aprovados em 21,623 s. Inclui concorrência na correção,
  rollback antes do commit, perda do ACK, esgotamento e bloqueio de uma segunda missão.
  A asserção da restrição SQLite foi colocada dentro da transação para observar o erro
  `UNIQUE`, antes da conversão existente do armazenamento para `invalid_store`.
- Catálogo: 23 testes aprovados em 2,345 s. Dez hashes de conteúdo atualizados;
  contratos, permissões e listas de arquivos preservados.
- CLI instalado em modo trial, para os dois clientes: `qa-retry` concluiu quatro PBIs
  com uma correção, dez resultados e onze recibos. `qa-exhaust` bloqueou o primeiro PBI
  após três correções, concluiu o independente e persistiu espera para os dependentes,
  também com dez resultados e onze recibos. Replay idêntico e status sem escrita.
- Sessões reais criadas pelos códigos `71d3ae1` (v1) e `00cd0df` (v2) retomaram em QA
  pelo CLI instalado novo. Recibos originais preservados; leitores/escritores antigos
  recusaram esquema 5 sem modificar o projeto.
- Revisão independente, somente leitura: nenhum achado material. Comparação em memória
  de 192 resultados v2 e dois resultados v1 idênticos à base; migrações 1/2/3/4 para 5
  idempotentes e recusadas pelo validador antigo.
- Suíte local completa: 705 testes em 397.901 s, 685 aprovados e 20 pulados
  por requisitos de ambiente/plataforma; zero falhas.

Medição estruturada: [queue-corrections](../medicoes/2026-10-10-queue-corrections.json).
Uso e estados: [guia da fila](../USAGE.md#queue-rehearsal).

## Limites

O contador pertence a uma sessão sintética. Novos ensaios são independentes. Não há
ledger real de autocorreção entre missões, revisões ou IDs, tratamento de falha de
provedor como defeito, notificação de líderes ou despacho de agentes. YC-303 permanece
pendente. O incremento não altera worktrees, código de consumidores, aceites reais,
credenciais ou produção. Zero chamadas de modelo e nenhuma nova tentativa Docker.

O CI da base passou nos oito checks de push/PR, inclusive Windows. Conferir os checks
do novo commit separadamente. Publicação limitada à branch e ao PR #24 em rascunho.

## English overview

The serial rehearsal now covers rejected QA, one successful correction and exhaustion
of three corrections. The closed scenario applies to the first eligible PBI; other
items pass initial QA. Counts increase at pure fixture correction dispatch and survive
restart, replay and transactional crashes within the same session. Exhaustion blocks
the PBI, preserves dependent waits and lets independent PBIs proceed. No eligible work
persists `waiting`, which holds the active slot and accepts cancel but not step.

New sessions use v3 and accepted writes migrate SQLite to schema 5. Existing v1/v2
sessions and exact receipts remain compatible; old writers refuse the new store.
The installed CLI proved both scenarios and resumed sessions created by both old
implementations. Real development/QA/production states were unchanged. Real correction
accounting across missions, revisions and IDs remains YC-303 roadmap work.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
