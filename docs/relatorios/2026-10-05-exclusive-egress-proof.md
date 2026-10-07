# Saída controlada: ativação interrompida e recuperação

Frente: executor isolado / 2A-R1.

**Estado final do ciclo:** v2 executada e encerrada como inconclusiva após `TimeoutExpired`,
antes da criação do recibo e de alterações no Docker. Não há recuperação pendente.
Entradas PowerShell/Python bloqueadas; 60 testes locais passaram. R1 continua parcial.

O mantenedor aprovou a implementação do [plano](../superpowers/plans/2026-10-05-exclusive-egress-proof.md)
com “confirmado vamos seguir”. A execução pelo operador parou antes de enviar tráfego:
a leitura do setting retornou `source=override`, mas o código exigia `source=user`.
Essa mesma incompatibilidade impediu a limpeza automática. O código foi corrigido e
54 testes passaram após as duas correções de contrato nativo. A recuperação está concluída,
com um reinício pelo operador e conferência final somente leitura às 18:48:37Z.
R1 continua parcial, R2/R3 não começaram e os perfis permanecem vazios.

## Falha nativa e estado recuperado

O recibo de 2026-10-05T17:27:18Z registra uma única intenção de escrita em
`proxy.sandbox`. Não houve intenção de alterar `no_proxy.sandbox`, criar regras ou
credenciais, iniciar VM, reiniciar daemon ou enviar GET. Os recibos originais foram
preservados antes da reconciliação. O estado observado confirmou o mesmo daemon,
cinco VMs paradas, guard ausente e políticas e inventário de credenciais intactos.

Os testes anteriores usavam uma resposta simulada com o rótulo errado. A fixture agora
reproduz `override`, observado no Docker Sandboxes 0.46.0. Novas regressões cobrem
ativação, recuperação do recibo consumido e restauração de um override anterior.
Elas falharam antes da correção. O retorno da CLI também distingue recuperação
concluída de prova aprovada; limpeza incompleta continua retornando erro.

Às 17:31:15Z, `settings unset proxy.sandbox` restaurou a única chave alterada.
As duas chaves estavam em `source=default`, valor vazio, e o daemon não havia reiniciado.
Nesse checkpoint, o recibo ficou em `restart_required`. O operador executou `-Reconcile`
e concluiu o reinício, mas a conferência final retornou `final_inventory: ValueError`.
O campo `reason=settings_readback_failed` ainda descrevia a falha original da ativação.

## Reconciliação final concluída

A inspeção isolou a diferença: somente `id` e `policy_id` da regra provisionada,
não editável, `kit:sbx-kit-builder` mudaram durante o reinício. Destino, decisão,
ações, escopo, origem e todos os demais campos permaneceram iguais. As outras regras
e a política da VM própria continuaram idênticas. A comparação integral dos IDs
produzia uma falha mesmo com as permissões preservadas.

A correção admite essa troca apenas para regras automáticas com a estrutura nativa
verificada e IDs UUID válidos. Preserva todos os campos de permissão e metadados adicionais;
regras editáveis, desconhecidas ou IDs inválidos continuam exigindo igualdade integral.
Os snapshots brutos permanecem intactos. Cinco regressões novas falharam antes da correção;
a suíte passou em 54/54, incluindo a recuperação com reinício já concluído sem novas mutações.

Às 18:48:37Z, a recuperação retornou `cleanup.restored=true`, sem erros. As chamadas ao
Docker foram limitadas a uma lista de consultas permitidas; nenhum novo reinício, GET
ou alteração de settings foi executado. O daemon continuava sendo o criado pelo reinício
do operador. Cinco VMs estavam paradas, guard/processo/listener ausentes, configurações
restauradas e inventário de credenciais inalterado. Permissões externas preservadas;
apenas os dois IDs provisionados diferiam do snapshot inicial.

As cópias `.operator-failure` e `.final-inventory-failure` preservam as falhas anteriores.
`recovery-complete.json` registra a conferência. O recibo continua consumido, com resultado
de rede `inconclusive`: nenhuma das fases A/B/A2 foi despachada. Não há comando de recuperação
pendente. Uma nova prova precisa de operação e autorização próprias antes de executar.

<a id="operação-v2-preparada"></a>

## Operação v2: preparação e encerramento

O mantenedor pediu continuidade com menos voltas. A entrada v2 reutiliza o controlador
corrigido e usa um diretório fixo novo. Confere os hashes dos recibos recuperados antes
de preparar o ensaio; recibo v2 existente impede outro despacho. O modo de recuperação
atua apenas sobre v2, sem depender de reabrir ou alterar o recibo anterior.

