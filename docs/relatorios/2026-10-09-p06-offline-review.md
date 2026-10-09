# P06: memória Claude confirmada por reavaliação offline

Frente: YC-010/P06, retomada do piloto público no Claude. Base desta correção:
`f3374622eaf1790d7ae97e7411bf279b5489ed33`.

A sessão real enviada pelo operador recuperou a memória. O verificador original
recusou a navegação, mas a auditoria do pacote completo confirmou a evidência.
A correção passou sobre os mesmos eventos e arquivos, seguida de revisão semântica.
**P06 está verificado no piloto, sem nova chamada ao Claude.** O recibo original
continua `failed / missing_memory_navigation`; o aceite desta reavaliação é separado.

## Origem e preservação

O operador forneceu `p06-auditoria-20261009-194520.zip`, 83.548 bytes, SHA-256
`f66667f784b0e9ce15357733d479e858877badd8fe2b2ed64a8ab06807990c74`.
Os 34 arquivos extraídos incluem contexto, setup, recibos de preparo/execução e eventos.
Os 30 arquivos do contexto coincidem com os hashes registrados em `setup.before`.
Todos os 34 arquivos permaneceram byte a byte iguais após a reavaliação.
Eventos completos e contexto recebido ficam privados; os hashes e resultados estão
na [medição](../medicoes/2026-10-09-p06-offline-review.json).

A prova é um artefato fornecido pelo operador, não uma nova execução Windows observada
pela cloud. A reavaliação corrigida rodou em Linux sobre os bytes originais Windows,
incluindo as terminações CRLF. A cópia atual das notas do exemplo foi atualizada
separadamente; não substitui o snapshot usado como prova.

## Sessão nativa observada nos registros

| Campo | Evidência |
|---|---|
| Operação | `164e5438-0cac-4089-845c-f1e3cc60db04` |
| Revisão preparada | `47a81504deeafe59920036d3cf39a422a7317f81` |
| SHA-256 do setup | `45ec8706433bbe3866c17d79d963df7e3617eaaf224ca15f4c27a24e87ea8ac4` |
| Cliente/modelo | Claude Code 2.1.220; `claude-haiku-5-5`, assinatura existente |
| Janela UTC | 9/out, 22:26:46.478812 a 22:27:25.830582 |
| Limite/uso | 300 s e 24 ferramentas; 39,351451 s e 18 ferramentas |
| Sessões/prompts | Uma sessão e um prompt; nenhuma repetição nesta auditoria |
| Ferramentas | 12 Read, 4 Glob, 1 Grep, 1 Bash; admissões, conclusões e resultados conciliados |
| Saída/limpeza | Saída 0, árvore encerrada, credencial temporária removida, bytes do login original preservados |
| Resposta Claude | `subtype: success`, `is_error: false` |
| Recibo original | `failed / missing_memory_navigation`, preservado |

Os contadores reportam 14 tokens de entrada, 29.691 de criação de cache,
99.660 de leitura de cache e 6.939 de saída. Isso confirma atividade de inferência;
não determina o valor cobrado ou a contabilização da assinatura.

## Correção limitada ao verificador

A navegação foi recusada porque as skills foram lidas em `.claude/skills/`, enquanto
o verificador exigia `skills/`, e porque a identidade foi consultada por Grep com
hash, sem Read completo de `project.json`. Depois desse gate, o parser também
recusaria o JSON final cercado por Markdown.

A função `verify` agora reconhece os três casos, com limites explícitos:

- Espelhos das três skills obrigatórias só contam se o caminho for conhecido e o
  hash coincidir com o da cópia canônica no snapshot conferido.
- A identidade por Grep exige modo `content`, linhas numeradas, caminho, número e
  conteúdo completos iguais à linha real de `vault/project.json`, mais o SHA-256
  completo do arquivo na saída da ferramenta. Isso prova o campo, não um Read inteiro.
- O resultado admite JSON puro ou uma única cerca `json` completa. A cerca foi um
  desvio do pedido original de JSON puro; a normalização é registrada. Texto extra,
  outros rótulos e múltiplos blocos continuam recusados.

`verification_details` revela os caminhos dos espelhos, `grep_with_hash` e
`json_code_fence`. Os controles de admissão, prazo, reserva, autenticação e prompt
não foram alterados. Nenhum evento, resposta ou recibo recebido foi reescrito.
O estado automático continua `evidence_verified_pending_semantic_review`.

## Revisão do conteúdo

O executor e um revisor independente somente leitura confrontaram a resposta com
as notas originais. Projeto, feature e seis UUIDs/hashes citados conferem. O texto
recupera a decisão por site estático, distingue implementação real dos estados
fictícios do quadro e atribui a produção à observação histórica registrada em 3/out.
Não afirma ter visitado o site nesta sessão.

O cliente também identifica que `native-memory.md` era um retrato anterior à nota
de operação. A ação de renovar OAuth veio desse retrato congelado; não é instrução
atual nem motivo para repetir o teste. As notas atuais do exemplo foram reconciliadas
para conservar a história e apontar o aceite P06.

A leitura das skills foi manual. `p06_initialized.skills` é uma lista vazia;
esta prova não demonstra descoberta automática, aplicação das quatro skills de
YC-011, refresh OAuth ou aceite dos clientes dentro do executor Docker (YC-203).
O revisor também conferiu o diff do verificador e suas regressões, sem impedimentos.

## Validação

As três regressões novas falharam antes da correção: 20 testes, três falhas,
zero erros, em 3,432 s. A exigência adicional de modo de busca/linhas numeradas
teve dois subcasos vermelhos antes de sua correção. A suíte focada então passou:
20 testes em 3,140 s.

A suíte completa executou 671 testes: **651 aprovados, 20 pulados, zero falhas**,
em 337,515 s. Após atualizar as notas usadas pelas fixtures, a suíte focada e os
validadores dos dois vaults foram executados novamente; resultados na medição.
O pacote Pages não inclui essas notas; não houve deploy nem nova observação do site.
A execução nativa Windows acima usou o verificador antigo. O CI da revisão corrigida
é uma validação separada, não uma nova inferência Claude.

## Continuidade / English

P06 is verified through offline re-evaluation of the operator's real Haiku session,
followed by independent semantic review. The original failed receipt and all input
bytes are preserved. Known byte-identical skill mirrors, an exact sourced identity
line plus its hash, and one JSON code fence are disclosed normalization cases.
No new model call, automatic skill discovery proof or Docker acceptance is implied.

Preservar os pacotes consumidos e seguir os aceites próprios de YC-011/YC-203.
A [campanha](../TEST-RUN-2026-10-10.md) não ganha outra tentativa com este aceite.

ATRASO: P06 0 | YC-011 pendente | executor Docker bloqueado.
