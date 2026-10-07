# Fronteira de rede do executor

Frente: executor isolado, 2A-R1. Ensaio de desenvolvimento no Windows com `sbx` 0.46.0,
registrado em 2026-10-05 UTC, ainda 2026-10-04 no horário local. Produção não publicada.

Continuação: a [integração no launcher](2026-10-04-network-launcher.md) implementa
autorizações por fase e registra novas provas. Este relatório conserva o experimento
anterior, seus hashes e as pendências observadas naquele momento.

O ensaio encontrou uma rota que precisa ficar fora do alcance do cliente: o proxy HTTP
do Docker respondeu `405` ao destino MCP mesmo com a regra de rede `deny **` ativa.
Não houve chamada de ferramenta ou mensagem JSON-RPC; a requisição foi `HEAD /`.
Falhar na resolução DNS do nome do gateway não impediu essa resposta pelo proxy.
Esse resultado reprova a hipótese de usar o proxy diretamente como fronteira MCP.

## Alternativa testada

O supervisor existente iniciou um contêiner com `network none`, aguardando o comando
de inicialização. O controlador confiável instalou regras IPv4/IPv6 de negação no
namespace de rede desse contêiner e liberou apenas TCP/443 para um IP público resolvido
para o provedor escolhido. Só depois conectou a interface. O namespace e as regras
permaneceram iguais nessa transição; o cliente não recebeu privilégios de rede.

A política temporária do Docker autorizou somente o domínio do provedor na porta 443,
na VM de teste. Cada provedor teve sua própria execução. O cliente e seu filho fizeram
requisições sintéticas `HEAD /`, com validação do certificado TLS e do nome do servidor.
Não receberam credenciais, configuração MCP ou acesso ao proxy HTTP do gerenciador.

| Verificação | OpenAI | Anthropic |
|---|---|---|
| TLS para o domínio selecionado, no cliente e no filho | Certificado válido; HTTP 421 | Certificado válido; HTTP 404 |
| Acesso ao proxy, inclusive a rota MCP | Timeout | Timeout |
| TLS usando o nome do outro provedor ou do gateway no IP permitido | Conexão encerrada | Conexão encerrada |
| Porta alternativa do gerenciador, rede privada, metadata, loopback e IPv6 testados | Sem conexão | Sem conexão |
| Sentinela na bridge do Docker interno | Zero conexões | Zero conexões |
| UID, capabilities e arquivos de controle | UID 1000, capabilities zeradas, acesso recusado | Mesmo resultado |
| Encerramento | PID 0, dentro do prazo | PID 0, dentro do prazo |

São quatro processos observados, com quatro respostas TLS do destino escolhido e
40 tentativas negativas de rede. O HTTP 421 da OpenAI também ocorreu numa comparação
fora da VM, com e sem ALPN. Ele comprova transporte TLS neste ensaio; não comprova que
a API ou um cliente autenticado esteja pronto para uso. O 404 da Anthropic tem o mesmo
limite: não houve inferência, login ou teste de catálogo.

## Falhas preservadas e limpeza

A primeira tentativa parou ao resolver o nome MCP. O segundo ensaio observou a resposta
405 pelo proxy; seu código de saída zero indica apenas que a coleta terminou. A primeira
tentativa direta recusou o HTTP 421. Esses recibos continuam registrados como resultados
distintos, sem substituir falhas por aprovações.

A limpeza inicial presumiu que uma lista de destinos gerava uma única regra. A CLI criou
uma regra por destino, e a verificação interrompeu a remoção depois de restaurar `deny **`.
A reconciliação conferiu os IDs gravados, retirou somente as regras temporárias e parou
a VM. Os dois ensaios seguintes concluíram a limpeza automaticamente. A negação restaurada
recebeu outro ID; seu conteúdo é equivalente. Regras globais e das outras VMs permaneceram
iguais. As cinco VMs estão paradas. Nenhum certificado, login ou reinício do daemon foi usado.

## O que falta

Esta é uma prova de viabilidade com controlador sintético. `runtime/sbx/guardian.py` e
`launcher.py` não mudaram; o launcher do produto ainda exige `NetworkMode=none`.
`REVIEWED_PROFILES` continua vazio e o preflight mantém `mcp_isolation_unverified`.

O próximo passo é incorporar a configuração e a conferência da rede ao lançamento
durável, recusando o despacho diante de estado ausente, alterado ou incerto. Depois,
provar perda do controlador, reinício e tentativas de alterar regras com essa rede ativa.
Ainda faltam uma sentinela no host Windows, alternativas de endereço do gateway,
redirecionamento e troca de resolução DNS, reconstrução do pacote e suspensão total do host.
O firewall testado rejeita saídas diretas para IPs não permitidos; isso não certifica o
comportamento de resolução do proxy transparente do fornecedor. Ubuntu também não foi testado.
Autenticação, descoberta dos modelos e os PBIs R2/R3 seguem pendentes.

Os [recibos e hashes](../medicoes/network-boundary.json) distinguem prova, falha e lacuna.
As sete fontes oficiais foram convertidas por Docling e relacionadas à execução no vault
privado. A [documentação de rede](https://docs.docker.com/ai/sandboxes/governance/concepts/)
orienta a política; a [documentação do gateway](https://docs.docker.com/ai/sandboxes/mcp-gateway/)
descreve sua presença. Os resultados acima vêm do runtime observado.

## English overview

The forward-proxy route returned HTTP 405 for the MCP gateway despite an active deny-all
network rule. DNS failure was therefore insufficient evidence of isolation. No RPC or MCP
tool was invoked. A separate feasibility probe installed default-deny IPv4/IPv6 rules in
the inner container network namespace before attaching its interface. Only one resolved
public provider IP on TCP/443 was reachable; a scoped Docker rule allowed that provider's
hostname. OpenAI and Anthropic were tested in separate operations.

Client and descendant both verified TLS for the selected domain. OpenAI returned 421,
also observed outside the VM; Anthropic returned 404. These are transport results, not
authenticated API or model readiness. Forty negative network attempts across four processes
did not connect to the tested proxy/private targets or complete TLS with disallowed names.
The inner bridge sentinel accepted zero connections. The physical Windows host sentinel,
DNS changes, redirects and remaining gateway address variants have not been tested.

An initial cleanup assumption failed because the CLI creates one rule per destination.
Deny-all was restored first; reconciliation removed only recorded temporary rules and
stopped the VM. Both final probes cleaned up automatically. Global and unrelated policies
are unchanged. All five VMs are stopped. Product guardian and launcher are unchanged,
native profiles remain empty, and R1 is partial. Next: integrate and verify the network
boundary in the durable launch protocol before rebuilding the package and completing the
remaining runtime and authentication proofs.

ATRASO: main 1
