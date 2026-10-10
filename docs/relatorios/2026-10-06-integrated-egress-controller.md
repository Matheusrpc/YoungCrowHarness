# Coletor integrado e entrada da prova nativa

Frente: executor isolado / YC-203, R1. A tentativa mais recente passou por permissões
e políticas, mas parou na consulta de credenciais do Docker. Não houve alteração;
o resultado de rede permanece pendente. Os checkpoints abaixo preservam o histórico.

O controlador candidato usa a nova coleta na fase B. As fases A/A2, a preparação e a
limpeza reutilizam a implementação existente. O teste atravessa o fluxo original de
orquestração com respostas locais, grava o resultado e confirma a recusa de repetição.
Os arquivos das operações já consumidas permanecem intactos.

## Comportamento verificado

- B registra snapshots completos, contexto, resultado do cliente e evidência do daemon.
  O controle da operação referencia o manifesto por caminho e SHA-256.
- A2 depende de B aceita. Evidência ausente, timeout ou falha de gravação impedem avanço.
  O teste sem a recusa executa A e B, passa pela limpeza e termina inconclusivo.
- A verificação de segurança após cada resposta também precisa passar. Uma resposta
  positiva seguida de erro não autoriza a próxima fase ou o aceite final.
- A operação e cada fase consumida recusam repetição. Recuperação chama a limpeza
  existente, sem disparar o cliente nem refazer a coleta.

O controlador tem diretório próprio e verifica os hashes do coletor, das dependências
e dos recibos anteriores. As referências temporárias usadas pelo observador são
restauradas mesmo quando ocorre erro. O caminho segue o contrato de um coordenador
por vez; não é um serviço para execuções concorrentes dentro do mesmo processo.

## Testes e revisão

A suíte final passou em **106 testes**, incluindo quinze de integração, sem falhas,
erros ou skips. O teste do fluxo completo usa a orquestração original e substitui suas
fronteiras externas. Os caminhos de sucesso e de evidência ausente chegam à limpeza;
a operação consumida não volta a disparar trabalho.

A revisão independente apontou dois achados importantes, ambos reproduzidos antes
da correção. O coletor ocultava a causa de uma troca inesperada do daemon dentro do
callback; agora a integração preserva o erro e a flag que restringe a limpeza. Além
disso, a recuperação poderia aceitar A2 após perda do coordenador durante a verificação
final. Agora cada fase exige `postcheck_complete`, gravado somente depois de concluir
essa verificação. Sem o marcador, a recuperação mantém o resultado inconclusivo.

As regressões e a suíte completa passaram após as correções. Não houve segunda revisão;
o parecer original e sua resolução estão registrados. Os 106 testes incluem os 91 da
etapa anterior, portanto as contagens não devem ser somadas.

## O que o teste representa

A recusa de B usa a mensagem real preservada do daemon. Os snapshots, as respostas
positivas de A/A2, as consultas ao Docker e a limpeza são substituídos por dados ou
funções locais. Isso prova a ligação entre controlador, coletor, persistência e regras
de avanço. Não prova restauração ou isolamento de rede numa execução nova do Docker.

O código fica em `integrated_egress.py`, na área privada de ensaios. A etapa de integração
terminou sem roteiro de terminal ou nova operação nativa. Naquela etapa não houve
comando Docker, pedido externo, reinício ou chamada de modelo pelo executor.
O recibo nativo anterior continua inconclusivo e sem A2.

## Entrada nativa preparada

O mantenedor aprovou a continuação. `run-integrated-egress-proof.ps1` exige exatamente
uma ação: execução ou recuperação. O roteiro confere Python e fontes; `integrated_entry.py`
verifica doze arquivos locais antes de importar o controlador. A execução só retorna
sucesso com `viable_within_probe`; a recuperação informa exclusivamente se a limpeza
foi concluída. O diretório `integrated-egress-proof/` está reservado à nova operação.

Três verificações reais recusaram PowerShell sem ação, PowerShell com ambas as ações
e Python sem ação. Nenhuma criou a operação. Os testes locais cobrem ainda fontes
alteradas, resultado inconclusivo, saída de erro, execução única e recuperação.

