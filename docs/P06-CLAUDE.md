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
e a revisão de uma nova tentativa de retomada permanecem pendentes.

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
The operator subsequently renewed login. Two test portability assumptions were
corrected and verified locally; Windows confirmation and retry review remain pending.
