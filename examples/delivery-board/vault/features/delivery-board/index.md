---
id: "7a8f5020-54ab-5c9d-8355-137c4fba336f"
type: "feature"
title: "Quadro de entregas"
origin: "youngcrow/public-pilot"
updated: "2026-10-12"
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
| P03: setup novo e migração preservando instruções | Verificado no Windows e Linux |
| P04: ponto inicial restaurado e trabalho do trial preservado | Ambos os consumidores verificados no Windows e Linux |
| P05: índices, identidade, links e resumo conciliado | 21 notas, zero problemas no validador |
| P06: retomada em sessões novas de Claude e Codex | Codex verificado; Claude aguarda login |
| P07: pacote permitido e CI | Linux: 8 testes passam sem skips; Windows: 7 passam, 1 skip de privilégio |
| P08: publicação observada e manifesto conferido | Verificada; revisão e hashes na operação |
| P09: roteiro PT/EN, README e processos | Demonstração, roteiro e provas ligados |

Desenvolvimento: página, modelo, pacote e adoção verificados. Produção: verificada na operação ligada acima.
Próxima ação registrada no piloto de 3/out: renovar o login do Claude e declarar nova tentativa limitada para concluir P06.

Incremento [U01: consulta retomável por URL](runs/filter-url.md), em 12/out: implementado e verificado
localmente com 11 testes Node e navegador em 1280px/360px. Integrado no PR #25, com deploy confirmado
pelo GitHub na revisão `80edd7786f3ecb13535565f5cb358ef1f983b757`.
Manifesto, bytes e filtros conferidos em 12/out. O teste de navegador usou transporte HTTPS delegado;
a TLS nativa do Chromium nesta cloud permanece sem validação. Veja os limites no registro de operação.

[Retomada nativa](runs/native-memory.md) registra hashes e limites da consulta.
