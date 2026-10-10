# Exclusive Egress Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. The operator already selected inline execution with one independent review at the end; preserve that choice.

**Goal:** Provar se a saída controlada após o proxy Docker preserva a injeção de credencial fictícia, observa o endereço conectado e bloqueia desvios, com restauração verificável da configuração.

**Architecture:** Uma prova descartável em Python recebe do Docker um pedido SOCKS5 por domínio, valida os endereços e conecta por IP numérico. Um controlador separado registra a configuração antes de alterá-la e reconcilia falhas. O caminho real é testado em uma única VM própria, sem instalar o protótipo no produto.

**Tech Stack:** Windows, Python 3.14.4/biblioteca padrão, `unittest`, Docker Sandboxes 0.46.0 e os helpers locais existentes. OpenSSL 3.5.6 já instalado com Git somente para material TLS fictício. Nenhuma nova dependência, conta ou API de modelo.

**Spec:** [Instalação exclusiva](../specs/2026-10-05-exclusive-egress-decision.md), aprovada pelo mantenedor com “aprovado” em 2026-10-05, selecionando a recomendação local. Complementa [R1 do plano existente](2026-10-04-isolated-executor.md), sem criar novos PBIs.

Frente: executor isolado / 2A-R1. **Ciclo encerrado como inconclusivo. V2 excedeu prazo antes do recibo; sem recuperação pendente.**
R1 continua parcial; R2/R3 não começaram. As três tarefas abaixo são etapas da prova,
não substituem os três PBIs aprovados. Execução nesta sessão já escolhida.

## Global Constraints

Encerramento: operador executou v2 e recebeu `TimeoutExpired`; nenhuma alteração no Docker
foi alcançada. Consultas às 19:05:21Z confirmaram inventários e configurações preservados.
O comando exato que excedeu o prazo não foi registrado. Entradas PowerShell/Python bloqueadas
pelo marcador de encerramento. Suíte 60/60 após regressão do bloqueio. Decisão de abordagem
pendente; não preparar v3 ou aumentar limites automaticamente. R1 permanece sem aceite.

Continuação de 2026-10-05: o mantenedor pediu seguir e reduzir as voltas. A primeira
operação está consumida e recuperada. A v2 usa o mesmo controlador corrigido, com
estado exclusivo em `D/exclusive-egress-proof-v2/`; `D/exclusive_egress_v2.py` confere
os hashes dos recibos anteriores, e `D/run-exclusive-egress-v2.ps1` fixa os executáveis
e fontes. Não há opção de escolher outro diretório ou repetir automaticamente.
Cinco regressões adicionais passaram (59 casos no total); preflight confirmou as cinco
VMs paradas e o daemon existente, sem chamar settings.

Critério de saída desta continuação: uma única rodada A/B/A2 dentro dos limites abaixo.
Sucesso permite avançar à integração do isolamento; desvio reprova o candidato, e evidência
incompleta encerra o ciclo como inconclusivo. Ambos exigem decisão antes de outro componente
ou ensaio. Limpeza necessária continua autorizada e não renova o orçamento de tráfego.
Não transformar falha do roteiro em afirmação de incompatibilidade do Docker.

- “Manter `REVIEWED_PROFILES = ()`.” Não alterar runtime, manifesto ou distribuição nesta prova.
- “Não consultar modelos, instalar certificados ou alcançar serviços privados reais.”
- “Uma GET por tentativa, sem retry/redirect, dez segundos por tentativa e 120 segundos para o ensaio”.
- “Começar por uma operação de diagnóstico por vez para atribuir as conexões sem ambiguidade.”
- “Alterar somente `proxy.sandbox` e as exclusões necessárias desse escopo.” Aqui, a única outra chave é `no_proxy.sandbox`.
- “Não alterar o proxy genérico, `proxy.daemon`, ambiente global ou proxy do sistema.” Sem firewall, login, novo daemon ou máquina remota.
- “Restaurar somente o que este modo alterou e somente se ainda corresponder ao valor aplicado”. Conflito fica registrado, sem sobrescrever terceiros.
- “Cada fase tem intenção durável e reconciliação após queda.” Recibo existente impede novo ensaio; a recuperação não envia outra GET.
- Preparação: até 180s; ensaio: 120s; limpeza: até 180s, com comandos individuais de até 15s e reinício de até 60s. Uma ativação e uma restauração podem exigir dois reinícios, ambos com VMs paradas.
- Usar a VM/imagem/nonce do recibo `native-package-proof.json` e a política final de `hostname-cidr-proof.json`; comparar globais e outros escopos sem confundir IDs substituídos da negação própria.
- Reinícios pelo terminal normal do operador, devido às falhas de socket anteriores. Não reiniciar pelo terminal do agente ou repetir um comando de resultado incerto.
- Um escritor no checkout. Sem commit/push de protótipos privados ou extratos Docling. README/guia PT/EN passam por humanizer e preservam imagens/BPMN.

