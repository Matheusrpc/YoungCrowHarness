---
id: capabilities-index
type: index
title: Capacidades / Capabilities
origin: youngcrow/template
updated: 2026-10-02
index: ../index.md
---

# Capacidades / Capabilities

[Vault](../index.md) · [Integrações / Integrations](../integrations/index.md)

| Capacidade | Finalidade / Purpose | Entrada / Entry | Versão / Version |
|---|---|---|---|
| personalizer | Ideia, entrevista retomável, auditoria guiada e adaptação do projeto | [Skill](../../skills/personalizer/SKILL.md) | 2 |
| integrate-from-docs | Integrações API/SDK/webhook/MCP; fontes oficiais e histórico verificável | [Skill](../../skills/integrate-from-docs/SKILL.md) | 2 |
| integration-specialist | Papel que aplica a skill na sessão ou subagente do cliente selecionado | [Contrato compartilhado / Shared contract](../../skills/integrate-from-docs/SKILL.md) | 1 |
| ingest-source | Documentos, anexos, URLs, áudio e vídeo; fontes locais, evidência e retomada / Local sources, evidence and recovery | [Skill](../../skills/ingest-source/SKILL.md) | 1 |
| Docling | Conversão local opcional, documentos e mídia em ambientes separados / Optional local conversion in separate runtimes | [Procedimento / Procedure](../../skills/ingest-source/SKILL.md) | 2.132.0 |
| retrieve-memory | Retomar notas selecionadas e verificar decisões/entregas / Resume selected notes and verify evidence | [Skill](../../skills/retrieve-memory/SKILL.md) | 1 |
| Graphify | Grafo local opcional de links explícitos / Optional local graph of explicit links | [Procedimento / Procedure](../../skills/retrieve-memory/SKILL.md) | 0.9.73 |

Entradas nativas, quando instaladas: `.claude/agents/integration-specialist.md` e `.codex/agents/integration-specialist.toml`.
Native entries depend on the selected client. Availability is not evidence of use: each run records the capabilities actually used.

Docling e Graphify são runtimes locais opcionais. A descoberta da skill não prova uso por um modelo; registre cliente, versão e evidência por execução. claude-mem e memória MCP permanecem planejados.
Docling and Graphify are optional local runtimes. Skill discovery does not prove model use; record client, version and evidence per run. claude-mem and memory MCP remain planned.

Acrescente skills, agentes e MCPs reais com gatilhos, entradas/saídas, limites, versão e instruções de acesso. Nunca registre credenciais aqui.
