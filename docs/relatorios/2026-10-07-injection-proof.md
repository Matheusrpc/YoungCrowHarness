# Prova interna de injeção da credencial fictícia

Frente: YC-203.6. Data: 2026-10-07.

A fixture anterior aceitava o eco do próprio placeholder. Esse resultado também
ocorria sem injeção. O contrato v4 exige um valor diferente e compara seu SHA-256
com o hash esperado fixado no plano. O teste integrado agora falha quando o upstream
simulado devolve o placeholder sem substituição. **203.6 continua parcial:** ainda
falta comprovar o contrato de remoção segura da credencial no sbx local 0.46.0.

## Implementação

Manifesto, plano e registro v4 acrescentam `relay.injection_sha256`. A/B/A2 compartilham
placeholder, hash esperado, proxy e CA, mantendo UUIDs/nonces distintos e prazo compartilhado.
Hash do próprio placeholder é recusado antes da conexão. A fixture exige um único
header textual, diferente do placeholder e com o hash correto; duplicatas, tipo
incorreto ou valor divergente falham. O resultado schema 2 devolve apenas metadados.
O valor fictício esperado não entra em manifesto, argv nem recibo.

Guardian confere os comandos completos de inicialização e despacho. Sufixo extra é
recusado. Launcher aplica os gates de CA/rede/UID ao v4 e valida o contrato antes de
consultar Docker. O controlador compara o resultado fechado com o hash do manifesto;
o hash recebido da resposta não define a expectativa.

V2/v3 continuam legíveis e recuperáveis. O eco schema 1 conserva o significado antigo,
sem virar prova de injeção. `proof_accepted=false`, B `blocked_unattributed` e perfis
vazios permanecem. A entrada pública conserva `failed/controller_pending`.
Dez hashes de conteúdo do catálogo foram atualizados; contratos e permissões não mudaram.

## Provas e limites

O teste A/B/A2 usa os processos do controlador, fixture, relay e guard, sockets locais
e o diário real. A e A2 verificam o hash; B não encontra saída. Depois da ausência do
proprietário, a recuperação encerra o registro v4. No negativo sem substituição, A
falha e impede o despacho de B, mantendo a tentativa consumida.

As fronteiras sbx, TLS e substituição de header no upstream são simuladas. A fixture
continua pedindo a porta fixa; o teste traduz a porta para um listener efêmero no
mesmo host, evitando disputa de `TIME_WAIT` entre testes. Produção conserva sua porta
e namespace. Não houve Docker, login, modelo, imagem reconstruída ou novo ciclo
nativo. O contador permanece em **2/3**.

A revisão independente não encontrou achados críticos ou importantes. Conferiu
hash fixado, configuração comum entre fases, comandos completos, recusa de resultados
legados e recuperação v2/v3/v4. Reproduziu 121 testes focados aprovados. A
[medição](../medicoes/2026-10-07-injection-proof.json) registra a suíte pública,
árvore testada, hashes dos logs, fontes e limites.

Suíte pública: **607 testes, 587 aprovados e 20 pulados**, sem falhas/erros em
250.427 s. Os pulados dependem de Windows nativo ou grupo secundário POSIX ausente.
Código, testes, setup e catálogo coincidem com a árvore testada; após a execução,
as alterações ficaram restritas à documentação.

## Contrato nativo: o que mudou na pesquisa

As fontes abaixo foram lidas no Docker Docs, revisão
`7ba25eeb0c4c594f79e6efadad1af5eaca0500a8`; URLs e SHA-256 constam na medição.

- A [referência Cloud](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/reference/api/sandboxes/_index.md)
  identifica o escopo publicado da API.
- O [OpenAPI](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/reference/api/sandboxes/api.yaml)
  define `Secret.uid`/nome imutáveis, `etag` forte e DELETE condicionado por `If-Match`.
  Ausência da precondição retorna 428; versão antiga, 412. A operação pode retornar
  501 quando não implementada. Placeholder é estável mesmo após rotação do valor.
- A [comparação local/cloud](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/manuals/ai/sandboxes/cloud/local-vs-cloud.md)
  documenta backends e recursos separados, inclusive secrets. A menção genérica a
  Unix socket na API não estabelece compatibilidade com o daemon local 0.46.0.
- [`secret set-custom`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_secret_set-custom.yaml)
  distingue injeção Cloud de substituição local do placeholder.
- A [proveniência 0.46.0](https://github.com/docker/sbx-releases/releases/download/v0.46.0/DockerSandboxes-windows-amd64.provenance.json)
  aponta para `docker/sandboxes`, revisão `991967dc90ce0d9a440cd1df1bdf3e395c5a2693`.
  O [repositório de releases](https://github.com/docker/sbx-releases/blob/2329d12106fee653c0890152947fdd827e00cfd0/README.md)
  identifica software proprietário; a fonte apontada não estava publicamente acessível.

A lacuna é a ligação desse contrato ao endpoint e armazenamento do sbx local 0.46.0,
incluindo suporte à remoção condicionada atômica. Ler/comparar e depois executar
`secret rm` deixa uma janela para alteração externa. Placeholder, host e sandbox
iguais não fecham essa janela. O adaptador nativo continua recusando set/restart;
nenhum schema local ou suporte de endpoint foi presumido.

Próxima etapa: obter o contrato compatível do daemon local, com identidade e versão
após rotação e recusa atômica de versão antiga. Depois, implementar o adaptador e
provar o pacote exato em A/B/A2. Docker TLS, bloqueio de MCP/host/rede privada,
atribuição de B, origem nativa dos IPs proibidos e clientes autenticados ainda exigem
aceite. A documentação foi lida diretamente; conversão Docling permanece pendente
por `runtime_missing`, com recibo privado.

## Publicação e retorno

Destino: branch `feat/isolated-executor`, [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
Base deste incremento: `ef88edc`; main preservada em `932b775`. A medição registra a
publicação observada. CI permanece não verificado; acesso Git não comprova resultado do CI.

Retorno: recuperar registros v4 com esta versão antes de reverter o incremento.
Código anterior não interpreta v4. Não apagar o ledger nem reabrir operações consumidas.
O ambiente cloud já oferece o Python necessário aos testes; nenhum serviço, dependência
ou configuração adicional foi necessário para esta entrega.

## English overview

V4 fixes an expected SHA-256 before dispatch and rejects a literal placeholder echo.
A/B/A2 share placeholder/hash/proxy/CA with distinct phase identities. Exact commands,
closed schema 2 results and legacy v2/v3 recovery are verified locally. The integrated
test runs real fixture/relay/guard processes and sockets with simulated sbx, TLS and
upstream substitution. It does not certify native injection or deletion.

Docker's Cloud API documents immutable secret identity and conditional deletion via
strong etags and `If-Match`. Compatibility with the local sbx 0.46.0 endpoint and store
remains unproven. This is the next required contract before implementing the native
adapter. Native profiles remain blocked, no models or Docker were run, and the cycle
counter remains 2/3. Measurement details and publication evidence are linked above.

ATRASO: main 1 frente sem aceite | PR #24 1 incremento pendente de publicação | aceite nativo pendente.
