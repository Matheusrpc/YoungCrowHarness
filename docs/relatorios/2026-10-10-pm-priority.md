# Decisão restrita de prioridade PM

Frente: YC-206 parcial. Base: `8897bb98e16b595785f4c02462b9d160c27a6fcb`.

`reprioritize` recebe uma proposta do PM para mudar somente a ordem dos PBIs já
selecionados. Por exemplo, antecipar B antes de A não reimporta notas nem muda
critérios, configuração ou escopo. A proposta identifica projeto, missão e revisão,
lista todos os PBIs uma vez e registra o motivo. [Uso](../USAGE.md#pbi-priority).

Dry-run lê sem escrever, reparar ou reservar. Aplicar valida novamente dentro da
mesma transação que grava a revisão. Ator, data, motivo e revisões ficam no histórico.
O snapshot muda apenas em `priority` e `last_planning_decision`; não é reconstruído
a partir de fontes atuais. Nenhuma tabela, dependência ou módulo novo foi necessário.

Uma fila ativa de qualquer revisão da missão bloqueia a decisão. PBIs com histórico
de workspace conservam sua posição absoluta, inclusive após release ou preparo em
outra missão. Esse histórico não prova se houve execução. Fontes/importações antigas,
projeção pendente/conflitante e diagnóstico sem resolução também bloqueiam novas decisões.

A mesma operação e pedido retornam o recibo original após interrupção, antes dos
gates atuais; a aplicação pode reparar sua projeção. Dry-run de uma decisão concluída
retorna `already_applied` sem reparar. Outro pedido ou ator com a operação usada é
recusado. Prévia não reserva a revisão; dois concorrentes não podem gravar a mesma
revisão esperada.

## Provas e revisão

Os oito testes iniciais falharam pela ausência da função/comando. Dez testes focados
passaram em 10,489 s, cobrindo preservação do snapshot, proposta inválida, papel incorreto,
fontes/projeção divergentes, fila de revisão anterior, workspace liberado em outra missão,
concorrência, rollback antes do commit e retomada de projeção. A prévia também foi
invalidada por uma fila criada antes da aplicação e não contornou o bloqueio.

Revisão independente do código não encontrou pendência material. O CLI instalado
nos perfis Claude e Codex passou em projeto novo e existente com alterações locais:
prévia sem escrita, aplicação/replay, snapshot preservado e retorno do trial conferidos.
O perfil global também permaneceu intacto. Revisão de documentação e catálogo sem
pendências; cinco contratos normalizados e dez hashes foram conferidos, preservando
permissões e listas de arquivos.

A suíte completa executou 750 testes em 534,883 s: 730 aprovados, 20 pulados por
requisitos de ambiente/plataforma e zero falhas.

Os 546 caminhos Markdown locais conferidos existem. O vault passou com 63 notas e
zero problemas. Resultados e hashes estão na
[medição estruturada](../medicoes/2026-10-10-pm-priority.json).

## Falha Windows observada na base

O [job do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38057222872/job/114228060887)
falhou no cleanup de `test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`:
WinError 32 ao remover o diretório temporário usado como cwd. O supervisor havia retornado
`completed`, `exit_code=71`, `tree_reaped=true`. A mesma etapa passou no run de push
do mesmo commit. O log não identifica quem ainda mantinha o diretório aberto.

O ajuste fica na fixture de teste: verifica ownership antes do cleanup no caso abrupto
e repete somente a remoção com WinError 32 até dois segundos. Não ignora bloqueio
persistente ou erro de permissão. Vinte e um testes de egress passaram em 4,993 s,
incluindo erro 32 transitório/persistente, erro 5 e owner ainda vivo. O supervisor
de produção não mudou. Revisão independente sem pendências; confirmação Windows
da correção depende do CI do novo commit.

## Distribuição e limites

README PT/EN, guia, backlog, handoff e skill `yc-missao` nos dois clientes acompanham
o comando. O catálogo atualiza uma finalidade e dez hashes em cinco capacidades;
listas de arquivos e permissões permanecem iguais. Atribuição do papel PM não
autentica um agente. JSON de proposta, notas, bancos e recibos reais continuam privados.

YC-206 permanece parcial: decisões Tech Lead, repriorização durante execução, avisos
por evento e entrega automática de contexto continuam pendentes. Desenvolvimento e
QA não avançam; produção segue não verificada e flags nativas falsas. Nenhuma chamada
de modelo, Docker ou nova prova nativa. Contador 2/3 e prova histórica de memória P06
preservados. Publicação autorizada somente na branch e no PR #24 em rascunho.

## English overview

The restricted PM proposal reorders only already-selected PBIs, preserving the frozen
scope/configuration and recording reason, actor and revision. Dry-run is read-only;
apply holds one transaction for replay, guards and revision CAS. Active queues block
changes; any workspace history pins that PBI's position. Replaying a completed decision
can repair its projection without creating another event. No worker or model is started.

Ten focused checks and the installed CLI in new/existing projects passed. The full suite
passed 730 tests, with 20 environment/platform skips and no failures. Review found no material issue. The Windows CI failure on
the base was a temporary-directory sharing violation; the fixture now retries that
specific deletion error for up to two seconds and still fails on persistent locks or
other errors. Production supervision is unchanged. Windows confirmation awaits new CI.
Tech Lead decisions, live reprioritization, notices and native acceptance remain pending.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