A revisão independente apontou quatro dependências locais sem hash no bootstrap.
O teste reproduziu a falha antes da correção. Agora essas dependências também são
conferidas antes do import; os arquivos reais não foram alterados pelo teste. Não
houve segunda revisão. A suíte final passou em 113 testes, incluindo sete da entrada, sem falhas, erros ou
skips. Esses 113 incluem os 106 da etapa anterior; não some as contagens. A medição
registra os resultados e seus limites.

A consulta preliminar de metadados excedeu o prazo. Uma consulta isolada posterior de
`daemon status --json` retornou `running`; isso não comprova todo o preflight nem
identifica a causa do timeout. Nenhuma configuração foi alterada, nenhuma GET foi
feita e não houve reinício. O diretório da operação continua ausente.

O [guia do mantenedor](../USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor) traz
o comando para executar uma vez no PowerShell normal. Esse terminal é necessário
porque reinícios pelo terminal do agente apresentaram falhas de socket. O escopo
aprovado continua limitado a três GETs com credencial fictícia e dois reinícios do
Docker Sandboxes, com VMs paradas. Os limites de tempo constam do guia e do roteiro.
Não há chamada de IA, certificado novo ou reinício do Windows.

[Medição da entrada](../medicoes/integrated-egress-entry.json).

## Resultado nativo: proprietário dos arquivos

Em 6 de outubro de 2026, às 10h27 (São Paulo), a entrada recebeu a ação correta.
Cinco consultas de metadados terminaram com código zero. Na validação seguinte,
`assert_private` encontrou o grupo Administradores como proprietário de `attempt.json`,
`commands.jsonl` e `reclaim.lock`; a pasta continuava pertencendo ao usuário.
As regras de acesso permitiam somente o usuário, mas o proprietário divergente também
é recusado pela proteção. O erro foi reproduzido por inspeção somente leitura.

`control.json` e `receipt.json` não existem. No fluxo fixado por hash, as alterações
no Docker vêm depois da criação de `control.json`. O registro contém somente consultas:
nenhuma GET, reinício, mudança de configuração ou chamada de IA. Não há restauração
do Docker pendente. Os arquivos da tentativa foram preservados, inclusive proprietário
e conteúdo; essa operação não será repetida.

O Windows usa o proprietário padrão do token para objetos novos. O auxiliar de testes
já existente ajusta esse campo para o usuário do processo, verifica o ajuste e restaura
o valor ao terminar. Isso segue o [mecanismo documentado pela Microsoft](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object).
Não modifica as permissões existentes nem habilita privilégios.

`check_mobile_owner.py` reutiliza esse auxiliar para um único arquivo sintético. A
verificação local passou com `adjusted: false`, as permissões foram aceitas e o arquivo
foi removido. O operador depois confirmou `owner_context_verified` com `adjusted: true`
no terminal do celular. O arquivo sintético passou e os recibos anteriores foram
preservados. Não houve comando Docker ou solicitação de rede nesse diagnóstico.

## Entrada com contexto de proprietário verificado

`mobile_egress.py` fixa as fontes do bootstrap e reutiliza o auxiliar de proprietário.
Antes de reservar trabalho, cria um arquivo na pasta privada do auxiliar e aplica a
mesma validação que recusou a tentativa anterior. Direciona o controlador existente
para `mobile-egress-proof/` e restaura a referência ao terminar. A operação anterior,
suas ACLs e seus arquivos permanecem intactos.

A nova entrada mantém as regras de aceite, despacho único e recuperação existentes.
O invólucro PowerShell confere Python e a entrada; a entrada confere as dependências
antes de carregá-las. Argumentos ausentes ou ambíguos não acionam o auxiliar. O contexto
de argumentos, caminhos de importação e variáveis temporárias é restaurado em `finally`.

Os testes incluem passagem pelo auxiliar Windows real até a fronteira de despacho
simulada. As chamadas Docker são substituídas nos testes. Três chamadas reais sem ação
válida foram recusadas sem criar a operação. A suíte passou em 120 testes, incluindo sete da nova entrada e os 113 anteriores.
A revisão independente não encontrou achados acionáveis. A medição registra as provas.
Essas verificações não substituem o novo ensaio nativo.

