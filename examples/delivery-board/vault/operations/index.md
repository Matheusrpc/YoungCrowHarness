---
id: "78e0331e-c5b3-56b7-9586-9d9171f76409"
type: "index"
title: "Operação da demonstração"
origin: "youngcrow/public-pilot"
updated: "2026-10-12"
index: "../index.md"
---

# Operação da demonstração

[Vault](../index.md) · [Feature](../features/delivery-board/index.md) · [Integração Pages](../integrations/github/pages/index.md)

Incremento [U01](../features/delivery-board/runs/filter-url.md), 12/out: [PR #25](https://github.com/Matheusrpc/YoungCrowHarness/pull/25) integrado.
[Build e deploy Pages](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38216618798) passaram; o ambiente `github-pages`
confirmou a revisão `80edd7786f3ecb13535565f5cb358ef1f983b757` às 07:14:47 UTC.
A rede da cloud recusou o domínio do site. Manifesto, bytes servidos e percurso externo de U01
continuam pendentes; a observação de 3/out abaixo não cobre esta nova revisão.

O relatório `docs/relatorios/2026-10-12-filter-url-publication.md`, na raiz do harness,
acompanha essa publicação. Retorno específico de U01: reverter somente seu commit por PR,
aguardar os checks/deploy e verificar o site. O procedimento do piloto original segue abaixo.

Observação histórica de produção em 2026-10-03T12:24:54.296Z: [abrir demonstração](https://matheusrpc.github.io/YoungCrowHarness/).
Revisão publicada: `2134134f14dc861be803173613bfd6a0d2e855e0`. [Execução de deploy](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37122731645).
Página e seis arquivos responderam HTTP 200. Os hashes do manifesto coincidem com os bytes recebidos
e com os blobs Git dessa revisão aprovada. Filtros combinados, vazio, limpeza, teclado, links do vault
e telas de 1280px/360px foram conferidos. Zero processos próprios de navegador ao fim.
HTTPS obrigatório; ambiente github-pages permite apenas a branch main. PRs não publicam.

Os estados das entregas na página pertencem ao cenário fictício. A prova de recuperação do Claude
continua pendente por OAuth expirado; a publicação estática não encerra esse aceite.
As [medições](https://github.com/Matheusrpc/YoungCrowHarness/blob/main/docs/medicoes/2026-10-03-public-pilot.json)
preservam revisão, hashes e limites. Uma edição posterior só de relato não altera a versão do site.

Retorno da publicação: se existir release anterior comprovada, reexecutar o workflow de publicação
daquela revisão aprovada e observar novamente URL/manifesto. Sem versão anterior, retirar o site
pelo mecanismo oficial Pages se for necessário despublicar. Esse retorno não foi acionado nesta prova.
Retorno da adoção: o executor externo restaura apenas o consumidor e conserva o trabalho do trial;
as duas operações são independentes. Próxima ação: renovar login Claude e declarar nova prova limitada.
