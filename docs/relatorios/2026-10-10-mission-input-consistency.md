# Coerência dos inputs de missão

Frente: preparação e consulta de missões. Base: `a6e556b52ca9e82cdf665e148861e156cb3eef22`.

Uma nota podia mudar depois da leitura de seu contrato e antes do congelamento dos
arquivos. Nesse caso, o preparo guardava o contrato importado com um hash e o input
com outro, mas ainda podia declarar `prepared`. O contexto e a seleção do plano
recusavam a divergência depois; status e outros consumidores podiam aceitá-la.

`build_mission` agora compara os hashes congelados com cada nota e referência dos
itens importados. Divergências entram em `gaps` como `stale_input:CAMINHO` e produzem
`draft`. O mesmo verificador alimenta `status.stale_inputs`, inclusive para snapshots
antigos gravados como `prepared`. O estado histórico permanece; a disponibilidade
atual fica bloqueada e a prévia não seleciona candidato.

O operador confere as edições, reimporta os itens afetados e revisa a missão.
Referências compartilhadas exigem reimportar todos os itens que as referenciam.
Não há troca silenciosa de hashes nem reparo durante consulta.
[Procedimento](../USAGE.md#mission-input-consistency).

## Provas

Três testes de regressão falharam antes da correção, em oito subcasos: mudança no
épico, feature, dois PBIs e referência compartilhada durante preparo; mudança na
revisão; dois snapshots legados inconsistentes. As três regressões passaram após
a correção. A cobertura final verifica também a recusa por `mission_agent`, consumidor
que consulta `stale_inputs` diretamente, sem depender de `check_available`.

Os testes preservam os arquivos editados e o histórico. Verificam replay sem novo
evento, recuperação explícita por importação/revisão, status sem escrita e recusa
de nova fila/workspace em um repositório Git real. As expectativas anteriores de
contexto e plano técnico foram ajustadas para a detecção antecipada da divergência.

Suíte completa: 761 testes, 741 aprovados, 20 pulados por requisitos de ambiente/plataforma e zero falhas. Execução em duas partes sem repetição: 432 testes de missões em 314,890 s e 329 demais testes em 358,154 s.

O smoke usa o código instalado em projetos novo e existente com alterações locais,
nos perfis Claude e Codex. Altera uma referência entre leitura e congelamento, comprova
o rascunho e a consulta sem escrita, restaura os bytes da fixture e recupera por revisão
explícita. Retorno do trial e perfil global foram preservados, com zero chamadas de modelo.
Hash do código e logs constam na [medição](../medicoes/2026-10-10-mission-input-consistency.json).

## Revisão, distribuição e limites

Revisões de código e documentação/catálogo encerradas sem achados materiais pendentes.
README PT/EN, guia, backlog e handoff atualizados. Cinco contratos de capacidades e suas
permissões permanecem iguais; dez hashes de conteúdo acompanham o script corrigido.

O CI da base tinha seis checks aprovados e dois Windows em andamento no checkpoint
de 10/out às 14h41 UTC: [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38060122673)
e [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38060127712).

A correção verifica coerência das revisões observadas; não trava editores externos.
Mudanças posteriores continuam sujeitas aos checks de atualidade de cada operação.
Replay, cancelamento, liberação de workspace e recuperação de operação já admitida
mantêm seus contratos. Não há novo comando, tabela, dependência ou chamada nativa.
O aceite do executor, YC-206, avisos e despacho de agentes permanecem pendentes.

## English overview

Preparation and revision now compare frozen input hashes with every imported note
and reference. Mismatches produce a draft with explicit gaps. Read-only status also
blocks internally inconsistent older snapshots while preserving their recorded state
and history. Reimport affected items and explicitly revise the mission to recover.
Shared references are checked for every referring item. This is a consistency check,
not a filesystem lock; later edits remain subject to each operation's freshness checks.

Regression tests reproduced the original race using real file changes. Installed
smoke checks passed for both client profiles in new/existing projects, including
preservation and explicit recovery. Native execution and automatic agent dispatch
remain unverified.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
