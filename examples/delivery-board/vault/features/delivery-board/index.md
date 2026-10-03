---
id: "7a8f5020-54ab-5c9d-8355-137c4fba336f"
type: "feature"
title: "Quadro de entregas"
origin: "youngcrow/public-pilot"
updated: "2026-10-03T11:41:15+00:00"
index: "../index.md"
---

# Quadro de entregas

[Features](../index.md) · [Perfil](../../product/profile.md) · [Entregas](delivery.md)
· [Execução](runs/implementation.md) · [Decisão](../../decisions/static-site.md)
· [Integração Pages](../../integrations/github/pages/index.md) · [Operação](../../operations/index.md)
· [Capacidades](../../capabilities/index.md)

Objetivo: permitir que uma pessoa consulte entregas e navegue de cada tema às suas decisões e provas.
O cenário da lista é fictício; os resultados deste vault descrevem a implementação real do exemplo.
Responsável pela aprovação: mantenedor. Execução: Codex nesta sessão, um escritor.

| Aceite | Estado observado |
|---|---|
| P01: lista, combinação de filtros, vazio, limpeza e entrada inválida | 4 testes e percurso de navegador passam |
| P02: teclado, tela estreita e processos encerrados | Verificado localmente em 1280px e 360px; zero processos próprios |
| P03: setup novo e migração preservando instruções | Verificado no Windows; CI Linux pendente |
| P04: ponto inicial restaurado e trabalho do trial preservado | Ambos os consumidores verificados no Windows |
| P05: índices, identidade, links e resumo conciliado | 20 notas, zero problemas no validador |
| P06: retomada em sessões novas de Claude e Codex | Pendente |
| P07: pacote permitido e CI | Pacote local: 7 testes passam, 1 skip Windows; job CI preparado |
| P08: publicação observada e manifesto conferido | Pendente |
| P09: roteiro PT/EN, README e processos | Documentação em andamento |

Desenvolvimento: página, modelo e dados verificados localmente. Produção: não verificada.
Próxima ação: conferir CI e retomar a memória nos dois clientes; consultar a execução para o detalhe de cada prova.
