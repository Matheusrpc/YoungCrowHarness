# Diagnóstico da falha Windows no CI

Frente: validação de YC-203 no PR #24. Data: 2026-10-07 (America/Sao_Paulo).

O CI do checkpoint `da28f00016861af8fecdd43a99cc5de085e70971` falhou na suíte
de missões de `adoption-windows`. As páginas públicas permitiram conferir esse
resultado, embora a API estivesse indisponível na consulta anterior. Os relatos
anteriores de CI não verificado descrevem a informação disponível naquela rodada.

| Execução | public-pilot | installer | adoption-windows | graphify-smoke |
|---|---|---|---|---|
| [Push 37702748727](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37702748727) | passou | passou | falhou | passou |
| [PR 37702753288](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37702753288) | passou | passou | falhou | passou |

A [página do job Windows do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37702753288/job/113069845967)
identifica `Verify mission diagnostics and process recovery`, saída 1. Essa etapa
executa `test_mission*.py`. As etapas anteriores passaram; o smoke seguinte foi
pulado. A página exige login para mostrar logs detalhados, e a URL de log nela
indicada respondeu 404. Não há evidência para atribuir a falha a um teste específico.
Não houve nova tentativa de autenticação nem acesso a credenciais.

## Diagnóstico inicial

`tests/ci_unittest.py` usa o runner padrão do unittest e, ao final, publica os IDs
de falhas, erros e sucessos inesperados como anotações do GitHub Actions. Subtestes
usam o ID do pai, sem repetição. A lista não inclui traceback, mensagens de exceção
ou valores de parâmetros. Identificadores fora do formato convencional recebem um
rótulo fixo. Sem `GITHUB_ACTIONS=true`, não há anotações adicionais.

O unittest conserva descoberta, saída normal e código de saída, inclusive o tratamento
de descoberta vazia da versão de Python em uso. O workflow troca somente a entrada
da etapa de missões, mantendo `windows_fixture_runner.py`, ACLs, seleção e flags.
Cancelamento, timeout ou falha anterior ao unittest podem impedir as anotações.
A instrumentação precisa de uma nova execução para identificar a causa no Windows;
ela não corrige a falha ainda desconhecida.

Cinco regressões executam módulos descartáveis em subprocessos reais. A versão sem
anotações falhou em duas verificações; após a alteração, todas passaram. Os casos
cobrem falha, erro, subtestes, erro de preparação de classe, sucesso inesperado,
skip, falha esperada, `-f`, identificador malformado, execução local e descoberta vazia.
A revisão independente não encontrou bloqueadores. Hashes, árvore testada e
resultado completo estão na [medição](../medicoes/2026-10-07-windows-ci-diagnostics.json).

Suíte pública local: **617 testes, 597 aprovados e 20 pulados**, sem falhas/erros em
249.575 s. Os pulados exigem Windows ou grupo secundário POSIX indisponível. O novo
runner executou a suíte com `GITHUB_ACTIONS=true`; não emitiu anotações de erro.

## Resultado do diagnóstico e rodada focal

O diagnóstico inicial foi publicado em `a9d05ea7fe99cfacaff494c202ba3904444f884b`,
com branch e ref do PR conferidas. O [push 37717179017](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37717179017)
e o [PR 37717181788](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37717181788)
falharam em `adoption-windows`; os três jobs Linux passaram em ambos.

Duas falhas apareceram nas duas execuções:

- `test_mission_network.NetworkBindingTests.test_real_guards_same_port_B_absent_and_recovery_after_owner_exit`.
- `test_mission_network.NetworkBindingTests.test_v4_fixture_relay_guard_journal_and_recovery_with_local_injection`.

O PR também anotou
`test_mission_egress.EgressTests.test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`.
Os IDs localizam os cenários, mas não distinguem timeout do supervisor, recusa interna
ou recuperação bloqueada. A hipótese estática de reutilização de porta continua sem
confirmação; o teste isolado de fechamento pelo upstream não apareceu entre as falhas.

A rodada focal executa os quatro casos NetworkBinding e o encerramento abrupto antes
das etapas longas. A suíte completa permanece depois; se o focal falhar, o CI pula as
etapas seguintes e conserva o job vermelho. Não houve mudança de asserts, prazos,
limites ou código de produção.

