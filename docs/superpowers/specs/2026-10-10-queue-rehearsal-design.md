# YC-204: coordenador persistente com executor determinístico

Frente: antecipação de YC-204 autorizada pelo mantenedor em 10/out/2026, após
o panorama do produto. Este recorte altera a sequência de desenvolvimento;
o aceite de YC-203 continua obrigatório para despacho nativo.

## Resultado observável

Uma missão preparada, com exatamente um PBI sem dependências, tem uma sessão
de ensaio persistente. O operador inicia, avança e consulta essa sessão pelo
CLI existente. Desenvolvimento e QA são etapas simuladas; nenhuma resposta de
modelo, alteração de código, aprovação real ou integração é inferida.

`queue start M001 --expected-revision 1 --operation-id UUID --actor-id operador`
congela a identidade/revisão da missão e do PBI. Retorna uma sessão com UUID,
revisão operacional 1 e estado `dev_pending`. `queue step UUID` usa a revisão
operacional esperada e outro UUID de operação; grava o resultado determinístico
do desenvolvimento e passa a `qa_pending`. Outro avanço verifica esse resultado
na fixture e termina em `fixture_completed`. Cada comando termina; não há daemon.

O status da missão inclui `queue_sessions`, com escopo `deterministic_rehearsal`,
etapa, próximo papel, recibos e próxima ação. A consulta é somente leitura.
Os campos de desenvolvimento, QA e produção reais permanecem sem conclusão;
`runtime_available` e `runnable` continuam falsos.

## Persistência e recuperação

Reutilizar SQLite, `mission_store.transaction`, validação de identidade e
canonicalização existentes. Duas tabelas: sessões e eventos da fila. O esquema
3 preserva os diagnósticos existentes do esquema 2; leituras aceitam 1/2/3 e
nunca migram. A migração ocorre na primeira escrita explícita da fila.

Uma operação UUID com o mesmo pedido retorna o recibo original. Reutilizar o UUID
com outro pedido ou usar revisão antiga é conflito. Resultado puro da fixture,
transição e recibo são gravados na mesma transação. Queda antes do commit pode
repetir cálculo puro; não duplica resultado persistido. Queda depois do commit
recupera o recibo. Isso não prova execução externa exatamente uma vez.

Uma sessão ativa por repositório e uma sessão por revisão da missão. `queue cancel`
encerra somente o ensaio e preserva eventos, inclusive quando a missão mudou.
Começar outro ensaio da mesma missão exige uma nova revisão explícita.
Missão/referências alteradas, projeção em conflito, lacunas e diagnóstico nativo
pendente impedem novos avanços. Cancelar não altera diagnósticos nem libera recursos
de execução nativa. Sessões antigas continuam consultáveis após revisão da missão.

## Limites deliberados

O executor é uma função fechada, pura e determinística: produz dados no SQLite,
sem processo, arquivo de trabalho, rede, login ou gasto. Não aceita executável,
plugin ou backend escolhido pelo usuário. Isso permite provar o coordenador
sem transformar o ensaio em um desvio dos gates nativos.

Ordenação de vários PBIs, worktrees, agentes reais, transferência, integração e
release permanecem nos itens correspondentes do roadmap. A prévia inicial da
fila conserva seu contrato; resultado sintético não satisfaz dependências.

## Aceite

- Percurso completo pelo CLI, status consultável e nenhuma conclusão real inventada.
- Replay, conflito de operação/revisão e concorrência preservam uma única transição.
- Queda de processo antes/depois do commit retoma a sessão e preserva seus recibos.
- Recusas por escopo, estado alterado e diagnóstico pendente; cancelamento recuperável.
- Migração mantém diagnósticos e seu bloqueio, instalação distribui o helper novo.
- Nenhuma chamada de modelo ou mudança no aceite do executor nativo.
