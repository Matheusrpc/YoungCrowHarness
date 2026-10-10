# Queue rehearsal implementation plan

> **For agentic workers:** Use superpowers:executing-plans; one writer and a final independent review.

**Goal:** Provar o ciclo persistente de um PBI por comandos e status reais, com executor determinístico.

**Architecture:** Duas tabelas no SQLite existente; transações, CAS e recibos por operação.
Fixture pura executada atomicamente com a transição, sem infraestrutura externa.

**Tech Stack:** Python e SQLite da biblioteca padrão; unittest existente.

**Spec:** [desenho](../specs/2026-10-10-queue-rehearsal-design.md).

## Global Constraints

- Escopo fixo `deterministic_rehearsal`, um PBI sem dependências.
- `runtime_available=False`, `runnable=False`; nenhuma inferência ou aceite nativo.
- Leituras não migram nem reparam; preservar dados e diagnósticos existentes.
- Autorização: resposta “bora” à proposta de antecipação; execução nesta sessão,
  publicação na branch do PR #24 conforme autorização vigente, sem merge.

## Review Focus

Recibos perdidos após commit; queda com transação aberta; dois avanços concorrentes;
missão revisada durante ensaio; helper antigo preservado numa instalação existente.
Cobrir cada caso nos testes ou na verificação de compatibilidade.

### Task 1: Ciclo persistente integrado

**Files:** criar `scripts/mission_queue.py`, `tests/test_mission_queue.py`;
alterar `mission_store.py`, `mission_runs.py`, `missions.py`, `setup.sh`, `test_setup.py`.

**Interfaces:** `mission_queue.apply(root, action, identifier, expected_revision,
operation_id, actor_id)` retorna recibo; `sessions(root, mission_id)` lê snapshots;
`view(sessions, status)` adiciona orientação sem mudar o estado. CLI `queue start/step/cancel`.

- [x] Escrever testes do percurso, replay, conflitos, quedas, recusas, migração e instalação.
- [x] Executar `python3 -B -m unittest discover -s tests -p test_mission_queue.py -v`;
  observar falha por capacidade ausente.
- [x] Implementar menor ciclo, adaptar compatibilidade de esquema e distribuição.
- [x] Executar a suíte focada e corrigir apenas falhas verificadas.

### Task 2: Revisão e publicação

**Files:** README, USAGE, BACKLOG, handoff, relatório/medição e memória local.

- [x] Revisão independente do diff, especialmente isolamento entre prova sintética e nativa.
- [x] Executar `python3 -B -m unittest discover -s tests -v`, registrar passes/skips/falhas.
- [x] Atualizar documentação PT/EN e demonstrar o CLI em projeto temporário.
- [x] Verificar vault, diff e links alterados; preparar publicação por caminhos explícitos.

Publicação autorizada: commit e push para `feat/isolated-executor`, atualização do PR #24
e consulta ao CI da revisão publicada, sem apresentar simulação como aceite nativo.
O recibo de publicação será registrado na memória local após confirmação do remoto.