## Review Focus

1. DNS devolve IP público e privado, ou muda entre consultas: validar o conjunto inteiro e conectar ao número da mesma resolução. Tarefa 1.
2. SOCKS chega em fragmentos, pede IP literal/UDP, ou o peer diverge: recusar sem encaminhar bytes. Tarefa 1.
3. Consulta de configuração iniciaria daemon ou ambiente sobrescreve o valor persistido: preflight sem partida e recusa antes de mutação. Tarefa 2.
4. Coordenador morre entre escrita e resposta, ou outra aplicação muda a configuração: recuperar por intenção/leitura, preservar terceiros e não duplicar despacho. Tarefa 2.
5. Docker responde sem passar pelo controle, inclusive quando ele está desligado: isso reprova a hipótese; falha genérica não prova bloqueio. Tarefa 3.

## Arquivos e responsabilidades

Nesta tabela, `D` significa o diretório existente `.superpowers/sdd/2026-10-04-isolated-executor/`.
É uma abreviação documental, não uma variável de ambiente.

| Caminho | Ação e responsabilidade |
|---|---|
| `D/egress_guard.py` | Criar: único destino de diagnóstico, parser SOCKS restrito, DNS/IP/peer e prazo |
| `D/exclusive_egress.py` | Criar: preflight, transação de configuração, classificação e reconciliação |
| `D/test_exclusive_egress.py` | Criar: testes determinísticos e sockets locais, sem Docker ou internet |
| `D/run-exclusive-egress-proof.ps1` | Criar: entrada para o operador, sem lógica duplicada |
| `D/exclusive-egress-proof/` | Criar somente após o plano aprovado: recibos privados, snapshots e saída sanitizada |
| `D/hostname-cidr-client.py`, `D/guardian_vm.py` | Reutilizar a coleta de uma GET e o transporte da VM; não executar o runner CIDR consumido |
| `scripts/adoption_fs.py`, `scripts/mission_process.py` | Reutilizar funções de diretório privado e supervisão; não editar |
| `docs/relatorios/2026-10-05-exclusive-egress-proof.md`, `docs/medicoes/exclusive-egress-proof.json` | Criar após execução: resultado sanitizado, limites e hashes |
| `README.md`, `docs/USAGE.md`, `docs/BACKLOG.md`, vault local | Atualizar em cada entrega com o estado observado |

Leitura do host encontrou Python, curl e SSH no PATH; não encontrou Squid, HAProxy,
nginx, 3proxy, gost ou mitmdump. Isso não é inventário de toda a máquina. curl não
fornece o servidor necessário e um túnel SSH, sozinho, não oferece a validação/recibo
exigidos. A prova usará biblioteca padrão, sem instalar um proxy de uso geral.

## Tarefa 1: controle descartável de destino

**Interfaces em `D/egress_guard.py`:**

- `validate_destination(host: str, port: int, addresses: tuple[str, ...], forbidden: frozenset[str]) -> tuple[str, ...]`: retorna o conjunto validado; recusa com `ValueError` de código estável.
- `connect_checked(host: str, port: int, deadline_ms: int, forbidden: frozenset[str], *, resolve, socket_factory) -> tuple[socket.socket, dict]`: resolve uma vez, conecta por número e confere `getpeername()` antes de retornar.
- `serve(config: dict, journal: Path) -> int`: listener somente `127.0.0.1`; uma conexão ativa, sem sessão persistente entre tentativas. CLI privada: `--config CAMINHO --journal CAMINHO`.
- Configuração: `schema_version=1`, `operation_id`, `phase`, `nonce`, `deadline_ms`, `host="postman-echo.com"`, `port=443`, `listen_port`, `forbidden_ips`, `max_connections=1`. Campos desconhecidos ou prazos vencidos são recusados.
- Na primeira fase, `listen_port=0` solicita porta livre com bind exclusivo; o recibo `ready` publica a porta efetivamente reservada antes de alterar settings. A recuperação usa essa mesma porta e recusa conflito, sem escolher outra silenciosamente.
- Recibo por conexão: operação/fase, domínio/porta, conjunto resolvido, IP escolhido, peer, tempos e decisão. Nunca registrar tráfego TLS, cabeçalhos ou credenciais.