[Medição da entrada remota](../medicoes/mobile-egress-entry.json).

## Resultado remoto: falha na leitura do status

Em 06/10, às 14:33 de São Paulo, a entrada passou pela verificação de proprietário
com `adjusted: true` e parou com `JSONDecodeError`. O registro contém somente uma
consulta `sbx daemon status --json`, concluída em 0,977 segundo com código zero.
No fluxo fixado por hash, a interpretação dessa resposta vem antes da próxima consulta.
Isso localiza a falha; não explica por que a resposta não pôde ser interpretada.

O registro anterior guardava metadados do comando, sem stdout/stderr. A resposta
original não pode ser recuperada desses recibos. Duas consultas posteriores daqui,
uma normal e outra com o mesmo auxiliar de proprietário, retornaram JSON válido:
180 bytes, daemon `running` e stderr vazio. Elas não reproduzem a falha remota.

`mobile-egress-proof/` contém a intenção e dois eventos do comando; não há `control.json`
ou `receipt.json`. A execução terminou antes de mudanças de configuração, GETs ou
reinícios. Não há restauração do Docker pendente. Os recibos e os roteiros consumidos
foram preservados. O ajuste de proprietário funcionou; o aceite da rede continua pendente.

O diagnóstico separado `check_mobile_status.py` consulta somente o status, com prazo
de 15 segundos, e salva os bytes originais antes da interpretação, inclusive no timeout.
Reutiliza o auxiliar existente e não aciona o controlador. Uma verificação offline com
três casos confirmou a preservação de respostas inválidas, erro do comando e timeout.
A consulta local real também passou. Esses resultados não somam à suíte anterior de 120 testes.

## Captura remota e consultas iniciais confirmadas

Às 14:41 de São Paulo, o diagnóstico remoto passou com `adjusted: true`: código zero,
180 bytes de JSON válido, daemon `running` e stderr vazio. Os arquivos salvos conferem
com a foto e têm a mesma resposta das consultas locais, byte por byte. Os recibos
anteriores continuam intactos. Isso confirma a consulta no contexto remoto atual;
a resposta histórica que causou `JSONDecodeError` permanece desconhecida.

Depois, a função original de preflight passou nas cinco consultas daqui, através do
registrador de comandos. Uma lista restrita permitiu somente status, inventário e
consulta do processo. Os bytes foram preservados antes de chegar ao interpretador.
Todas as sandboxes estavam paradas e a identidade do daemon permaneceu igual.
Não houve alteração no Docker, GET, reinício ou chamada de IA. Essa verificação cobre
somente os metadados iniciais; configurações globais e A/B/A2 não foram executadas.

## Captura integrada à entrada separada

`captured_mobile_egress.py` usa o auxiliar de proprietário e o controlador existentes.
Acrescenta captura somente ao comando exato `sbx daemon status --json`, mantendo seu
identificador, prazo e resultado. Os bytes de stdout/stderr são gravados e sincronizados
antes da interpretação, inclusive os bytes parciais de timeout. Não há nova tentativa
automática. As respostas dos outros comandos continuam fora do registro.

Cada fluxo tem limite de 64 KiB. Uma resposta maior deixa prefixo, tamanho e hash
registrados e é recusada; falha de gravação também impede a entrega da resposta ao
controlador. A nova operação fica em `captured-mobile-egress-proof/`. Estado e observador
são trocados juntos e restaurados no `finally`; a recuperação mantém o caminho anterior.
Nenhum arquivo ou recibo de uma operação consumida foi alterado.

Nove testes falharam pela ausência da entrada e depois passaram. A suíte conjunta
passou em 129 testes, incluindo os 120 anteriores, em 76,350 segundos. Os testes cobrem
JSON inválido preservado antes da recusa, timeout parcial, ausência de conteúdo de
credenciais no log, resultado e prazo mantidos, limite de tamanho, falha de escrita,
reserva única, recuperação sem despacho e passagem pelo auxiliar Windows real até
a entrada simulada. Docker e rede são substituídos nesses testes.

