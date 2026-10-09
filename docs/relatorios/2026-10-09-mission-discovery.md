# Descoberta de missões na retomada

Frente: preparação e consulta de missões.

`python3 -B scripts/missions.py --json list` permite encontrar uma missão sem lembrar
seu código. A consulta retorna código, UUID, título, revisão e estado salvo. Usa o
banco existente e encontra também missões cuja projeção no vault falhou.
`status CODIGO` continua responsável por conferir fontes, projeções e recibos atuais.

A listagem não inicializa nem repara arquivos. Banco ausente ou vazio produz uma lista
vazia; armazenamento incompatível ou de outro projeto permanece recusado. O índice
Markdown continua disponível para navegação manual. Não há novo esquema, módulo ou
dependência. O [guia de uso](../USAGE.md#mission-workflow) e `yc-status` ensinam a retomada.
Dez hashes de conteúdo do catálogo foram atualizados; contratos e permissões permanecem.

## Verificação

Quatro testes novos falharam antes da implementação e passaram depois em 0,858 s.
Cobrem consulta antes da inicialização, várias missões com revisões e estados distintos,
projeção interrompida, banco inválido e identidade divergente. Conferem preservação
dos arquivos. A revisão independente não encontrou bloqueantes e reproduziu os quatro
testes em 0,822 s.

A suíte completa executou 648 testes em 236,935 s: 628 aprovados e 20 pulados,
sem falhas ou erros. Os pulados exigem Windows nativo ou um grupo secundário POSIX
ausente neste ambiente.

O teste de instalação passou em projeto novo e projeto Git com trabalho existente,
para ambos os clientes. A CLI instalada encadeou `list` e `status` com o código
descoberto, mantendo os arquivos intactos. O teste da referência `yc-status` identificou
a ausência de instrução de descoberta antes da edição; depois, o revisor conseguiu
descrever o percurso e distinguir estado salvo de verificação atual.

A [medição](../medicoes/2026-10-09-mission-discovery.json) registra comandos, resultados
e hashes dos arquivos testados. As provas ocorreram na cloud Linux, com dados fictícios;
não houve chamada de modelo, Docker/sbx ou novo ciclo nativo. CI não consultado.

## Continuidade e retorno

Destino: branch `feat/isolated-executor`, PR #24. A consulta ao Docker continua em espera
por decisão do mantenedor. A fila 2B e os perfis nativos permanecem indisponíveis,
`proof_accepted=false`, com 2/3 ciclos usados. Retorno por revert deste incremento,
preservando o estado privado. Main não recebe merge nesta entrega.

## English overview

`missions.py --json list` discovers saved missions by code, UUID, title, revision and
recorded state, including failed note projections. It uses existing storage without
initializing or repairing files. Use `status CODE` to check current sources and blockers.

Four new tests failed before implementation and passed afterward. The full suite passed
628 tests with 20 skips. Independent review found no blockers. Installed CLI checks passed in new and existing projects for both
client installations, preserving files during discovery and status queries. The updated
`yc-status` reference explains discovery and the limits of recorded state.
No native execution or model calls occurred. The Docker inquiry remains on hold.

ATRASO: main 1 frente sem aceite | aceite nativo pendente.
