# QA das fixtures no Windows

Frente: executor isolado, 2A-R1. Desenvolvimento local; produção não publicada.

A [rodada anterior](2026-10-04-shutdown-reserve.md#suíte-geral-pendências-de-qa) executou
381 testes, com 6 falhas, 2 erros e 11 skips. As causas foram a raiz temporária longa
nas provas de adoção e a leitura de um arquivo de PID ainda vazio. Os recibos anteriores
foram preservados. Esta rodada trata essas duas causas, sem alterar o executor isolado.

## Caminhos temporários

O runner já aceita `RUNNER_TEMP`. Neste Windows, a raiz padrão gerava uma reserva de
trial com 256 unidades UTF-16; a raiz curta reduziu a mesma projeção para 237. A adoção
exige menos de 248 para as operações nativas do PowerShell. A correção usa a configuração
existente; `adoption.py` e `adoption_fs.py` não mudaram. O runner agora imprime a pasta
privada para facilitar o diagnóstico. Veja o [comando reproduzível](../USAGE.md#tests-windows).

Os nove testes de trial passaram, incluindo Claude, Codex e ambos, reaproveitamento da
baseline, falha parcial e recusa de caminho excessivo antes da primeira escrita. A
restauração de um repositório Git com alterações staged, unstaged e arquivos ignorados
também passou. Essas provas usam projetos descartáveis.

## Publicação do PID

`open('x')` tornava o arquivo visível antes de escrever seu conteúdo. A limpeza podia
encontrar o arquivo vazio e falhar em `int('')`. O novo teste pausa um processo real
exatamente entre a criação e a primeira escrita; falhou antes da correção.

A fixture escreve e fecha um arquivo pendente e usa `os.link` para publicar o PID
completo. Se o destino existir, a publicação falha sem substituí-lo. O arquivo pendente
é retirado depois da tentativa de publicação. A limpeza considera uma publicação ainda
pendente como incompleta; outro teste mostrou o falso sucesso antes dessa correção.
O encerramento continua sendo solicitado pela fixture, sem matar PIDs externos.

Os sete testes dessa área passaram. Além dos dois casos de regressão, cobrem o registro
existente e o encerramento de um servidor real aguardando stdin. A primeira verificação
mostrou uma mensagem de decodificação no teste novo de colisão; a captura passou a usar
bytes e a repetição ficou limpa. Os dois logs foram preservados.

## Verificação

| Escopo | Resultado |
|---|---|
| Trial Windows | 9 testes, 155,206 s, sem falhas |
| Restauração com Git alterado | 1 teste, 20,126 s, sem falhas |
| Fixture de capacidades | 7 testes, 0,695 s, sem falhas |
| Suíte geral Windows/Python 3.14.4 | 384 testes, 1836,435 s, sem falhas ou erros; 11 skips |

Os 11 skips permanecem explícitos na medição, com nome e motivo. Esta execução
comprova apenas os testes disponíveis neste Windows; não substitui as provas nativas pendentes.

Hashes, comandos e recibos estão na [medição](../medicoes/qa-fixtures.json). Esta rodada
não inicia VMs, não muda certificados ou rede e não chama modelos. Guardian e launcher
mantêm os hashes da prova anterior. Os perfis nativos continuam vazios.

Próxima prova funcional: rede/MCP com o provedor acessível e sentinelas, ainda sem modelos.
Reconstrução do pacote corrigido, suspensão total do host e autenticação seguem pendentes.
R1 continua parcial; R2/R3 não começaram.

## English overview

The earlier full Windows run remains recorded with 381 tests, 6 failures, 2 errors and
11 skips. This change addresses its fixture causes. Existing `RUNNER_TEMP` configuration
reduces the projected trial path from 256 to 237 UTF-16 units on the evaluated host;
adoption still requires fewer than 248. No product path or permission checks changed.

The synthetic MCP server now closes the pending PID write before publishing through a
hard link, which refuses an existing destination. An unfinished publication cannot count
as completed cleanup. A paused real writer reproduced the incomplete-PID race before the
fix. The focused checks passed: 9 trial tests, 1 dirty-Git restore test and 7 capability
tests. The full suite ran 384 tests in 1836.435 seconds with no failures or errors
and 11 environment-dependent skips. The measurement lists every skip and its reason.

No VM, network, certificate or model operations were performed. Guardian and launcher
are unchanged. Native profiles remain empty; R1 is partial. Next are provider-enabled MCP
isolation and sentinel checks, followed by package rebuilding and the remaining proofs.

ATRASO: main 1
