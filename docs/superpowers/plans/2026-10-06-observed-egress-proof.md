# Prova de saída com registro por comando

**Atualização de 06/10, 21h50 (São Paulo):** a entrada corrigida foi executada e
parou em `sbx secret ls --json`, com código 1. Foram 25 consultas: proprietário,
configurações e políticas passaram; nenhuma ação de alteração foi iniciada.
`cleanup.restored=true`, sem erros. Não repetir nem reconciliar essa operação.
A consulta passou em duas verificações locais, uma com o auxiliar Windows original;
a mensagem da falha remota não foi capturada. A causa permanece desconhecida.
Próximo: obter o erro dessa consulta no contexto remoto, com diagnóstico somente
leitura, antes de preparar outro ensaio completo. A/B/A2 e o aceite de R1 continuam
pendentes. Os 102 testes anteriores verificaram preparação e respostas simuladas.

**Current checkpoint:** the corrected entry was consumed at 21:50 São Paulo time
on October 6. `sbx secret ls --json` exited 1 after ownership, settings and policy
checks passed. All 25 commands were reads; no mutation began. Cleanup is verified.
Do not replay or reconcile this operation. Two local inventory queries passed,
including one through the existing Windows helper, but the remote error message was
not retained. Its cause remains unknown. Next: capture only that read-only query's
error in the remote context before preparing another full probe. Native A/B/A2 and
R1 acceptance remain pending; the earlier 102 tests used simulated Docker replies.
Earlier next actions below are historical.


Frente: executor isolado / YC-203, R1. Operação executada e encerrada como inconclusiva,
com restauração confirmada. A v2 permanece encerrada e os perfis do produto bloqueados.

## Continuação aprovada: captura de status na entrada remota

O pedido “próximo” autoriza integrar a captura à entrada, após a confirmação remota.
Preparar `captured-mobile-egress-proof/`, preservando fontes e recibos consumidos.
Guardar stdout/stderr somente de `sbx daemon status --json`, por correspondência
exata com o executável fixado. Correlacionar os arquivos ao identificador do comando,
antes da interpretação original; manter erro de JSON, código não zero e timeout.
Até 64 KiB por fluxo; guardar prefixo/hash e recusar respostas maiores. Outros comandos
mantêm apenas metadados, sem argumentos ou saídas de credenciais.

Reutilizar o auxiliar de proprietário, o controlador, o coletor de B e os prazos
aprovados. Trocar estado e observador juntos, restaurando ambos ao terminar. Manter
reserva única, recusa de repetição e recuperação sem novo despacho. Testar a passagem
real entre entrada, observador e interpretador com fronteiras externas substituídas;
verificar o auxiliar Windows e uma leitura real de status. Revisão independente antes
do comando ao operador. Essa preparação não dá aceite ao ensaio de rede.

Foco da revisão: comandos semelhantes ou com argumentos extras não devem capturar
segredos; interrupção e falha de gravação não podem deixar a execução prosseguir sem
evidência; o timeout original não pode aumentar; recuperação não pode enviar nova GET;
a troca de módulos deve ser desfeita nos caminhos de erro. Os testes não simulam crash
de kernel, falta física de espaço nem a rede real; registrar esses limites.

## Resultado da execução e correção local

Em 2026-10-06 UTC, o operador executou o roteiro uma vez. Os 60 comandos registrados
terminaram com código zero, sem timeout. O controlador recusou o readback de
`no_proxy.sandbox`: esperava `override`, embora o valor atribuído fosse o padrão vazio.
Docker documenta que atribuir o padrão remove o override. Não houve GET, registro de
credencial fictícia ou nova regra; o único reinício ocorreu na restauração.

Uma leitura independente confirmou configurações, política, inventário de credenciais,
cinco VMs paradas e porta temporária fechada. Não há recuperação pendente. Fonte executada,
recibos e medição da preparação foram preservados. O contrato foi corrigido na cópia de
desenvolvimento: 75 testes passaram, incluindo reprodução da falha antes da correção.
Os hashes do roteiro consumido continuam os originais; não executar ou reconciliar essa
operação. Não foi criado outro ensaio. Veja [evidência e limites](../../relatorios/2026-10-06-observed-egress-proof.md).

