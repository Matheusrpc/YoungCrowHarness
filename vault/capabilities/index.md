---
id: capabilities-index
type: index
title: Capacidades / Capabilities
origin: youngcrow/template
updated: 2026-10-03
index: ../index.md
---

# Capacidades / Capabilities

[Vault](../index.md) · [Integrações / Integrations](../integrations/index.md)

| Capacidade | Finalidade / Purpose | Entrada / Entry | Versão / Version |
|---|---|---|---|
| govern-capabilities | Catálogo, auditoria offline, revisão privada e provas por cliente / Catalog, offline audit, private review and client evidence | [Skill](../../skills/govern-capabilities/SKILL.md) | 1 |
| personalizer | Ideia, entrevista retomável, auditoria guiada e adaptação do projeto | [Skill](../../skills/personalizer/SKILL.md) | 2 |
| integrate-from-docs | Integrações API/SDK/webhook/MCP; fontes oficiais e histórico verificável | [Skill](../../skills/integrate-from-docs/SKILL.md) | 2 |
| integration-specialist | Papel que aplica a skill na sessão ou subagente do cliente selecionado | [Contrato compartilhado / Shared contract](../../skills/integrate-from-docs/SKILL.md) | 1 |
| ingest-source | Documentos, anexos, URLs, áudio e vídeo; fontes locais, evidência e retomada / Local sources, evidence and recovery | [Skill](../../skills/ingest-source/SKILL.md) | 1 |
| Docling | Conversão local opcional, documentos e mídia em ambientes separados / Optional local conversion in separate runtimes | [Procedimento / Procedure](../../skills/ingest-source/SKILL.md) | 2.132.0 |
| retrieve-memory | Retomar notas selecionadas e verificar decisões/entregas / Resume selected notes and verify evidence | [Skill](../../skills/retrieve-memory/SKILL.md) | 1 |
| Graphify | Grafo local opcional de links explícitos / Optional local graph of explicit links | [Procedimento / Procedure](../../skills/retrieve-memory/SKILL.md) | 0.9.73 |
| yc-personalizer | Start or resume project onboarding and mission discovery | [Skill](../../skills/yc-personalizer/SKILL.md) | 1 |
| yc-config | Choose or update project agent defaults | [Skill](../../skills/yc-config/SKILL.md) | 1 |
| yc-missao | Refine backlog and prepare or revise one to N features | [Skill](../../skills/yc-missao/SKILL.md) | 1 |
| yc-status | Read mission state and pending work | [Skill](../../skills/yc-status/SKILL.md) | 1 |

Entradas nativas, quando instaladas: `.claude/agents/integration-specialist.md` e `.codex/agents/integration-specialist.toml`.
Native entries depend on the selected client. Availability is not evidence of use: each run records the capabilities actually used.

Docling e Graphify são runtimes locais opcionais. A descoberta da skill não prova uso por um modelo; registre cliente, versão e evidência por execução. claude-mem e memória MCP permanecem planejados.
Docling and Graphify are optional local runtimes. Skill discovery does not prove model use; record client, version and evidence per run. claude-mem and memory MCP remain planned.

Acrescente skills, agentes e MCPs reais com gatilhos, entradas/saídas, limites, versão e instruções de acesso. Nunca registre credenciais aqui.

O manifesto estruturado é `skills-lock.json` (esquema 3, leitura compatível com 2). Registros privados
de revisão e uso ficam no microíndice `vault/local/capabilities/index.md`, quando criado. Consulte-o
localmente; este catálogo público não aponta para pacotes privados nem prova execução.

The structured manifest is `skills-lock.json` (schema 3, compatible reader for 2). Private review/use
records belong in `vault/local/capabilities/index.md` when created. Consult it locally; this public
catalog does not link private bundles or establish execution evidence.
