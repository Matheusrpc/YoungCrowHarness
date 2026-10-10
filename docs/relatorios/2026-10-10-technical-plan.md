# Plano técnico vinculado ao PBI

Frente: YC-206 parcial. Base: `f3e00b1b2727bfd67c323f5bd11e979d4720b852`.

`technical-plan` registra qual referência direta do PBI foi escolhida pelo Tech Lead
para orientar a implementação. `context` devolve essa escolha junto aos contratos e
ao conteúdo já selecionado da nota. [Comandos e limites](../USAGE.md#technical-plan).

A proposta identifica projeto, missão/PBI e suas revisões, referência exata e motivo.
Dry-run não escreve, repara ou reserva. Aplicar usa a mesma transação para verificar
repetição, condições atuais e revisão antes de gravar. A nota, seus critérios e
dependências permanecem intactos. Referência de outro item ou divergência entre seu
hash e os inputs congelados recusa a decisão.

O backend reutiliza o fluxo de prioridade do PM, seus eventos e projeções. Grava apenas
`technical_decisions` no snapshot; `context.technical_decision` contém a escolha do
PBI consultado ou `null`, incluída no digest do contexto. Repriorização preserva todos
os planos. `revise` refaz o planejamento e remove as escolhas atuais, conservando os
eventos anteriores; uma nova seleção precisa usar a revisão atual.

Uma fila ativa da missão, de qualquer revisão, bloqueia a escolha. Histórico de
workspace do PBI, inclusive liberado ou de outra missão, também bloqueia. Histórico
de outro PBI não impede a decisão. A missão precisa estar preparada e atual, com
projeções íntegras e sem diagnóstico pendente. Repetição exata retorna o recibo original
e pode recuperar a projeção; dry-run nunca repara. Não há novo módulo, esquema ou dependência.

## Validação e revisão

Os seis testes iniciais falharam pela ausência do comando, após corrigir a ordem de
importação da própria fixture. A bateria final de oito testes passou em 10,490 s;
os dez testes de prioridade PM também passaram, em 11,010 s.

A prova pelo CLI registra planos para dois PBIs, recupera cada escolha no contexto
correto, reprioriza sem perder os planos e revisa a missão removendo as escolhas atuais
sem apagar eventos. Também cobre referências de outro PBI, perfil sem referência direta,
identidades/revisões/papel incorretos, concorrência PM/Tech Lead, fonte alterada, projeção
interrompida, fila antiga e workspace liberado em outra missão.

A revisão encontrou uma corrida na preparação: uma nota alterada entre a leitura do
contrato e o congelamento dos inputs podia produzir hashes distintos. A seleção do
plano conferia apenas a referência importada. Uma regressão reproduziu a aceitação
incorreta; a correção compara também o hash congelado antes de escrever. A regressão
passou e o revisor encerrou o achado. Não houve outras pendências materiais de código.

A suíte completa executou 758 testes em 580,444 s: 738 aprovados, 20 pulados por
requisitos de ambiente/plataforma e zero falhas.

Resultados completos, instalação e hashes constam na
[medição estruturada](../medicoes/2026-10-10-technical-plan.json).

O comando instalado nos perfis Claude e Codex passou em projeto novo e existente
com alterações locais. Conferiu prévia sem escrita, escolha/repetição, contexto do
PBI correto e preservação do contrato e da nota. Retorno do trial e perfil global
ficaram íntegros. Revisão de documentação e catálogo sem pendências; os 551 caminhos
Markdown locais conferidos existem. O vault passou com 64 notas e zero problemas.

## Distribuição e estado

README PT/EN, guia, backlog, handoff e skills `yc-missao`/`yc-status` acompanham o
incremento. O catálogo altera duas finalidades e dez hashes de conteúdo em cinco
capacidades; mantém permissões e listas de arquivos. Propostas e recibos reais são privados.

O CI da base passou na etapa Windows de rede, locks e cleanup nos dois runs
[push 38058710715](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38058710715) e
[PR 38058715422](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38058715422).
Installer, public-pilot e graphify-smoke passaram em ambos. Os demais testes Windows
ainda executavam no checkpoint; a revisão inteira não foi declarada aprovada.

A seleção comprova identidade, estado e preservação do contrato; não valida a qualidade
semântica do plano nem autentica um agente. A nota continua dado não confiável. Decomposição,
revisão técnica, avisos e despacho automáticos continuam pendentes, assim como prioridade
durante execução. Desenvolvimento/QA/produção não avançam. Zero novas chamadas de modelo
ou Docker; P06 e contador nativo 2/3 preservados. Publicação limitada ao draft PR #24.

## English overview

The Tech Lead can select an existing direct PBI reference as its technical plan.
The revision-bound choice appears only in that PBI's context; source content is already
included and verified. Scope, criteria, dependencies and source notes remain unchanged.
Preview is read-only; apply and replay use existing transactional history and projections.
Active mission queues and workspace history for the target PBI block selection.
Reprioritization preserves plans; broad revision clears current choices and retains history.

Eight focused checks and ten PM regression checks passed. The full suite passed 738 tests,
with 20 environment/platform skips and no failures. Review identified a hash mismatch
possible during mission preparation; a failing regression reproduced it and passed after
the selection guard was added. This is a planning choice, without semantic approval, model
calls or worker dispatch. The installed command passed in both client profiles and new/existing
trial projects, preserving source notes, contract, trial restoration and the global profile.
Native acceptance and automated squad operation remain pending.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