Cinco novos testes falharam antes da implementação; a suíte passou em 59/59.
O preflight do wrapper passou com as cinco VMs paradas e o mesmo daemon. Essa consulta
não leu settings nem iniciou VM. A [medição de preparação](../medicoes/exclusive-egress-v2.json)
registra os hashes e os limites. O comando foi entregue para execução no PowerShell normal
do mantenedor, devido às falhas anteriores de socket ao reiniciar pelo terminal do agente.

A rodada foi executada pelo mantenedor e devolveu `TimeoutExpired`. A inspeção encontrou
o diretório v2 ausente. O fluxo cria o recibo antes de alterar configurações, iniciar o
guard ou enviar tráfego; nenhuma dessas etapas foi alcançada. O erro genérico não identifica
se o timeout veio da CLI, da consulta de processos ou da preparação das permissões do diretório.
Não há evidência suficiente para atribuí-lo ao Docker ou ao Windows especificamente.

Às 19:05:21Z, consultas confirmaram o mesmo daemon, as cinco VMs paradas, ambas as chaves
restauradas e configurações globais, política própria, permissões externas e credenciais
preservadas. O guard anterior continuava ausente. Não foi necessário reinício ou reconciliação;
a mensagem genérica do wrapper sugeria `-Reconcile`, mas não existe recibo v2 para recuperar.

O encerramento agora tem bloqueio persistido: PowerShell e Python recusam todos os modos
antes de chamar o controlador. Uma regressão falhou antes da mudança e passou depois;
suíte 60/60. Isso fecha o ciclo operacional, sem comprovar ou reprovar a hipótese de rede.
Nenhuma v3, aumento de timeout ou novo componente foi iniciado.

## Decisão seguinte

Após discutir a adoção pelo VS Code, o mantenedor confirmou [manter as duas opções](../superpowers/specs/2026-10-05-local-and-dedicated-execution.md):
execução local por padrão e runner dedicado opcional. Essa decisão substitui a escolha
exclusiva de uma abordagem. Próximo: detalhar setup, pré-requisitos e conexão do runner,
aproveitando o backlog existente. Ambos continuam exigindo provas de rede e autenticação.
O runner ainda precisa de ambiente escolhido; não houve provisionamento ou migração.
A causa exata do timeout permanece desconhecida.

