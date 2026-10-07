# Rede restrita no launcher

Frente: executor isolado, 2A-R1. Implementação e provas de desenvolvimento em Windows
com Docker Sandboxes 0.46.0, registradas em 2026-10-05 UTC. Produção não publicada.

O launcher agora instala e verifica a fronteira de rede antes de autorizar o cliente.
O manifesto v2 fixa um domínio e um IPv4 público por operação. O contêiner começa sem
rede; o launcher aplica a negação IPv4/IPv6 antes de conectar a bridge. A única saída
permitida nesse namespace é TCP/443 para o IP selecionado, com retorno estabelecido.
O cliente recebe o nome fixado em `/etc/hosts`, sem acesso ao proxy HTTP do gerenciador.

## Autorização por fase

O launcher grava um claim exclusivo antes de qualquer efeito de rede. Uma falha ou
interrupção consome essa tentativa. A inicialização aplica e confere as regras; a fase
de despacho apenas as confere, recusando regras alteradas. Ambas verificam identidade,
imagem, recursos, montagem de controle e estado efetivo do contêiner.

Cada fase produz um recibo root/0600, dentro do controle root/0700. O guardian exige
que operação, hash do manifesto, nonce, fase e namespace coincidam antes de iniciar
o processo. O launcher mantém aberto o descritor do namespace durante a operação;
os comandos não dependem apenas de um PID que poderia ser reutilizado.

O manifesto v1 continua sem rede. O comando novo é interno ao runtime confiável:
`launcher.py network OPERATION_ID NONCE initialize|dispatch`. Ele não concede política
Docker, não habilita perfil e não pode ser executado pelo cliente sem privilégios.

## Provas observadas

Os testes falharam antes da implementação por ausência do recibo de rede, do comando
de configuração e do hostname fixado. Depois passaram os 14 testes do guardian e os
11 do launcher. A suíte geral executou 390 testes: 379 passaram, 11 foram ignorados por requisitos de ambiente, sem falhas ou erros.
A [medição](../medicoes/network-launcher.json) registra comandos, duração e cada skip.

O smoke Linux usou código e imagem separados do pacote nativo anterior:

| Caso | Resultado observado |
|---|---|
| Conclusão | Inicialização e despacho autorizados uma vez; saída 0 |
| Sem recibo de inicialização | Nenhum cliente iniciado; saída 125 |
| Sem recibo de despacho | Nenhum despacho iniciado; saída 125 |
| Queda durante a instalação das regras | Claim consumido, nova tentativa recusada; nenhum cliente iniciado |
| Regras alteradas antes do despacho | Conferência recusada; nenhum despacho iniciado |
| Repetição da autorização de rede | Segunda tentativa recusada; a primeira permanece válida para um despacho |
| Perda do transporte Docker interno | Cliente encerrado, PID 0, antes do limite |
| Prazo esgotado | Saída 124, com 993,053 ms de sobra no deadline original |

Os oito casos recusaram outro início da mesma operação e conservaram o estado final.
A fixture também confirmou UID 1000, bounding set vazio, `no_new_privs`, nome fixado,
recusa de novo namespace de rede, socket raw e leitura dos recibos privados.
Esses casos usaram uma operação de 15 segundos, sem chamadas externas.

Em duas execuções adicionais, o próprio launcher v2 autorizou inicialização e despacho
com a política temporária do provedor. O cliente e seu filho fizeram somente `HEAD /`:

| Provedor | TLS no cliente e no filho | Tentativas negativas | Sentinela na bridge |
|---|---|---|---|
| OpenAI | Certificado e nome verificados; HTTP 421 | 20 recusadas | Zero conexões |
| Anthropic | Certificado e nome verificados; HTTP 404 | 20 recusadas | Zero conexões |

As tentativas cobrem proxy/MCP, portas e destinos privados especificados no recibo,
metadata, loopback, IPv6 e nomes TLS não autorizados. São quatro respostas TLS e
40 tentativas negativas. HTTP 421/404 comprova transporte neste ensaio; autenticação,
catálogo e inferência não foram testados. A [prova anterior](2026-10-04-network-boundary.md)
preserva a descoberta da rota MCP pelo proxy e a comparação externa do HTTP 421.

## Recuperação e limpeza

As duas provas de provedor restauraram a negação da VM antes de retirar as exceções.
Seu conteúdo voltou ao estado anterior, com novo ID de regra. Políticas globais e de
outras VMs permaneceram iguais. Os contêineres terminaram com PID 0, recusaram repetição
e a VM foi parada. Nenhum certificado, login ou reinício do daemon foi necessário.

### Reinício ativo e reconciliação

O operador executou o ensaio v2 em 2026-10-05 às 03:43 UTC. O recibo permanece
reprovado: saída 255 e `FinishedAt` 3.962,503 ms após o deadline. PID 0 e recusa de
repetição (`start_consumed`, saída 125) foram observados, com estado final preservado.

| Evidência no host | Horário UTC |
|---|---|
| Reinício solicitado durante o despacho | 03:43:17.547 |
| Partição WHP removida nos logs | 03:43:23.065 |
| Containerd registra o contêiner externo sem tarefa, encerrado | 03:43:24.2712445 |
| Deadline original | 03:43:29.597 |
| Novo boot durante o comando de observação | 03:43:32.2321766 |
| `FinishedAt` retornado pelo Docker interno | 03:43:33.559503 |

A consulta usou `sbx exec`, que iniciou novamente a VM parada. O ensaio não registrou
seu estado pelo gerenciador antes dessa ação. Os logs explicam a falha da medição,
mas não substituem retroativamente a observação que faltou ao recibo.

