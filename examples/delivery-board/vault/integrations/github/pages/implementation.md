---
id: "cd667baf-3f62-5142-9032-c5a718366005"
type: "implementation"
title: "Contrato da publicação"
origin: "youngcrow/integrations"
updated: "2026-10-03T11:41:15+00:00"
index: "index.md"
---

# Contrato da publicação

[Integração](index.md) · [Decisão](../../../decisions/static-site.md)

Entrada prevista: revisão aprovada da main, testes verdes e dados públicos revisados.
Saída prevista: HTML, CSS, app.mjs, model.mjs, data.json, gema-cobalto.svg e manifest.json.
O manifesto tem revisão Git e hashes SHA-256. Links do navegador permitem somente destinos HTTPS revisados.
Arquivos privados, vaults locais e recibos não entram no pacote. Nenhum link de arquivo é aceito no staging.

Estado: gerador implementado; job de CI preparado. Testes locais: 7 aprovados e 1 skip Windows em 2026-10-03.
Workflow de publicação e prova externa ainda pendentes.
Isso não comprova deploy, autenticação, disponibilidade nem produção.
