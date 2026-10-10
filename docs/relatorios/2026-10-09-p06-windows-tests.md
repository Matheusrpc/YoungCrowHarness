# Compatibilidade dos testes P06 no Windows

Frente: correção dos testes de P06. Base: `09f95c6`.

A saída enviada pelo operador, em Python 3.14 no Windows, mostrou 13 testes:
10 aprovados, uma falha e dois erros. Os erros ocorreram ao ler Markdown UTF-8
com a codificação padrão cp1252. A falha buscava a chave
`scripts/adoption_acl.ps1`, embora o manifesto Windows use barras invertidas.
O arquivo e seu hash estavam presentes; a consulta do teste usava outro separador.

Duas linhas de `tests/test_pilot_claude.py` mudaram: a leitura declara UTF-8 e
a consulta monta o caminho com `Path`. O manifesto continua no formato nativo,
usado para comparar preparo e execução na mesma máquina. O runner, os limites,
as credenciais e o marcador da tentativa original não foram alterados.

## Verificação

Os dois erros de leitura foram reproduzidos na cloud, impondo cp1252 como padrão
às leituras que omitiam a codificação. Ambos passaram após a correção.
A consulta com barras fixas também foi demonstrada com `PureWindowsPath`.
Esse diagnóstico não substitui execução no Windows.

A suíte afetada passou com os 13 casos na cloud, inclusive após a reconexão do
ambiente. Não foi necessário repetir a suíte inteira para uma alteração restrita
aos testes. Contagens e hashes estão na
[medição](../medicoes/2026-10-09-p06-windows-tests.json).
Na confirmação enviada depois pelo operador, os 13 casos passaram no Windows
em 9,373 s, com checkout fixo em `6481a91`. O CI completo ainda está pendente.

O teste de protocolo completo, orçamento, timeout e limpeza já havia passado
na saída Windows do operador. Esses resultados usam um cliente fictício;
a falha OAuth da tentativa real permanece uma evidência separada.

## Confirmação Windows e preparo r2

O anexo do operador tem SHA-256
`036d72bab1385952e3220fa9bb3f53da45089167c1745623f4313936d66e4d46`
e 5.451 bytes. A saída mostra os 13 casos aprovados e, em seguida, o preparo real
concluído em 13,889191 s. Foram reportados zero prompts, árvore encerrada, remoção
da credencial temporária e preservação da autenticação original.

A operação `323ef492-4967-4d13-bd71-8afe0bc2ed00` está preparada, com
`setup_sha256: 6d1c2bd27f6c35308712310ab640205b06d5f19de5836d60b00c1730431d9811`.
A revisão independente `review_retry_preparation` não encontrou impedimento para
apresentar a autorização de uma nova sessão. Não houve inferência adicional.
O [guia](../P06-CLAUDE.md#nova-operação-preparada-em-9out) registra pacote, comando
e limites; a autorização antiga continua consumida pela primeira tentativa.

Na consulta de 9/out às 20h20 UTC, o [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37984411482)
falhou em `test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`, antes
do P06, que foi pulado. A asserção exata não está disponível; os logs redirecionam
para um host fora da política de rede. O [run do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37984416730)
passou nesse diagnóstico e segue em testes de missões; P06 pendente. Os demais jobs
passaram nos dois runs. A prova local Windows não equivale a CI completo aprovado.

## Próxima ação

Obter autorização única da operação r2 já preparada, preservando sua revisão e
os recibos anteriores. Após executar, revisar o resultado semântico antes do aceite
P06. Acompanhar o CI separadamente; nenhum perfil Docker foi habilitado.

## English overview

Two test assumptions failed on Windows: an implicit text encoding and a fixed
slash in a native-path manifest lookup. The tests now read UTF-8 explicitly and
build the expected path with pathlib. All 13 affected tests pass locally, including
the two encoding cases under a cp1252 default. The operator then confirmed all 13
tests passed on Windows and prepared a new r2 package with zero prompts. Its exact
operation awaits approval for one bounded session. Full CI remains pending: push
Windows failed before P06; PR Windows passed that diagnostic and is still running.
The runner and the original Claude attempt are unchanged.

ATRASO: CI completo pendente | autorização r2 e retomada Claude pendentes.
