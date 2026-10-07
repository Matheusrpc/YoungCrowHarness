# Revisão aprovada: autenticação por domínio e controle do destino

Frente: executor isolado / 2A-R1. Revisão solicitada em 2026-10-05: “proximo continue”.
Estado: revisão e ensaio limitado aprovados pelo mantenedor: “aprovado”. O contrato
de segurança aprovado continua valendo, assim como os três PBIs do plano original.

Resultado: [ensaio concluído](../../relatorios/2026-10-05-hostname-cidr-proof.md), com
HTTP 200 nas três etapas, inclusive sob negação universal de IP. A combinação foi
reprovada para o requisito de destino final. O roteiro abaixo preserva o escopo
aprovado; não autoriza repetição ou implementação de um intermediário. Próximo:
decidir o controle no ponto que resolve e abre a conexão final.

O objetivo é executar Claude Code e Codex com credenciais mantidas no host, sem dar
ao cliente ou seus filhos acesso ao MCP, ao host ou à rede privada. A substituição
de credencial fictícia funcionou por domínio no [proxy real](../../relatorios/2026-10-05-native-proxy-compatibility.md).
O caminho por IP foi recusado pelo Docker. A revisão preserva esse bloqueio e procura
um controle de destino compatível com o caminho autenticado.

## O que já sabemos

