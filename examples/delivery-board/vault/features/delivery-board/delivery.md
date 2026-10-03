---
id: "c1a90a67-924d-5a86-8e14-62d3ff499a56"
type: "delivery"
title: "Entregas do piloto"
origin: "youngcrow/public-pilot"
updated: "2026-10-03T12:24:54.296Z"
index: "index.md"
---

# Entregas do piloto

[Feature](index.md) · [Execução](runs/implementation.md)

| Entrega | Aceite e dependência | Responsabilidade | Estado |
|---|---|---|---|
| Dados e memória | Dados válidos, consulta combinada, índices | Tech Lead/executor | 4 testes do modelo passam |
| Página | Controles nativos, vazio/erro, teclado e tela estreita | Executor | Verificada localmente |
| Pacote e CI | Lista explícita, hashes e zero arquivos privados | Executor/revisor | Pacote, CI Windows/Linux e revisão verificados |
| Consumidores | Setup real, personalização e restauração exata | Executor | Windows e Linux verificados |
| Retomada | Duas sessões novas, UUIDs e hashes reais | Clientes e executor | Codex verificado; Claude aguarda login |
| Publicação | Main protegida, Pages e observação externa | Mantenedor/executor | Publicação e hashes observados; ver operação |

PM define o aceite e o Tech Lead sustenta essa divisão. Cada entrega atualiza README e execução.
O revisor independente lê o diff completo antes da publicação. Falha fica pendente com a próxima ação.
