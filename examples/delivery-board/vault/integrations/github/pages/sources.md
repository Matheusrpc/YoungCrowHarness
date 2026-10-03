---
id: "7eadacec-fe23-5863-aaba-59db4b66a2be"
type: "source"
title: "Orientação oficial Pages"
origin: "youngcrow/integrations"
updated: "2026-10-03T11:41:15+00:00"
index: "index.md"
---

# Orientação oficial Pages

[Integração](index.md)

Fonte: [workflows próprios do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), consultada em 2026-10-03.
A fonte foi ingerida com Docling na área privada do harness; esta nota contém apenas o contrato revisado.

O fluxo oficial usa configure-pages v5, upload-pages-artifact v4 e deploy-pages v4. O deploy depende
do pacote e usa o ambiente github-pages com pages:write e id-token:write. Ações serão fixadas por commit.

Decisão do projeto: PRs só validam. Publicação usa main protegida e staging com seis arquivos permitidos,
mais manifesto. Não usar upload da raiz. A URL real é obtida do deploy e verificada depois dele.
Payload, paginação, webhook e segredos de usuário não se aplicam ao site estático. Nenhum SDK é necessário.

A [API oficial de Pages](https://docs.github.com/en/rest/pages/pages), consultada em 2026-10-03 e ingerida privadamente,
permite configurar build_type workflow e exigir HTTPS. A [API de ambientes](https://docs.github.com/en/rest/deployments/environments)
define a restrição de branches do ambiente de publicação. A configuração deve permitir apenas a main.
