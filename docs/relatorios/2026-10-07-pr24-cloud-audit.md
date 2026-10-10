# Auditoria do PR #24 na cloud

Frente: revisão do executor isolado publicado em `feat/isolated-executor`, em 7 de outubro de 2026. Sem implementação de correções, chamadas de modelos ou publicação.

O código que faltava na auditoria anterior chegou à cloud. Foram reproduzidos **dois novos defeitos P2**, além da persistência dos dois achados anteriores. A suíte completa passou, mas não cobre esses casos. O checkpoint continua adequado como rascunho de desenvolvimento; esta auditoria não certifica o executor nativo.

## Revisão e escopo

- PR: [#24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
- Base: `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`.
- Revisão auditada: `b801bec963e8af4af921b8c5473d3884ee5a7a03`, conferida novamente na branch remota e em `refs/pull/24/head` ao fim das verificações.
- Diff: 125 arquivos. Os nove hashes de implementação do handoff conferem integralmente.
- O checkout existente passou para esse commit, em HEAD destacado, preservando os relatórios locais anteriores. Nenhum worktree foi criado.

Três revisores somente leitura examinaram guardian/launcher, relay/egress e reserva/preflight. O executor principal revisou integração, seleção de ambiente, alterações de setup/adoção, testes e evidências. As hipóteses foram separadas dos defeitos reproduzidos. Não foi executado o desenho de continuidade do handoff: o pedido desta frente é auditoria.

## PR24-F1 — P2: a primeira reserva falha no Linux com umask 022

Local: [scripts/mission_execution.py:104](../../scripts/mission_execution.py#L104), no bloco de criação de `reclaim.lock`.

`Path.open('xb')` cria o arquivo usando `0666 & umask`. Sob a máscara comum `022`, o lock nasce com modo `0644`. No POSIX, `protect_for_storage()` apenas inspeciona; ele não aplica `0600`. O `check_private()` seguinte recusa o arquivo que acabou de ser criado.

**Reprodução real de filesystem**, em diretório temporário privado, sem substituir os verificadores de permissão:

| Caso | Resultado |
|---|---|
| Primeira reserva, umask `022` | `execution_storage_unprotected`; lock `0644`; ledger ausente |
| Nova tentativa no mesmo diretório, agora sob `077` | Continua recusada, pois o arquivo existente permanece `0644` |
| Controle com diretório novo e umask `077` | Reserva criada; lock `0600`; ledger presente |

Impacto: o componente não consegue registrar sua primeira operação em uma configuração Linux comum e deixa um estado parcial que bloqueia a tentativa seguinte. Isso acontece antes de qualquer efeito Docker. Não é alegação de falha em um runner Linux já certificado, pois essa certificação ainda não existe.

Correção recomendada: criar o arquivo novo de forma exclusiva e já com modo `0600`. Preservar as recusas de permissões inseguras em arquivos existentes; não reparar registros antigos recursivamente. Acrescentar regressão POSIX real sob umask `022`: a suíte atual substitui os verificadores e a proteção por mocks nesses testes de reserva.

## PR24-F2 — P2: timeout de Git na primeira leitura escapa do diagnóstico estruturado

Local: [scripts/mission_environment.py:114](../../scripts/mission_environment.py#L114).

Quando `.operacao-local/execution/` ainda não existe, `read_selection()` chama `_git_boundary()` diretamente. Um `subprocess.TimeoutExpired` não é capturado por `read_selection()` nem por `missions.main()`. A mesma chamada feita por `_storage()` já converte esse erro para um diagnóstico sanitizado.

**Reprodução com timeout injetado somente na consulta Git**, usando a entrada real da CLI:

- Projeto sem armazenamento: `environment show --json` deixa escapar `TimeoutExpired`, não produz JSON e a exceção conserva o comando e o marcador fictício de caminho privado.
- Controle com armazenamento existente: o mesmo timeout retorna código 2 e JSON com `execution_storage_unprotected`, fase `git_boundary` e razão `git_query_timeout`; o marcador privado não aparece.

Impacto: a primeira consulta perde justamente a classificação de falha necessária para orientar setup e diagnóstico. Não foi observado vazamento de credencial real; a prova usa um marcador fictício para demonstrar que o comando bruto escapa.

Correção recomendada: aplicar a conversão já existente `storage_error(..., 'git_boundary')` também ao caminho inicial. A regressão deve chamar a CLI com e sem armazenamento existente e verificar saída JSON, motivo e ausência do marcador.

## Estado dos achados anteriores

As reproduções da [auditoria da base](2026-10-07-cloud-audit.md) foram repetidas no SHA do PR:

| Achado anterior | Resultado atual |
|---|---|
| F1: interrupção de projeção seguida de revisão | Continua reproduzível: revisão, `repair` e replay retornam `conflict`; reparar antes da revisão passa |
| F2: catálogo Codex com `supportedReasoningEfforts: [null]` | Continua reproduzível: `AttributeError` escapa e a resposta JSON fica vazia |

Os pontos atuais são `scripts/mission_vault.py:82` e `scripts/mission_clients.py:161`. São defeitos herdados da base, não duas regressões adicionais introduzidas pelo PR #24. A ausência do código, registrada no relatório anterior, está resolvida.

## Validação executada

| Verificação nesta cloud | Resultado |
|---|---|
| Suíte completa `python3 -B -m unittest discover -s tests -v` | 494 testes: **474 aprovados, 20 skips**, zero falhas; 214,826 s |
| Testes Node do delivery-board | **8 aprovados**, zero falhas/skips |
| `smoke_execution_setup.py` | **8 combinações** novo/migrado × Claude/Codex × local/dedicado passaram |
| `smoke_mission_runtime.py --client both` | **2 consumidores**, diagnóstico/replay/interrupção/reconciliação simulados aprovados |
| Sintaxe Bash e whitespace do diff | Aprovados |
| Vault disponível | 3 notas, zero problemas |
| Hashes do handoff | 9 de 9 conferem |

Os skips pertencem a condições de plataforma/ambiente; não são aceites Windows obtidos no Linux. Os oito cenários de setup verificam seleção e preservação, sem executar um runner dedicado. A suíte completa e os smokes usam fixtures; os resultados não somam certificações nativas aos 149 testes locais informados na publicação.

Os registros `NATIVE_PROFILES` e `REVIEWED_PROFILES` permanecem vazios. O dispatcher integrado, a recuperação/liberação após efeitos, A/B/A2 no candidato atual e as duas provas autenticadas continuam pendências explicitamente declaradas pelo projeto. Elas não foram tratadas como bugs novos desta revisão nem como entregas concluídas.

## Limites e continuidade

Esta cloud não tem `sbx` instalado nem `/dev/kvm`. Não foram construídas imagens, iniciadas VMs, repetidas operações históricas ou feitas chamadas de modelos. O limite de ciclos nativos da consolidação não foi consumido por esta auditoria.

O estado remoto do CI permanece **não verificado**: consultas GraphQL e REST de leitura à API do GitHub retornaram `Forbidden`. O resultado local acima não substitui os checks do PR. A publicação de comentários ou revisão no GitHub não foi solicitada nem realizada.

A revisão estática levantou ainda hipóteses sobre contexto persistido do Docker, coleta de processos encerrados pelo PID 1 e parsing de respostas HTTP upstream. Não foram promovidas a achados confirmados sem reprodução e avaliação do contrato no candidato nativo. Não há alegação de isolamento certificado ou de ausência universal de falhas em guardian/relay/egress.

Próximas ações recomendadas: corrigir os dois P2 novos com regressões locais; tratar os dois P2 herdados antes de confiar nos caminhos de recuperação/diagnóstico; conferir o CI do SHA que será promovido; prosseguir com os gates de integração nativa já aprovados pelo mantenedor. Nenhum perfil deve ser habilitado apenas porque testes determinísticos passaram.

## Evidência preservada

Medição estruturada, saídas das reproduções e hashes dos logs: [2026-10-07-pr24-cloud-audit.json](../medicoes/2026-10-07-pr24-cloud-audit.json).

Na instância atual, `.runtime/audit-pr24-b801bec/` contém log completo, resultados dos smokes, comparação de hashes e `reproduce_new_findings.py`. A reprodução anterior está em `.runtime/audit-20261007/reproduce_findings.py`; sua nova saída foi guardada no diretório do PR. Esses auxiliares ignorados não acompanham um clone comum.

Código e testes versionados permaneceram sem alterações. Foram acrescentados apenas este relatório, sua medição e auxiliares locais de auditoria; os relatórios anteriores foram preservados. Não houve commit, push, merge ou publicação. Não foi realizada evidência visual de interface.
