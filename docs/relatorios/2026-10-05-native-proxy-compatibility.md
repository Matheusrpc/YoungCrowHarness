# Compatibilidade com o proxy real

Frente: executor isolado / 2A-R1. Continuação autorizada: “bora seguir man”.
Ensaios de 2026-10-05, entre 01h58 e 02h02 em São Paulo. R1 parcial, sem publicação.

Continuação: a [prova de domínio com negação CIDR](2026-10-05-hostname-cidr-proof.md)
foi concluída depois desta rodada e reprovou a combinação nativa para o controle
do endereço resolvido. As evidências abaixo permanecem válidas para seus ensaios.

O proxy real aceitou CONNECT por IP e TLS para OpenAI e Anthropic. Entretanto, os
ensaios com credencial descartável passaram somente por domínio: os caminhos por IP
falharam no TLS em dois serviços de teste. O log do Docker recusou o nome do serviço
no túnel sem interceptação (`forward-bypass`). O candidato da simulação ainda não reúne
evidência para integração ao produto. Não houve chamada de modelo ou uso de tokens reais.

## Resultado das três provas

| Prova | Resultado | O que comprova |
|---|---|---|
| OpenAI e Anthropic: CONNECT por domínio e por IP | Quatro CONNECTs aceitos e quatro TLS validados | Transporte com a identidade TLS solicitada; nenhuma requisição HTTP de aplicação |
| httpbingo: credencial descartável | Por domínio: HTTP 200 e valor substituído; duas tentativas por IP falharam no TLS | Substituição no caminho por domínio; combinação com IP não comprovada |
| Postman Echo: controle independente | Por domínio: HTTP 200 e valor substituído; por IP: falha TLS | Repete a diferença em outro serviço |
| Postman Echo: marcador não registrado, por domínio | HTTP 200 e marcador original preservado | Controle negativo da substituição |
| Windows fora do Docker, para os dois serviços | TLS validado por IP/SNI, sem HTTP de aplicação | Os destinos aceitaram essa forma de conexão fora do caminho da sandbox |

Nos dois serviços, o CONNECT por domínio respondeu `HTTP/1.1 200 OK`; por IP,
`HTTP/1.0 200 Connection established`, seguido de `SSLEOFError`. No Postman, o
certificado do caminho por domínio tinha emissor `Docker Sandboxes Proxy CA`.
O controle externo recebeu certificado Let's Encrypt. O log de política atribuiu os
três bloqueios a `forward-bypass`, com o motivo
`tunneled name not permitted on a no-MITM CONNECT tunnel`. O IP foi aceito inicialmente,
mas o nome apresentado dentro do túnel foi recusado. Este é o motivo reportado pelo
runtime; a implementação interna não foi auditada. A prova não autoriza desligar essa proteção.

O primeiro controle com marcador não registrado também usou IP e falhou antes de HTTP.
Ele não foi contado como controle negativo de credencial. A terceira prova corrigiu
esse desenho usando o domínio para o marcador não registrado, com recibo separado.
Nenhum recibo anterior foi apagado, sobrescrito ou reexecutado.

As falhas por IP ocorreram antes do envio de HTTP de aplicação. Ao todo, houve dez
CONNECTs nativos, sete TLS nativos concluídos e três requisições GET de eco com HTTP 200.
Os dois TLS no Windows são controles adicionais. Esses números não se somam à suíte
histórica de testes unitários. Receber 200 no CONNECT não prova TLS, autenticação ou isolamento.

## Credenciais e limpeza

Foram criadas duas entradas temporárias de `secret set-custom`, cada uma restrita à VM
de diagnóstico e ao domínio exato do serviço de eco. Os valores eram textos aleatórios
identificados como credenciais falsas. Nenhuma chave de OpenAI/Anthropic ou token OAuth
foi lido, substituído ou enviado. O código dentro da VM recebeu apenas o placeholder e
o hash esperado; o valor descartável foi registrado no gerenciador do host.

Os serviços de eco devolveram o cabeçalho recebido. A prova comparou seu hash e salvou
somente resultados booleanos, status e metadados TLS; não guardou a resposta bruta.
Por ser um serviço de eco, ele pode devolver o valor injetado ao chamador: este ensaio
não demonstra proteção contra um fornecedor que reflita credenciais em suas respostas.

Cada entrada foi removida pelo placeholder exclusivo. Os inventários de credenciais
antes/depois coincidiram. As permissões temporárias de rede foram retiradas, a negação
foi restaurada e as políticas globais/outros ambientes permaneceram iguais. Cinco VMs
paradas na conferência final. Sem instalação, certificado de confiança, firewall ou
reinício do daemon. [Recibos sanitizados e hashes](../medicoes/native-proxy-compatibility.json).

Fontes oficiais: [credenciais Docker](https://docs.docker.com/ai/sandboxes/configuration/credentials/),
[remoção por placeholder](https://docs.docker.com/reference/cli/sbx/secret/rm/),
[Postman Echo](https://learning.postman.com/docs/reference/developer-resources/echo-api/) e
[httpbingo](https://httpbingo.org/). Remoção e Postman foram convertidos com Docling;
a aquisição da página httpbingo retornou erro HTTP e ficou pendente no vault. Sua
documentação foi consultada na web; não foi registrada como conversão concluída.

## Consequência para o desenho

A [simulação anterior](2026-10-05-auth-egress-spike.md) permanece válida somente para
suas fixtures. A prova nativa não confirmou a combinação de IP fixo e injeção de
credencial. Também não testou OAuth, clientes reais, isolamento do intermediário,
streaming, MCP pelo intermediário ou o endereço final conectado pelo gerenciador.
O êxito isolado de TLS nos provedores não preenche essas lacunas.

Recomendo interromper a integração do candidato por IP e revisar o contrato usando
o caminho por domínio que demonstrou a substituição. Um intermediário de origem fixa
ainda precisa demonstrar bloqueio de MCP/rede privada e controle do destino final.
Não basta repetir a segunda fixture, que já mostrou a limitação da resolução no proxy.
Antes de novo código, identificar um mecanismo observável no runtime para cumprir
esse requisito; se ele não existir, a limitação exige decisão de arquitetura.

O runtime do produto não mudou, `REVIEWED_PROFILES` continua vazio e R2/R3 não começaram.
Pacote atualizado, suspensão do host e provas autenticadas continuam pendentes.
O relatório encerra esta rodada de compatibilidade, sem declarar R1 concluído.

## English overview

The real proxy completed four TLS handshakes for OpenAI/Anthropic using hostname and
numeric-IP CONNECT targets. Disposable custom credentials were substituted over hostname
CONNECT on two echo services, while numeric-IP CONNECT failed during TLS on both.
A hostname request with an unregistered marker remained unchanged. Direct Windows TLS
controls succeeded for both echo-service IPs.

Docker's policy log reported `forward-bypass` and rejected the tunneled service name
on a no-MITM CONNECT tunnel. IP pinning plus credential injection remains unverified;
the guard was preserved. Both temporary sandbox-scoped dummy entries were removed and the
credential inventory restored. Network policies were restored and five VMs stopped.
No model calls or real account credentials. Revisit the supported hostname path and
observable destination controls before product integration; native profiles stay empty.

ATRASO: main 1