Uma consulta real de status atravessou a nova captura e o interpretador original;
retornou `running`, com os bytes preservados. Três chamadas reais sem ação válida foram
recusadas. Nenhuma dessas verificações criou a nova operação ou reiniciou serviços.
A revisão independente não encontrou defeitos acionáveis e considerou a entrada pronta
para a prova única. Não se simulou crash de kernel ou falta física de espaço; os erros
de write/flush/fsync foram examinados no código, com falha de captura injetada no teste.
O aceite nativo de rede permanece pendente.

[Medição da captura integrada](../medicoes/captured-mobile-egress-entry.json).

## Comparação da política: falha do controlador

A execução pelo operador em 06/10, às 15:18 de São Paulo, foi consumida e terminou
com `policy_baseline_changed`. Os 24 comandos registrados foram consultas e retornaram
zero. As quatro respostas de status foram preservadas e interpretadas. Não houve GET,
reinício, alteração de configuração ou chamada de modelo. `cleanup.restored=true`,
sem erros; não há limpeza pendente.

A regra de bloqueio geral da sandbox manteve permissões, escopo e metadados. Mudaram
somente seu UUID e o nome automático igual ao UUID. A limpeza de uma prova anterior
havia recriado essa regra, como registra `corrected-egress-proof/control.json`.
O controlador comparava o objeto inteiro com uma fotografia anterior. Assim, recusou
uma mudança de identidade que ele próprio havia causado, sem mudança de permissão.
A comparação existente das políticas externas passou.

Essa falha é do roteiro. O teste de integração devolvia a própria política histórica
como resposta simulada, sem exercitar um identificador regenerado. A checagem real
preparatória havia coberto cinco consultas de metadados, sem a comparação completa de
configuração e política. Esse conjunto não justificava tratar toda a entrada como pronta.

A regressão reproduziu a recusa no controlador original usando os recibos reais.
O candidato separado `exclusive_egress_policy_candidate.py` normaliza somente o par
UUID/nome automático da regra conhecida de bloqueio geral dessa sandbox. Permissões,
escopo, metadados, campos adicionais e demais regras continuam sujeitos à comparação.
Fontes e recibos consumidos permanecem intactos; o candidato recusa execução direta.

A revisão independente encontrou um caso em que remover identificador e nome podia
passar pela normalização. Um teste reproduziu o defeito; a correção mantém ambas as
chaves e usa um marcador interno que não pode ser confundido com campo ausente ou nulo.
A suíte final passou em 68 testes: cinco novos e 63 existentes do controlador, com
fronteiras nativas simuladas. Não houve segunda revisão. Esse resultado não valida a
ligação do candidato à entrada de captura nem substitui A/B/A2 nativo.

[Resultado da operação e correção local](../medicoes/captured-mobile-egress-entry.json).

## Próxima ação

Executar uma vez `run-policy-egress-proof.ps1 -RunApprovedProbe` no terminal do operador,
conforme o [guia](../USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor). Conferir
A/B/A2 e restauração nos novos recibos. Preservar todas as tentativas consumidas; elas
não devem ser repetidas. Se a nova operação falhar, reconciliar somente se houver limpeza
pendente. A preparação abaixo não certifica rede nem autenticação.
R1 continua parcial; R2/R3 e os perfis de execução seguem pendentes. Produção não publicada.

## Correção integrada e sequência inicial completa

`integrated_policy_egress.py` conserva a coleta e as fases do controlador anterior,
mas usa o candidato corrigido como base. O observador também recebe essa base, para
que parsers, comparação de políticas, recuperação e registro de comandos pertençam
à mesma execução. As referências de módulo são restauradas no `finally`.
`policy_egress_entry.py` verifica os hashes e reutiliza a captura de status e a checagem
de proprietário. Sua execução direta é bloqueada; não foi criado outro roteiro PowerShell.

Doze testes falharam pela ausência dessa entrada e depois passaram. Usam as políticas
dos recibos reais e respostas externas simuladas, sem substituir as funções de preflight,
leitura de configurações, parsers ou comparação. A sequência chega à primeira chamada
de `start_guard`, onde o teste interrompe antes de criar processo ou alterar o Docker.
Passam as sete configurações, identidade da VM, políticas e inventário fictício de
credenciais. Mudanças de permissão, política externa, configuração ou imagem são
recusadas antes desse ponto. JSON inválido e timeout mantêm suas capturas; repetição é
recusada e a recuperação não inicia outro trabalho. A checagem Windows de proprietário
é substituída nesses testes; sua prova anterior não foi repetida.

