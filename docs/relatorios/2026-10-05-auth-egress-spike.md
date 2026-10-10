# Prova conjunta de autenticação e saída de rede

Frente: executor isolado / 2A-R1. Prova autorizada pelo mantenedor: “beleza bora”.
Executada em 2026-10-05, às 01h40 em São Paulo. Investigação concluída; R1 continua parcial.

A simulação encontrou um candidato: um intermediário confiável que fixa o IP do CONNECT,
o nome TLS e o Host HTTP do fornecedor. Ele recusou os pedidos inválidos testados e
preservou a injeção de uma credencial falsa. Isso ainda precisa funcionar com o proxy
real do Docker e com os clientes autenticados; nenhum perfil foi habilitado.

## Ambiente e alcance

O ensaio usou Python 3.14.4, curl 8.18.0 e OpenSSL disponíveis na VM de diagnóstico.
Não havia Squid, HAProxy ou nginx instalado. A configuração nativa consultada anteriormente
não ofereceu um controle de desligamento do gateway MCP. Para esta investigação, usamos
curl como transporte e servidores HTTP/TLS locais como fixtures, sem instalar dependências.

Todos os destinos eram simulados em loopback. `203.0.113.20` era um identificador da fixture,
sem conexão externa. O fornecedor, MCP e serviço privado tinham receptores locais que
registravam as requisições; controles positivos confirmaram que os três estavam acessíveis.
A troca de DNS foi uma substituição controlada da tabela de resolução do proxy simulado,
não uma alteração de DNS real. O MCP simulado não executa ferramentas.

Todos os atores compartilharam o processo confiável de teste. Portanto, esta prova cobre
o protocolo e o roteamento simulados; não cobre isolamento de processos ou segredo em memória.
A credencial falsa ficou no simulador de proxy e chegou ao receptor escolhido, sem aparecer
na resposta devolvida ao cliente. Credenciais reais e o proxy do Docker não foram usados.

## Três ciclos, sem uma quarta tentativa

| Ciclo | Desenho exercitado | Resultado observado |
|---|---|---|
| 1 | Túnel com CONNECT e SNI do fornecedor | O Host HTTP ainda podia selecionar o MCP da fixture. Desenho recusado. |
| 2 | Intermediário com domínio e Host fixos | A troca de resolução no proxy enviou a requisição ao serviço privado simulado. Desenho recusado. |
| 3 | IP fixo no CONNECT, SNI/Host fixos e pedidos reconstruídos | Os casos medidos passaram; permanece candidato para a prova nativa. |

As duas primeiras falhas são contraexemplos construídos na fixture. Não são descobertas
de vulnerabilidades no Docker. O terceiro ciclo demonstra que o transporte consegue separar
IP de conexão e identidade TLS/HTTP conforme a opção `--connect-to` do
[curl](https://curl.se/docs/manpage.html#--connect-to). A fonte foi convertida com Docling
e relacionada à execução no vault local.

No terceiro ciclo:

- Dez requisições inválidas receberam 403 sem evento no proxy: CONNECT, URLs absolutas
  para MCP/loopback, caminho iniciado por `//`, caminho codificado, Host MCP/privado,
  porta alterada, Host duplicado e enquadramento com Transfer-Encoding.
- Uma resposta 302 do fornecedor virou recusa 502; não houve seguimento do redirecionamento.
- A troca de resolução permaneceu ativa, mas os quatro CONNECTs usaram o IP fixo da fixture.
  Os quatro nomes TLS e Hosts HTTP foram os do fornecedor; seus quatro receptores receberam
  a credencial falsa. Nenhum desses pedidos atingiu os receptores MCP/privado.
- Tentativas de substituir Authorization e X-Forwarded-Host mantiveram a credencial sentinela
  e o fornecedor selecionado. O cliente recebeu somente a resposta sanitizada da fixture.
- Um cliente de controle rejeitou o certificado ao pedir outra identidade TLS. Essa checagem
  usou Python SSL; não equivale a uma prova de SNI arbitrário contra o futuro intermediário.

O protótipo aceita somente dois caminhos GET fictícios. Não é um proxy pronto para uso,
não valida todo HTTP e não comprova streaming, HTTP/2, WebSocket ou compatibilidade dos
clientes Claude Code/Codex. O código descartável fica fora dos arquivos distribuídos do produto.

## Limpeza e evidências

[Medição sanitizada](../medicoes/auth-egress-spike.json): hashes do código e recibos,
resultados dos três ciclos, versões e limites da prova. O recibo foi consumido e não foi repetido.
Cinco listeners de teste foram fechados, as cinco threads servidor terminaram e a VM foi
parada. Cinco VMs paradas na conferência final. Não houve alteração de política, certificado
do host, credenciais, firewall ou reinício de serviço. O certificado da fixture existiu somente
no diretório temporário do teste, removido ao final; não foi instalado em repositório de confiança.

Zero chamadas de IA e zero requisições externas durante o ensaio. A consulta e ingestão de
documentação oficial ocorreram separadamente. O runtime do produto permanece inalterado;
a suíte de 390 testes citada nos relatórios anteriores não foi repetida nesta rodada.

## Recomendação e próximo passo

Resultado posterior: a [prova com o proxy real](2026-10-05-native-proxy-compatibility.md)
confirmou injeção por domínio, mas o runtime recusou o nome do serviço em túneis por IP
sem interceptação. A recomendação abaixo pertence ao momento da simulação; o candidato
ainda não atende ao aceite nativo e exige revisão do contrato antes da integração.

Recomendo levar o candidato de origem fixa para uma prova de compatibilidade com o proxy
real, antes de incorporar um intermediário ao produto. Essa prova precisa demonstrar que
o Docker aceita CONNECT por IP, conserva a identidade do fornecedor e injeta a credencial
no destino correto. A simulação não estabelece nenhuma dessas propriedades do Docker.

O desenho de produto também precisa manter o intermediário fora do processo e da rede
controlada pelo agente, negar acesso direto ao proxy e definir os endpoints usados por
Claude Code e Codex autenticados. Suporte a streaming, limites e encerramento independente
do coordenador devem entrar no aceite. Usar um componente mantido ou biblioteca de transporte
é preferível a distribuir o servidor Python desta fixture.

R1 continua bloqueando R2/R3. Também faltam pacote atualizado, suspensão do host e provas
autenticadas. A investigação aprovada está encerrada nos três ciclos; implementação e
certificação do candidato não estão incluídas neste resultado.

## English overview

Three synthetic design cycles finished using existing Python, curl and OpenSSL in the
diagnostic VM. A generic tunnel allowed Host confusion in the fixture. Fixing only the
hostname still allowed simulated parent-side DNS substitution. Fixing CONNECT IP, SNI
and HTTP Host passed ten rejected-request cases, refused a redirect and kept four permitted
requests on the simulated provider with fake credential injection.

All actors shared a trusted process and used loopback fixtures. Docker's proxy, real OAuth,
process isolation, real DNS changes, streaming and native-client compatibility were not
tested. Five test listeners closed and the VM stopped. No product code changed; native
profiles remain empty. Next is proving compatibility with the real proxy before product integration.

Subsequent [native results](2026-10-05-native-proxy-compatibility.md#english-overview)
confirmed hostname-based substitution but rejected tunneled service names on the IP path.
The candidate requires a revised contract before integration.

ATRASO: main 1
