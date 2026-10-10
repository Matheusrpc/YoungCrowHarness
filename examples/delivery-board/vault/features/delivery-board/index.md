---
id: "7a8f5020-54ab-5c9d-8355-137c4fba336f"
type: "feature"
title: "Quadro de entregas"
origin: "youngcrow/public-pilot"
updated: "2026-10-09T22:59:34Z"
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
| P06: retomada em sessões novas de Claude e Codex | Codex verificado; Claude verificado por reavaliação offline e revisão semântica; ver retomada nativa |
| P07: pacote permitido e CI | Linux: 8 testes passam sem skips; Windows: 7 passam, 1 skip de privilégio |
| P08: publicação observada e manifesto conferido | Verificada; revisão e hashes na operação |
| P09: roteiro PT/EN, README e processos | Demonstração, roteiro e provas ligados |

Desenvolvimento: página, modelo, pacote e adoção verificados. Produção: verificada na operação ligada acima.
Próxima ação: preservar as provas de P06 e continuar o roadmap pelos aceites próprios de YC-011 e YC-203. Nenhum novo run de P06 é necessário.
[Retomada nativa](runs/native-memory.md) registra hashes e limites da consulta.