Mais 83 testes passaram contra a nova base: 15 da integração de fases, cinco da
comparação e 63 do controlador. As fases A/B/A2 usam fronteiras nativas simuladas;
não houve GET externo, reinício, mudança de configuração ou chamada de IA. Os 95 casos
desta etapa se sobrepõem às suítes históricas e não devem ser somados a elas.
Fontes e recibos consumidos foram preservados. A revisão independente não encontrou
defeitos acionáveis na integração; conferiu 17 pins de recibos históricos sem divergência.
A execução continua limitada a um coordenador, conforme o contrato existente.

[Medição da integração](../medicoes/policy-egress-integration.json).

[Coletor](2026-10-06-captured-egress-evidence.md) ·
[Resultado nativo anterior](2026-10-06-corrected-egress-proof.md) ·
[Panorama](2026-10-06-panorama-executor.md) ·
[Medição](../medicoes/integrated-egress-controller.json)

## Entrada nativa corrigida preparada

`native_policy_egress.py` liga a entrada validada ao adaptador Windows real, com estado
fixo em `policy-mobile-egress-proof/`. `run-policy-egress-proof.ps1` exige exatamente
uma ação e confere Python e entrada por hash. O Python confere dependências e os três
recibos da última tentativa, que continuam intactos. Recuperação seleciona somente
essa nova operação, sem repetir A/B/A2. Os limites permanecem em três GETs com credencial
fictícia e dois reinícios do Docker Sandboxes, sempre com VMs paradas.

Seis testes novos falharam por entrada ausente e depois passaram. O adaptador de
proprietário e sua checagem de ACL reais chegaram às validações iniciais; as chamadas
nativas do controlador permaneceram simuladas e pararam antes de criar o guard.
A revisão independente não encontrou defeitos acionáveis nesse código.

A verificação seguinte do PowerShell encontrou `Get-FileHash` indisponível sob o
ambiente herdado desta sessão. A nova regressão reproduziu o problema. O roteiro passou
a calcular o mesmo SHA-256 pelo .NET, fechando arquivo e hasher no `finally`, sem instalar
módulos ou mudar configuração global. A regressão passou; não houve segunda revisão.
A suíte final passou em 102 testes, incluindo os 95 anteriores e sete novos, sem falhas,
erros ou skips. O PowerShell foi analisado sem erros; quatro chamadas reais com ação
inválida ou arquivo alterado foram recusadas antes de criar a operação.

Nenhum comando Docker, GET externo ou reinício foi executado nesta preparação. O teste
real ainda depende do terminal do operador, devido às falhas anteriores de socket no
terminal do agente. A nova operação ainda não foi criada. As pastas privadas de fixtures
seguem o comportamento de retenção do auxiliar existente. R1 e o aceite nativo continuam
pendentes; nenhum perfil de produto foi liberado.

[Medição da entrada nativa](../medicoes/native-policy-egress-entry.json).

## Consulta de credenciais falhou na sessão remota

Em 06/10, às 21h50 de São Paulo (07/10, 00h50 UTC), o mantenedor executou a entrada
corrigida uma vez. O resultado foi `stopped/inconclusive/sbx_command_failed`.
O registro de comandos identifica `sbx secret ls --json`: código 1 em 0,147 segundo,
com limite de 15 segundos. As outras 24 consultas retornaram zero.

| Etapa | Evidência desta tentativa |
|---|---|
| Proprietário e permissões | Verificação passou, com `adjusted=True` no terminal remoto |
| Status e configurações | Quatro respostas de status capturadas; sete configurações lidas |
| Identidade e políticas | Comparações passaram; o defeito anterior não se repetiu |
| Inventário de credenciais | Consulta recusada pelo CLI; mensagem original não retida |
| A/B/A2 | Nenhuma fase iniciada |
| Efeitos e limpeza | Zero intenções de alteração/reinício, zero GET do ensaio, zero IA; restauração confirmada |

