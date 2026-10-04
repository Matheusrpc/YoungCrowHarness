---
id: "d584975a-66b6-5759-85e7-a1253e9fcbc5"
type: "sources"
title: "Fontes oficiais"
origin: "youngcrow/integrations"
updated: "2026-10-04T01:41:28+00:00"
index: "index.md"
---

# Fontes oficiais

[Integração](index.md)

Consulta em 2026-10-04 UTC. Documentação web atual; versão local de `sbx`: não instalada.
As nove fontes abaixo foram convertidas por Docling 2.132.0 em Markdown privado e conferidas
contra os trechos oficiais usados. Fonte convertida não é prova de runtime. Não publicamos as
cópias extraídas. O desenho define requisitos; a documentação descreve o fornecedor.

| Fonte | Orientação usada | Limite |
|---|---|---|
| [Instalação](https://docs.docker.com/ai/sandboxes/install/) | CLI local e pré-requisitos Windows/Ubuntu | Host ainda sem runtime |
| [Isolamento](https://docs.docker.com/ai/sandboxes/security/isolation/) | Clone ainda expõe ignorados; recursos compartilhados exigem revisão | MicroVM não certifica sozinha o perfil YoungCrow |
| [Credenciais](https://docs.docker.com/ai/sandboxes/configuration/credentials/) | OAuth, proxy, bindings e precedência API | Login/precedência ainda precisam de prova |
| [Codex](https://docs.docker.com/ai/sandboxes/agents/codex/) | Fluxo documentado do cliente | Nenhum diagnóstico autenticado executado |
| [Claude](https://docs.docker.com/ai/sandboxes/agents/claude-code/) | Login de assinatura pelo cliente | Nenhum diagnóstico autenticado executado |
| [TTL](https://docs.docker.com/reference/cli/sbx/ttl/) | Comando gerencia apenas cloud | Prazo local independente ainda será implementado/provado |
| [Política local](https://docs.docker.com/ai/sandboxes/governance/access-controls/local/) | Conferir política efetiva, incluindo kits | Preset não basta como prova |
| [FAQ](https://docs.docker.com/ai/sandboxes/faq/) | Conta Docker e execução local gratuita | Cloud e governança paga fora do escopo |
| [Windows OptionalFeature](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-optionalfeature) | `InstallState: 2` significa desabilitado | Hipervisor ativo não prova que WHP está habilitado |

Fatos de versões futuras precisam ser reconferidos antes da instalação. Não há pin de imagem
inventado: identidade e capacidades serão medidos no ambiente de prova antes da liberação.
