# DNS, destino final e autenticação do executor

Frente: executor isolado / 2A-R1. Ensaios de 2026-10-05, entre 01h26 e 01h28 em São Paulo.
Estado: investigação parcial em desenvolvimento, sem publicação ou perfil certificado.

O cliente e seu filho não conseguiram consultar DNS diretamente nem alterar os arquivos
de resolução. A investigação também encontrou uma dependência ainda sem solução: a saída
direta atual não usa o mecanismo documentado de autenticação com credenciais retidas no host.
Os perfis permanecem vazios; R2/R3 não começaram.

## O que foi medido

O ensaio usou o launcher atual em Docker Sandboxes 0.46.0, sem montar o projeto, chamar
modelos ou executar ferramentas MCP. Um novo recibo preserva a tentativa de preparação
anterior. [Medição sanitizada e hashes](../medicoes/proxy-resolution.json).

| Controle | Observação | Limite da conclusão |
|---|---|---|
| DNS na VM confiável | Resposta UDP com uma resposta DNS | Controle positivo do resolvedor |
| DNS no cliente e filho | UDP: `PermissionError`; TCP: timeout | Não obtiveram resposta nos casos medidos |
| `/etc/hosts` e `/etc/resolv.conf` | Escrita recusada para cliente e filho | Arquivos protegidos nesta configuração |
| TLS com SNI Anthropic e IP fixado em `1.1.1.1` | Certificado validado e HTTP 404, nos dois processos | Não revela o endereço final do fornecedor |
| SNI de outro provedor, MCP, host e localhost | Encerramento TLS, sem resposta HTTP | Erro TLS sozinho não comprova negação de política |
| Sentinela Windows `127.0.0.1:443` | Dois controles positivos locais; zero acessos inesperados | Não prova disponibilidade da rota entre VM e host |
| Encerramento | Saída 0, PID 0, antes do prazo; repetição recusada com 125 | Recibo consumido, sem nova execução |

### Correção de interpretação

O TLS da Anthropic também foi validado no Windows, fora do Docker, ao conectar em
`1.1.1.1` com o mesmo SNI. Esse controle não enviou HTTP. Portanto, a observação **não
permite atribuir ao Docker** a seleção de outro destino. A interpretação inicial da sessão
foi corrigida: o endereço visto pelo socket não comprova o destino final depois dos
intermediários de rede. Não identificamos qual intermediário explica o resultado.

Não houve mudança controlada de DNS nem resposta HTTP de redirecionamento. Esses dois
casos continuam pendentes e não foram contabilizados como aprovados.

### Política declarada e comportamento observado

Durante o ensaio, `policy check` negou MCP e o alias do host e permitiu apenas o provedor
selecionado. Entretanto, o log do runtime registrou duas tentativas adicionais de MCP em
`allowed_hosts`, com regra `<dial failed>`. Isso registra uma conexão que falhou; não prova
negação de política, acesso ao serviço ou execução de uma ferramenta. A inacessibilidade
do MCP ainda não está estabelecida para o conjunto de rotas exigido.

## Dependência da autenticação

A documentação Docker informa que a injeção de credenciais ocorre somente no forward
proxy. A saída direta do candidato atual passa pelo caminho transparente, que não oferece
essa injeção. Portanto, ela ainda não atende ao mecanismo previsto de autenticação com
credenciais fora da VM. Não foi feita tentativa de login ou inferência nesta rodada.
Fontes: [isolamento](https://docs.docker.com/ai/sandboxes/security/isolation/) e
[credenciais](https://docs.docker.com/ai/sandboxes/configuration/credentials/), reconvertidas
com Docling 2.132.0 e relacionadas à execução no vault local.

O [ensaio anterior do proxy explícito](2026-10-04-network-boundary.md) alcançou uma resposta
MCP sob deny-all. Liberar esse caminho diretamente ao cliente, copiar tokens para a VM ou
substituir OAuth por API não resolve os requisitos aprovados. A CLI instalada expõe
`mcp.forceLocalGateway`, que seleciona o gateway local; não foi encontrado nela um controle
documentado de desligamento total.

## Preparação e limpeza

A primeira preparação tratou o código 1 de `policy check` para um destino negado como
falha do comando. Ela terminou antes do cliente na VM. O coletor corrigido leu a decisão
JSON e criou uma prova separada; os arquivos e recibos anteriores foram preservados.

As políticas temporárias foram retiradas, a política global permaneceu igual e a VM foi
parada. A sentinela desta tarefa foi fechada; um listener preexistente em outro endereço
do Windows foi preservado. A conferência posterior registra os cinco ambientes parados.
Não houve alteração de certificado, credenciais, firewall do Windows ou reinício do daemon.

## Próxima decisão: uma prova conjunta de rede e autenticação

Proposta apresentada nesta rodada, [aprovada e executada posteriormente](2026-10-05-auth-egress-spike.md): verificar se um filtro
confiável, limitado ao fornecedor escolhido, pode usar o forward proxy do Docker sem
expor MCP, rede privada ou tokens ao cliente. Priorizar configuração nativa ou componente
existente, antes de considerar um proxy próprio.

A prova seria descartável, com credencial falsa e fornecedor simulado, sem chamadas de IA
ou cópia de tokens reais. Deve testar destino permitido, MCP, endereços privados,
discordância entre CONNECT/Host/SNI, redirecionamentos e alteração de DNS. Cada caso
negativo precisa de controle positivo que estabeleça a causa do bloqueio. Um resultado
sintético não certifica OAuth real: essa prova continua exigida antes de habilitar perfis.
Limite de três ciclos; entregar uma recomendação de viabilidade, sem integrar código ao
produto. Mudanças globais, instalação permanente ou novo backend ficam fora da proposta.

Depois dessa decisão ainda faltam pacote atualizado, suspensão do host, autenticação real,
integração e recuperação dos recibos em R2 e adoção nos dois clientes em R3. A suíte de
390 testes (379 aprovados e 11 skips) é histórica; o runtime do produto não mudou nesta rodada.

## English overview

Direct DNS and resolver-file writes failed for both client and child. Verified Anthropic
TLS succeeded with a deliberately mismatched pinned IP, but the same result occurred
outside Docker. Attribution to Docker is therefore unproven, and final upstream resolution
remains unverified. DNS changes and redirects were not exercised.

Docker documents credential injection only through its forward proxy. The current direct
path does not provide that mechanism, while earlier unrestricted forward-proxy access
reached an MCP response. The proposed joint network/authentication probe was
[subsequently approved and executed](2026-10-05-auth-egress-spike.md#english-overview). Policies were restored, the task's listener
closed and the VM stopped. No model calls; native profiles remain empty; R1 is incomplete.

ATRASO: main 1
