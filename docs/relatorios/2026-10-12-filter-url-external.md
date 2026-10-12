# U01: conferência do site público

Frente: fechar a verificação externa dos filtros por URL já publicados no PR #25.
Observação em 12/out/2026, a partir de 11:07 UTC, após o mantenedor publicar a configuração de rede.
O [recibo anterior](2026-10-12-filter-url-publication.md) e sua medição preservam o checkpoint de publicação.

O [site público](https://matheusrpc.github.io/YoungCrowHarness/) serviu o manifesto e os seis arquivos
com HTTP 200 e TLS verificada. Revisão `80edd7786f3ecb13535565f5cb358ef1f983b757`;
os hashes e tamanhos conferem com o manifesto e os blobs Git dessa revisão.
A [medição](../medicoes/2026-10-12-filter-url-external.json) contém resultados, hashes e limites.

Chromium 154, em 1280px e 360px, passou em: recuperar `status/q`, recarregar, abrir outra aba,
digitar sem crescer o histórico, preservar texto com acentos e caracteres reservados, limpar filtros,
manter parâmetros extras repetidos e fragmento, e sincronizar Voltar/Avançar.
Zero erros JavaScript e zero transbordamentos horizontais nos cenários medidos.
As [capturas desktop](../medicoes/2026-10-12-u01-public-1280.png) e
[móvel](../medicoes/2026-10-12-u01-public-360.png) registram a apresentação; as asserções do navegador
registram o comportamento. Navegadores fechados em `finally`, zero processos próprios remanescentes.

Limite: a navegação HTTPS nativa do Chromium falhou com `ERR_CERT_AUTHORITY_INVALID`;
o diagnóstico provável é a ausência da CA atual do proxy no NSS existente, sem recibo específico preservado. O teste usou rotas Playwright que buscaram
cada resposta real por `urllib`, com `CERT_REQUIRED`, verificação do hostname e proxy herdado,
e entregaram os bytes ao navegador mantendo a URL pública. Todas as 112 respostas tiveram
hash conferido contra a leitura HTTP. TLS nunca foi desativada; nenhum perfil global foi alterado.
Isso comprova os arquivos publicados e seu comportamento no navegador com transporte delegado;
a cadeia TLS nativa do Chromium neste ambiente permanece sem validação.

A política observada passou de `unrestricted/enforced` para `unrestricted/unknown` na consulta final.
O estado desconhecido não prova aplicação da política; as requisições HTTPS efetivas passaram.
Nenhuma mudança no código público, chamada de modelo, repetição de P06 ou ensaio Docker nesta frente.
Retorno continua pelo procedimento do recibo de publicação; não foi acionado.

**English.** Public manifest and all six files match revision `80edd7786f3e` over verified HTTPS.
Filter navigation passed at 1280px and 360px. Browser HTTPS was delegated to verified Python transport
after Chromium rejected the certificate chain; a missing proxy CA in NSS is the probable diagnosis. Native Chromium TLS remains
unverified; TLS checks stayed enabled and all owned browser processes were closed.

ATRASO: arquivos públicos 0 | navegação com TLS delegado 0 | TLS nativa Chromium 1