- [x] **1. Escrever testes de destino e parser em `D/test_exclusive_egress.py`.**

Fixar as assertivas:

```python
self.assertEqual(validate_destination("postman-echo.com", 443, ("1.1.1.1",), frozenset()), ("1.1.1.1",))
with self.assertRaisesRegex(ValueError, "destination_forbidden"):
    validate_destination("postman-echo.com", 443, ("1.1.1.1", "127.0.0.1"), frozenset())
```

O IP público acima é dado de teste; o teste não faz conexão externa. Acrescentar
`test_private_mapped_and_host_ips_refused`, `test_domain_and_port_exact`,
`test_socks_fragmented_or_truncated`, `test_literal_bind_udp_and_unknown_method_refused`,
`test_peer_mismatch_sends_no_payload`, `test_rebinding_resolves_once` e
`test_resolver_and_slow_client_obey_original_deadline`. Conector/resolvedor de teste
registram chamadas: conjunto inválido implica zero dials; peer divergente implica
zero bytes retransmitidos; duas conexões exigem duas resoluções independentes.

- [x] **2. Rodar e guardar o RED pelo componente ausente.**

`python -B -m unittest discover -s .superpowers/sdd/2026-10-04-isolated-executor -p test_exclusive_egress.py -v`

- [x] **3. Implementar o subconjunto mínimo de SOCKS e a validação.**

SOCKS versão 5, método 0 e somente CONNECT com ATYP 3/domínio; outros métodos,
BIND, UDP, IP literal, NUL, userinfo e domínio diferente são recusados. Essa fixture
não é uma implementação completa da RFC1928 nem um serviço público autenticado.
Listener loopback e processos do host confiáveis são premissas desta prova; não
confundir isso com a futura fronteira contra o cliente de IA.

Consultar A/AAAA numa única resolução com prazo. Usar `ipaddress`, exigir endereço
global, recusar explicitamente categorias proibidas e IPs do host/gateway. Normalizar
IPv4 mapeado; recusar endereços de transição/escopo. Validar todos os resultados antes
de escolher um IPv4 público por ordem numérica, sem tentativa alternativa. IPv6 não
abre socket nesta primeira prova; IPv6 isolado ou representação ambígua falha fechado.
Não apresentar isso como prova nativa IPv6.

O socket conecta ao número validado sem `create_connection` por hostname ou uso de
variáveis de proxy. Recusa DNS vazio, quantidade acima de 64 endereços, resposta
misturada e peer divergente. O limite de cada conexão é o menor entre dez segundos
e o prazo restante da operação. Resolver em subprocesso supervisionado, pois thread
presa em `getaddrinfo` não pode ser tratada como cancelada. Reusar
`mission_process.supervise(plan, on_started=..., stop_requested=...)` para conter
os subprocessos próprios; fechar sockets no fim e persistir a confirmação da parada.

- [x] **4. Rodar o GREEN, sem Docker ou internet.**

Mesmo comando do passo 2. Sockets de teste usam somente loopback; substituições do
resolvedor/conector ficam no teste e não aparecem como opções de relaxamento na CLI.
Limitar quadros de handshake a seus tamanhos de protocolo, retransmissão a 64KiB por
buffer e 8MiB por conexão; excesso encerra a operação. Atualizar o registro local
como “contrato sintético”, sem compatibilidade Docker ou autenticação comprovadas.

## Tarefa 2: ativação, perda de resposta e restauração

**Interfaces em `D/exclusive_egress.py`:**

