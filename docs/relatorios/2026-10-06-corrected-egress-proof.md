# Prova corrigida: controle positivo passou, bloqueio inconclusivo

Frente: executor isolado / YC-203, R1. Operação nativa inconclusiva; limpeza confirmada.

A operação corrigida foi executada uma vez em 2026-10-06 UTC. A fase A passou:
HTTP 200, TLS verificado, credencial fictícia correspondente e peer público registrado
pelo guard. A fase B, com guard ausente, terminou em `RemoteDisconnected` e
`upstream_refused=false`. O CONNECT 200 veio do proxy; não prova resposta da aplicação
externa. Faltou atribuir a falha ao bloqueio esperado. A2 não foi executada.

Resultado: `inconclusive`, razão `negative_control_unproven`, sem chamada de modelo.
Os 190 comandos registrados retornaram zero; essa contagem inclui consultas e limpeza,
não 190 testes independentes. Houve duas tentativas de GET e dois reinícios do serviço.
A operação conservou os limites. A prova anterior de settings permanece preservada.

A limpeza informou `restored=true`. Uma conferência independente às
2026-10-06T03:34:25Z confirmou settings originais, política semanticamente preservada,
inventário de credenciais preservado, cinco VMs paradas, porta temporária fechada e
identidade do daemon igual à registrada pela limpeza. Recibos originais intactos.
**Não repetir o ensaio nem executar `-Reconcile`: não há limpeza pendente.**

O diagnóstico posterior abaixo identificou a causa da queda pelos registros existentes.
Nenhum aceite foi relaxado, perfil liberado ou código de controle alterado nesta análise.
[Panorama consolidado](2026-10-06-panorama-executor.md),
[plano](../superpowers/plans/2026-10-06-observed-egress-proof.md) e
[medição atual](../medicoes/corrected-egress-proof.json).

## Diagnóstico posterior da fase B

Às **00:31:10,251 de 6 de outubro, horário de Brasília**, o `HTTP Proxy Logger` do
Docker registrou uma recusa explícita ao conectar à porta loopback do guard desligado.
O evento pertence à mesma sandbox, ao mesmo destino e à mesma porta da operação. Seu
horário está dentro do transporte B, entre 00:31:09,877 e 00:31:10,293. A ausência do
guard já havia sido observada antes do despacho.

Isso atribui a queda observada à tentativa de conectar ao upstream indisponível. Não
prova ausência universal de fallback ou outros caminhos. O recibo automático continua
`inconclusive`: a fase A2 não foi executada e nenhum critério foi alterado retroativamente.

O diagnóstico encontrou três limitações no nosso coletor:

1. Ele procurava uma recusa de conexão em `policy log → blocked_hosts`. A evidência
   recuperada está no log de transporte HTTP do daemon. O help instalado descreve o
   histórico de política como decisões de permitir/bloquear hosts e contagem de pedidos.
2. O predicado exige a expressão `connection refused` e uma única menção ao endpoint.
   A mensagem nativa do Windows usa `actively refused it` e cita a mesma porta três vezes.
   Mesmo mapeada para a estrutura esperada, essa mensagem não passa no predicado atual.
3. O roteiro salvou apenas os hashes dos snapshots de política antes/depois, não seus
   conteúdos. Portanto, não é possível reproduzir exatamente a decisão original. Uma
   consulta posterior, com identidade estável do daemon, retornou listas vazias e hashes
   diferentes; ela não substitui os snapshots da época.

Uma verificação offline correlacionou o recibo do cliente B, seu hash de código, a janela
do transporte, a sandbox, a porta e a linha preservada do daemon. Também confirmou que
os quatro recibos originais continuam com os mesmos hashes. Apenas a linha pertinente
foi copiada para a área privada; o log inteiro da máquina não foi copiado nem publicado.

Não houve nova GET, mudança de configuração, reinício, chamada de modelo ou alteração
no controlador. As leituras atuais se limitaram ao estado/identidade do daemon e histórico
de política. As provas de restauração anteriores permanecem válidas para a rodada encerrada.