- Docker 0.46.0 aceita regras locais por domínio, CIDR IPv4/IPv6 e método/caminho HTTP.
  Uma negação prevalece sobre uma permissão para o mesmo tipo de alvo. Os guias gerais
  consultados inicialmente não esclareceram a comparação do endereço resolvido.
  A [referência específica](https://docs.docker.com/reference/cli/sbx/policy/deny/network/)
  e a ajuda instalada, consultadas antes da execução, dizem que um domínio permitido
  não é verificado contra CIDRs do IP resolvido. A prova confirmou essa semântica.
  [Conceitos](https://docs.docker.com/ai/sandboxes/governance/concepts/) e
  [política local](https://docs.docker.com/ai/sandboxes/governance/access-controls/local/).
- A CLI instalada confirma essas opções. Nas três consultas desta revisão,
  `policy check --verbose --json` retornou o alvo e a decisão, sem endereço final.
  O log histórico inspecionado agrega host, regra, motivo e contagem; não contém
  endereço remoto ou identificador por conexão. Isso limita a evidência disponível,
  sem provar a ausência de controles internos.
  [Medição somente leitura](../../medicoes/hostname-egress-review.json).
- A documentação limita `policy check` e `policy log` à camada de rede; eles não
  demonstram autorização de um método/caminho HTTP específico. `forward` é o caminho
  de injeção; `forward-bypass` e `transparent` não oferecem essa injeção.
  [Monitoramento](https://docs.docker.com/ai/sandboxes/governance/monitor-and-enforce/monitoring/).
- O acesso direto do cliente ao proxy já foi recusado nas provas de MCP. Regras por
  domínio, sozinhas, não substituem a [fronteira aprovada](2026-10-04-mcp-boundary-decision.md).
  Também não basta verificar o DNS no coordenador: o proxy pode resolver outra vez.

## Alternativas

| Caminho | Consequência | Situação após o ensaio |
|---|---|---|
| Medir primeiro a negação CIDR no caminho autenticado por domínio | Reutiliza o controle nativo; pode refutar a hipótese sem construir outro serviço | Medido; combinação reprovada |
| Implementar agora um intermediário na VM | Pode fixar Host/SNI e filtrar pedidos, mas continua sem controlar a resolução feita no host | Adiar até resolver a lacuna |
| Introduzir um componente no host que resolva, valide e conecte ao IP final | Amplia o código confiável, a configuração e a manutenção multiplataforma | Exige outra decisão se o mecanismo nativo não atender |

Não está proposta a cópia de tokens para o cliente, a remoção do guard do Docker,
uma mudança global de proxy ou a troca de backend. O resultado desta rodada deve
orientar a arquitetura, sem transformar uma fixture em componente do produto.

## Roteiro aprovado e executado: permissão de domínio versus negação de IP

Pergunta: no caminho por domínio com injeção de credencial, a negação de todos os
destinos IP impede a saída mesmo quando o domínio continua permitido?

Usar apenas a VM de diagnóstico já identificada, sob controle confiável e sem agente
de IA. Conferir versão/hash do executável, identidade/imagem/mounts da VM, política
final do recibo anterior e ausência de outras VMs ativas. Qualquer diferença impede
a execução até reconciliação. Um recibo novo registra intenção antes de cada efeito;
recibo existente nunca é removido ou repetido.

Registrar uma única credencial fictícia, restrita à VM e a `postman-echo.com`. O
cliente recebe somente seu marcador e hash esperado. Usar CONNECT por domínio,
TLS verificado e o GET de eco já empregado na prova anterior, com resposta limitada.
Nenhuma chave de fornecedor ou token OAuth participa.

| Etapa | Política restrita à VM | Resultado esperado |
|---|---|---|
| A: controle positivo | Permitir somente o domínio de eco em 443; manter as negações MCP/host/privadas | HTTP 200 e digest da credencial fictícia correto |
| B: discriminação | Manter A e acrescentar negações `0.0.0.0/0` e `::/0` | Recusa atribuível à regra de IP no caminho de saída |
| A2: recuperação | Remover somente as duas negações criadas em B, voltando a A | HTTP 200 e digest correto novamente |

Até três requisições, uma por etapa, sem retry automático; dez segundos por tentativa
e 120 segundos para o ensaio, com limpeza limitada separadamente. Cada tentativa usa
uma conexão nova. A2 só ocorre se a política puder ser reconciliada; falha de limpeza
encerra o ensaio e mantém a operação bloqueada. As negações de MCP/host/rede privada
permanecem nas três etapas. Não sondar serviços privados nem executar RPC MCP.

A negação geral original precisa ser retirada apenas durante as etapas, depois de
conferir as regras substitutas. Ao encerrar, restaurá-la antes de retirar permissões,
remover somente a credencial pelo marcador exclusivo, parar a VM e conferir os
inventários. Se o controlador cair, reconciliar o recibo antes de qualquer nova ação;
um `finally` não é garantia de recuperação após encerramento forçado. Nenhuma alteração
de política global, certificado, firewall, DNS do Windows ou reinício do daemon.

## Como interpretar sem extrapolar

- Se B alcançar o serviço de eco, a combinação não atende ao controle de IP proposto.
  Encerrar esta hipótese; não tentar compensá-la com um relay que ainda usa o mesmo
  resolvedor no host.
- Se B falhar por timeout, DNS, TLS genérico ou negação do próprio acesso ao proxy,
  o resultado será inconclusivo. Os controles A/A2 e os logs precisam separar esses
  casos de uma decisão sobre o endereço de saída. Não converter ausência de resposta
  em aprovação de segurança.
- Se A/A2 passarem e B demonstrar bloqueio pela faixa do destino, isso justifica
  estudar o controle nativo. Ainda será preciso vincular resolução, endereço
  conectado e política na mesma conexão; testar mudança de endereço e redirecionamento;
  e confirmar as identidades HTTP/TLS e a inacessibilidade MCP. Um bloqueio universal
  isolado não certifica a futura permissão seletiva nem a inspeção de cada conexão.

Sem mecanismo observável para a última condição, o perfil permanece incompatível.
O log atual, sozinho, não fornece essa comprovação. O ensaio não promete fechar R1.

## Contrato da futura integração

Se a viabilidade for estabelecida, o cliente se comunicará apenas com uma origem
restrita, controlada fora do seu processo e sem acesso ao proxy genérico. O
intermediário deverá reconstruir os pedidos para a origem do fornecedor, recusar
destinos/cabeçalhos divergentes e redirecionamentos, respeitar o prazo original e
falhar fechado. O Docker conservará a injeção de credenciais no host; o controle
do endereço efetivamente conectado terá evidência própria. Apenas fixar SNI/Host
na VM não prova essa última parte.

Essa integração requer desenho e plano revisados depois da prova. Não se acrescenta
agora um formato de manifesto, dependência, serviço de host ou perfil suportado.
OAuth, streaming e clientes reais continuam sem validação. R1 parcial, R2/R3 não
iniciados; produção não publicada.

## English overview

Approved probe completed; the candidate was rejected after all three phases returned
HTTP 200, including with universal IP denial. Product integration is not implemented.
The original scope below is preserved as history, not authorization for a rerun.
Keep hostname CONNECT for host-managed
credential injection and preserve the existing MCP/private-network boundary. First
run one disposable A/B/A test: hostname allow with a fake scoped credential, the same
request with all IPv4/IPv6 destinations denied, then restore the baseline. At most
three echo requests, no models or real credentials. A successful request under the
IP deny rejects the proposed mechanism; unexplained failures are inconclusive.

Even an attributable denial is only a feasibility result. Final-address enforcement,
DNS changes, redirects, request identities and process isolation still need evidence.
The current CLI check and inspected aggregate logs do not report the final remote
address. Defer relay implementation until that gap is resolved. Profiles remain empty.

ATRASO: main 1