- `preflight(sbx: Path, state_dir: Path) -> dict`: confere arquivos, versão e presença do daemon sem chamar a família settings, que pode iniciá-lo. Não inicia daemon/VM.
- `activate(snapshot: dict, endpoint: str, state_dir: Path) -> dict`: escreve somente as duas chaves permitidas, com intenção fsync antes de cada efeito; devolve `restart_required`.
- `reconcile(state_dir: Path) -> dict`: fecha admissões, identifica recursos próprios, restaura quando seguro e devolve `restored`, `restart_required` ou `conflict`. Nunca executa GET.
- CLI: `--check`, `--operator`, `--reconcile`. `--check` nunca muda configuração; `--operator` consome o recibo exclusivo uma vez; `--reconcile` só recupera a operação existente.
- Estado persistido: identidade de operação/VM/executável, baseline, valores aplicados, intenção/resultado por efeito, fase, prazo e erros de limpeza. Um único recibo inicial criado com `x`; fases nunca geram uma segunda autorização de execução.

- [x] **1. Escrever testes com uma CLI falsa, incluindo queda após efeito e antes da resposta.**

Casos: `test_stopped_daemon_never_autostarts`, `test_unknown_vm_refused`,
`test_environment_override_refused`, `test_snapshot_precedes_setting_write`,
`test_lost_setting_reply_is_reconciled_without_replay`,
`test_restore_uses_unset_for_original_default`, `test_third_party_change_preserved`,
`test_partial_cleanup_keeps_gate_closed`, `test_drift_or_new_consumer_blocks_next_phase`
e `test_existing_receipt_cannot_dispatch`. Incluir
`test_unexpected_daemon_transition_refuses_native_probe`: identidade mudou durante
consulta, nenhuma GET é despachada e o recibo registra a transição inesperada.
Assertivas centrais: `mutations == []` nos preflights recusados; restaurar default
gera `settings unset`, não `settings set DEFAULT`; conflito não escreve nessa chave;
recuperar não chama transporte da VM e não renova `deadline_ms`.

- [x] **2. Rodar o mesmo comando de testes e guardar o RED dos contratos novos.**

- [x] **3. Implementar o controlador reutilizando os helpers de armazenamento.**

Usar `adoption_fs.private_dir(path)` e `inspect_permissions(path, role="snapshot")`
num diretório novo desta prova; ACL sem comprovação impede mutação. Não reutilizar
`validate_storage` do trial: seu contrato de backup fora do repositório é diferente.
Gravar JSON por substituição atômica, flush/fsync e intenção antes de efeitos.

`--check` não usa settings. Somente `--operator`, com intenção persistida, confirma
daemon ativo e VMs paradas antes das consultas efetivas. Capturar
`settings get CHAVE --json` dentro do processo, sem imprimir saída bruta, conferindo
a identidade do daemon antes/depois. Essas consultas podem iniciá-lo se ele cair
nesse intervalo: a observação não elimina a corrida. Uma transição inesperada
encerra a prova antes de GETs/escritas dependentes, consome o orçamento de transição
e exige reconciliação; nunca declarar a chamada livre de efeitos ou repetir o início.
O baseline restaurável desta primeira prova aceita apenas chaves específicas em
default ou override vazio/`direct`/`system` para proxy, e default/vazio para exclusões.
Recusar overrides de ambiente, URLs com credenciais/PAC e exclusões mais amplas;
não removê-los para fazer a prova passar. Estado/formato desconhecido é incompatível.
Globais e daemon são somente comparados por metadados/digests, nunca alterados.

Depois de validar os consumidores conhecidos, exigir todas as VMs paradas. Aplicar
`proxy.sandbox=socks5h://127.0.0.1:PORTA` e `no_proxy.sandbox` vazio; conferir a leitura
efetiva. Caso vazio herde exclusão mais ampla, recusar antes da prova. O script do
operador confere as variáveis relevantes no próprio terminal antes do reinício.
O endpoint não contém segredo; valores antigos potencialmente sensíveis não entram
em argumentos, relatórios, logs ou Git.

Antes e depois de cada fase, reconferir consumidores e configuração. Divergência
fecha admissões e inicia reconciliação; trabalhos próprios conservam o corte pelo
prazo original, sem depender dessa consulta para encerrar. Não usar essa checagem
periódica como substituto do bloqueio de rede.

