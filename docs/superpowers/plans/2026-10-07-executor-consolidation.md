# Concluir o executor isolado

Plano aprovado pelo operador em 2026-10-07. Docker Sandboxes permanece; o aceite
exige Claude Code e Codex por assinatura. Sem fallback para API ou execução no host.

## PBI 1 — Diagnóstico

Consolidar consultas sbx num adaptador, com comandos permitidos, prazo, identidade,
contexto e erros classificados. Preservar stdout/stderr sensíveis somente em armazenamento
privado opcional. Reusar client environment/check/runs/reconcile. Investigar secret ls
somente por leitura; contexto remoto é hipótese. Consultas preparatórias completas
antecedem efeitos. Testar saída vazia, JSON inválido, timeout, permissões e deriva.

## PBI 2 — Executor

Reusar guardian, launcher e reservas; intenções duráveis antes dos efeitos, identidade
antes do despacho, credenciais fora da VM, MCP/host inacessíveis. Prova sintética
A/B/A2 com bloqueio atribuível, restauração verificada e digest exato. Recuperar sem
iniciar VM parada nem repetir operação. Preservar recibos e fontes consumidas.

## PBI 3 — Clientes e adoção

Integrar check aos recibos; uma chamada até 120s para cada cliente autenticado,
modelo/esforço escolhido e resultado verificado. Liberar perfil somente após ambos.
Testar adoção nova/existente e recuperação. README PT/EN, guia, backlog, diagramas
e vault coerentes; runner dedicado somente comprovado depois de ensaio real.

## Gates

Contratos → diagnóstico somente leitura → prova sintética integrada → Claude → Codex
→ adoção. No máximo três ciclos de correção, cada um com causa e regressão antes
de ensaio nativo. Incompatibilidade estrutural ou limite encerra investigação,
sem roteiro alternativo nem redução de segurança. Pipeline PBI/QA/deploy não faz
parte deste aceite. Nenhuma longa prova do operador antes do diagnóstico completo.