O escopo abaixo registra a preparação original; não é uma autorização para repetir.

## Continuação com o contrato corrigido

**Resultado atual:** executada uma vez. A passou; B recebeu `RemoteDisconnected`, sem
atribuição suficiente da recusa; A2 não executada. Limpeza confirmada por leitura.
Não repetir ou reconciliar. O diagnóstico posterior encontrou recusa ao guard no log
do daemon, correlacionada à fase B. O coletor não reconheceu a evidência. Um
[candidato separado](../../relatorios/2026-10-06-captured-egress-evidence.md) passou em onze
testes offline. A [integração ao controlador](../../relatorios/2026-10-06-integrated-egress-controller.md)
também foi validada offline. A entrada nativa está preparada; 113 testes passaram.
Próximo: uma execução A/B/A2 pelo mantenedor no PowerShell normal. A2 nativa permanece
não executada; nenhum novo diretório de operação foi criado.
O texto abaixo preserva a preparação, cujos 80 testes não deram aceite nativo à rede.

Após o diagnóstico, o mantenedor pediu o próximo passo. Preparar uma operação separada,
com o mesmo escopo de rede e os mesmos limites, reutilizando o observador e o controlador
corrigido. Não reabrir a operação anterior. O novo roteiro é
`run-corrected-egress-proof.ps1 -RunApprovedProbe`; os registros ficam em
`corrected-egress-proof/`. Os hashes da fonte corrigida e da restauração anterior são
conferidos antes dos efeitos. A execução continua pelo PowerShell normal do operador
por causa das falhas de socket registradas no terminal do agente.

Verificação da preparação: consultas somente leitura com cinco VMs paradas; 80 testes
locais aprovados; entradas PowerShell/Python sem ação explícita recusadas; flags conflitantes
recusadas. Os recibos antigos e o roteiro consumido permanecem intactos. Nenhum estado
da nova operação foi criado. [Relatório da continuação](../../relatorios/2026-10-06-corrected-egress-proof.md).

Foco da revisão: seleção do estado novo, restauração do mapa de hashes após exceção,
preservação dos recibos anteriores, encaminhamento de `-Reconcile` sem dispatch e contrato
de settings. A revisão da preparação não dá aceite para rede, OAuth ou isolamento.

## Objetivo e motivo

Medir uma vez se Docker → guard SOCKS local → `postman-echo.com:443` preserva a
substituição de credencial fictícia, comprova o destino final e falha quando o guard
está indisponível. É a hipótese ainda não medida do
[plano anterior](2026-10-05-exclusive-egress-proof.md).

O timeout da v2 ocorreu antes do recibo e não identificou o comando. Na consulta de
6 de outubro UTC, daemon, inventário de processos e inventário das cinco VMs responderam
em menos de dois segundos por comando. Todas as VMs estavam paradas. A causa histórica
do timeout continua desconhecida. Essa observação não prova a saída de rede.

## Alteração preparada

Reutilizar o controlador e o guard já revisados, com seus hashes fixados. Acrescentar
somente um invólucro privado que grava a tentativa antes do preflight e observa as
chamadas síncronas do controlador e do transporte delegado: identificador do comando, categoria, UTC, duração,
prazo e resultado. Não registrar argumentos, stdout, stderr ou texto de exceção.
O tempo gasto gravando a intenção é descontado do prazo do comando.

Estado novo em `.superpowers/sdd/2026-10-04-isolated-executor/observed-egress-proof/`.
`attempt.json` impede uma segunda execução mesmo se o preflight falhar. O lock do
sistema operacional impede executar e reconciliar ao mesmo tempo. A reconciliação
usa somente `control.json` existente; não envia outra GET nem renova tentativas.
Controlador, guard, encerramento da v2 e recibo anterior de recuperação ficam intactos.

## Escopo da execução proposta

- Docker Sandboxes local exclusivo do YoungCrow, como já definido pelo mantenedor.
- Uma operação; até três GETs para `postman-echo.com`, uma por fase A/B/A2, sem retry
  ou redirect e com credencial descartável fictícia. Nenhuma chamada a modelos.
