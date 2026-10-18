# Contexto do piloto com suas fontes públicas

> Registro histórico recuperado em 17/out/2026. Os números abaixo pertencem à sessão
> original. Os arquivos JSON daquela sessão não foram recuperados; veja as
> [provas atuais e os limites da recuperação](2026-10-17-codex-workspace.md).

Frente: preparação das provas locais do executor. Base `f55155d`, com alterações
anteriores do checkout preservadas. A evolução usa o exemplo existente; não depende
de um projeto novo do mantenedor.

Os 20 testes de `test_pilot_claude` falhavam em `make_context`: o vault de U01
referenciava seis arquivos públicos que a cópia de contexto omitia. A correção
inclui esses arquivos por lista explícita, preserva seus bytes e verifica tipo,
links e limite de 1 MiB antes de criar o destino. Notas não ampliam a seleção.
Dados privados, `.env` e `.git` ficam fora da cópia.

Provas desta rodada: os 20 erros foram reproduzidos; os dois testes novos falharam
antes da correção; depois, as 22 regressões do piloto passaram. Os verificadores
do vault passaram com 3 notas na raiz e 22 no exemplo. Revisão independente dos
dois arquivos de código não encontrou problemas relevantes.
A suíte completa terminou com **839 testes: 819 passaram e 20 foram ignorados**,
sem falhas ou erros, em 359,063 segundos. `git diff --check` também passou.
Comandos, resultados e hashes: `2026-10-16-pilot-context.json` (registro original indisponível).

O bloqueio do Codex continua: o cliente oficial cria um grupo de processos para
o transporte, e o supervisor atual proíbe essa operação. Liberá-la isoladamente
invalidaria a garantia de encerramento. O próximo incremento deve supervisionar
vários grupos e provar encerramento após prazo ou queda, antes do aceite nativo.
As consultas locais a namespaces nesta sessão foram recusadas sob o sandbox;
isso não qualifica nem descarta uma implementação fora dessa restrição.

Nenhum modelo, login, Docker, deploy ou repetição da sessão P06 foi iniciado.
Produção não foi verificada. README e guia de uso receberam apenas a descrição
da seleção de fontes. A redação PT passou por `humanizer-ptbr`; a skill inglesa
não estava instalada e a revisão EN foi manual.

English: the pilot context now includes its six explicitly selected public source
files. Regression checks cover intact sources, private-file exclusion and the
per-file limit. Native client qualification remains pending.
