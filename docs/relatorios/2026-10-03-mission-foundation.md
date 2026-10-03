# Fundação das missões

Frente: perfil, configuração e contrato da missão. Implementação na branch `feat/mission-foundation`.

## O que foi entregue

Quatro entradas compartilhadas, com adaptadores para Claude Code e Codex: `yc-personalizer`,
`yc-config`, `yc-missao` e `yc-status`. A personalizer reaproveita a entrevista e o baseline do trial.
PM e Tech Lead são papéis na sessão atual. O operador pode registrar modelos e esforço por agente,
refinar épicos/features/PBIs e preparar uma missão com uma ou mais features.

A configuração usa JSON; as notas e seus contratos ficam no vault; SQLite guarda revisões e eventos
privados. A missão congela escolhas e referências. Repetir uma operação conserva seu evento, e falhas
na projeção Markdown permitem recuperação. A consulta não repara nem inicializa o projeto.

Os limites declarados são três PBIs ativos, três agentes paralelos e três correções por padrão
(correções fixas nesta versão). Quatro PBIs totais cabem em uma missão. Modelos são escolhas ainda
sem prova de compatibilidade. Execução autônoma, branches de PBI, QA de produto e deploy aguardam
as próximas frentes; `prepared` mantém `runtime_available: false` e `runnable: false`.

## Provas e limites

[Medidas desta frente](../medicoes/2026-10-03-mission-foundation.json).
Os 32 testes de configuração/backlog/missões passaram; o caso adicional de helper antigo também.
Os três testes de instalação passaram com seleção Claude/Codex/both e preservação na migração.
Os 22 testes de capacidades passaram, com um skip de symlink sem privilégio no Windows.
Quatro avaliações de aplicação das referências passaram depois de corrigir lacunas nas instruções.
Elas não são conversas nativas com os clientes nem prova de uso dos modelos escolhidos.

Os diagramas PT/EN preservam paleta e tipografia dos processos existentes. XML válido, sem recursos
externos; renderização em 900 e 390 px sem estouro de texto. Inspeção visual feita e zero processos
próprios de navegador restantes. O README oferece abertura em tamanho completo para leitura ampliada.

A suíte anterior à alteração teve 256 testes, oito erros e dez skips no Windows: seis timeouts do
instalador, uma limitação de caminho da fixture de retorno e uma corrida na leitura do PID de teste.
O caso de preservação do guia passou isoladamente. Isso não é registrado como baseline verde.
O ensaio final e o CI ainda estão em andamento; resultados serão acrescentados antes do fechamento.

## Decisões de execução e detalhes adiados

- Ruling: reuse the existing exclusive checkout on a feature branch — approved inline workflow and no competing writer — cost if wrong: shared-checkout interference; no other writer will be dispatched.
- Ruling: use installed Git Bash through process-local PATH — bash is absent from current PATH — cost if wrong: test environment mismatch, recorded in evidence.
- Task 1 RED: six configuration tests failed on absent module. GREEN: six passed after implementation. Ruling: reuse capabilities.read_inputs/parse_json/canonical for bounded stable JSON reads — avoids duplicate security logic — cost if wrong: helper compatibility, tested at installation in task 4.
- Task 3: Ruling: batch record reads under a verified connection and initialize storage only for an absent database — repeated Git preflights dominated Windows runs — cost if wrong: reduced rechecks; transaction and read boundaries still verify paths and privacy.
- Task 3: Ruling: reads with no database return not_initialized even before personalization — status must be useful and read-only on a new checkout — cost if wrong: sidecars without a database need an explicit write preflight, which still rejects unsafe paths.
- Task 4 Ruling: author reference tests/entries while task-3 final checks run, with one writer and no installed setup/catalog changes until baseline ends — independent reference preparation — cost if wrong: test discovery overlap; task-3 run loaded its modules first and passed all 32 cases.
- Task 4 Ruling: add fixture FILES entries only when files exist — baseline should fail on actual installation assertions rather than missing fixture inputs — cost if wrong: a missing fixture dependency could be hidden; explicit missing-dependency test covers it.
- Final: minor (deferred): preexisting personalizer adoption.md wording mixes mechanism-only fields with general adoption planning; mission entry explicitly preserves the confirmed baseline.

## Publicação

PR, revisão independente e CI pendentes. Esta nota não afirma atualização da `main`.

ATRASO: main 1
