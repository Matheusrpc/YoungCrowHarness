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
O CI Windows da nova revisão ainda precisa confirmar a correção.

O teste de protocolo completo, orçamento, timeout e limpeza já havia passado
na saída Windows do operador. Esses resultados usam um cliente fictício;
a falha OAuth da tentativa real permanece uma evidência separada.

## Próxima ação

Conferir o teste afetado no CI Windows. O operador já renovou o login por assinatura;
revisar uma nova tentativa de retomada somente após essa confirmação. Preservar
os recibos da primeira operação. Esta correção não autoriza outra inferência.

## English overview

Two test assumptions failed on Windows: an implicit text encoding and a fixed
slash in a native-path manifest lookup. The tests now read UTF-8 explicitly and
build the expected path with pathlib. All 13 affected tests pass locally, including
the two encoding cases under a cp1252 default. Windows CI confirmation remains
pending. The runner and the original Claude attempt are unchanged.

ATRASO: confirmação Windows pendente | retomada Claude pendente.
