# Quadro de entregas / Delivery board

[YoungCrowHarness](../../README.md) · [Vault](vault/index.md) · [Plano](../../docs/superpowers/plans/2026-10-03-public-pilot.md)

Este exemplo acompanha uma entrega desde a descoberta até a publicação. Os três itens de `data.json`
são fictícios; o estado real da demonstração fica no [registro de operação](vault/operations/index.md).
Node 24 executa os testes do exemplo. O instalador do harness continua independente de Node.

```bash
node --test tests/model.test.mjs
```

Execute na pasta `examples/delivery-board`. O modelo valida os dados e combina estado e busca.
Página, adoção com retorno, retomada nativa e publicação ainda estão em implementação.

O vault tem identidade própria e índices de produto, features, decisões, integração e operação.
Comece pelo índice geral e siga a frente. O setup não copia este exemplo para todos os consumidores.
Notas privadas em `vault/local/` ficam fora do Git. Fontes, backups e recibos nunca acompanham o site.

## English

This example follows a delivery from discovery to publication. The three entries in `data.json`
are fictional; the [operation record](vault/operations/index.md) holds the demonstration's actual state.
Run the command above from `examples/delivery-board`, with Node 24. The harness installer does not need Node.

The model validates input and combines status and search. The page, reversible adoption, native client
retrieval and publication are still being implemented. The example has its own vault identity and linked
indices. Setup does not copy this example into every consumer. Private notes, source documents, receipts
and backups stay outside the public site.
