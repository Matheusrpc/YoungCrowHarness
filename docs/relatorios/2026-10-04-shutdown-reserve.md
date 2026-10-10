# Prazo de encerramento após reinício do serviço

Frente: executor isolado, 2A-R1. Desenvolvimento local; produção não publicada.

O operador reiniciou o Docker Sandboxes durante uma operação sintética de cinco segundos.
O serviço voltou, o contêiner terminou com 124/PID 0 e um segundo início foi recusado com
`start_consumed`, sem alterar seu estado. A prova do prazo falhou: o limite era
`2026-10-05T00:24:31.587Z`; o Docker registrou término às `00:24:31.5908935Z`, 3,8935 ms depois.
Esse timestamp não mede o instante de saída do cliente isoladamente. O recibo permanece
reprovado e preservado; não acrescentamos tolerância à checagem.

O guardian armava o encerramento no próprio deadline. Isso não reservava tempo para
atender o sinal e terminar os processos. Python executa handlers posteriormente no
interpretador, e os timers do Linux podem vencer depois do instante pedido.
Fontes: [Python signal](https://docs.python.org/3/library/signal.html#execution-of-python-signal-handlers)
e [Linux setitimer](https://man7.org/linux/man-pages/man2/setitimer.2.html).

## Correção e prova

A candidata reserva um segundo dentro do prazo original para encerramento. Guardian e
launcher compartilham a regra; criação, início e despacho recusam a janela reservada.
O corte monotônico impede que a volta do relógio recupere esse segundo. O manifesto não
muda e o teto total continua em 120 segundos. Os smokes comparam o timestamp completo
do Docker com o prazo original usando aritmética decimal.

Quatro novos testes reproduziram a ausência da reserva antes da correção. Depois dela,
os 11 testes do guardian e os oito do launcher passaram. Na VM, a candidata usa caminho
e imagem interna próprios; os arquivos do pacote anterior ficaram intactos.

| Cenário nativo | Retorno | Sobra até o deadline original |
|---|---:|---:|
| Launcher: conclusão | 0 | 3.977,1457 ms |
| Launcher: prazo | 124 | 984,5955 ms |
| Launcher: perda do transporte | 125 | 3.942,0802 ms |
| Guardian: conclusão | 0 | 4.263,465 ms |
| Guardian: repetição | 125 | 4.317,734 ms |
| Guardian: identidade inválida | 125 | 4.419,1224 ms |
| Guardian: descoberta falhou | 126 | 4.434,1405 ms |
| Guardian: prazo | 124 | 991,3736 ms |
| Guardian: saída acima de 8 MiB | 122 | 5.261,0838 ms |

Todos terminaram com PID 0 e recusaram outra execução. O primeiro teste de saída atingiu
o prazo de cinco segundos antes do limite de bytes, retornando 124. Esse resultado ficou
preservado. Uma operação distinta recebeu dez segundos para medir o limite de saída e
retornou 122. Os testes específicos de prazo continuaram com cinco segundos. Não houve
mudança adicional no produto entre esses dois ensaios.

Os valores, hashes e recibos estão na [medição](../medicoes/shutdown-reserve.json). Nenhum
modelo, certificado ou liberação de rede foi usado nesta correção; a VM da candidata
terminou parada.

## Suíte geral: pendências de QA

No Windows/Python 3.14.4, `python -B tests/windows_fixture_runner.py -m unittest discover -s tests -v`
executou 381 testes em 1.836,401 segundos: 6 falhas, 2 erros e 11 casos ignorados. Os 19
testes do guardian/launcher passaram também nessa rodada. A suíte geral não está verde.

| Teste | Resultado observado |
|---|---|
| `test_restore_keeps_trial_work_and_returns_dirty_git_state` | `unsupported_path_length`; reproduzido isoladamente |
| `test_fixture_cleanup_ends_a_real_server_waiting_on_stdin` | `int('')` ao ler PID; passou isoladamente, corrida não corrigida |
| `test_trial_git_configuration_is_disabled_in_installer_child` | `unsupported_path_length` |
| `test_trial_is_project_only_and_reuses_first_baseline` | `unsupported_path_length` nos três perfis: Claude, Codex e ambos |
| `test_trial_missing_target_has_absent_baseline` | `unsupported_path_length` |
| `test_trial_partial_failure_retains_baseline_and_repeats` | `unsupported_path_length`, antes da falha parcial esperada |

Os caminhos temporários usados nesta execução excedem a fronteira aceita pela adoção.
A rotina de limpeza lê o arquivo de PID depois de verificar sua existência; o escritor
ainda pode estar preenchendo esse arquivo. Essas rotinas não foram alteradas nesta
correção. A prova específica do executor passou, mas as pendências da suíte devem ser
tratadas antes de declarar o QA geral aprovado. Preservar o controle de tamanho de caminho
e a recusa de encerrar um processo sem identidade conhecida.

Continuação: a [correção das fixtures](2026-10-04-qa-fixtures.md) registra a rodada seguinte.
Os resultados reprovados acima permanecem como histórico.

## Reinício com a candidata e próxima ação

O operador executou `run-active-daemon-reserve-proof.ps1` uma vez no PowerShell normal.
O reinício começou às `00:36:08.562Z`, durante o trabalho. O Docker registrou término às
`00:36:08.9473688Z`, 993,6312 ms antes do limite original `00:36:09.941Z`. O serviço voltou
às `00:36:16.700Z`. O contêiner saiu com 124/PID 0, o novo início foi recusado com 125 e
`start_consumed`, e a inspeção confirmou estado inalterado. A VM terminou parada, sem
erros de limpeza. O recibo local confirma o resultado enviado pelo operador.

O terminal do operador foi necessário pela falha de sockets já observada quando o daemon
partiu do terminal do agente. Ambos os scripts de reinício estão consumidos; não repetir
nem apagar seus marcadores. O próximo trabalho é provar rede/MCP com acesso ao provedor
e sentinelas, ainda sem modelos, antes de reconstruir e validar o pacote corrigido.

A reserva não garante resposta sob suspensão ou atraso arbitrário do sistema. Ainda
faltam reconstrução do pacote, rede/MCP com acesso
ao provedor, sentinelas e suspensão do host. R1 segue incompleto, R2/R3 não começaram e
o catálogo de perfis nativos continua vazio.

## English overview

The operator restarted Docker Sandboxes during a five-second synthetic operation. The
daemon returned, the container exited 124 with PID 0, and replay was refused without
changing its state. Docker recorded termination 3.8935 ms after the original deadline.
That proof remains failed; the timestamp alone does not measure the client's exit instant.

The candidate reserves one second within the original deadline for shutdown. Guardian
and launcher refuse new work in that window; the manifest and 120-second ceiling remain
unchanged. A monotonic cutoff prevents a backward clock from recovering execution time.
Four regression tests failed before the fix; 19 guardian/launcher tests now pass.

Nine native scenarios passed with the candidate in a separate path and inner image.
Both five-second deadline tests finished over 984 ms early. The output-cap test first hit
the five-second deadline; a separate ten-second operation reached the 8 MiB cap and exited
122. Both receipts are retained. Earlier packaged files stayed unchanged; native profiles
remain disabled.

The full Windows suite ran 381 tests in 1,836.401 seconds, with 6 failures, 2 errors and
11 skips. All 19 guardian/launcher tests passed. Seven negative results hit the adoption
path-length limit; one cleanup test read an empty PID file before the writer closed it.
The adoption error reproduced in isolation; cleanup passed alone, but the race remains
unfixed. The table above names every affected test. This is a passing executor proof,
with outstanding full-suite QA issues.

The operator also ran the candidate's active restart proof. The container exited 124 with
PID 0 during the restart, 993.6312 ms before its original deadline. Replay returned 125
with unchanged state; cleanup passed. Both restart scripts are consumed. Next are
provider-enabled MCP isolation and sentinel checks. Suspension and package rebuilding
remain pending. No model calls or publication.

ATRASO: main 1
