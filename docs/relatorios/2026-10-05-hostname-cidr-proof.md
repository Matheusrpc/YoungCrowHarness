# Domínio permitido com negação CIDR

Frente: executor isolado / 2A-R1. Ensaio aprovado e executado em 2026-10-05,
às 07h59 em São Paulo, com Docker Sandboxes 0.46.0. R1 permanece parcial.

**A combinação nativa foi reprovada para o nosso requisito de controle do destino.**
O pedido por domínio alcançou o serviço de eco mesmo com `0.0.0.0/0` e `::/0`
negados. Os controles antes e depois também passaram. A credencial fictícia foi
substituída nos três pedidos. Nenhum modelo ou token real participou.

## Evidência da sequência A/B/A

| Etapa | Política da VM | Resultado observado |
|---|---|---|
| A | Domínio de eco permitido em 443; negações MCP/host/privadas mantidas | CONNECT/TLS válidos, HTTP 200, digest fictício correto |
| B | Mesma política, acrescida das duas negações CIDR universais | CONNECT/TLS válidos, HTTP 200, digest fictício correto |
| A2 | Apenas as duas regras de B retiradas; política A restaurada exatamente | CONNECT/TLS válidos, HTTP 200, digest fictício correto |

Foram três conexões novas e três GETs, sem retry ou redirecionamento, em 19,738s de
ensaio. A limpeza teve prazo separado. Cada tentativa tinha limite de dez segundos;
a sequência, de 120 segundos. O certificado observado tinha emissor Docker Sandboxes
Proxy CA. Os corpos e cabeçalhos devolvidos pelo eco foram descartados após comparar
o hash do valor fictício.

Na etapa B, a consulta de política continuou permitindo `postman-echo.com:443`.
Os alvos numéricos de documentação `203.0.113.1:443` e `[2001:db8::1]:443` receberam
negação explícita, associada às duas regras CIDR instaladas. Essas consultas não
abriram conexões aos alvos numéricos. O pedido real por domínio recebeu HTTP 200.
[Medição sanitizada e hashes](../medicoes/hostname-cidr-proof.json).

## Comportamento documentado

A ajuda de `sbx policy deny network`, consultada antes do ensaio, esclarece que um
domínio permitido não é comparado às regras CIDR do endereço resolvido. A
[referência oficial do comando](https://docs.docker.com/reference/cli/sbx/policy/deny/network/)
descreve o mesmo comportamento. A prova confirmou essa diferença na versão instalada.

A [revisão anterior](../superpowers/specs/2026-10-05-hostname-egress-decision.md) havia
registrado essa semântica como desconhecida a partir dos guias gerais. A referência
específica e a medição substituem essa dúvida. O resultado não demonstra uma falha
em relação ao contrato documentado do Docker; demonstra que essa combinação de
controles não cumpre o requisito adicional do YoungCrow.

Não houve tentativa de alcançar uma rede privada, chamada MCP, troca de DNS ou
redirecionamento controlado nesta rodada. O IP e a família da conexão final não
foram medidos; configurar as duas faixas não comprova tráfego IPv6. A fixture rodou
sob controle confiável na VM, sem cliente de IA ou isolamento adversarial novo.

## Limpeza e verificação

A negação geral foi restaurada antes da retirada das permissões temporárias. As
13 regras criadas pelo ensaio foram removidas, assim como a única entrada de
credencial fictícia, identificada por seu marcador exclusivo. Inventários de
credenciais iguais antes/depois; política da VM restaurada semanticamente, com
novo ID da negação geral; regras globais e das demais VMs preservadas. As cinco
VMs estavam paradas na conferência final. Nenhum erro de limpeza.

O classificador passou em um teste com seis cenários: resposta real sob negação
reprova a hipótese; timeout, TLS genérico, 403 sem atribuição ou controles ausentes
permanecem inconclusivos. O teste falhou antes da implementação e passou depois.
Essa checagem não substitui os três pedidos reais nem os transforma em certificação.
O runtime do produto não mudou; a suíte histórica de 390 testes não foi reexecutada.

## Próxima decisão

Encerrada a hipótese de obter o controle do IP final apenas acrescentando CIDRs ao
domínio permitido. Um intermediário na VM que dependa da mesma resolução do proxy
não corrige essa lacuna. `REVIEWED_PROFILES` continua vazio; R2/R3 não começaram.

O próximo desenho precisa de controle no ponto que resolve e abre a conexão final.
Uma possibilidade a avaliar é uma saída controlada após o proxy de credenciais.
O [upstream proxy do Docker](https://docs.docker.com/ai/sandboxes/configuration/upstream-proxy/)
é experimental e a documentação oferece configuração para o tráfego das sandboxes,
sem seletor por nome de VM nessa configuração. VMs existentes só incorporam essa
mudança quando seus proxies são recriados pelo reinício do daemon. Portanto, esse
caminho amplia o escopo operacional e exige nova decisão; não foi configurado ou
testado aqui. Nenhuma mudança global ou reinício ocorreu.

Essa avaliação produziu o [desenho de instalação exclusiva](../superpowers/specs/2026-10-05-exclusive-egress-decision.md),
aprovado para o modo local. O [plano da prova](../superpowers/plans/2026-10-05-exclusive-egress-proof.md)
aguarda revisão; nenhuma alteração de configuração.

É preciso definir isolamento do escopo, bloqueio de saída alternativa, validação do
IP no momento da conexão e observação desse endereço antes de implementar outro
componente. Credenciais no host e inacessibilidade de MCP/rede privada continuam
requisitos. Produção não publicada; nenhum recibo consumido deve ser repetido.

## English overview

The approved A/B/A probe completed three fresh connections and three echo GETs.
All returned HTTP 200 with the expected dummy credential, including phase B with
both universal IPv4/IPv6 CIDR denies active. Numeric policy checks were explicitly
denied while the hostname remained allowed. This matches the installed CLI help
and the command reference: resolved IPs of allowed hostnames are not checked
against CIDR rules. The native combination fails YoungCrow's destination requirement.

The disposable credential and all 13 temporary rules were removed, the original
policy restored, and all five VMs stopped. No real credentials, models, DNS changes,
private-network requests, MCP calls or daemon restart. Runtime code is unchanged.
Final peer address/family and new adversarial isolation were not measured. Profiles
remain empty. Evaluate enforcement at the final connection point; an upstream proxy
would require a separate scope decision and was not configured here.

The subsequent [exclusive local design](../superpowers/specs/2026-10-05-exclusive-egress-decision.md#english-overview)
is now approved; its [proof plan](../superpowers/plans/2026-10-05-exclusive-egress-proof.md)
awaits review. No configuration change or new native proof has occurred.

ATRASO: main 1
