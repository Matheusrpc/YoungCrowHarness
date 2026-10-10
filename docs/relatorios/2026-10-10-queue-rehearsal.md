# Coordenador persistente de um PBI

Frente: YC-204 antecipado com executor determinístico. Base: `6ff88e8`.

O mantenedor autorizou antecipar este recorte antes do aceite nativo de YC-203.
O CLI agora inicia, avança e cancela uma sessão de ensaio; o status consulta
etapa, próximo papel, bloqueios e recibos. Uma missão preparada com um PBI sem
dependências percorre `dev_pending`, `qa_pending` e `fixture_completed`.

O executor calcula dados determinísticos no SQLite. O QA simulado confere o hash
do resultado anterior. Não há chamada de modelo, edição de código de projeto,
worktree, aprovação de QA real, integração ou publicação de aplicação.
Desenvolvimento e produção da missão mantêm o estado anterior ao ensaio.

## Persistência e retomada

Sessões e eventos ocupam duas tabelas no banco privado existente. O esquema 3
preserva diagnósticos dos clientes e suas reservas; consultas aceitam os esquemas
anteriores e não fazem migração. Helpers incompatíveis são recusados, inclusive
quando uma instalação preservou `mission_runs.py` antigo.

Cada comando de escrita leva revisão esperada e UUID de operação. A repetição do
mesmo pedido retorna seu recibo original. Operação com conteúdo diferente, revisão
antiga ou outra sessão ativa é recusada. O cancelamento preserva resultados e
continua disponível se a missão original foi revisada.

O teste de queda encerra outro processo antes do cálculo, depois de atualizar a
sessão mas antes de inserir seu recibo, e depois do commit com resposta perdida.
Após recuperação, o caso intermediário conserva revisão 1, zero resultados e um
evento; retry e replay terminam em revisão 2, um resultado e dois eventos.
Um cálculo puro pode ser repetido antes do commit. Esta prova não certifica
execução externa exatamente uma vez.

## Verificação

- Primeiro red: 11 testes falharam porque o coordenador ainda não existia.
- Os 77 testes focados de fila, missões e recibos passaram em 66,818 s.
- Os 13 testes finais de fila, incluindo a queda após escrita SQL, passaram em 6,701 s.
- Uma regressão existente detectou 12 consultas Git no status, acima do limite de 9.
  A leitura da fila passou a usar a conexão existente; o limite e a releitura final
  dos recibos nativos foram preservados e passaram na rodada de 77 testes.
- A verificação de QA recusando hash corrompido falhou antes da implementação e passou depois.
- O catálogo inclui o novo helper e os hashes dos cinco conjuntos afetados; permissões
  de clientes, rede e credenciais permanecem. O teste detectou o catálogo desatualizado
  na primeira rodada geral; o hash legado de personalizer também foi corrigido.
- Instalação trial em projeto temporário com ambos os perfis passou no CLI instalado:
  estados dev/QA/conclusão sintéticos, 3 eventos, 2 resultados e replay idêntico.
  Os primeiros arranjos da fixture foram recusados por destino aninhado, backup dentro
  de Git e volumes distintos; o ensaio passou com projeto, fonte e backup separados
  no mesmo volume. Nenhum controle do instalador foi alterado.
- Catálogo final: 23 testes passaram em 3,623 s.
- Revisão independente somente leitura sem defeito funcional ou complexidade material.
  A sugestão de fortalecer a prova de queda entre escritas foi incorporada ao teste.

Suíte geral final: 693 testes em 423,028 s; 673 aprovados, 20 pulados por condições
de ambiente e nenhuma falha. A primeira rodada teve uma falha de catálogo, corrigida
antes desta execução. Recibos e hashes constam na medição desta entrega.

[Uso e migração](../USAGE.md#queue-rehearsal) ·
[Desenho](../superpowers/specs/2026-10-10-queue-rehearsal-design.md) ·
[Plano](../superpowers/plans/2026-10-10-queue-rehearsal.md) ·
[Medição](../medicoes/2026-10-10-queue-rehearsal.json).

## CI anterior e publicação

O commit base `6ff88e8` passou em sete dos oito jobs de push/PR. O job Windows de
[push 38013775494](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38013775494/job/114099458431)
falhou em `test_mission_controller.ControllerTests.test_deadline_reaps_descendants_in_the_existing_supervisor`.
O Windows do PR passou. As anotações identificam o teste, mas não a causa; essa
falha anterior não foi corrigida pelo coordenador e permanece registrada.
O CI da nova publicação precisa ser observado na revisão correspondente.

## English overview

The existing CLI now coordinates a persistent single-PBI deterministic rehearsal.
Start, step and cancel commands use operation receipts and expected revisions;
status shows the current stage, role, blockers and history. Synthetic completion
never grants real development, QA, integration or production acceptance.

Schema 3 retains existing native diagnostics and their blockers. Process-crash
checks cover a partial SQL update before its event and a lost reply after commit;
replay retains one logical result. Pure computation may repeat before commit.
Native dispatch and external exactly-once execution remain unproven. Multi-PBI
scheduling, worktrees, real agents and release remain separate roadmap work.

ATRASO: CI da nova revisão a conferir após publicação | aceite nativo YC-203 pendente.
