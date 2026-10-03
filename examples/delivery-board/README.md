# Quadro de entregas / Delivery board

[YoungCrowHarness](../../README.md) · [Vault](vault/index.md) · [Plano](../../docs/superpowers/plans/2026-10-03-public-pilot.md)

Este exemplo acompanha uma entrega desde a descoberta até a publicação. Os três itens de `data.json`
são fictícios; o estado real da demonstração fica no [registro de operação](vault/operations/index.md).
Node 24 executa os testes do exemplo. O instalador do harness continua independente de Node.

```bash
node --test tests/*.test.mjs
```

Execute na pasta `examples/delivery-board`. O modelo valida os dados e combina estado e busca.
A página usa controles nativos e mostra critérios e referências. O percurso local foi conferido em
1280px e 360px, com teclado, filtros vazios, limpeza e falhas de carregamento. Adoção com retorno,
retomada nativa e publicação ainda estão em implementação.

Para preparar uma prévia a partir da raiz do harness, escolha um destino novo fora da pasta do exemplo:

```bash
node examples/delivery-board/package.mjs .runtime/pilot-site REVISION
python -m http.server 8765 --bind 127.0.0.1 --directory .runtime/pilot-site
```

Troque `REVISION` pela revisão Git de 40 caracteres obtida com `git rev-parse HEAD`. No PowerShell,
capture-a em `$revision = git rev-parse HEAD` e passe `$revision` no lugar de `REVISION`.
O gerador recusa destino existente, links de arquivo, dados inválidos e destinos dentro da origem.
Para repetir, escolha outro diretório novo. Abra `http://127.0.0.1:8765` e encerre o servidor depois da consulta.
O pacote contém apenas HTML, CSS, dois módulos, JSON revisado, a gema e `manifest.json`.
O manifesto associa hashes à revisão informada; ele não concede aprovação nem autentica o conteúdo.
Os links do vault usam a main e só ficam
disponíveis quando esta frente for integrada.

O vault tem identidade própria e índices de produto, features, decisões, integração e operação.
Comece pelo índice geral e siga a frente. O setup não copia este exemplo para todos os consumidores.
Notas privadas em `vault/local/` ficam fora do Git. Fontes, backups e recibos nunca acompanham o site.

## English

This example follows a delivery from discovery to publication. The three entries in `data.json`
are fictional; the [operation record](vault/operations/index.md) holds the demonstration's actual state.
Run the command above from `examples/delivery-board`, with Node 24. The harness installer does not need Node.

The model validates input and combines status and search. The page was checked at 1280px and 360px,
with keyboard controls, empty results, reset and loading failures. To preview the allowed package,
run the two commands above from the harness root. Replace `REVISION` with the 40-character output of
`git rev-parse HEAD`; in PowerShell assign it to `$revision` and pass that variable. Choose a new
destination outside the source; existing destinations, linked files and invalid data are refused.
Open `http://127.0.0.1:8765`, then stop the server. The package contains six public files and a hash
manifest. The manifest records bytes and the supplied revision, not approval or authentication.
Vault links become available after merge.
Reversible adoption, native retrieval and publication are still in progress. The example has its own vault identity and linked
indices. Setup does not copy this example into every consumer. Private notes, source documents, receipts
and backups stay outside the public site.
