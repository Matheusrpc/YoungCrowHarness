# Compatibilidade com Claude Code e Codex

Frente: completar as adaptações de cliente previstas em R01 na [especificação](../superpowers/specs/2026-10-01-youngcrow-foundation-design.md), por solicitação do mantenedor após a primeira entrega.

## Comportamento entregue

O setup passa a aceitar `--client claude`, `--client codex` e `--client both`, que é o padrão. `CLAUDE.md` e `AGENTS.md` mantêm as regras comuns. Cada modo copia somente as configurações específicas necessárias, preservando arquivos existentes sem force.

Claude mantém as skills em `~/.claude/skills/`, usa `.mcp.json` e `.claude/settings.json`. Codex recebe as skills no projeto, em `.agents/skills/`, usa `.codex/config.toml` e `.codex/hooks.json`. O preflight valida todos os destinos selecionados antes de copiar; divergências de revisão ou mudanças locais em humanizer são preservadas e interrompem a execução. Downloads no projeto ficam ignorados pelo Git, inclusive ao adotar um ignore preexistente.

O modo Codex não executa instalações do Claude. Plugins Codex continuam pelo catálogo do próprio cliente, sem assumir compatibilidade automática entre marketplaces. O setup não altera sandbox, credenciais nem aprovações pessoais. Os MCPs de exemplo do Codex começam desativados para configuração e revisão.

O hook do Codex ganhou comando Windows com Python e encaminhamento ao Bash somente se o executável opcional de impeccable existir. O teste confirma ausência segura e propagação de código de falha. A execução de hooks no cliente continua exigindo confiança explícita.

## Verificação com clientes reais

Em Windows, `tests/smoke_clients.py` foi executado com Codex CLI **0.146.0** e Claude Code **2.1.220**, usando usuário/configuração temporários, Git local e nenhuma chamada de modelo:

- Codex `config/read`: carregou os dois MCPs do TOML do projeto, ambos desativados.
- Codex `skills/list`: descobriu humanizer e humanizer-ptbr. A skill humanizer era uma fixture Git local com metadata válida; humanizer-ptbr era o arquivo distribuído pelo harness.
- Codex `hooks/list`: descobriu PostToolUse e Stop, sem erros de configuração.
- Claude `mcp get n8n`: reconheceu o servidor do projeto em estado pendente de aprovação; nenhuma conexão MCP foi iniciada.

Isso comprova descoberta/configuração nesses clientes. Não comprova autenticação externa, execução de plugins reais, comportamento do modelo ou execução aprovada dos hooks. O [guia bilíngue](../USAGE.md) ensina como conferir e ativar cada componente.

## Decisões e limites

- Skills Codex no projeto: a descoberta no diretório de usuário simulado não ocorreu no teste Windows. O caminho de projeto documentado oficialmente foi reconhecido pelo cliente real e evita alterar o catálogo pessoal do Codex. Cada clone/worktree precisa rodar o setup.
- Instalação Claude no usuário: mantém compatibilidade com o instalador anterior e exige atenção a skills preexistentes.
- Sem conversão automática de MCPs existentes: guias explicam como reconciliar JSON e TOML, preservando configurações do consumidor. Os testes conferem que os exemplos versionados têm as mesmas URLs.
- Confiança de projeto e de hooks continua sendo decisão do usuário no cliente. A fixture de teste confia somente em seu projeto descartável.
- Design system preservado: assets intactos; README e guia continuam bilíngues com a mesma identidade visual.
- Entradas Bash preservadas com LF por `.gitattributes`; conferido um checkout com `core.autocrlf=true` para evitar quebra do setup ao clonar no Windows.

Estado de desenvolvimento: adaptações implementadas; resultados de regressão e CI registrados no PR. Estado de produção: nenhuma aplicação publicada. Vault, personalizer e demais entregas seguem na especificação.

Revisão independente: sem achados críticos ou importantes. A alternância de modos (`both → claude → both`) pode acrescentar regras repetidas ao ignore; a proteção permanece válida e repetições do mesmo modo são estáveis. Essa melhoria menor permanece adiada.
