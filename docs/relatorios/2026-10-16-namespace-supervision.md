# Supervisão dos grupos de processos do Codex

> Registro histórico recuperado em 17/out/2026. Os números abaixo pertencem à sessão
> original. Os arquivos JSON daquela sessão não foram recuperados; veja as
> [provas atuais e os limites da recuperação](2026-10-17-codex-workspace.md).

Frente: YC-203, compatibilidade da supervisão `isolated-tools`. Base `f55155d`,
com alterações anteriores do checkout preservadas. Este incremento atende ao próximo
corte do [relatório dos clientes](2026-10-12-tool-client-acceptance.md).

O Codex oficial 0.159.2 agora inicia o transporte e apresenta as ferramentas sob o
supervisor. Antes, `process_group(0)` recebia `EPERM`; o catálogo só continha
`request_user_input`. A prova nativa com o novo supervisor apresentou `exec_command`,
`apply_patch`, `write_stdin`, `view_image` e `request_user_input`, terminou com código
zero, confirmou o encerramento da árvore e removeu o worker.

## Implementação e decisão

Somente `isolated-tools` passa por `unshare --user --map-current-user --pid --fork
--kill-child=KILL`. Um guardian Python como PID 1 confere seu grupo externo antes
de iniciar o cliente. O cliente pode criar grupos e sessões; quando PID 1 termina,
o kernel encerra os descendentes do namespace. O guardian conserva um prazo monotônico
absoluto próprio, mesmo após a morte do wrapper e do coordenador. O filtro continua
recusando mudanças de namespace.

O grupo externo contém wrapper, launcher e guardian. A observação só declara o novo
owner encerrado se conseguir ler `/proc` e não encontrar integrantes vivos.
Recuperação não envia sinais a PIDs registrados. Recibos `linux-group` continuam
válidos; novos recibos usam `linux-pidns-group` e incluem `mission_process.py` no hash
do código. O catálogo de distribuição recebeu os hashes correspondentes.

Esta decisão amplia o trecho do plano que previa apenas ajustar o ambiente do cliente.
O custo é dois processos auxiliares adicionais e a exigência de user/PID namespaces
com `/usr/bin/unshare` em Linux x86_64. Reaproveita o helper Python e a biblioteca padrão,
sem serviço ou dependência Python nova. Os contratos legados conservam o filtro anterior.
Namespace indisponível impede despacho; não há retorno automático à contenção antiga.

## Provas

Os testes novos reproduziram a recusa de `setpgid` antes da implementação. Também
reproduziram a falsa confirmação de encerramento com `/proc` inacessível antes de
corrigir a observação. Os nove testes finais de namespace passaram na suíte nativa:
grupos novos, sessões, órfãos, prazo, cancelamento, falhas do coordenador/wrapper/
launcher/guardian, morte anterior ao despacho, falha de persistência e identidade
inválida. Um processo alheio permaneceu vivo nos testes de cancelamento e prazo.

A saída completa da suíte original não foi recuperada. A retomada executa novamente
os testes; os resultados atuais constam no relatório indicado acima.

A revisão independente não encontrou bloqueadores no supervisor ou nos recibos.
Encontrou um vazamento do servidor de teste se a preparação do pacote falhasse;
a correção foi revisada e reproduzida com socket fechado e nenhuma thread restante.
Comandos, resultados e hashes estão na `2026-10-16-namespace-supervision.json` (registro original indisponível).

## Limite da prova e próximo corte

`tests/smoke_codex_supervision.py` fornece uma resposta fixa em loopback, sem conta
ou chamada de modelo. Confere inicialização, catálogo e encerramento; registra
`tools_executed=[]` e `qualified=false`. Usa metadados embarcados de `gpt-5.5` para
expor ferramentas diretas, sem alterar a seleção de modelo do produto.

O ensaio separado que solicitou uma edição chegou ao próximo impedimento: o sandbox
do Codex recusou o caminho `.git` porque o diretório espelhado do worker é um symlink
para `/work`. A chamada retornou código 1 com `cannot enforce sandbox read-only path`.
Esse ensaio falhou; a edição pelo cliente completo não está aprovada. Próximo corte:
corrigir o mapeamento do workspace e repetir execução/patch dentro do worker,
preservando as proteções e a ausência de execução local de reserva.

Há ainda uma diferença de catálogo: os metadados de `gpt-6.1-sol` declaram
`tool_mode=code_mode_only`; com code mode desligado no perfil atual, a solicitação
não traz ferramentas. Isso exige qualificação por modelo, sem substituição silenciosa.
Observação de modelo/esforço, outras rotas do Codex, ferramentas tardias do Claude e
os dois aceites por assinatura continuam pendentes. `QUALIFIED` segue vazio e a fila
geral continua com `runtime_available=false` e `runnable=false`.

Nenhuma chamada de modelo, login, deploy ou publicação foi feita. A redação PT foi
revisada com `humanizer-ptbr`; a revisão EN foi manual, pois a skill inglesa não estava
instalada.

English: PID namespace supervision now permits Codex's process groups while bounding
descendant lifetime after crashes. Native startup and cleanup passed; the separate
editing probe failed on the worker workspace symlink. Full client qualification and
subscription acceptance remain pending. No model calls or publication occurred.