Na recuperação, parar a VM própria antes de restaurar. Comparar cada chave ao valor
aplicado; se já for o original, apenas registrar; se for de terceiros, registrar
conflito sem sobrescrever. Se a VM não puder ser confirmada parada, não retirar seu
controle de saída. Restaurar override antigo ou removê-lo conforme sua origem.
Uma resposta perdida exige observação antes de qualquer nova escrita. Reinício
incerto exige estado observado e decisão, nunca retry automático.

- [x] **4. Rodar os testes e preparar a entrada PowerShell.**

O wrapper chama Python por caminho verificado e apenas encaminha `--operator` ou
`--reconcile`. Aviso informa escopo das sandboxes, até dois reinícios do serviço,
nenhum reinício do Windows/modelo e os limites acima. Falha indica o recibo e a
ação de reconciliação; não recomenda repetir o ensaio. Parsear PowerShell sem
executá-lo. Não iniciar esse script neste passo.

## Tarefa 3: prova nativa única e conclusão da hipótese

**Interfaces:** consumir `serve`, `preflight`, `activate` e `reconcile` sem duplicá-los.
Adicionar `run_native(state_dir: Path) -> dict` e `classify(rows: list[dict], cleanup: dict) -> str`
em `D/exclusive_egress.py`. Resultados: `viable_within_probe`, `candidate_rejected`,
`inconclusive` ou `cleanup_incomplete`. Nenhum resultado habilita perfil de produto.

- [x] **1. Fixar o classificador antes da prova.**

`test_echo_without_guard_rejects`, `test_missing_peer_is_inconclusive`,
`test_generic_tls_or_timeout_is_inconclusive`, `test_cleanup_failure_blocks_acceptance`
e `test_supported_sequence_is_only_scoped_viability`. Só aceitar os controles
positivos com TLS, hash fictício e cadeia domínio/resolução/dial/peer da mesma fase.
O controle negativo exige evidência específica de recusa no upstream; timeout ou
403 genérico, mesmo com A/A2 positivos, permanece inconclusivo.

- [x] **2. Preparar o ensaio e seus sentinelas sem requisições externas.**

Reusar o corpo de uma tentativa de `hostname-cidr-client.py`, com configuração nova;
preservar o arquivo/recibo antigo. A fixture roda como processo confiável na VM; o
relay restrito do produto ainda não participa. Reusar `guardian_vm.execute` apenas
após conferir identidade/nonce e garantir que sua saída contém só metadados sanitizados.
IPs do host/gateway são inventariados localmente; falha de inventário bloqueia.

Conferir os contratos Host/SNI/redirect da fixture anterior pelos seus hashes e
registrar sua natureza histórica/sintética. Acrescentar ao novo teste uma resposta
302 local e identidade TLS inválida: cliente não segue Location e TLS falha, sem
envio do marcador de credencial. Usar material TLS de teste local, sem instalar CA
ou converter a recusa do cliente em propriedade do guard SOCKS, que não interpreta HTTP.
Gerar certificado/chave fictícios no diretório privado desta prova com o OpenSSL
observado em `C:/Program Files/Git/usr/bin/openssl.exe` (3.5.6), conferindo hash/versão
antes do uso. A confiança fica apenas no `SSLContext` da fixture, sem tocar stores
do Windows, Docker ou clientes. Se o binário divergir, registrar antes de continuar.

- [x] **3. Executar uma vez no terminal normal do operador, após o preflight aprovado.**

Executado em 2026-10-05; ativação interrompida antes de A/B/A2. Resultado inconclusivo,
recibo consumido e preservado. Este checkbox registra a tentativa, sem aceite da hipótese.

Disponibilizar o wrapper pronto e o resultado de `--check`; a solicitação do terminal
é operacional, decorrente das falhas de socket já registradas. O roteiro completo
ativa, mede e restaura; não deixa um processo parado esperando aprovação.
Uma credencial fictícia fica restrita à VM e `postman-echo.com`. Somente o marcador
e o digest entram na VM. Preservar o inventário real de credenciais e a política dos
demais escopos. Na VM própria, permitir somente o domínio de eco/443 e conservar as
negações MCP/host/privadas; registrar os IDs de regras temporárias e restaurar deny-all.

| Fase | Ação única | Resultado necessário |
|---|---|---|
| Disponível | Nova conexão, uma GET; guard aceita domínio exato, resolve/diala número e registra peer | HTTP200, TLS válido, hash fictício correto e conexão atribuída |
| Desligado | Encerrar guard próprio, confirmar processo/listener ausentes; nova tentativa | Recusa atribuída ao upstream, sem resposta de eco; sucesso reprova imediatamente |
| Recuperado | Iniciar nova instância com mesmo endpoint e prazo original; nova conexão/GET | Mesmas provas do primeiro controle, sem extensão do prazo |

