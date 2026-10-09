# Prova de memória Claude do piloto

Frente: lote A, uma sessão Claude, 300 segundos, 24 ferramentas e assinatura existente.
O runner de desenvolvimento é `tests/pilot_claude.py`; não integra o instalador nem
habilita os perfis do executor Docker. O lote autorizava uma tentativa de retomada.

Em 9/out, o operador enviou o recibo `prepared_no_model_prompt`: inicialização
concluída em 3,065 s no Windows, zero prompts, árvore encerrada e autenticação original
preservada. A execução seguinte terminou por OAuth expirado, com um prompt registrado
e contadores de tokens zerados. O pacote já tem uma tentativa reservada:
preservar seus recibos e marcador, renovar o login e revisar qualquer nova tentativa.
[Registro e limites da prova](relatorios/2026-10-09-p06-correction.md#preparo-no-windows).

O operador concluiu a renovação do login e reportou `loggedIn: true`,
`authMethod: claude.ai` e `apiProvider: firstParty`. A tentativa original continua
preservada. Duas suposições de plataforma nos testes foram
[corrigidas](relatorios/2026-10-09-p06-windows-tests.md); a confirmação Windows
passou nos 13 testes no PC do operador. O novo pacote r2 foi preparado com zero
prompts e revisado. O mantenedor aprovou uma sessão e exigiu o modelo mais barato:
a execução de r2 com modelo padrão foi substituída pelo preparo explícito de Haiku.
A [tentativa Haiku](relatorios/2026-10-09-p06-haiku.md) foi executada e falhou por
OAuth expirado sem renovação. Registrou um prompt e zero tokens reportados;
processos e credencial temporária foram limpos. A autorização está consumida.
Os metadados posteriores confirmaram vencimento cerca de 20 segundos antes do
preparo e 25 segundos antes do run. O runner recebeu a checagem descrita abaixo;
a renovação OAuth e o aceite de memória continuam pendentes.

## Validade do login antes do preparo e da reserva

A [correção de admissão](relatorios/2026-10-09-p06-expiry-guard.md) exige mais de
seis minutos de validade em `expiresAt` antes de criar o pacote ou reservar o run.
O campo deve ser um inteiro em milissegundos Unix. A cópia temporária também passa
pela checagem antes de liberar o cliente. Essa validação local não comprova aceitação
ou renovação pelo fornecedor.

`subscription_login_expired_or_expiring` pede renovação do login original antes
de continuar. `subscription_expiry_unknown` indica metadados ausentes ou inválidos;
não editar credenciais nem enviá-las no chat. A recusa anterior à reserva não cria
`started.json`; uma recusa posterior à reserva conserva o marcador. Nenhuma dessas
checagens libera as tentativas antigas. Preparar nova revisão em pacote separado,
com `--model claude-haiku-5-5`, e registrar sua operação antes de pedir autorização
para outra inferência. Não substituir o código dentro de um pacote preparado.

## Pacote corrigido preparado

O operador confirmou os 17 testes Windows em 12,776 s na revisão
`47a81504deeafe59920036d3cf39a422a7317f81`, renovou o login interativo e preparou
`p06-package-20261010-expiry` com `--model claude-haiku-5-5`.
O recibo registra `prepared_no_model_prompt`, zero prompts e conclusão em 4,968794 s;
árvore encerrada, credencial temporária removida e bytes do login original preservados.

- Operação: `164e5438-0cac-4089-845c-f1e3cc60db04`.
- SHA-256 de `setup.json`: `45ec8706433bbe3866c17d79d963df7e3617eaaf224ca15f4c27a24e87ea8ac4`.
- Escopo aprovado: uma sessão, um prompt, até 300 s e 24 ferramentas, esforço
  `medium`, `claude-haiku-5-5`, assinatura existente, sem API adicional ou repetição automática.

Estado: aprovado para uma tentativa, execução pendente. O mantenedor respondeu
«aprovado pr» ao pedido específico desta operação em 9/out. Essa autorização cobre
a sessão Haiku descrita acima; as tentativas anteriores permanecem consumidas.
Manter a revisão fixada e todos os recibos anteriores.
O runner volta a verificar validade do login antes da reserva; o preparo não prova
que o fornecedor aceitará a inferência. [Evidência](relatorios/2026-10-09-p06-expiry-guard.md#confirmação-no-windows).

Para executar a operação aprovada no Windows, conferir o hash e chamar `run`:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ycPkg = 'C:\Users\rmfon\YoungCrowHarness-review-20261001\.runtime\p06-package-20261010-expiry'
    $ycSetup = "$ycPkg\.runtime\test-campaign-20261010\claude-p06\setup.json"
    $ycHash = (Get-FileHash -LiteralPath $ycSetup -Algorithm SHA256).Hash
    if ($ycHash -ne '45ec8706433bbe3866c17d79d963df7e3617eaaf224ca15f4c27a24e87ea8ac4') {
        throw 'Pacote diferente do aprovado. Envie esta mensagem no chat.'
    }
    python -B "$ycPkg\tests\pilot_claude.py" run
    if ($LASTEXITCODE) { throw 'Tentativa encerrada com falha. Preserve a pasta e envie a saída; não repita.' }
}
```

A reserva do runner impede reutilizar a tentativa. Se falhar, preservar o resultado
e revisar o diagnóstico antes de qualquer repetição.

## Modelo econômico autorizado

Esta seção registra a decisão e o preparo da tentativa já consumida. O diagnóstico
atual está no relatório acima; as instruções históricas não autorizam repetição.

O mantenedor aprovou uma única sessão e, antes da execução, restringiu o teste ao
modelo mais barato. O [catálogo oficial](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/claude-api/shared/models.md)
indica `claude-haiku-5-5`: US$ 0,10/0,50 por milhão de tokens de entrada/saída até
100 mil tokens de entrada, ou US$ 0,50/2,50 acima disso. Esses são preços de API,
usados para comparar modelos; este ensaio continua na assinatura existente.

Preparar um pacote irmão `p06-package-20261010-haiku` na mesma revisão `6481a91`,
usando `prepare --model claude-haiku-5-5`. Preservar os dois pacotes anteriores;
não executar r2 com `default` nem alterar seu `setup.json`. A aprovação agora cobre
somente uma sessão com esse modelo, um prompt, até 300 s e 24 ferramentas, esforço
`medium`, sem API adicional nem substituição por modelo mais caro. Não exigir
nova aprovação por esta restrição explícita do mantenedor.

O suporte ao Haiku 5.5 foi anunciado no [Claude Code 2.1.293](https://github.com/anthropics/claude-code/blob/2301018b1f61073c501a8e7a4813ef48c239163b/CHANGELOG.md#21293);
o runner fixa 2.1.220. A compatibilidade do ID explícito precisa ser conferida no
preparo sem prompt; não atualizar o cliente automaticamente. Mesmo um preparo
positivo não prova que o fornecedor aceitará a inferência. Registrar a nova
operação e o hash retornados sob esta aprovação antes do comando `run`.

O runner já passa o modelo preparado em `--model`, sem `--fallback-model`, e ignora
configurações externas de seleção. O catálogo oficial declara ausência de fallback
no servidor para Haiku 5.5. Conferir `observed_models` no resultado: o verificador
registra os modelos observados, mas não compara automaticamente com o solicitado.
Uma recusa encerra a tentativa; não substituir por outro modelo ou repetir.

## Roteiro da tentativa Haiku registrada

O bloco abaixo foi executado no rmfon e fica como histórico. Não repetir, apagar
marcadores ou mudar a pasta para renovar a tentativa. Ele não repete os 13 testes do código inalterado.
Uma pasta existente ou qualquer falha interrompe o fluxo, preservando os recibos.
O registro de autorização fica fora do contexto que o modelo pode ler.
O preparo passou; a execução terminou com a falha OAuth registrada acima.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ycHaiku = 'C:\Users\rmfon\YoungCrowHarness-review-20261001\.runtime\p06-package-20261010-haiku'
    $ycRevision = '6481a9174070e9c2fbc65fc66950381089136758'
    $ycModel = 'claude-haiku-5-5'
    if (Test-Path -LiteralPath $ycHaiku) { throw 'Pasta já existe. Preserve e envie a mensagem no chat.' }

    git clone --depth 1 --filter=blob:none --sparse --no-checkout --branch feat/isolated-executor https://github.com/Matheusrpc/YoungCrowHarness.git $ycHaiku
    if ($LASTEXITCODE -ne 0) { throw 'Clone falhou.' }
    git -C $ycHaiku fetch --depth 1 origin $ycRevision
    if ($LASTEXITCODE -ne 0) { throw 'Busca da revisão falhou.' }
    git -C $ycHaiku sparse-checkout set scripts skills/retrieve-memory tests examples/delivery-board
    if ($LASTEXITCODE -ne 0) { throw 'Seleção de arquivos falhou.' }
    git -C $ycHaiku checkout --detach $ycRevision
    if ($LASTEXITCODE -ne 0) { throw 'Checkout falhou.' }
    $ycHead = git -C $ycHaiku rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $ycHead -ne $ycRevision) { throw 'Revisão divergente.' }

    python -B "$ycHaiku\tests\pilot_claude.py" prepare --model $ycModel
    if ($LASTEXITCODE -ne 0) { throw 'Preparo falhou. Não executar nem repetir.' }
    $ycBase = "$ycHaiku\.runtime\test-campaign-20261010\claude-p06"
    $ycSetup = Get-Content -LiteralPath "$ycBase\setup.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $ycReceipt = Get-Content -LiteralPath "$ycBase\prepare-receipt.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $ycHash = (Get-FileHash -LiteralPath "$ycBase\setup.json" -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ycSetup.model -cne $ycModel -or $ycSetup.git_revision -ne $ycRevision -or
        $ycSetup.effort -ne 'medium' -or $ycSetup.seconds -ne 300 -or $ycSetup.tool_calls -ne 24 -or
        $ycReceipt.setup_sha256 -ne $ycHash -or $ycSetup.operation_id -ne $ycReceipt.operation_id -or
        $ycReceipt.state -ne 'prepared_no_model_prompt' -or $ycReceipt.native_prompt_count -ne 0 -or
        $ycReceipt.supervision.exit_code -ne 0 -or $ycReceipt.supervision.tree_reaped -ne $true -or
        $ycReceipt.temporary_credential_removed -ne $true -or $ycReceipt.original_auth_unchanged -ne $true) {
        throw 'Pacote não confere com a autorização. Não executar.'
    }
    [ordered]@{
        operation_id = $ycSetup.operation_id; setup_sha256 = $ycHash; model = $ycModel
        approved_sessions = 1; approved_prompts = 1; seconds = 300; tool_calls = 24
        approval = 'Aprovado no chat, depois restrito ao modelo mais barato; assinatura existente.'
        supersedes_prepared_operation = '323ef492-4967-4d13-bd71-8afe0bc2ed00'
    } | ConvertTo-Json | Set-Content -LiteralPath "$ycBase\authorization-haiku.json" -Encoding UTF8

    Write-Output "Executando uma única sessão com $ycModel."
    python -B "$ycHaiku\tests\pilot_claude.py" run
    if ($LASTEXITCODE -ne 0) { throw 'Tentativa encerrada com falha. Preserve a pasta e envie a saída; não repita.' }
}
```

Preservar o recibo e os eventos. A inicialização registrou Haiku 5.5; a falha OAuth
impediu o aceite de memória. Não mudar o modelo nem repetir a chamada.

## Renovar o login após a falha OAuth

No PowerShell do operador, usar o perfil original:

```powershell
claude auth login
```

Concluir o login com a conta da assinatura Claude. Depois, conferir apenas o estado:

```powershell
claude auth status | ConvertFrom-Json |
    Select-Object loggedIn, authMethod, apiProvider
```

Esperado: `True`, `claude.ai`, `firstParty`. Esse comando confirma o estado que
o cliente apresenta; não prova inferência nem libera a repetição de `run`.
Preservar a pasta, recibos e `started.json` da tentativa. Não usar `--console`,
que seleciona cobrança API. Os subcomandos estão no
[changelog oficial da versão 2.1.220](https://github.com/anthropics/claude-code/blob/7ef6eec9d9ba84ea6f233f26c45f1df5c5991843/CHANGELOG.md#L3568).

## Preparar no Windows

Este procedimento descreve o preparo original. Não o repetir em outra pasta para
contornar o marcador da tentativa de 9/out.

Requisitos: Python 3.11+, Git/Git Bash, Claude Code 2.1.220 autenticado por assinatura
e as skills `karpathy` e `ponytail` já existentes em `%USERPROFILE%\.codex\skills`.
`retrieve-memory` e o vault público vêm desta revisão do repositório.
Versão diferente ou fonte ausente interrompe a preparação; não instala ou atualiza nada.

Use uma cópia desta branch que contenha o runner. Para obter somente os diretórios
necessários e preservar o checkout original, cole este bloco no PowerShell:

```powershell
$ycP06 = 'C:\Users\rmfon\YoungCrowHarness-review-20261001\.runtime\p06-package-20261010'
if (Test-Path -LiteralPath $ycP06) { throw 'Pasta já existe. Preserve os recibos e confira o estado antes de repetir.' }
git clone --depth 1 --filter=blob:none --sparse --branch feat/isolated-executor https://github.com/Matheusrpc/YoungCrowHarness.git $ycP06
if ($LASTEXITCODE) { throw 'Clone falhou.' }
git -C $ycP06 sparse-checkout set scripts skills/retrieve-memory tests examples/delivery-board
if ($LASTEXITCODE) { throw 'Seleção de arquivos falhou.' }
python "$ycP06\tests\pilot_claude.py" prepare
```

O Git baixa código público. O preparo copia apenas o vault e as três skills para
um consumidor descartável, confere versão/login, inicializa o protocolo e encerra
os processos. Não envia prompt de usuário ao modelo. Autenticação e inicialização
podem acessar o fornecedor; não se afirma ausência de tráfego de rede.
O modelo permanece no padrão do cliente, com esforço `medium`, como no ensaio
histórico. `--model NOME` permite explicitar a escolha **durante o preparo**;
o recibo vincula a escolha e os hashes do pacote, cliente e contexto.

Se o executável não for encontrado, use `prepare --claude CAMINHO_DO_CLAUDE.EXE`.
O launcher npm `.ps1` não é o executável. Uma pasta de skills diferente pode ser
informada por `--skills-dir CAMINHO`. Não use dados ou credenciais fictícios com
o cliente real, nem exponha o perfil ou os eventos brutos no GitHub.

Resultado esperado: `state: prepared_no_model_prompt`, `native_prompt_count: 0`,
árvore encerrada e cópia temporária da credencial removida. O recibo fica na cópia
do pacote, em `.runtime/test-campaign-20261010/claude-p06/prepare-receipt.json`.
Uma falha preserva o material de diagnóstico; não apagar a pasta para tentar novamente.

## Nova operação preparada em 9/out

Após renovar o login, o operador preparou uma cópia irmã `p06-package-20261010-r2`,
fixa em `6481a9174070e9c2fbc65fc66950381089136758`. Antes do preparo, os 13 testes
locais passaram no Windows em 9,373 s. O recibo reportou inicialização concluída
em 13,889191 s, zero prompts, árvore encerrada, credencial temporária removida e
autenticação original preservada. A [medição](medicoes/2026-10-09-p06-windows-tests.json)
registra essa evidência enviada pelo operador. O CI do PR `37984416730` passou
integralmente, incluindo P06; o push `37984411482` preserva a falha anterior ao P06.

| Identificação | Valor |
|---|---|
| Operação preparada | `323ef492-4967-4d13-bd71-8afe0bc2ed00` |
| SHA-256 de `setup.json` | `6d1c2bd27f6c35308712310ab640205b06d5f19de5836d60b00c1730431d9811` |
| Escopo proposto | Uma sessão nova, um prompt, até 300 s e 24 ferramentas |
| Cliente e autenticação | Claude Code 2.1.220, assinatura `claude.ai`/`firstParty` |
| Modelo e esforço | Padrão do cliente, `medium`, conforme preparo |
| Estado | Preparo concluído; execução com modelo padrão substituída pela restrição Haiku |

A revisão independente não encontrou impedimento para apresentar essa operação
à autorização do mantenedor. Ela não envia um prompt nem aceita a memória recuperada.
Os campos `approval_revision` e `planned_local` de `setup.json` são metadados
históricos fixos no runner; não autorizam r2. O preparo acima fica como histórico;
vincular a aprovação atual à nova operação Haiku, sem editar os pacotes anteriores.
Manter a cópia Windows nesta revisão, mesmo que a documentação avance no GitHub.

Comando histórico de r2, não executar após a restrição de modelo acima:

```powershell
python -B 'C:\Users\rmfon\YoungCrowHarness-review-20261001\.runtime\p06-package-20261010-r2\tests\pilot_claude.py' run
```

O runner reconfere os hashes e reserva a nova tentativa antes de iniciar processos.
Uma falha não libera repetição. O preparo não prova aceitação da inferência pelo
fornecedor. Um resultado positivo ainda exige a revisão semântica descrita abaixo.

## Execução da tentativa registrada

O horário original era **10/out, 18h30, America/Sao_Paulo**. O operador executou
o pacote em 9/out; essa tentativa ficou registrada apesar da falha de autenticação.
Não há agendador ou notificação automática. Comando usado, apenas para referência:

```powershell
python 'C:\Users\rmfon\YoungCrowHarness-review-20261001\.runtime\p06-package-20261010\tests\pilot_claude.py' run
```

O comando reserva a tentativa antes de liberar processos. Falha, interrupção ou
fim da sessão mantêm o marcador: repetir `run` não envia outro prompt. O diretório
de 3/out e a prova Codex anterior permanecem intactos. Não mudar o modelo, editar
`setup.json`, apagar marcadores ou usar outra cópia para renovar a tentativa.

O supervisor existente contém a árvore e impõe o prazo de 300 segundos, incluindo
a preparação do cliente dentro do processo. A limpeza e sua medição podem ampliar
o tempo total do comando; não concedem tempo adicional ao cliente. O callback
`PreToolUse` admite no máximo 24 ferramentas antes de liberá-las. Uma solicitação
fora do escopo ou acima do teto recebe recusa e interrompe o cliente.

Só admite `Read`, `Glob`, `Grep` sobre o consumidor e `Bash` com `sha256sum --`
seguido de caminhos literais previamente fotografados. Mudanças no contexto
interrompem a prova. Não há shell arbitrário, agentes ou MCPs externos.
Isso é controle das ferramentas deste ensaio, não aceite do sandbox de YC-203.

As configurações de filesystem do Claude ficam desligadas por `--setting-sources=`;
as skills são lidas explicitamente no consumidor. Descoberta automática registrada
na inicialização é informativa e não substitui `smoke_clients.py`. Não se afirma
que este ensaio comprova a descoberta de toda a instalação do harness.

## Ler o resultado

O recibo de execução confere um prompt, uma sessão, resultado Claude de sucesso,
admissões, conclusões, saídas das ferramentas, UUIDs, hashes e preservação dos arquivos.
Exige a operação atual e a última retomada, além da feature, decisão e implementação.
O estado positivo automático é `evidence_verified_pending_semantic_review`.

Em 9/out, o terminal trouxe `subtype: success` junto de `is_error: true` e a mensagem
`Failed to authenticate: OAuth session expired and could not be refreshed` no campo
`result`. O subtipo sozinho não prova sucesso. `auth status` e inicialização haviam
passado; isso não comprovou renovação OAuth nem aceitação da chamada pelo fornecedor.

Ainda é necessário confrontar um handoff bem-sucedido com as notas citadas: decisão vigente,
desenvolvimento, publicação observada e próxima ação. Um campo preenchido não prova
que seu significado esteja correto. Só depois dessa revisão registrar o aceite P06.
O recibo resumido pode ser enviado ao responsável por essa revisão; eventos e
logs completos ficam privados. Uma falha de parsing ou limpeza também conserva
a captura recebida e a supervisão para diagnóstico, sem repetir a sessão.

Se o processo principal for encerrado abruptamente, a remoção da cópia temporária
de autenticação pode não ocorrer. O marcador continua bloqueando outra tentativa:
conferir os processos e os arquivos próprios antes de reconciliar, sem apagar a
autenticação original. Não há limpeza ou repetição automática após estado incerto.

## Contrato e verificação

O protocolo usa o SDK oficial na revisão que embarca CLI 2.1.220:
[`cadaa636a221f14e587a2e21a9b9532ce60adba3`](https://github.com/anthropics/claude-agent-sdk-python/commit/cadaa636a221f14e587a2e21a9b9532ce60adba3).
Os [callbacks](https://github.com/anthropics/claude-agent-sdk-python/blob/cadaa636a221f14e587a2e21a9b9532ce60adba3/src/claude_agent_sdk/_internal/query.py#L220)
e as [fontes de configuração](https://github.com/anthropics/claude-agent-sdk-python/blob/cadaa636a221f14e587a2e21a9b9532ce60adba3/src/claude_agent_sdk/types.py#L1987)
foram conferidos no código/documentação; o SDK não é instalado pelo runner.
A correspondência documental e as simulações não substituem o ensaio com o cliente real.

Regressões sem modelo: `python -B -m unittest discover -s tests -p test_pilot_claude.py -v`.
O CI executa essas provas também no Windows, com um cliente fictício local.
Consulte a [campanha](TEST-RUN-2026-10-10.md) e a
[auditoria do original](relatorios/2026-10-09-p06-runner-review.md).

## English overview

Run `python tests/pilot_claude.py prepare` from this revision on the operator's
Windows machine. Preparation checks the subscription, client version and protocol
without sending a user prompt. At the approved time, `run` reserves one attempt,
uses the existing process supervisor and admits at most 24 tools before execution.
Filesystem settings are disabled; the three staged skills are read explicitly.
The verifier checks Claude evidence and requires a separate semantic review.
No Docker profiles are enabled, no Codex session is repeated, and no native Claude
success is inferred from fixtures. Original receipts and failed attempts are preserved.
The operator supplied a successful Windows preparation receipt on Oct 9, followed
by a failed attempt with expired OAuth and zero reported token counts. Preserve the
reserved attempt, renew login and review any retry. Retrieval remains unverified.
The operator subsequently renewed login. All 13 corrected tests passed on the
operator's Windows PC in 9.373 seconds. A separate r2 package pinned to `6481a91`
completed preparation with zero prompts and preserved credentials. Its operation
and setup hash are recorded above. The maintainer approved one bounded session,
then restricted it to the cheapest model. Prepare a separate package with explicit
`claude-haiku-5-5`; do not run default-model r2 or alter its setup. Approval covers
one session/prompt, 300 seconds and 24 tools through the existing subscription,
with no more expensive fallback. Native compatibility with pinned CLI 2.1.220 and
retrieval remain unverified; Haiku 5.5 support was announced in CLI 2.1.293.
Keep both earlier packages unchanged. No additional approval is required merely
to apply this explicit restriction.

The Haiku attempt has now been executed and failed with expired OAuth that could
not be refreshed. Initialization reported the selected model, one prompt was
recorded and token counters were zero. Cleanup passed; the reservation remains
consumed. Diagnose the authentication source without starting another session.

Metadata subsequently confirmed that the credential expired before preparation.
The corrected runner checks for more than six minutes of declared validity before
creating the package or reserving a run, and rechecks the actual temporary copy.
Missing or malformed expiry is refused without printing credential contents.
This does not prove provider acceptance or fix refresh. Preserve old packages and
prepare a separate corrected revision before reviewing any new inference.

The corrected `47a8150` revision passed all 17 tests on the operator's Windows PC.
Following interactive login, preparation completed in 4.968794 seconds with zero
prompts and confirmed cleanup. Operation `164e5438-0cac-4089-845c-f1e3cc60db04`
was approved for one bounded Haiku session under the existing subscription.
Execution and native retrieval acceptance remain pending.