No [código do Moby consultado](https://github.com/moby/moby/blob/c7b76b939576290b5daa5b3671fff06fcaeb6d2e/daemon/daemon.go),
uma tarefa ausente pode receber saída 255 durante a recuperação. Sem horário de saída,
[`SetStopped` usa o horário atual](https://github.com/moby/moby/blob/c7b76b939576290b5daa5b3671fff06fcaeb6d2e/daemon/container/state.go).
Isso é consistente com a sequência local; a referência não identifica o commit exato
do Engine instalado. O atraso registrado, isoladamente, não comprova execução além do limite.

A comparação de políticas encontrou somente novos `id` e `policy_id` da regra
imutável `kit:sbx-kit-builder`, além da ordem da lista. Conteúdo e permissões dessa
regra permaneceram iguais; todas as outras regras, inclusive a negação da VM, ficaram
idênticas. A reconciliação não alterou políticas. Cinco VMs foram confirmadas paradas.

O novo ensaio salva `ls` e `inspect` imediatamente após o reinício, antes de `exec`.
Aceita parada do gerenciador como evidência somente com operação, identidade, imagem,
ausência de mounts e intervalo de observação compatíveis com o prazo original. Mantém
a verificação do contêiner e da recusa de repetição após o novo boot. Mudanças de
permissão continuam reprovando; a renovação dos IDs da regra interna fica registrada.
Dois testes locais passaram após falharem pela ausência desses controles. Preflight
somente leitura e sintaxe Python/PowerShell passaram. O operador executou o novo
ensaio às 03:56 UTC. `ls`/`inspect` registraram a VM parada entre 03:56:49.501 e
03:56:50.052 UTC, antes do deadline 03:56:53.808 UTC: margem de 3.756 ms. Após boot
para inspeção, PID0 e repetição recusada conservaram o estado. O término dentro do
prazo foi comprovado pela parada do ambiente; o `FinishedAt` recuperado permaneceu
posterior e não foi usado como essa evidência. Prazo e reserva não mudaram.

A regra interna do builder renovou os IDs novamente; permissões e demais regras
foram preservadas. Limpeza sem erros, cinco VMs paradas, zero chamadas a modelos
e zero requisições externas. Ambos os scripts estão consumidos. A [medição](../medicoes/network-launcher.json)
vincula cada resultado ao seu recibo e conserva a reprovação anterior.

## Limites e próxima ação

`REVIEWED_PROFILES` permanece vazio. O pacote nativo ainda precisa incorporar e provar
esses arquivos. A suíte e os ensaios acima não concluem R1 nem iniciam R2/R3.

Os [endereços observados e as sentinelas Windows](2026-10-05-gateway-endpoints.md)
foram testados no checkpoint seguinte, com os limites registrados naquele relatório.
Próxima ação: verificar DNS/redirecionamento e o
comportamento de resolução do proxy transparente. Suspensão total do host, Ubuntu,
reconstrução do pacote e clientes autenticados continuam pendentes. Os IPs observados
pertencem aos recibos; não são um catálogo permanente de provedores.

Os [hashes, comandos e resultados](../medicoes/network-launcher.json) vinculam as provas
aos arquivos testados. A implementação usa o descritor de namespace descrito em
[nsenter](https://man7.org/linux/man-pages/man1/nsenter.1.html); as regras dentro desse
namespace são distintas das regras que o [Docker instala no gerenciador](https://docs.docker.com/engine/network/firewall-iptables/).
As fontes já convertidas por Docling foram consultadas pelo microíndice do vault.

## English overview

Manifest v2 binds one hostname and public IPv4 to an operation. The trusted launcher
installs default-deny IPv4/IPv6 rules before connecting the bridge, then verifies them
again before dispatch. Each phase consumes a durable claim and issues a private root
receipt bound to operation, manifest, nonce, phase and network namespace. A missing or
changed receipt prevents the client from starting. Manifest v1 remains networkless.

Fourteen guardian and eleven launcher tests passed after reproducing the missing
controls. Eight native Linux cases passed, including setup interruption, changed rules,
missing receipts, repeated requests, transport loss and the deadline. The deadline
case finished 993.053 ms early. The full suite ran 390 tests: 379 passed and 11 were skipped for environment requirements, with no failures or errors.

Two additional operations used the actual v2 launcher with scoped provider policy.
Client and descendant verified TLS: OpenAI returned 421 and Anthropic 404. Forty
negative network attempts failed; the inner bridge sentinel received zero connections.
These HEAD requests used no credentials, inference or MCP RPC. Both operations restored
scoped policy, preserved unrelated rules, refused replay and stopped the VM.

The v2 active restart ran and failed its deadline measurement: recovered exit 255
and a finish timestamp 3962.503 ms past the limit. Host logs show the VM shutting down
before the deadline, then booting again during inspection. The original failed receipt
is preserved. Its replacement records manager state before any exec can restart the VM,
checks identity and timing, and still requires PID 0 and refusal of replay after boot.
Two local regression tests and read-only preflight passed. The operator then ran the
replacement: manager observations completed 3756 ms before the deadline, with the VM
stopped. After boot, PID0 and replay refusal preserved its state. This proves shutdown
of the execution environment within the deadline; the recovered finish timestamp is
not that evidence. Only IDs of the immutable builder rule changed; permissions and
all other rules matched. Both scripts are consumed; cleanup reported no errors.
No policy was edited during reconciliation; five VMs were stopped. Runtime files are
unchanged, so the 390-test suite above is the preceding run, not a new execution.

The [next checkpoint](2026-10-05-gateway-endpoints.md#english-overview) covers observed
gateway address variants and Windows sentinels within its stated limits.
Remaining checks include DNS/redirects and transparent-proxy resolution, package rebuilding, whole-host
suspension and authenticated clients. Native profiles remain empty; R1 is partial.

ATRASO: main 1
