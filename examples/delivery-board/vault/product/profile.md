---
id: "52afdaf0-b360-50d5-9724-a917ab0fcd8c"
type: "product"
title: "Perfil do quadro de entregas"
origin: "youngcrow/public-pilot"
updated: "2026-10-03T11:41:15+00:00"
index: "index.md"
---

# Perfil do quadro de entregas

[Produto](index.md) · [Entrevista](interviews/public-pilot.md) · [Feature](../features/delivery-board/index.md)

Público: desenvolvedores individuais e pequenos times com Claude Code e Codex. O mantenedor
confirmou em 2026-10-03 um quadro público para acompanhar uma ideia até publicação e retomada.
O exemplo mostra dados fictícios. O estado real da aplicação fica na [operação](../operations/index.md).

Escopo: lista de entregas, filtro por estado e busca, critérios e links de evidência. Dados mudam
por arquivos e PR. Não há edição colaborativa, login, banco, API de IA ou exportação de relatório.
HTML/CSS/JavaScript e Node 24 para testes; Node é requisito do exemplo, não do setup do harness.
Fundo #17130f, texto #F3E7C6, gemas e títulos serifados preservam o design do repositório.

PM define resultado e aceite; Tech Lead divide entregas; um executor escreve; um revisor independente
avalia diff e evidências. Esses são papéis, sem orquestração autônoma. O orçamento dos ensaios nativos
é uma sessão por cliente, até 300 segundos/24 ferramentas, assinatura existente e nenhuma API extra.

Comando verificado: `node --test tests/model.test.mjs` a partir da pasta do exemplo.
O aceite completo está na feature. Fontes e recibos privados não acompanham os arquivos públicos.
Desenvolvimento: modelo e dados testados. Produção: ainda não verificada.