O fornecedor documenta Ubuntu 24.04+ com KVM para execução local e exige virtualização
aninhada quando o host é uma VM: [requisitos de instalação](https://docs.docker.com/ai/sandboxes/install/).
Essa elegibilidade documentada não certifica o YoungCrow nessa plataforma. Os perfis seguem vazios.

## O que foi medido

| Verificação | Evidência e alcance |
|---|---|
| Destino e SOCKS | Domínio/porta exatos, DNS misto, IP privado/mapeado, quadros fragmentados, BIND/UDP/IP literal e peer divergente. DNS/dials desses testes são substitutos locais |
| Prazo | Guard ocioso encerra no prazo; subprocesso real simulando DNS lento é encerrado e recolhido |
| Recuperação | Intenção antes de escrever, resposta perdida após efeito, retorno ao default por `unset`, preservação de terceiros, recusa de recibo consumido e reinício incerto sem repetição |
| Inventário após reinício | Dois IDs provisionados podem mudar; alteração de permissão, campo adicional, regra editável, ID inválido ou regra extra impede equivalência |
| TLS e redirect | Servidor TLS local responde 302 sem nova conexão; identidade inválida impede enviar o marcador. Certificados fictícios ficam em arquivos privados e no `SSLContext` do teste |
| Classificação | Sucesso com guard desligado reprova; timeout, falha TLS e ausência de peer ficam inconclusivos. Limpeza incompleta impede aceite |
| Host | Preflight somente leitura encontrou Docker Sandboxes 0.46.0, daemon ativo e cinco VMs conhecidas paradas; não chamou settings |

Comando local: `python -B -m unittest discover -s .superpowers/sdd/2026-10-04-isolated-executor -p test_exclusive_egress.py -v`.
Os recibos de RED/GREEN, fontes e o roteiro PowerShell permanecem no diretório privado
da prova. O parser PowerShell aceitou o wrapper. [Medição sanitizada](../medicoes/exclusive-egress-proof.json).

## Revisão e correções

A revisão somente leitura encontrou cinco problemas. A recuperação agora consulta a
intenção de criação de regra, restaura apenas settings cuja escrita foi registrada
e exige IDs devolvidos pela criação antes de adotar regras. A prova negativa exige
endpoint completo e incremento de exatamente uma recusa; o positivo exige bytes
retransmitidos nos dois sentidos. As oito novas regressões falharam antes das correções;
a suíte final passou em 44/44. Não houve segunda revisão independente após as correções.

Uma resposta perdida sem IDs não comprova autoria de regra. Nesse caso, a VM fica
parada, os settings próprios são recuperados e a regra ambígua fica preservada para
reconciliação. Formato nativo sem IDs ou sem evidência específica de recusa não gera
aceite. A compatibilidade desses retornos ainda precisa do ensaio real.

## Limites do ensaio e retorno

O operador concluiu o reinício pelo PowerShell normal; a recuperação final foi conferida
sem outro reinício. A tentativa não chegou a testar o caminho Docker → controle SOCKS
local → serviço de eco.
O roteiro permite até três GETs, dez segundos por tentativa, 120 segundos de ensaio,
180 segundos de preparação e 180 segundos de limpeza. Até dois reinícios do serviço
ativam e restauram as duas chaves autorizadas; todas as VMs devem estar paradas ao reiniciar.

O recibo exclusivo impede repetir uma execução incompleta. A recuperação usa
`-Reconcile`, sem nova GET. Alterações de terceiros, reinício de resultado incerto
ou limpeza sem comprovação preservam o bloqueio e o registro para reconciliação.
Nenhuma instalação de certificado, reinício do Windows ou chamada de modelo faz parte do roteiro.

Na preparação inicial, não houve alteração de settings, política, credencial ou VM.
Na execução do operador, houve uma escrita de proxy, restaurada durante a recuperação.
Os testes TLS usaram somente loopback, sem instalar CA. A suíte histórica do produto
(390 casos) não foi repetida porque `runtime/sbx/guardian.py` e `launcher.py`
permaneceram inalterados. O candidato anterior por CIDR continua reprovado e seu recibo consumido.

Mesmo um futuro `viable_within_probe` demonstrará apenas a viabilidade nesse processo
confiável. Isolamento de cliente hostil, OAuth, MCP inacessível com rede do fornecedor,
integração do relay, pacote corrigido e suspensão do host continuam pendentes.

## English overview

The operator's native attempt stopped before traffic: Docker returned `source=override`,
while both the code and its fake CLI expected `source=user`. That also blocked automatic
cleanup. That correction passed 49 local tests, including the consumed-receipt recovery case.
The only written setting, `proxy.sandbox`, was restored to default at 17:31:15Z. Five VMs
were stopped, the guard was absent, and policies and credentials were unchanged.

The maintainer completed the recovery restart, but final inventory comparison failed:
Docker had regenerated only `id` and `policy_id` in the non-editable, provisioned kit rule.
Every permission and all other rule fields were unchanged. The comparator now permits
only those UUID changes on the verified automatic-rule structure, retaining all other
fields and strict identity checks for editable or unknown rules. Five new regressions
failed before the fix; all 54 tests then passed.

At 18:48:37Z, final read-only verification completed recovery with no errors, new restart,
settings mutation or GET. Five VMs were stopped, the guard was absent, settings were restored
and credential inventory was unchanged. Raw snapshots and both failure receipts are preserved.
No recovery command remains pending. Network results remain `inconclusive`, with no A/B/A2
phase dispatched. The consumed probe cannot be replayed; a new proof needs its own operation
and authorization. The original budget permits at most three GETs,
ten seconds per attempt, a 120-second probe and up to two service restarts, with
180-second preparation and cleanup budgets. Recovery never dispatches another GET.
Local TLS certificates were trusted only in the fixture SSLContext; no CA was installed.

Operation v2 was prepared using the same corrected controller and a fixed new receipt path.
It checks the recovered receipt hashes, refuses replay and supports recovery of v2 only.
Five new regressions failed before implementation; all 59 tests then passed. Wrapper preflight
confirmed five stopped VMs and the existing daemon without settings calls or VM starts.
The maintainer then ran it; `TimeoutExpired` occurred before receipt creation or Docker changes.
The exact command was not recorded. At 19:05:21Z, observation confirmed the same daemon,
five stopped VMs, restored settings and preserved policies/credentials. No recovery is needed.
Both entry points now reject execution under a persisted cycle-closure marker; all 60 tests
passed. Network results remain inconclusive. No v3, timeout increase or new component was started.
The maintainer subsequently approved retaining both product options: local execution by
default and an optional dedicated runner. Next, define setup selection, prerequisites and
runner connectivity using the existing backlog. Both require security and authentication
proofs. No runner has been selected or provisioned; timeout causality remains unknown.

Timeouts and generic TLS failures do not prove enforcement. Missing connection evidence
is inconclusive; echo success with the guard absent rejects the candidate. Incomplete
cleanup blocks acceptance. R1 remains partial, R2/R3 have not started and no product
profile is enabled. Rule ownership requires creation-result IDs; ambiguous rules are preserved while owned settings are recovered after stopping the VM. Native output compatibility remains unproven. Native viability would still leave hostile-client isolation,
OAuth, MCP isolation, relay integration, packaging and host suspension unproven.

ATRASO: main 1
