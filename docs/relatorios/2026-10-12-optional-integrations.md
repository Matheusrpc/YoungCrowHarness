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

O recorte original foi preparado independentemente do PR #27. Não inclui a redução geral do
README, alterações nas leis, avisos, pausa ou executor. O aceite YC-203 continua dependendo
do contrato local do fornecedor.

O [PR #27](https://github.com/Matheusrpc/YoungCrowHarness/pull/27) foi integrado em
`063df45633b93b1fe981290ccaa9d4c624240831`. A atualização do PR #28 sobre essa main produziu
`c2b1ef83dc629d6a47c9eefc3f2e6fea7a2f3069`, árvore `c03bad0d6b176cbe6a48cd1b5474d19ae3f13757`,
sem conflitos. A revisão independente confirmou que as correções de fontes/memória foram
preservadas; nenhum achado.

Na combinação, a suíte geral executou 345 casos em 155.647 s: 331 aprovados, 14 skips,
zero falhas/erros. O ensaio instalado passou nos dois consumidores com ambos os clientes:
hooks sem escrita, busca por palavras inteiras, citação literal sem alteração da fonte,
MCP vazio ou personalizado preservado e 18 capacidades obrigatórias correspondentes.
Restauração, trabalho do trial e perfil do usuário permaneceram íntegros. A conversão usa
fixture sintética; nenhuma chamada de modelo ou conversa nativa foi executada.

Os 11 testes Node passaram; vaults raiz/exemplo tiveram 3/22 notas sem problemas. Às 14:22 UTC,
manifesto e seis arquivos públicos responderam HTTP 200, com TLS verificada e hashes iguais
à árvore combinada. A revisão pública continua `80edd7786f3ecb13535565f5cb358ef1f983b757`:
os arquivos que disparam Pages não mudaram. A prova funcional anterior de navegador permanece
separada em [seu relatório](2026-10-12-filter-url-external.md); não foi repetida nesta conferência HTTP.

CI do código combinado: [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38262152085)
e [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38262159569). No checkpoint deste
registro, seis checks Linux passaram e dois Windows ainda executavam. O commit de documentação
também deve cumprir os checks protegidos. O estado final da integração fica no
[PR #28](https://github.com/Matheusrpc/YoungCrowHarness/pull/28).
Retorno após integração: reverter somente as mudanças deste PR por novo PR; configurações dos
consumidores existentes exigem comparação e decisão explícitas.

**English.** Setup now skips marketplace plugins by default; `--with-plugins`/`--com-plugins`
enables them for Claude. Trial and Codex retain their limits. New Claude MCP configuration is
empty; existing configuration survives `--force`. Installed adoption and restoration passed in
new and existing projects. Plugin calls are simulated; native client and provider execution
remain unverified by this delivery. PR #27 is merged. The combined code passed 331 tests with
14 skips, installed adoption/restoration in both consumer cases and all 11 board tests. Fresh
HTTPS checks confirmed unchanged public bytes; the public revision remains `80edd778`.
Six Linux CI checks passed at this checkpoint; two Windows checks and PR #28 integration
were still pending. Follow PR #28 for the final protected-check and merge state.

ATRASO: GitHub PR #27 0, PR #28 pendente neste checkpoint | CI final pendente | Pages 0
