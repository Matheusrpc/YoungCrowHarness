# Endereços do gateway e sentinelas no Windows

Frente: executor isolado, 2A-R1. Provas locais em 5 de outubro de 2026, entre
01h13 e 01h18 de São Paulo. Desenvolvimento parcial; produção não publicada.

Dois ensaios usaram o launcher v2 já testado, um com OpenAI e outro com Anthropic.
O cliente sintético e seu filho não estabeleceram nenhuma das 124 conexões TCP
negativas. As sentinelas temporárias no Windows receberam somente os controles
positivos feitos pelo próprio host. A saída TLS do provedor permaneceu acessível.
Não houve autenticação, inferência ou chamada de ferramenta MCP.

## Escopo e resultados

O inventário consultou os nomes do gateway e do host dentro da VM. Seus endereços
IPv4/IPv6 foram conferidos novamente em cada ensaio. O teste incluiu portas 80,
443 e 3128, IPv4 mapeado em IPv6, o alias do host, loopback, metadata e a bridge
Docker. O nome `mcp-gateway.docker.internal` não resolveu diretamente; essa falha
de DNS permanece uma limitação, sem contar como prova de isolamento do serviço.

Cada rodada abriu três sentinelas TCP no Windows: loopback IPv4, um endereço da
interface LAN e loopback IPv6. Elas usaram portas efêmeras, sem alterar o firewall,
e aceitaram um controle positivo antes e outro depois do trabalho na VM. Os
endereços particulares e as portas exatas ficam nos recibos privados.

| Evidência | OpenAI | Anthropic |
|---|---:|---:|
| Tentativas TCP negativas, cliente e filho | 62 sem conexão | 62 sem conexão |
| TLS verificado, cliente e filho | HTTP 421 / 421 | HTTP 404 / 404 |
| Controles positivos nas sentinelas Windows | 6 | 6 |
| Conexões inesperadas nas sentinelas Windows | 0 | 0 |
| Conexões na sentinela da bridge | 0 | 0 |
| Pacotes contados em OUTPUT DROP IPv4 / IPv6 | 48 / 4 | 48 / 4 |
| Margem até o deadline de 45 segundos | 29.091,5458 ms | 28.993,1659 ms |
| Saída do trabalho / PID final | 0 / 0 | 0 / 0 |
| Tentativa de iniciar novamente | Recusada, 125 | Recusada, 125 |

As 124 tentativas são o total desta rodada, incluindo controles repetidos das
provas anteriores. Não são 124 cenários inéditos nem acréscimos à suíte de 390
testes. Os contadores de pacotes também não correspondem um a um às tentativas.

Em cada processo, seis conexões aos endereços IPv6 do gateway/host retornaram
`OSError`; esse registro não distingue ausência de rota de outros erros de rede.
As demais retornaram timeout. Não atribuímos todas as recusas ao firewall. Os
contadores confirmam descarte no namespace nos casos que produziram pacotes.
O ensaio não estabelece uma rota positiva da VM para o Windows: os controles
positivos das sentinelas foram locais ao Windows. Ele comprova a falta de acesso
nas rotas, configurações e versões observadas.

## Integridade e limpeza

O transporte conferiu ID da VM, digest da imagem, ausência de montagem do projeto
e hash do `sbx`. Os hashes do guardian e launcher corresponderam ao código atual
e ao candidato na VM. Cada operação teve UUID e recibo exclusivos, sem repetir os
ensaios anteriores. Um descritor manteve o namespace disponível para leitura dos
contadores após o fim do container e foi fechado na limpeza.

A negação da VM foi restaurada antes da retirada das exceções temporárias. As
permissões voltaram ao estado inicial; o ID da regra de negação mudou, como nos
ensaios anteriores. Políticas globais e de outras VMs permaneceram iguais. As
seis sentinelas foram fechadas, seus threads terminaram, e a VM ficou parada.
Nenhum certificado, login, regra de firewall do Windows ou reinício foi necessário.

O verificador auxiliar de evidências passou após falhar por ausência de implementação.
Seus casos negativos recusam tentativas ausentes, conexão estabelecida, filho
ausente, TLS sem verificação, falta de controle positivo, acesso à sentinela,
listener ainda aberto, VM em execução e política não restaurada. Esse teste é
privado do ensaio; não compõe a suíte histórica de 390 testes.

Os [comandos, hashes e resultados](../medicoes/gateway-endpoints.json) vinculam
os registros aos arquivos medidos. A [prova anterior de rede](2026-10-04-network-launcher.md)
preserva a implementação, a falha do proxy e as provas de recuperação.

## Próxima ação e limites

Atualização posterior: a [investigação de DNS e proxy](2026-10-05-proxy-resolution.md)
registra as medições seguintes e a dependência de autenticação ainda sem solução.
A próxima decisão passou a ser uma prova conjunta de autenticação e isolamento MCP.
Os resultados abaixo preservam o escopo e as pendências desta rodada anterior.

Verificar DNS, redirecionamentos e resolução no proxy transparente com controles
positivos e negativos. Estes ensaios não provocaram mudança de DNS nem receberam
redirecionamento controlado. As respostas 421/404 comprovam transporte TLS neste
cenário, sem certificar o uso autenticado dos clientes.

Também faltam reconstrução e prova do pacote atualizado, suspensão do Windows e
as etapas de integração e autenticação R2/R3. Ubuntu não foi homologado.
`REVIEWED_PROFILES` continua vazio. Nenhum código do runtime mudou nesta rodada;
a suíte de 390 testes é a execução anterior, não uma nova medição.

## English overview

Two operations exercised the current v2 launcher with provider networking enabled.
Client and child made 124 unsuccessful TCP connection attempts in total. These
include previously tested controls and must not be added to the historical unit
suite. OpenAI returned two TLS-verified HTTP 421 responses; Anthropic returned two
TLS-verified HTTP 404 responses. No credentials, inference or MCP RPC were used.

Each operation opened Windows sentinels on IPv4 loopback, one LAN interface and
IPv6 loopback. All six listeners passed controls before and after execution,
received zero unexpected connections and were closed. The inner bridge sentinel
also received none. Namespace counters recorded 48 IPv4 and four IPv6 OUTPUT
drops per operation. Six gateway/host IPv6 attempts per process returned generic
network errors, so their failures cannot all be attributed to filtering.

Gateway addresses were rechecked against the inventory. MCP had no directly
resolved address; DNS failure is not evidence of isolation. Windows positive
controls originated on Windows, without establishing a positive VM-to-host route.
Proof is limited to the measured addresses, versions and configuration.

Both workloads exited before their deadlines with PID 0, refused replay and
preserved final state. Scoped permissions were restored, unrelated policies were
unchanged and the VM stopped. No Windows firewall, certificate, login or daemon
restart was involved. Runtime source files are unchanged. R1 remains partial;
DNS/redirects, transparent-proxy resolution, package rebuilding, whole-host
suspension and R2/R3 still need proof. Native profiles remain empty.

ATRASO: main 1