O erro ocorreu antes da criação do intermediário de rede e da credencial fictícia.
`control.json` registra listas vazias de intenções, reinícios, intermediários, regras
criadas e fases; `receipt.json` de alterações de settings não existe. Não há limpeza
pendente. Os 31 hashes de fontes, recibos e capturas foram preservados.

A consulta isolada retornou zero localmente. Uma segunda comparação pelo auxiliar
Windows original, com diretório temporário privado, também retornou zero e JSON
válido: 94 bytes, mesmo hash da resposta anterior, stderr vazio. O auxiliar precisou
ajustar o proprietário no terminal remoto, mas não no local. Essas observações não
demonstram a causa histórica. Valores e nomes de credenciais não foram impressos ou
salvos pelo diagnóstico.

Há uma lacuna no roteiro: `Sbx.call` troca qualquer retorno não zero por
`sbx_command_failed`; o observador guarda comando/código, e a captura de bytes cobre
somente o status do daemon. Assim, a mensagem dessa falha de inventário foi perdida.
A janela correspondente do log do daemon não trouxe erro que explicasse a consulta.
Não há base para atribuir a falha a autenticação, SSH, permissões ou indisponibilidade.

Próximo: obter o erro dessa consulta no contexto remoto, em diagnóstico somente
leitura. Não preparar outro A/B/A2 antes disso. O roteiro consumido e seus recibos
continuam intactos; não há novo comando para o operador nesta rodada. A medição
mantém os 102 testes como evidência histórica da preparação, sem convertê-los em
aceite de rede. R1 segue parcial; perfis de produto bloqueados e produção não publicada.

[Medição](../medicoes/native-policy-egress-entry.json) ·
[Guia atualizado](../USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor).

## English overview

The separate controller now routes B through the evidence collector and retains the
existing A/A2, orchestration and cleanup code. Offline tests exercise the complete
sequence, persistent results, refusal to repeat a consumed attempt, and cleanup without
A2 when evidence is absent. Failed postchecks also prevent advancement and acceptance.

B uses the preserved real refusal event; Docker boundaries, positive replies and cleanup
are fixtures. This validates controller wiring, not a new native network proof. No native
operation was created during integration, and old receipts remain unchanged. The
integration suite passed 106 tests, including
15 integration tests. Two important review findings were reproduced and fixed: preserving
daemon-transition errors for safe cleanup and requiring a durable postcheck-complete
marker after coordinator interruption. Regressions passed; no second review was performed.

The operator entry is now prepared. It requires exactly one action, checks twelve local
bootstrap sources before controller import and uses a separate single-use directory.
The independent entry review found four unpinned local dependencies; a regression
reproduced the issue and the entry now verifies them. No second review was performed.
Three real invalid-action calls were refused without creating a native operation.
The final suite passed 113 tests, including seven entry tests, with no failures, errors
or skips. These include the previous 106; the counts must not be added together.

A read-only metadata preflight timed out; a later daemon-status query returned running.
This does not establish complete readiness or the timeout cause. No new native operation,
GET, restart or model call occurred. Next: one maintainer run from normal PowerShell,
within the approved three-GET/two-restart limits, then receipt and restoration checks.
The subsequent native attempt completed five metadata queries and stopped because its
files were owned by Administrators rather than the current user. No control record,
Docker changes or GETs occurred; no Docker reconciliation is needed. Receipts and their
ownership were preserved. A synthetic diagnostic reuses the existing process-owner
adapter and passed locally without an owner change. The operator only has phone access;
the remote diagnostic then passed with `adjusted: true`. A separate native entry now
wraps the existing controller in that verified owner adapter, validates a private file
before reservation and records only `mobile-egress-proof/`. Existing receipts remain
unchanged. Unit tests replace Docker boundaries; native acceptance is still pending.
That mobile run passed its owner check but failed parsing its first daemon-status reply
despite exit code zero. The original raw response was not retained. No control record,
Docker changes or cleanup occurred. Two later local status queries returned valid JSON,
including one through the owner adapter; they do not explain the remote failure.
A separate read-only diagnostic now saves original bytes before parsing. One offline
test covers three failure cases; a real local status capture also passed. Next: capture
the remote reply with that diagnostic, preserving all consumed attempts. That capture
subsequently passed, matching the local reply byte for byte. All five original preflight
queries then passed locally through the command recorder, with stopped sandboxes and
no Docker mutations. The old failure remains unexplained. A separate entry now retains
only exact status replies before parsing, preserving partial timeout bytes, original
deadlines and strict refusal. Other command payloads stay unrecorded. Oversized replies
retain up to 64 KiB per stream and are refused; capture-write failures also stop the call.
Nine new tests passed; the aggregate suite passed 129, including the previous 120.
One real read-only status capture passed and three invalid CLI invocations were refused.
At preparation time, independent review found no actionable defects and considered the
entry ready for one operator run. Kernel crashes and physical disk exhaustion were not simulated; write/flush/fsync
propagation was inspected statically and capture failure was injected in a test.

