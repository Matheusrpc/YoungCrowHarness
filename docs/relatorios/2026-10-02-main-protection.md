# Proteção da main

Frente: regras remotas do repositório Matheusrpc/YoungCrowHarness.
Data UTC: 2026-10-02.

A consulta inicial mostrou repositório público, sem rulesets e sem proteção clássica da `main`.
A conta Matheusrpc era o único colaborador listado, com papel administrador.

Foi ativado o [ruleset Protect main](https://github.com/Matheusrpc/YoungCrowHarness/rules/24342817),
ID `24342817`, somente para `refs/heads/main`, com lista de bypass vazia. Ele bloqueia exclusão e
force push, exige PR e resolução das conversas e requer o check `installer`, emitido pelo aplicativo
GitHub Actions (`15368`). A branch deve estar atualizada em relação à base antes do merge.

O número de aprovações obrigatórias é zero para permitir trabalho com um único mantenedor.
Quando houver outro revisor com escrita, a orientação é exigir uma aprovação independente.
Administradores também seguem as regras, embora ainda possam editá-las nas configurações.

A resposta de criação confirmou estado `active`, destino `main` e as quatro regras. A configuração
versionada fica em [main.json](../../.github/rulesets/main.json). O README e o guia PT/EN explicam
como operar e adotar a proteção; editar o JSON ou executar setup não altera regras remotas.
Assets e diagrama existentes foram preservados; prosa revisada com humanizer.

Esta entrega altera configuração do GitHub e documentação. Não altera código de aplicação,
credenciais ou permissões de colaboradores. Não houve merge do PR nem tentativa de escrita
destrutiva na branch para testar a proteção. O estado remoto foi conferido pela API do GitHub.