As notices projetam somente campos/códigos permitidos: estado, motivo, resultado do
supervisor, duração, contagens e tamanho das saídas. Não publicam seus conteúdos,
exceções, caminhos ou identidades. Códigos desconhecidos viram `other`. O registro
ocorre após a restauração do ambiente da fixture, pois ela remove variáveis externas
inclusive `GITHUB_ACTIONS`. A prova local confirmou as quatro notices esperadas.
Um teste adicional com canários falhou antes da implementação e passou depois; a
revisão independente confirmou a projeção e a preservação dos asserts.

Suíte pública desta rodada: **618 testes, 598 aprovados e 20 pulados**, sem falhas ou
erros em 257.096 s. Depois desse snapshot, somente a condição que publica
uma notice para saída não zero esperada mudou em `test_mission_egress.py`; os 16 testes
desse arquivo passaram na versão final. A rodada focal passou nos cinco casos e
emitiu as quatro notices de rede. Seis testes validam o runner e a projeção de estados.
Não houve reprodução Windows local nem correção de produto nesta rodada.

## Dependências preservadas

A avaliação de 203.8 confirmou outra pendência: o coletor de B e sua evidência original
não estão nesta cloud. Antes de integrar, transferir os bytes correspondentes aos
registros de [captura](2026-10-06-captured-egress-evidence.md) e
[controlador integrado](2026-10-06-integrated-egress-controller.md), incluindo:

| Arquivo no checkout privado anterior | SHA-256 registrado |
|---|---|
| `captured_egress.py` | `cd4394082e8da687efeff9bd835169163a540385e80faaacec8dc06b8fb7531c` |
| `test_captured_egress.py` | `6945516531eaa08b0bdb89c31f257f26b10919ec2a481311069af5b5ae55330c` |
| `corrected-egress-proof/B-daemon-refusal.jsonl` | `e16a55e82f8105b22dee598cd4d5efbd0b7dabf05d5f880d5236d5e17433cb46` |

Também conservar `integrated_egress.py`, seus testes e o recibo de origem da captura
para conferir o fluxo integrado. Os hashes identificam a transferência necessária;
não demonstram que os arquivos foram recuperados. Não reconstruir o parser nativo
a partir do relato nem criar uma fixture substituta apresentada como evidência real.

O contrato externo de identidade/versão/remoção atômica da credencial e escrita
condicional dos settings locais 0.46.0 continua pendente. Nenhum Docker, sbx, login,
modelo ou novo ciclo nativo foi executado. O contador permanece **2/3**, com perfis
vazios e aceite nativo bloqueado. O ambiente Python da cloud não exigiu configuração
adicional. Fontes HTML foram lidas diretamente e guardadas em área privada com hashes.

## Publicação e retorno

Destino autorizado: `feat/isolated-executor`, [PR #24 em rascunho](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
Base inicial `da28f00`; main conferida em `932b775`. Próxima ação: consultar os
estados da rodada focal e investigar a causa antes de alegar correção.
Retorno: reverter o incremento na branch restaura a entrada anterior do unittest;
isso remove as anotações e mantém a falha Windows pendente. Não altera ledger,
perfis ou autorizações nativas. Recibos e HTML brutos ficam fora do Git.

## English overview

Public GitHub pages confirmed that both CI runs for `da28f00` failed in Windows
mission tests while the other three jobs passed. Detailed logs require sign-in;
the initial diagnostic identified two positive network tests and, on the PR run,
an abrupt controller shutdown test. The existing Windows fixture wrapper now
calls a unittest entry point that adds failed parent test IDs as GitHub annotations.
It excludes exception text and subtest values and preserves standard output and
exit status. Controlled regressions and independent review cover this diagnostic,
which does not itself fix the Windows failure. A focused step now runs the affected cases first and publishes only allowlisted
fixture states, durations and counts to locate the cause. Assertions and deadlines
remain unchanged; later full-suite steps remain gated on the focused step.
Original B collector sources and capture also need transfer from the private
checkout. Native contracts remain blocked, with no new native cycles (2/3 used).

ATRASO: main 1 frente sem aceite | PR #24 diagnóstico em publicação | CI Windows e aceite nativo pendentes.
