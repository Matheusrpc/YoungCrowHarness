---
id: "c5392ec6-80a8-4672-8cdb-c9cbec0c6f29"
type: "run"
title: "U01: reabrir a consulta pelo endereço"
origin: "youngcrow/assisted-delivery"
updated: "2026-10-12"
index: "../index.md"
---

# U01: reabrir a consulta pelo endereço

Integração/publicação autorizada pelo mantenedor em 12/out e em preparação na branch
`feat/delivery-board-url`, baseada na main `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`.
O registro `docs/relatorios/2026-10-12-filter-url-publication.md`, na raiz do harness, acompanha
essa etapa. O relato e os hashes abaixo preservam a observação do desenvolvimento na cópia de origem.

[Feature](../index.md) · [Entregas](../delivery.md) · [Operação](../../../operations/index.md)

Registros locais, a partir da raiz do harness que contém este exemplo:
`docs/relatorios/2026-10-12-filter-url.md` e `docs/medicoes/2026-10-12-filter-url.json`.
Não acompanham o pacote do site; ainda não foram publicados.

Projeto: `f60e681f-a8f3-40a5-aac6-fbcdc7aad86c`. Base Git:
`ca379107e9804180790afb3bb8c9a862a96bd554`, branch `feat/isolated-executor`.
Incremento local, com alterações anteriores preservadas no checkout. Os hashes da medição
identificam os novos bytes; a base Git sozinha não contém esta implementação.

Objetivo: guardar ou compartilhar o endereço do quadro e reabrir a mesma consulta.
O mantenedor autorizou avançar na direção de uma entrega assistida real com evidências.
A escolha desta extensão pequena foi uma decisão de implementação da sessão.
Os cartões de `data.json` continuam fictícios e não são o backlog de U01.

Decisão: `status` e `q` na URL, com `URLSearchParams` e `history.replaceState` nos módulos existentes.
Sem armazenamento adicional, dependência ou arquivo público novo. Estado desconhecido usa todos;
parâmetros repetidos usam o primeiro valor. Limpar remove só os filtros. `popstate` recupera controles
e lista no Voltar/Avançar, preservando as entradas de histórico e `history.state`.

| Aceite | Prova observada |
|---|---|
| Abrir estado+busca, recarregar e abrir nova aba recupera a consulta | Chromium em 1280px e 360px |
| Alterar os filtros atualiza o endereço sem criar entrada por tecla | Navegador; `history.state` preservado |
| Limpar conserva outros parâmetros, repetições e fragmento | Teste Node e percurso por teclado |
| Estado inválido usa todos; acentos e caracteres reservados continuam texto | Testes Node e navegador |
| Voltar/Avançar após o link de âncora sincroniza a consulta | Regressão reproduzida antes da correção; percurso final passou |
| Falha da History API mantém filtros; erro HTTP/dados inválidos mantém carga recusada | Navegador com falhas induzidas |
| Pacote mantém apenas seis arquivos públicos e manifesto | Quatro testes de pacote; hashes conferidos |

Comando reproduzível, na pasta `examples/delivery-board`: `node --test tests/*.test.mjs`.
Resultado: 11 testes passaram, zero falhas ou skips, Node 24.19.0 em Linux.
Fonte da implementação: [modelo](../../../../model.mjs), [aplicação](../../../../app.mjs),
[página](../../../../index.html), [estilo](../../../../style.css) e [testes](../../../../tests/model.test.mjs).
O [README](../../../../README.md#reabrir-a-mesma-consulta) explica como gerar uma prévia.

Desenvolvimento: implementação, testes e revisão local realizados. Produção: U01 não publicado;
última observação histórica refere-se a `2134134f14dc861be803173613bfd6a0d2e855e0`, em 3/out.
Nenhuma nova chamada nativa Claude/Codex, ciclo Docker ou repetição de P06 foi executada.
Revisores desta sessão são agentes assistidos; não representam novas sessões dos dois clientes.

Próxima ação registrada na observação de desenvolvimento: revisar estes arquivos e a medição para integração. Quando houver autorização de
publicação, conferir o novo manifesto e repetir o percurso externo; main aciona o workflow Pages.
Uma sessão que retome agora deve começar pelo índice do vault, conferir os hashes e preservar
esse estado local. Não iniciar outra feature nem repetir P06 para validar esta leitura.

English: U01 persists the board filters in its URL. Unit/package tests and local browser checks
passed; it remains unpublished. The measurement identifies the working-copy bytes. Resume through
the vault indexes, inspect the implementation and evidence, then prepare authorized integration.
This is a new assisted delivery, separate from the historical native retrieval proof and executor acceptance.
