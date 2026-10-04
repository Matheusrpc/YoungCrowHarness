---
id: "14b8c843-2597-50e0-ad81-de68d09dfbc8"
type: "implementation"
title: "Implementação"
origin: "youngcrow/integrations"
updated: "2026-10-04T01:41:28+00:00"
index: "index.md"
---

# Implementação

[Integração](index.md) · [Desenho](../../../../docs/superpowers/specs/2026-10-04-isolated-executor-design.md)

Estado: não implementado. Nenhum adaptador, cliente, container ou serviço instalado nesta entrega.
O desenho mantém Python/SQLite, clientes oficiais e recibos existentes, acrescentando isolamento
local e um prazo que não depende da sobrevivência do coordenador.

| Entrega | Aceite necessário |
|---|---|
| 2A-R1 | Preflight, pacote sanitizado, política e prazo comprovados sem modelo |
| 2A-R2 | Adaptador, reserva antes do efeito, parada e reconciliação |
| 2A-R3 | Diagnóstico autenticado limitado de cada cliente e adoção verificada |

Sem APIs de modelo próprias, mudança automática de modelo/esforço ou importação de caches de login.
Paginação e webhooks não se aplicam ao diagnóstico. API de modelo opcional continua sem perfil
executável até prova de conexão e orçamento. A reserva por UUID antecede o efeito; queda mantém
incerteza, sem repetição automática. O CLI do fornecedor pode criar estado persistente; encerrar
seu processo não comprova término da VM. O limite precisa de controle independente e testes.

Desvio consciente dos exemplos do fornecedor: não montar o checkout original, mesmo com `--clone`;
não herdar permissões amplas, skills compartilhadas, SSH ou gateway MCP. O supervisor interno,
protegido do cliente sem privilégios, é uma hipótese do YoungCrow que precisa ser provada antes
da chamada real.