- Consultas preliminares: até cinco comandos de 15 segundos. O controlador conserva
  seus limites: preparação de 180 segundos, ensaio de 120 segundos, até dez segundos
  por GET e limpeza de 180 segundos. Não aumentar prazos após uma falha.
- Alterar temporariamente somente `proxy.sandbox` e `no_proxy.sandbox`; até dois
  reinícios do serviço, sempre com todas as VMs paradas. Não reiniciar Windows,
  instalar certificado, mudar proxy do sistema ou usar credenciais reais.
- Uma VM de prova já identificada, regras temporárias apenas para ela e um guard
  loopback temporário. Inventários divergentes impedem a execução.
- Restaurar configurações próprias e comprovar inventários finais. Preservar mudanças
  de terceiros; conflito exige reconciliação da mesma operação.

## Resultado que encerra a rodada

| Resultado | Consequência |
|---|---|
| A e A2 comprovam TLS, substituição fictícia e peer validado; B comprova recusa do upstream; limpeza confirmada | Viabilidade medida nesse ensaio; avançar ao isolamento do intermediário |
| B alcança o destino sem guard, há fallback ou peer indevido | Candidato reprovado; não integrar |
| Timeout, TLS genérico, falta de prova ou limpeza incompleta | Inconclusivo; parar e conservar a etapa exata, sem repetir |

Mesmo com sucesso, OAuth, isolamento do cliente contra o intermediário, MCP no caminho
autenticado, pacote atualizado, suspensão e clientes reais continuam pendentes.
R2/R3 só começam após o aceite de R1.

## Operação após autorização

O roteiro privado `run-observed-egress-proof.ps1` exige `-RunApprovedProbe` para iniciar.
Sem flag, recusa. `-Reconcile` só recupera a operação existente. Ambos conferem os
hashes antes de chamar Python. A execução pelo PowerShell normal do operador preserva
o caminho de inicialização do serviço que funcionou nos ensaios anteriores.

Os testes locais cobrem intenção antes de timeout, sigilo do registro, retorno nativo,
falha de escrita, prazo expirado, repetição, reconciliação e fontes alteradas.
A revisão independente encontrou uma lacuna no transporte delegado. Uma regressão
reproduziu a ausência do registro; a correção passou, incluindo restauração das duas
dependências após timeout. O contexto do revisor foi reutilizado por limite da plataforma;
ele não é um contexto novo. Não houve segunda revisão. Os resultados estão no
[relatório da preparação](../../relatorios/2026-10-06-observed-egress-proof.md).
Não há commit, push ou mudança no executor do produto nesta preparação.

## English overview

A corrected entry is now prepared following the maintainer's request to continue.
It reuses the observer with separate state, corrected controller pins and immutable
prior restoration receipts. The same scope and limits apply. Eighty local tests and
three entry-refusal checks passed before execution. The subsequent native run passed A,
left B inconclusive and did not run A2. Cleanup was confirmed; analyze existing B records
without retry or reconciliation. Subsequent daemon-log analysis attributed B to guard
connection refusal. A separate collector passed eleven offline tests, and its controller
integration was also validated offline. The native entry is prepared; 113 tests passed.
Next: one maintainer execution from normal PowerShell. Native A2 remains unexecuted.

The operator ran the proof once. All 60 native commands returned zero; the controller
then rejected the default-valued setting because it incorrectly expected an override.
There were no GETs, dummy credential registration or new rules. One service restart
restored settings. Independent read-only checks confirmed cleanup. The correction passed
75 local tests, with the executed source and receipts preserved. The consumed wrapper
was not repinned; no new attempt was created and no recovery remains pending.

Original scope, preserved for history:

One proposed, separately authorized network proof reuses the unchanged controller and
guard. A private wrapper records a durable attempt before preflight and sanitized
command timing, including failures; replay is refused and recovery cannot dispatch
another request. The read-only observation found five stopped VMs and responsive
queries; it did not explain the earlier timeout or establish network enforcement.

The proposal retains the original A/B/A2 limits, dummy credentials and restoration
rules. Native execution requires operator authorization for temporary sandbox proxy
settings and up to two service restarts. Success proves only feasibility of this path;
it does not certify OAuth, client isolation, host suspension or product execution.

ATRASO: main 1
