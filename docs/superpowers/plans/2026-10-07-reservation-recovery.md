# Plano de integração de reserva e recuperação

> Execução inline com `superpowers:executing-plans`, conforme continuidade autorizada.

**Objetivo:** persistir o plano A/B/A2 antes de efeitos e recuperar a carga identificada sem repetir despacho.
**Arquitetura:** registro v2 no ledger global existente, vínculo bilateral com a missão e diário do controlador. O launcher observa e para somente contêineres registrados; a recuperação mantém a reserva se qualquer evidência faltar.
**Stack:** Python e biblioteca padrão, SQLite existente, protocolo do launcher existente.
**Especificação:** [executor aprovado](2026-10-07-executor-consolidation.md), [decisão de uso exclusivo](../specs/2026-10-05-exclusive-egress-decision.md) e [handoff §10](../../HANDOFF-CLOUD-2026-10-07.md#10-próximos-passos-de-implementação-em-ordem).

## Restrições

- Preservar registros v1, UUIDs consumidos e perfis bloqueados. Nenhum sidecar na reserva global.
- Plano privado com valores de baseline, hashes, revisão/autorização, digests externo/interno e três UUIDs/nonces distintos.
- Prazo compartilhado de até 120 segundos para as fases, limitado pelos segundos admitidos na missão; recuperação tem prazo próprio e nunca estende despacho.
- Um escritor neste checkout. Revisores somente leitura. Nenhuma operação Docker ou modelo durante testes da cloud.
- `new:false`, processo ausente e `verified:true` não autorizam efeito nem encerramento.
- Integração do egress/configuração global (203.6), pacote e aceite nativo permanecem gates posteriores; comandos desconhecidos não serão inventados.

## Revisão focada

- Queda entre reserva da missão e global: nenhum efeito e nenhum replay.
- Plano expirado deve continuar legível para recuperação; comparação de daemon após restart não confunde identidade histórica com configuração.
- Perda da resposta depois de prepare/stop: observar estado existente sem repetir mutação.
- VM parada sem prova interna: manter pendência sem `sbx exec`.
- Alterações externas, recibos inválidos, carga/helper/porta pendentes: não encerrar reserva.

### Task 1: plano, vínculo e diário

Arquivos: `scripts/mission_transaction.py`, `scripts/mission_execution.py`, `scripts/mission_runs.py`, `scripts/mission_sbx.py`; testes correspondentes.

Interfaces: `build_plan(...)`, `reserve(registry, plan)`, `phase_event(registry, operation_id, phase, kind, payload)`, admissão interna da missão com ID/hash do plano; `Sbx.baseline` privado.

- [x] Escrever regressões de plano persistido, v1 preservado, exclusão entre projetos, replay e falha de persistência.
- [x] Executar testes e observar falhas pela funcionalidade ausente.
- [x] Implementar schema v2 estrito, vínculo bilateral e diário ordenado no ledger existente.
- [x] Exercitar controlador real com launcher local e diário real; repetir operação sem segundo despacho.

### Task 2: observação e recuperação

Arquivos: `runtime/sbx/launcher.py`, `scripts/mission_transaction.py`; testes do launcher e transação.

Interfaces: comandos fechados `observe UUID NONCE` e `stop UUID NONCE`; recuperação lê o plano salvo e observa os recursos da operação.

- [x] Escrever regressões de identidade divergente, parada única, perda de resposta, expiração e recuperação repetida.
- [x] Observar RED, implementar parada com intenção persistida e conferência do estado terminal, observar GREEN.
- [x] Testar fechamento recusado sem prova de carga/VM/configuração e preservação de mudanças externas. Helpers/portas ficam para sua integração em 203.6.
- [x] Separar evidência de contrato local da prova nativa indisponível nesta cloud.

### Task 3: revisão e publicação

- [x] Atualizar dependências/hashes do catálogo e instalação, README PT/EN, guia, backlog, handoff e memória.
- [x] Revisão independente e suíte completa; corrigir achados com regressões.
- [x] Commit por caminhos explícitos e push para `feat/isolated-executor`; conferir refs do PR #24.

Validação: `python3 -B -m unittest discover -s tests -v`, sintaxe do setup, hashes de capacidades e `git diff --check`. Resultado esperado: zero falhas/erros; skips discriminados.