Continuação: o [coletor separado](2026-10-06-captured-egress-evidence.md) passou em onze
testes offline com essa mensagem real. Preserva snapshots e reconhece a recusa com
origem, endpoint e tempo atribuídos. A [integração com o controlador](2026-10-06-integrated-egress-controller.md)
também passou na validação offline; a nova prova nativa permanece pendente.
Uma futura execução completa A/B/A2 continua sendo uma operação distinta; não repetir
a rodada consumida nem executar recuperação sem pendência.

## Preparação anterior à execução

`corrected_egress.py` reutiliza o observador existente e seleciona somente
`corrected-egress-proof/`. O mapa de hashes inclui o controlador corrigido, o observador
inalterado e os recibos da restauração anterior. O mapa original é restituído mesmo se
a chamada falhar. O novo PowerShell confere Python e fontes antes de iniciar.
Nenhum arquivo do executor do produto ou perfil foi alterado.

Uma consulta preliminar somente leitura confirmou o daemon em execução e cinco VMs
conhecidas paradas. Não consultou settings, iniciou VM ou reiniciou o serviço.
O comando de teste foi `python -B -m unittest discover -s .superpowers/sdd/2026-10-04-isolated-executor -p 'test_*egress.py' -v`:
80 testes aprovados, sem skips, falhas ou erros. Cinco testes cobrem a entrada nova,
incluindo tentativa consumida, recibo antigo alterado e recuperação sem dispatch.
A regressão falhou antes da implementação e passou depois.

Três verificações reais de entrada recusaram antes de criar a operação: PowerShell sem
flag, PowerShell com ambas as flags e Python sem ação. Nenhuma delas chamou Docker.
Essas verificações comprovaram o preparo do roteiro; o resultado nativo está registrado acima.

## Revisão independente

Um revisor em contexto novo conferiu a alteração, os hashes e o encaminhamento da
recuperação. Não apontou achados relevantes ou menores. Leu a evidência de 80 testes;
não reexecutou a suíte, consultou Docker ou executou a prova. A revisão não julgou a
implementação integral de SOCKS/TLS/DNS nem certificou A/B/A2, OAuth, MCP ou restauração
nativa da nova operação. Esses aceites continuam pendentes.

## Escopo executado (histórico)

O operador executou uma vez `run-corrected-egress-proof.ps1 -RunApprovedProbe` pelo seu PowerShell normal. Esse terminal é necessário por causa das falhas de socket observadas ao
iniciar o daemon pelo terminal do agente. O roteiro está na área privada de ensaios do
mantenedor e não é distribuído pelo setup.

Limites mantidos: até três GETs para `postman-echo.com`, credencial fictícia e até dois
reinícios do Docker Sandboxes com VMs paradas. Preparação de 180 segundos, ensaio de 120,
cada GET de até dez segundos e limpeza de 180. Sem modelo, certificado ou reinício do Windows.

Os registros foram preservados. A recuperação e a prova são caminhos separados; uma
operação consumida não volta à execução. Rede/autenticação, isolamento do intermediário,
MCP, pacote e suspensão continuam pendentes. R1 parcial, R2/R3 não iniciados.

## English overview

The native operation ran once. Phase A passed within the probe: HTTP 200, verified TLS,
matching dummy credential and recorded peer. Phase B, with the guard absent, ended in
RemoteDisconnected without sufficient evidence attributing it to upstream refusal.
The proxy CONNECT 200 is not an external application response. A2 was not run.

Outcome: inconclusive, negative_control_unproven. All 190 native commands returned zero;
they include queries and cleanup, not independent tests. Two GETs were attempted and
two daemon restarts occurred, without model calls. Independent read-only checks confirmed
restoration, five stopped VMs and the closed port. No retry or reconciliation is needed.

Preparation passed 80 local tests and independent review; that does not establish native
network acceptance. A subsequent offline diagnosis attributed B to an explicit upstream connection refusal
in the daemon HTTP proxy log, matching sandbox, endpoint and transport time. The collector
looked in blocked policy hosts, required different wording and preserved only snapshot
hashes. Exact replay of its original decision is impossible. The native verdict remains
inconclusive because A2 did not run. A separate collector subsequently passed eleven offline
tests; controller integration subsequently passed offline validation. No product profile was enabled, consumed
controller changed, or new probe started. R1 remains partial and unpublished.

ATRASO: main 1
