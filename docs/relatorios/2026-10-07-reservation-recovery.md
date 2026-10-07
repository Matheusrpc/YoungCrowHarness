# Plano persistente e recuperação do executor

Frente: YC-203.4 e parte de YC-203.5, no PR #24.

O coordenador interno grava o plano A/B/A2 e os valores do baseline na reserva global
antes dos efeitos. A missão e a reserva guardam os mesmos IDs e hash do plano. O diário
impede repetição e as três fases compartilham o prazo admitido, até 120 segundos.
O setup distribui `mission_transaction.py` e preserva cópias locais existentes.

A recuperação tem prazo próprio de até 60 segundos. Confere o proprietário host,
identidade do contêiner, estado da carga, VM e configuração. O launcher grava intenção
antes de parar; após resposta perdida, observa o estado existente. Uma criação sem
resposta pode ser localizada pelo nome fixo e pela intenção protegida, seguida de
inspeção completa por CID. A recuperação nunca inicia uma VM parada para consultá-la.
A projeção na missão conserva tentativas e segundos reservados.

A revisão independente encontrou quatro falhas, reproduzidas e corrigidas:

- CID diferente do recibo preparado ou da observação anterior ao stop agora bloqueia encerramento.
- Reinício legítimo anterior do daemon é aceito; sua identidade precisa ficar estável durante a recuperação.
- Tentativas recusadas sem progresso não esgotam o histórico necessário ao encerramento.
- O adaptador recebe o prazo do coordenador e não pode estendê-lo ao executar comandos.

Os dois revisores confirmaram as correções. Passaram 76 testes focados de transação,
launcher e adaptador. Instalação: 61 aprovados e dois pulados; catálogo: 23 aprovados.
A suíte do código público exportado passou: **567 testes, 547 aprovados e 20 pulados**,
zero falhas/erros em 233,921 s. Os skips cobrem 19 casos Windows e um que exige grupo
secundário POSIX. Depois, a fixture de ACL foi delimitada à Registry temporária no
Windows, no pai e no worker, preservando lock, escrita atômica, SQLite e supervisor
reais. Os 23 testes transacionais passaram novamente em 5,130 s; a fronteira da fixture
também passou em um probe local. Fontes de produto permanecem idênticas às da suíte.
Isso não é execução Windows nativa. Consulte [a medição](../medicoes/2026-10-07-reservation-recovery.json).

## Limites e próxima task

**203.4 implementada internamente; 203.5 parcial.** As fixtures usam processos,
ledger e banco reais, com a fronteira Docker simulada. A fase B continua
`blocked_unattributed`; `proof_accepted=false`. `client check` permanece em
`failed/controller_pending`, os perfis nativos continuam vazios e registros v1
consumidos permanecem bloqueados.

Próxima task: **203.6**, integrar filtro de saída, configurações globais, credencial
fictícia e políticas com as intenções do plano. Incluir identidades de helpers/portas
e restaurar somente alterações ainda próprias para completar 203.5. O resolvedor de
DNS deve herdar a contenção existente, sem um segundo supervisor dentro do controlador.
Depois vêm pacote exato, A/B/A2 nativo, ambos os clientes por assinatura e adoção.

A cloud não executou Docker nem modelos. Permanecem dois ciclos nativos usados de
três. A sintaxe de `sbx exec` e `sbx stop` foi consultada em `docker/docs`, commit
`7ba25eeb0c4c594f79e6efadad1af5eaca0500a8`, arquivos
[sbx_exec.yaml](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_exec.yaml)
e [sbx_stop.yaml](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_stop.yaml). Essa fonte documenta argumentos; não comprova execução em sbx 0.46.0.

README PT/EN, guia, backlog e handoff acompanham o incremento. Publicação e consulta
final das refs estão pendentes. O último acesso à API do GitHub retornou `Forbidden`;
o resultado do CI permanece não verificado. Não houve merge, deploy ou mudança na main.

ATRASO: main 1 frente sem aceite | PR #24 1 incremento pendente de publicação | aceite nativo pendente.
