# U01: retomar uma consulta do quadro

Registro do desenvolvimento anterior à integração. O [estado de publicação](2026-10-12-filter-url-publication.md)
acompanha o PR #25, o deploy e a pendência de verificação externa.

O quadro do exemplo agora guarda estado e busca no endereço. Recarregar, abrir outra aba e navegar
por Voltar/Avançar recupera a mesma consulta. A alteração está implementada e verificada localmente;
publicação pendente. [Uso](../../examples/delivery-board/README.md#reabrir-a-mesma-consulta) ·
[Execução no vault](../../examples/delivery-board/vault/features/delivery-board/runs/filter-url.md) ·
[Medições](../medicoes/2026-10-12-filter-url.json).

Base: `ca379107e9804180790afb3bb8c9a862a96bd554`, branch `feat/isolated-executor`.
Os hashes da medição identificam a cópia de trabalho. O repositório já tinha alterações locais;
a baseline desta entrega guarda seus hashes em `.runtime/filter-url-20261012/baseline.json`.

## Decisão e escopo

Esta é uma pequena entrega assistida para exercitar implementação, revisão e continuidade pelo vault.
Usa os módulos existentes, controles nativos e a mesma lista de seis arquivos públicos. Os parâmetros
`status` e `q` representam os filtros; os outros parâmetros, suas repetições e o fragmento permanecem.
`replaceState` evita criar uma entrada por tecla e preserva `history.state`. `popstate` repõe a consulta.
Estado desconhecido usa todos e buscas permanecem texto. A página explica quando a History API
recusa a atualização, mantendo a filtragem funcional.

Os três cartões continuam fictícios. U01 é uma mudança real da aplicação; não converte seus estados
em progresso de produção. Exportação de relatório e cockpit continuam fora deste incremento.

## Verificação observada

- Node 24.19.0: `node --test tests/*.test.mjs`, na pasta `examples/delivery-board`.
  11 testes passaram, zero falhas e zero skips; três testes novos cobrem o contrato da URL.
- O primeiro teste novo falhou pela ausência dos helpers. A revisão independente encontrou o caso
  de Voltar após uma âncora; ele também falhou no navegador antes da correção de `popstate`.
- Chromium 154.0.8037.57, Playwright Python 1.62.0 já disponível no ambiente: percurso no pacote
  servido em loopback, em 1280px e 360px. Recarga, nova aba, edição, histórico, limpeza por teclado,
  texto com caracteres reservados, estado inválido e ausência de transbordamento horizontal passaram.
- Falha induzida de History API preservou a lista; respostas HTTP 503 e JSON inválido mantiveram
  controles desabilitados e a mensagem de carga. Nenhum erro JavaScript no percurso normal.
- Pacote com seis arquivos e manifesto; testes conferem bytes, hashes e exclusão de arquivos privados.
  A revisão-base passada ao gerador não autentica os bytes modificados nem prova publicação.
- Capturas de 1280px e 360px inspecionadas. O ensaio final encerrou navegador, descendentes próprios
  rastreados e servidor; zero PIDs próprios remanescentes desse ensaio.
- Vault: 22 notas e zero problemas. A conferência de links locais verificou 552 destinos/âncoras
  sem problemas. Dos 504 arquivos da baseline, 490 mantêm os mesmos bytes; os 14 alterados pertencem
  ao incremento e à sua documentação. Alterações anteriores fora desses caminhos ficaram intactas.

Logs, capturas e script do navegador ficam em `.runtime/filter-url-20261012/`, ignorado no Git.
O ensaio inicial teve uma falha no código de injeção do teste, corrigida antes do percurso final;
o ensaio de regressão também detectou dois processos já encerrados em estado zumbi, adotados pelo
PID 1. O script final recolheu seus próprios descendentes e conferiu o encerramento.
A suíte Python do harness não foi repetida, pois seu código não mudou nesta entrega.
Navegadores Safari/Firefox e Windows não foram verificados para U01.

## Reproduzir o aceite de histórico

Gere e sirva uma prévia conforme o README do exemplo. Abra
`http://127.0.0.1:8765/?status=production&q=list`, acione o link «Ir para as entregas» por teclado,
mude para desenvolvimento e busque `filtrar`. Voltar precisa repor produção/`list` e «Listar entregas»;
Avançar precisa repor desenvolvimento/`filtrar`. Recarregue e confira a mesma consulta.
Abra `?ref=a&ref=b&status=development&q=filtrar#quadro`: limpar deve deixar
`?ref=a&ref=b#quadro`, com três itens. Encerre a prévia ao terminar.

## Continuidade e próximo passo

O índice da feature liga U01 à decisão, ao código, aos testes e ao estado de publicação.
A revisão `recover_delivery_context`, iniciada sem o histórico da conversa, recuperou objetivo,
decisão, implementação, evidências, desenvolvimento versus produção e próxima ação. Seguiu cinco
notas a partir do índice geral, sem usar `git diff` ou pedir esclarecimentos. Conferiu o UUID do
projeto, UUIDs e hashes das notas, cinco arquivos de código, seis do manifesto e 15 artefatos locais.
Tempo observado pelo revisor: 42 segundos, entre 07:00:14 e 07:00:56 UTC. Os cinco hashes de notas
foram conferidos novamente nesta sessão. A medição registra essa leitura em contexto independente
no mesmo ambiente; é uma única observação, sem comparação de produtividade ou prova nativa Claude/Codex.
O índice de memória do exemplo não tinha seleção; a consulta seguiu os microíndices Markdown,
sem criar seleção automática ou ativar Graphify.

Próxima ação: revisar U01 para integração. Quando a publicação for autorizada, conferir manifesto,
bytes e percurso no endereço público. A evidência histórica de produção continua vinculada a
`2134134f14dc861be803173613bfd6a0d2e855e0`, observada em 3/out. Não houve consulta externa ou deploy
nesta entrega. P06 e seu recibo original permanecem preservados; nenhum ciclo nativo do executor
foi consumido. Este incremento não encerra YC-203 ou a esteira completa YC-502.

## English

This development record predates integration; see the [publication record](2026-10-12-filter-url-publication.md) for the current deployment and external verification state.

U01 restores the board filters from its URL, including reload, a new tab and Back/Forward.
Eleven Node tests and local Chromium checks at 1280px/360px passed. Working-copy hashes and
observations are recorded separately from the historical production revision. The increment is
unpublished. Independent context recovery through the vault is recorded separately from native
client retrieval; P06 was not repeated and executor acceptance remains open.