Não permitir retries do cliente, redirecionamentos ou tráfego adicional. Conexão
inesperada, dial extra do Docker, DNS incompatível ou ausência de prova de atribuição
encerra a hipótese como rejeitada/inconclusiva. Não relaxar limites para obter 200.
O controlador reconcilia configuração e inventários após qualquer falha; guard encerra
no prazo mesmo se o coordenador morrer. Sem testes de queda do host/daemon adicionais
nesta rodada: os reinícios são apenas os necessários para ativar/restaurar a rota.

- [x] **4. Verificar limpeza e revisar o resultado.**

Recuperação concluída às 18:48:37Z, após um reinício pelo operador. A conferência final
foi somente leitura; cinco VMs paradas, settings restaurados, guard ausente e permissões
preservadas. Dois IDs provisionados do kit mudaram; snapshots brutos preservados.

Exigir VM parada, processos/listeners próprios ausentes, credencial fictícia removida,
configuração explícita e efetiva restauradas, políticas globais/demais VMs inalteradas.
Guardar os recibos consumidos; tentativa incompleta não é repetida. Aplicar a revisão
independente ao incremento conforme o método já escolhido, sem segundo escritor.
Uma prova do caminho em processo confiável não comprova isolamento de cliente hostil.

- [x] **5. Atualizar documentação e registrar a próxima ação real.**

README/USAGE/BACKLOG PT/EN e vault atualizados. Conferidos 307 destinos locais,
52 imagens e diagrama preservados, vault com 345 notas/zero issues e diff sem erros.
Recuperação concluída; saída de rede não medida e perfis bloqueados.

Relatório/medição públicos trazem hashes, controles positivos/negativos, família
observada, limites, limpeza e hipóteses restantes. README/USAGE/BACKLOG PT/EN e vault
distinguem prova descartável de implementação. Conferir links, 52 imagens do README,
`git diff --check` e `python scripts/vault.py check --json`. Não repetir a suíte geral
histórica de 390 testes se o produto permanecer inalterado.

Commit documental, quando revisado e dentro da janela de publicação da frente:
somente caminhos públicos explícitos, autor humano, sem coautoria de IA; não incluir
`D` ou fontes do vault local. Não publicar o incremento como conclusão de R1.

## Cobertura, dependências e aceite

O controle de DNS/IP/peer, parsing e prazo pertence à tarefa 1; exclusividade,
precedência, proteção do estado e reversão pertencem à tarefa 2; injeção, ausência de
desvio e evidência de limpeza pertencem à tarefa 3. Os cinco riscos de Review Focus
têm testes nomeados. Não há alteração em R2/R3 ou na preferência por execução inline.

O resultado responde à viabilidade do upstream. Integração do relay isolado contra
cliente/filhos, prova conjunta de inacessibilidade MCP, pacote corrigido, suspensão do
host e clientes reais permanecem no plano principal. Essas dependências são explícitas;
`viable_within_probe` não as conclui. Falha do candidato encerra este caminho antes
de introduzir outro componente ou nova exceção operacional.

Fontes: [upstream Docker](https://docs.docker.com/ai/sandboxes/configuration/upstream-proxy/),
[RFC1928, quadros SOCKS](https://www.rfc-editor.org/rfc/rfc1928.html) e
[ipaddress](https://docs.python.org/3.14/library/ipaddress.html), consultadas em 2026-10-05.
Compatibilidade deve ser medida nos binários instalados; documentação não a concede.
Implementação aprovada pelo mantenedor com “confirmado vamos seguir”. Controle, transação,
classificador e roteiro implementados; a suíte atual passou em 60 testes locais. O primeiro ensaio nativo parou na leitura
de source=override, antes de tráfego. Contratos de source e IDs provisionados corrigidos;
recuperação concluída. V2 encerrou antes do recibo com TimeoutExpired; sem efeitos no Docker.
Próximo: decisão de abordagem, sem outra prova automática. Hipótese inconclusiva e R1 parcial.
Método inline preservado.

ATRASO: main 1
