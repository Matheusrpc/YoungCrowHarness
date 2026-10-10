# Fila determinística com vários PBIs

Frente: YC-204, extensão serial do coordenador. Base: `71d3ae1`.

A fila agora percorre os PBIs de uma missão preparada. Mantém a prioridade congelada,
conclui o QA do item iniciado e escolhe o próximo cuja dependência terminou o ensaio
na mesma sessão. O CLI conserva `queue start`, `queue step`, `queue cancel` e `status`.
A continuação foi autorizada pelo mantenedor após a proposta deste incremento.

## Comportamento e limites

A sessão v2 guarda os PBIs, suas revisões, dependências e estados. O status apresenta
`items[].waiting_on` e o candidato atual. Com prioridade `[C, D, B, A]`, onde C depende
de B e B depende de A, o percurso observado é `D → A → B → C`, cada qual com Dev e QA.
O desenvolvimento sozinho não libera o dependente. O QA confere hash, identidade,
revisão e candidatura do desenvolvimento do PBI atual antes de avançar.

`dependency_basis: rehearsal_results` restringe essa resolução ao ensaio. A prévia
`initial_backlog` e os estados reais da missão permanecem independentes. Não há
integração, chamada de modelo, execução de agentes reais ou edição de worktree.
O limite é um PBI por vez; concorrência, decisões dos líderes, correções e reservas
nativas continuam nos respectivos itens do roadmap. Esta extensão não implementa
os seis critérios completos de múltiplas candidaturas da política aprovada.

O preparo já recusa ciclos e dependências ausentes. Um grafo válido sempre oferece
um próximo item ou termina; este recorte não cria um serviço de espera.

## Recuperação e compatibilidade

Resultado, transição do PBI, escolha seguinte e recibo continuam na mesma transação
SQLite. Cada candidatura inclui sessão, PBI, revisão e papel. Repetir a operação
recupera seu recibo original; revisão antiga e operação conflitante são recusadas.
Cancelar conserva resultados e estados individuais no histórico da sessão encerrada.

O esquema 4 usa as mesmas tabelas e impede que escritores antigos interpretem sessões
v2 como um único PBI. Status e replay exato não migram o banco. Novas escritas aceitas
fazem a migração; sessões v1 continuam com o comportamento original e os recibos antigos
permanecem intactos. Diagnósticos nativos e seus bloqueios continuam visíveis.
Atualizar `missions.py`, `mission_store.py`, `mission_runs.py` e `mission_queue.py` juntos.

## Evidência

- Antes da implementação, os testes novos recusaram vários PBIs e detectaram a ausência
  da barreira de compatibilidade: 18 testes, duas falhas e quatro erros esperados por
  funcionalidade ausente. A rodada anterior de 16 testes teve três recusas de escopo.
- Após a implementação, os 18 testes da fila passaram em 19,023 s. Incluem percurso
  por processos CLI separados, prioridade, dependências, cancelamento, replay,
  concorrência, recusa de QA com resultado de outro PBI e preservação de sessão v1.
- A prova de queda interrompe o processo depois do UPDATE e antes do recibo, inclusive
  durante QA → próximo PBI. Recuperação mantém o estado anterior; resposta perdida
  depois do commit recupera a única transição persistida.
- Os 23 testes de catálogo passaram em 1,766 s. Só os hashes de conteúdo mudaram;
  permissões, contratos e listas de arquivos das capacidades permanecem iguais.
- Instalação trial com ambos os perfis passou no CLI instalado: quatro PBIs, oito
  resultados, nove recibos e revisão 9, consulta sem escrita e replay idêntico.
  Os programas reais de `71d3ae1` recusaram leitura e escrita no esquema 4 com
  `invalid_store`, sem alterar o projeto.
- Revisão independente somente leitura: nenhum achado material. O revisor também
  retomou uma sessão v1 em QA criada pelo código antigo e conferiu seus recibos.
  Incorporar o código antigo à suíte permanente ficou como sugestão não bloqueadora;
  o teste versionado usa o contrato de sessão legada e a prova adicional ficou local.
- Suíte geral: 698 testes em 568,288 s; 677 aprovados, 20 pulados e uma falha em
  `test_deadline_reaps_descendants_in_the_existing_supervisor`, pela ausência de
  `helper.pid`. Os testes da fila passaram nessa rodada.
- A repetição instrumentada sem atraso artificial reproduziu a falha: supervisor
  encerrado com saída zero e árvore coletada, controlador recusando por prazo e
  registros apenas até `run_intent`. O helper ainda não havia sido registrado.
  Os arquivos desse percurso eram idênticos aos da base `71d3ae1`.
- O teste encurtava o prazo para 1,8 s; a reserva de um segundo do controlador
  deixava cerca de 800 ms para iniciar wrapper, controlador e launcher. A prova
  mostrou aproximadamente 639 ms entre o registro do dono e `run_intent`, antes
  dos gates e do descendente. Um caso adicional com atraso artificial de um segundo
  retornou `invalid_manifest`; não foi considerado reprodução da mesma falha.
- Correção restrita ao teste: remover três linhas que encurtavam o prazo e usar os
  5 s já padrão da fixture. O supervisor permanece com 6 s e as verificações de
  expiração, ausência de dispatch, presença do helper e coleta continuam iguais.
  Os 16 testes do controlador passaram depois da correção, em 18,316 s.
  Revisão independente da alteração sem achado material; o teste ainda depende
  da inicialização dentro do prazo, agora com margem maior.
- A suíte completa não foi repetida após essa mudança apenas no teste; o CI da
  revisão publicada executará novamente o conjunto completo. O resultado inicial
  com uma falha continua registrado.

Nenhuma chamada paga. Desenvolvimento e QA reais permanecem `not_started` e produção
`not_verified`. Os logs privados ficam fora do Git; hashes e resultados estão na
[medição](../medicoes/2026-10-10-queue-multi.json).

A base `71d3ae1` passou nos oito jobs, inclusive Windows, dos runs
[push 38016008023](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38016008023) e
[PR 38016011187](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38016011187).
A falha Windows de `6ff88e8` permanece histórica, sem causa estabelecida; não se atribui
sua correção a esta fila. Conferir o CI da revisão nova após publicar.

[Guia de uso](../USAGE.md#queue-rehearsal) ·
[Entrega anterior](2026-10-10-queue-rehearsal.md) ·
[Política completa de ordenação](../superpowers/specs/2026-10-09-queue-eligibility-refinement.md).

## English overview

The deterministic rehearsal now processes multiple PBIs serially. QA of the active
item precedes new development; frozen priority selects the next eligible PBI. Only
predecessors completed within this rehearsal satisfy its simulated dependencies.
The real mission and initial backlog preview remain unchanged.

Schema 4 prevents old writers from misinterpreting v2 sessions while retaining v1
sessions and exact receipt replay. Crash recovery includes the QA-to-next-PBI boundary.
The installed CLI completed four PBIs with eight results and nine receipts; no models
were called. The full local suite had one controller-fixture startup failure. Removing
its shortened deadline restored the existing fixture default; all 16 controller tests
then passed. The final full-suite result remains pending in CI. Native dispatch, concurrent scheduling, leader decisions, corrections,
worktrees and real delivery acceptance remain outside this increment.

ATRASO: suíte completa da revisão final a conferir no CI | aceite nativo pendente.