The subsequent native operation was consumed at 15:18 São Paulo time. All 24 recorded
commands were read-only queries and returned zero; four valid status replies were
retained. No GET, restart, configuration change or model call occurred. Cleanup is
verified. The controller rejected a deny-all rule UUID regenerated by earlier cleanup,
despite unchanged permissions. Only its ID and automatic name differed. The existing
external-policy check passed. A test had supplied the historical policy itself as the
current response, missing this case; the earlier real preflight covered only five
metadata queries. The controller's readiness had been overstated.

A separate offline candidate normalizes only that known rule's validated UUID/name
pair while preserving all other comparisons. The original controller reproduces the
failure with the saved receipts. Independent review found a missing-ID acceptance case;
its regression failed, the fix was applied, and all 68 final tests passed (five new,
63 existing controller cases). No second review was run. The candidate's direct CLI
is disabled. Consumed sources and receipts are unchanged. Next: integrate the candidate
and validate all initial checks locally. No new operator command, replay or cleanup is
needed. Full native A/B/A2 acceptance remains pending.

The correction has since been integrated in `integrated_policy_egress.py` and an
import-only entry reusing status capture and the owner check. Twelve new tests run
the original initial checks and parsers against simulated subprocess replies and saved
native policies, stopping before the first guard process. They cover all seven settings,
VM identity, policy comparisons, synthetic credential inventory, refusal paths, recovery
and replay protection. The Windows owner check is mocked in these tests; its earlier
proof was not repeated. Another 83 tests passed against the corrected controller,
including simulated A/B/A2 phases. No external GET, Docker command or model call occurred.
Consumed artifacts are unchanged. Next: prepare a native entry pinned to this integration;
real A/B/A2 acceptance remains pending. That integration checkpoint is now followed by the native entry below.
R1 remains partial and unpublished.

The native entry is now prepared: `native_policy_egress.py` connects the corrected
integration to the actual Windows owner adapter; its PowerShell launcher pins Python
and sources, requires exactly one action, and uses `policy-mobile-egress-proof/` only.
Earlier receipts are pinned and preserved. Independent review found no actionable
issues. A subsequent CLI check found `Get-FileHash` unavailable in the inherited
PowerShell environment. A regression reproduced it; a .NET SHA-256 helper fixed it
without changing pins or global configuration. There was no second review. All 102
final tests passed, including seven new cases; four real refusal checks and PowerShell
parsing also passed. Docker replies remained simulated; no native operation was created.
That preparation was followed by the operator's October 6, 21:50 run. The new entry
passed ownership, settings and policy checks, then `sbx secret ls --json` exited 1
in 0.147 seconds. The other 24 queries passed. No mutation, external probe request,
restart or model call occurred; cleanup is verified. Do not replay or reconcile it.
Two local queries passed, including one with the existing Windows helper. Both gave
the same 94-byte JSON response; no credential contents were retained. This does not
explain the remote failure. The wrapper discarded stderr and the daemon log did not
recover its cause. Next: obtain only that query's error in the remote context before
preparing another full probe. No new operator command is prepared. All 31 frozen
artifact hashes are preserved. Native A/B/A2 and production acceptance remain pending.

ATRASO: main 1
