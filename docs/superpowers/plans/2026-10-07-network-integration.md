# Integração interna do filtro de saída

> Execução inline com `superpowers:executing-plans`; root escreve, revisores somente leitura.

**Goal:** ligar guard, plano e recuperação de configuração ao controlador A/B/A2.
**Architecture:** plano/registro v3 no mesmo ledger, preservando v1/v2; helper de egress e DNS herdam o grupo/job do controlador. Somente proxy/exclusões sandbox podem mudar; política e credenciais permanecem comparadas ao baseline.
**Tech Stack:** Python/biblioteca padrão e supervisor existente, sem novas dependências.
**Spec:** [instalação exclusiva aprovada](../specs/2026-10-05-exclusive-egress-decision.md), [consolidação aprovada](2026-10-07-executor-consolidation.md), backlog recebido 203.6.

## Escopo e limites

O operador autorizou a próxima tarefa e preservou execução inline. Este plano detalha o incremento do desenho aprovado. Integração nativa permanece bloqueada: a documentação de sbx 0.46.0 não demonstra identidade/fingerprint da credencial customizada necessária à remoção segura diante de mudança externa. Não inventar esse campo nem implementar remoção por placeholder como se provasse propriedade. Políticas são imutáveis neste incremento; baseline divergente bloqueia.

A/B/A2 compartilham prazo original de até 120s, com DNS até 5s e túnel até 10s. Recuperação mantém prazo próprio de até 60s. A2 reutiliza a porta de A; conflito bloqueia. Nunca executar Docker ou modelo nesta cloud, aumentar ciclos (2/3 usados), reabrir UUIDs, habilitar perfil, merge ou mudar main. Publicar código/testes/documentação sanitizados no PR #24 após QA.

## Review Focus

- Helper criado e controlador morto antes do recibo: dono global ainda impede liberação sem ausência do grupo/job e da porta.
- Clock regressivo ou DNS preso: corte absoluto/monotônico, filho coletado e zero dial após prazo.
- Mudança externa em setting, política, credencial ou porta: preservar terceiro, manter reserva.
- Resposta perdida de set/unset/restart: observar sem repetir a intenção consumida.
- Leitura de v1/v2 após introdução de v3: nenhuma migração de autorização ou alteração do baseline histórico.

### Task 1: guard sob a contenção existente

Arquivos: `scripts/mission_egress.py`, testes e helpers locais.
Interfaces: `resolve_addresses(host, timeout)` passa a usar filho direto; `Guard(config, persist, cwd)` inicia helper fechado por pipe, persiste PID antes de liberar configuração, confere recibos e coleta o filho. `port_available(port)` observa bind exclusivo local sem matar processo.

- [x] RED: reproduzir DNS aninhado; testar prazo/filho coletado, guard real com SOCKS inválido e falha de persistência antes de configuração.
- [x] Implementar DNS herdado e guard privado; guardar somente metadados.
- [x] GREEN: `python3 -B -m unittest discover -s tests -p test_mission_egress.py -v` e integração sob supervisor real.

### Task 2: plano v3 e configuração com intenção durável

Arquivos: `scripts/mission_network.py`, `mission_transaction.py`, testes.
Interfaces: `build_plan(..., network=...)`, `network_event(...)`; `Network.before_phase/after_phase/verify/close`. Plano v3 vincula guard, resolvedor do sistema e IPs proibidos; diário registra recursos e alterações antes dos efeitos.

- [x] RED: v2 preservado, hashes do guard, ready antes de proxy, somente duas chaves sandbox, source default/override, deriva e resposta perdida.
- [x] Implementar `proxy.sandbox` e `no_proxy.sandbox`, preservando demais settings, política e inventário de credenciais. Uma ativação/restart, sem replay.
- [x] GREEN: testes de configuração e transação; backend local simula somente fronteira sbx.

### Task 3: A/B/A2 e recuperação

Arquivos: coordenador/guard/recovery e fixtures.
Interfaces: `run_reserved(..., network=...)` usa guard pronto em A/A2 e porta ausente em B; `recover` verifica owner/porta e restaura apenas settings ainda próprios, depois de carga/VM paradas. `Recovery` nativo recusa mutação global sem contrato suficiente.

- [x] RED: sockets reais nas fases A/A2, mesma porta, B ausente, conflito de porta, interrupções e repetição sem tráfego/mutação duplicada.
- [x] Ligar guard ao controlador e recuperação ao ledger; manter B não atribuída e perfis vazios.
- [x] GREEN: testes focados; prova local cobre os efeitos ligados, sem reivindicar Docker/TLS nativo, injeção ou MCP certificado.

### Task 4: instalação, revisão e publicação

- [x] Distribuir dependências, preservar arquivos locais, atualizar hashes do catálogo.
- [x] Revisão independente, regressões dos achados e suíte pública; comandos e resultados na medição.
- [x] Atualizar README PT/EN, USAGE, BACKLOG, HANDOFF e memória; explicitar lacuna nativa de credenciais e próximo passo.
- [x] Commit/push por caminhos explícitos no PR #24 e verificar refs. CI permanece desconhecido se API recusada.

## Decisões de execução

- Contratos nativos desconhecidos bloqueiam somente as mutações dependentes; o incremento implementa coordenação/observação local e restauração das duas chaves com backend de teste. Não cria adaptador fictício de secret/policy no produto.
- O guard conserva comando privado e fixo; não ganha serviço geral nem argumentos livres de rede.
- Registros legados mantêm versões e listas de hashes originais; novos campos exigem versão 3.

## Provas e achados

A revisão read-only encontrou TIME_WAIT e expiração após save; a integração expôs
concorrência do escritor e deriva do daemon na recuperação. Correções têm regressões.
As provas acrescentadas medem zero bytes com recibo de destino recusado e coleta
após morte abrupta do controlador. Catálogo usa identidade legada resolvida antes
do hash. Ver relatório/medição deste incremento; sbx, TLS e clientes nativos pendentes.
