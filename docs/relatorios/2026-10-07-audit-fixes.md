# Correções da auditoria: recuperação e diagnóstico

Frente: AUD-01, AUD-02 e PR24-F2, antes da integração 203.4/203.5.

Os três defeitos reproduzidos foram corrigidos com regressões locais e revisão
independente. Notas interrompidas de missão/backlog se recuperam mesmo após outra
revisão. Respostas inválidas dos clientes e falhas de Git na primeira leitura do
ambiente conservam o contrato JSON sanitizado.

Base do checkout: `b801bec963e8af4af921b8c5473d3884ee5a7a03`,
[PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24). O incremento anterior
de admissão/controlador e as evidências históricas foram preservados. As correções
permanecem locais; não houve commit, push ou merge.

## Causa e correção

| Achado | Causa | Comportamento corrigido |
|---|---|---|
| AUD-01 | O Markdown podia ser gravado antes do commit de seu hash; uma nova revisão fazia o arquivo legítimo parecer edição humana | Reconstrói os bytes pelos eventos duráveis do mesmo registro, posteriores à última projeção confirmada. Conserva a revisão atual e recupera inclusive conflitos deixados pelo código anterior |
| AUD-02 | A descoberta acessava objetos aninhados e membros de listas antes de validar o tipo | Valida envelopes e listas de esforços na fronteira compartilhada; recusa com `client_protocol_error` e mantém catálogos válidos, aliases e opcionais existentes |
| PR24-F2 | A primeira leitura chamava a consulta Git fora da conversão já usada pelo armazenamento existente | Aplica a mesma classificação nesse caminho, incluindo `git_boundary/git_query_timeout`, sem criar arquivos ou exigir configuração nova |

AUD-01 não exige migração do SQLite nem tabela adicional: os eventos de missão e
backlog já contêm retratos completos. A recuperação histórica só alcança a nota
agregada. Notas de eventos exigem os bytes esperados; edições humanas e restauração
manual de versões antigas confirmadas continuam em conflito. Não são alterados
eventos operacionais, reservas consumidas, limites ou execução de processos.

`project_run` usa eventos com deltas; sua recuperação histórica não foi ampliada.
O teste de reserva comprova que reparar missão preserva `agent_runs`, seus eventos,
projeções, UUID e segundos reservados. Ele não certifica recuperação de notas de runs.

PR24-F1, criação privada do lock POSIX, já havia sido tratado no
[incremento anterior](2026-10-07-synthetic-admission.md). Os quatro achados confirmados
das auditorias têm correção local; o aceite integrado do executor continua pendente.

## Evidências

As regressões falharam antes das correções:

- Catálogos/envelopes malformados: três falhas e 13 erros em subcasos, incluindo
  `supportedReasoningEfforts: [null]`, `result: null` e respostas Claude nulas.
- Primeira consulta Git: timeout escapava da CLI; erro de I/O recebia classificação
  diferente da consulta com armazenamento existente.
- Projeções: falharam escrita inicial interrompida, revisão posterior interrompida,
  importação de item, interrupção durante repair e preservação da reserva na recuperação.

Depois das correções, os testes focados passaram. Cobrem também relógio regressivo,
reparo repetido, replay com o mesmo evento, conflitos legados, texto humano, retorno
manual à revisão confirmada, campos opcionais ausentes, stdout JSON único, stderr
vazio, ausência do marcador privado e projeto sem alterações durante diagnóstico.

Comandos de validação:

```bash
python3 -B -m unittest discover -s tests -p 'test_mission_clients.py' -v
python3 -B -m unittest discover -s tests -p 'test_execution_storage_diagnostics.py' -v
python3 -B -m unittest discover -s tests -p 'test_missions.py' -v
python3 -B -m unittest discover -s tests -v
bash -n setup.sh
git diff --check
python3 -B scripts/vault.py --json check
```

Suíte completa: **536 testes, 516 aprovados, 20 pulados, zero falhas/erros em 234,694s**.
Foram acrescentados 12 testes. As provas de recuperação usam arquivos e SQLite reais,
com falhas injetadas nas fronteiras de gravação; diagnósticos usam respostas externas
substituídas. Resultados e hashes: [medição](../medicoes/2026-10-07-audit-fixes.json).
Logs e snapshots anteriores ficam em `.runtime/audit-fixes-20261007/`.

Dois revisores independentes não encontraram pendências nas correções. A revisão de
projeções também criou o conflito com a implementação anterior e o reparou com a nova,
preservando os dois eventos. A revisão de diagnóstico executou 23 testes de clientes
e dez de armazenamento: 31 passaram e dois específicos de Windows foram pulados.

Os dez hashes de conteúdo das cinco capacidades afetadas foram atualizados.
Contratos, dependências e permissões permanecem iguais neste incremento. README PT/EN,
guia, backlog, handoff e memória local refletem as correções.

## Limites e continuidade

Não houve operação Docker, inferência externa ou nova prova nativa. Perfis permanecem
bloqueados; o contador conserva dois dos três ciclos nativos usados. Esta cloud não
tem `sbx`/KVM. O anexo de backlog informa CI verde do checkpoint em dois runs; a API
não foi verificada novamente e esse resultado não cobre o incremento local.

Próximo: 203.4/203.5, plano imutável A/B/A2 e baseline restaurável vinculados à missão
e à reserva global, com controlador e recuperação no mesmo fluxo antes de efeitos.
Depois vêm egress, imagem exata, provas nativas e clientes autenticados.

## English overview

Three audited defects are fixed locally: interrupted mission/backlog projections
recover across later revisions; malformed model catalogs and nested discovery replies
return structured JSON errors; the initial environment query sanitizes Git failures.
Historical recovery only accepts exact unconfirmed projections of the same record,
preserving human edits, confirmed-version rollbacks and consumed run reservations.
There is no database migration or extension to historical client-run note recovery.

Regressions and independent review cover the changes. Content hashes were refreshed
without changing contracts or permissions. Native executor acceptance, publication,
global reservation and verified recovery integration remain pending.

ATRASO: main 1 frente sem aceite | PR #24 correções locais não publicadas.
