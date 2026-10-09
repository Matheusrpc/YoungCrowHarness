# Próxima ação no status da missão

Frente: preparação e consulta de missões, independente do executor nativo.

`yc-status` passa a indicar a revisão de uma operação pendente ou o reparo de uma
nota antes de recomendar refinamento. Antes, `next_action` considerava apenas fontes,
lacunas e disponibilidade do runtime, mesmo com recibo incerto ou projeção em conflito.
Também podia mostrar `check_available=true` quando um recibo de outra missão do
mesmo projeto já impedia um novo diagnóstico.

A consulta final de recibos inclui operações `reserved`, `running` e `uncertain`
do repositório. `blocking_runs` mostra seus identificadores, revisão, estado e
próxima ação; `client_runs` conserva somente os recibos da missão pedida. O status
prioriza operações abertas, projeções conflitantes/pendentes, fontes alteradas e
lacunas. Recibos integrados orientam revisão da recuperação específica, sem sugerir
o `client reconcile` legado que não pode encerrá-los.

`check_available=false` indica impedimentos conhecidos nesta consulta. O valor
`true` não autoriza execução nem comprova orçamento, cliente ou autenticação.
O [guia de uso](../USAGE.md#mission-workflow) descreve cada orientação.

Não há migração, novo módulo ou serviço. A consulta preserva arquivos, UUIDs,
contadores e estados; não observa processos nem tenta reparação. A leitura final
independente e o teto de nove processos Git permanecem. Dez hashes de conteúdo do
catálogo foram atualizados; contratos e permissões não mudaram.

## Verificação

Quatro regressões falharam antes da correção, todas por orientação incorreta.
Os 11 testes focados de status passaram depois. Cobrem recibos abertos da própria
missão e de outra, recuperação integrada, projeções, leitura sem escrita e as
verificações anteriores de armazenamento. A revisão independente não encontrou
achados bloqueantes e reproduziu seis testes focados.

A suíte completa executou 644 testes em 236,436 s: 624 aprovados e 20 pulados,
sem falhas ou erros. Os pulados mantêm os requisitos de Windows nativo ou grupo
secundário POSIX ausente; esta rodada ocorreu na cloud Linux.

O teste de adoção instalou o harness para ambos os clientes em projeto novo e em
projeto Git com trabalho existente. Nos dois casos, a CLI instalada identificou o
recibo incerto e manteve os arquivos do vault intactos durante a consulta. O percurso
também confirmou reconciliação, ausência de despacho repetido e retorno do trial.

A [medição](../medicoes/2026-10-08-mission-status-guidance.json) registra a suíte
completa, a prova do comando instalado, os hashes e seus limites. Os clientes nessa
prova são fixtures; não houve modelo, Docker/sbx ou novo ciclo nativo.

## Continuidade e retorno

A consulta ao Docker está em espera por pedido do mantenedor; a issue não foi
publicada. Esta entrega avança a preparação existente, sem liberar a fila 2B.
Perfis nativos continuam bloqueados, `proof_accepted=false`, com 2/3 ciclos usados.
Destino: `feat/isolated-executor`, PR #24; sem merge na main. Retorno por revert do
incremento documental e de consulta, sem apagar o estado privado nem repetir operações.

## English overview

Mission status now identifies unresolved repository runs and projection problems
before recommending input refinement. `blocking_runs` carries receipt identities,
revision, state and next action, including other missions in the same project.
`client_runs` stays mission-specific. Integrated receipts direct recovery review
instead of legacy reconciliation. Status remains read-only; availability is not
execution authorization or a substitute for manifest/preflight validation.

Four regressions reproduced incorrect guidance before the fix; 11 focused status
tests passed afterward. The full suite passed 624 tests with 20 skips. Installed-CLI
checks passed in new and existing projects for both client installations, using
client fixtures and no model calls. The Docker inquiry is on hold; native profiles
and the 2/3 cycle count remain.

ATRASO: main 1 frente sem aceite | aceite nativo pendente.
