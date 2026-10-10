# Contexto vinculado ao workspace do PBI

Frente: YC-206 parcial, consulta de contexto para desenvolvimento e revisão.
Base: `77f6e378099487e0f7c6c99d205f97f9f328bede`.

O contexto de um PBI já podia ser consultado pelo UUID da missão e do item. Agora
`workspace context UUID --expected-revision N` deriva essas identidades do registro
do workspace e confere o diretório Git antes de retornar o contexto. N é a revisão
do workspace; a revisão da missão vem do registro. Isso permite retomar o trabalho
sem escolher manualmente outra missão ou outro PBI por engano.

A leitura usa o vault original. O envelope inclui caminho, branch, commit base e
HEAD observado, com `workspace_context_sha256` próprio. O contexto interno mantém
seu `context_sha256`, seus contratos, fontes e plano técnico selecionado. A consulta
não copia notas para o worktree nem entrega o resultado automaticamente a um agente.
[Procedimento e erros](../USAGE.md#workspace-context).

Revisão antiga, fonte divergente, workspace liberado, diretório substituído e branch
alterada são recusados. Uma segunda inspeção Git e uma leitura transacional final
conferem HEAD, registro do workspace e revisões dos itens/da missão. Alterações locais
e commits de trabalho são permitidos e preservados; não se exige diretório limpo.

## Provas

Quatro testes iniciais falharam antes da implementação, em sete subcasos. Os seis
testes finais passaram em 8,706 s. Usam Git real e verificam vínculo, hashes, conteúdo
privado fora do worktree, preservação de arquivos/índice Git, revisão e fonte antigas,
diretório substituído, branch alterada e mudanças de missão/workspace durante a leitura.

Suíte completa: 767 testes, 747 aprovados, 20 pulados por requisitos de ambiente/plataforma, zero falhas/erros, em 525.570 s.

O smoke executa o comando instalado em projetos novo e existente, com perfis Claude
e Codex. Prepara o workspace, consulta o contexto com plano técnico, confere o vínculo,
comprova leitura sem escrita e libera a fixture. Status e diferenças Git originais,
backup do trial e perfil global foram preservados. Zero chamadas de modelo.
Hashes de código e evidências constam na [medição](../medicoes/2026-10-10-workspace-context.json).

## Revisão e distribuição

Revisões de código, documentação e catálogo encerradas sem achados materiais
pendentes. README PT/EN, guia, backlog e handoff
explicam o comando e seus limites. As instruções compartilhadas e os dois clientes
acompanham a consulta. O catálogo acrescenta leitura dos metadados Git do workspace
ao `yc-status`; muda um contrato e dez hashes de conteúdo. Nenhuma nova permissão
de escrita ou rede, tabela, migração ou dependência.

O CI da base passou nos oito checks, incluindo Windows:
[push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38061225355) e
[PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38061229317).
O CI do novo commit precisa de confirmação separada. A
[issue Docker #690](https://github.com/docker/sbx-releases/issues/690) segue aberta,
sem comentários no checkpoint desta entrega.

## Limites

É uma observação pontual: escritores externos não são travados. HEAD identifica
um commit e não descreve mudanças no índice ou arquivos locais. Se a missão for
revisada, o comando recusa usar silenciosamente o contexto atual ou histórico.
Fontes continuam sendo dados privados não confiáveis, e nenhum hash concede
autorização. Recuperação, replay e liberação conservam seus contratos existentes.
O resultado declara `runtime_available: false` e `runnable: false`.

YC-205/206 permanecem parciais. Despacho de agentes, decisões automáticas, avisos e
aceite do executor nativo continuam pendentes. Prova P06 e contador nativo 2/3
preservados; nenhuma chamada nativa, Docker, merge ou release nesta entrega.

## English overview

`workspace context` resolves mission/PBI identities from an owned workspace record,
checks its Git identity, then reads the original vault at the pinned revisions.
Its envelope has a separate hash and preserves the existing context digest.
Dirty files and work commits are allowed. Stale revisions, changed sources and
replaced workspaces are refused without repair or silent fallback.

Real-Git tests and installed smoke checks cover both client profiles in new and
existing projects. This is a read-only observation, not a filesystem lock or a
description of uncommitted changes. Automatic agent delivery and native execution
remain pending.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
