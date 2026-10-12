# Integrações opcionais na instalação

Frente: adoção do harness com escolha explícita de plugins e MCPs. Recorte da auditoria
já implementada no checkout do executor, transportado para `fix/optional-client-integrations`
sobre a main `e966e7e06dd30bbd039be839887f8d6de31c32f4`.

O setup pula plugins por padrão. `--com-plugins` ou `--with-plugins` habilita os cinco
plugins Claude de marketplace do catálogo; os aliases negativos continuam aceitos.
Trial e Codex continuam pulando esses plugins mesmo com opção positiva. A instalação
normal ainda instala humanizer e humanizer-ptbr, com os escopos atuais de cada cliente.
Pular plugins não remove instalações anteriores nem torna a instalação normal offline.

O template `.mcp.json` começa com `mcpServers` vazio. Configurações existentes permanecem
iguais byte a byte, inclusive com `--force`. Os exemplos Codex continuam desabilitados.
O smoke opcional de clientes declara n8n apenas em sua fixture descartável; nenhum
servidor real foi configurado ou ativado nesta frente.

Os testes reproduziram a chamada automática de plugins, os servidores presentes no template
e a ausência da opção positiva antes da mudança. Depois, 60 testes de setup terminaram:
58 aprovados, dois skips de plataforma. Incluem instalação padrão, ambos os aliases positivos,
falhas de marketplace/instalação, aliases negativos, preservação com `--force` e isolamento de
trial/Codex. A suíte geral terminou com 346 casos: 332 aprovados e 14 skips, zero falhas/erros,
em 142.877 s. Três notas do vault e 313 links locais passaram sem problemas; `bash -n` e
`git diff --check` também passaram. [Medição](../medicoes/2026-10-12-optional-integrations.json).

O ensaio com o runner real de adoção passou em pasta nova e projeto Git com alterações locais,
perfil `both`. Conferiu MCP vazio ou personalizado preservado, 18 observações obrigatórias do
catálogo correspondentes e dois MCPs Claude opcionais ausentes. O retorno restaurou o estado
inicial e preservou o trabalho do trial e o perfil do usuário nos dois casos. A auditoria do
checkout também passou. Catálogo e permissões ficaram iguais à base.

Revisão independente de código, testes e documentação sem achados. As skills retrieve-memory,
govern-capabilities, Ponytail, Karpathy e humanizer-ptbr orientaram retomada, escopo e redação.
As chamadas de plugins são simuladas e o Git dos testes usa origem local. Sem instalação real
de plugins, conversa de modelo, ensaio nativo de clientes, Docker, repetição de P06 ou navegador.
O smoke nativo foi ajustado, mas sua execução continua separada desta prova.

O PR #27 permanece independente, com oito checks aprovados em `9ff8eec`. Este recorte não leva
as correções de fontes/memória, a redução geral do README, alterações nas leis, avisos, pausa ou
executor. O aceite YC-203 continua dependendo do contrato local do fornecedor.

Integração e CI deste recorte ainda pendentes no checkpoint local. Retorno após integração:
reverter somente os commits deste PR por novo PR; configurações dos consumidores existentes
exigem comparação e decisão explícitas. Os arquivos públicos do site não mudaram.

**English.** Setup now skips marketplace plugins by default; `--with-plugins`/`--com-plugins`
enables them for Claude. Trial and Codex retain their limits. New Claude MCP configuration is
empty; existing configuration survives `--force`. Installed adoption and restoration passed in
new and existing projects. Plugin calls are simulated; native client and provider execution
remain unverified by this delivery. Integration and remote CI are tracked separately.

ATRASO: GitHub integração pendente | CI remoto pendente | Pages não aplicável
