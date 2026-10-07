# Admissão sintética na cloud

Frente: executor isolado do YoungCrowHarness.

Base: PR [#24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24), commit
`b801bec963e8af4af921b8c5473d3884ee5a7a03`. As refs da branch e do PR apontavam
para esse commit durante a retomada. A API do GitHub respondeu `Forbidden` à
consulta do PR/CI; o resultado remoto permanece desconhecido.

## Alterações

`client check` aceita `isolated-egress-v1` e grava um recibo terminal
`failed/controller_pending`, com `model_calls=0` e `effects_allowed=false`.
Valida a missão preparada, revisão, autorização, papel e limites antes da gravação.
Reutiliza o armazenamento transacional e a projeção no vault, entrando antes de
`inspect_client/build_check`. Não consulta clientes, executável ou Docker nem
inventa observações de autenticação, modelo, candidato ou baseline.

Cada tentativa bloqueada consome uma entrada de diagnóstico e seus segundos no
orçamento da missão. Repetir o manifesto retorna o mesmo recibo. Alterar o conteúdo
com o mesmo UUID é conflito. A futura implementação do controlador não reativa
UUIDs consumidos. `echo-v1` mantém seu contrato e os perfis vazios.

A criação do lock compartilhado usa abertura exclusiva com modo POSIX `0600`.
Isso corrige a recusa de uma instalação nova sob `umask 022`, reproduzida na
[auditoria do PR](2026-10-07-pr24-cloud-audit.md). Um lock existente com permissões
inseguras permanece intacto e bloqueado.

Os dez hashes de conteúdo do Personalizer e das quatro capacidades `yc-*` em `skills-lock.json`
foram recalculados para os arquivos deste incremento. Contratos e permissões
declaradas permanecem iguais; a correspondência de conteúdo não habilita execução.

## Verificação

A suíte final `python3 -B -m unittest discover -s tests -v` percorreu 506 testes em
208,592 segundos: 486 passaram, 20 foram pulados e não houve falhas ou erros.
Dezenove skips dependem de mecanismos Windows; um exige grupo secundário POSIX
ausente nesta cloud. Eles não comprovam os controles nativos dessas plataformas.
Veja a [medição](../medicoes/2026-10-07-synthetic-admission.json), com hashes das
fontes e dos logs privados.

Os testes focados cobriram dez casos de admissão sintética, 15 de reserva (14
passaram e um foi pulado), 13 de execução existente e 23 de capacidades. Os dois
métodos de instalação/auditoria passaram nas seis variantes de cliente. A
verificação estrutural conferiu todos os 24 hashes de conteúdo não nulos do
catálogo. `git diff --check`, sintaxe Bash e vault também passaram (três notas,
nenhum problema). Sete novos links da documentação foram conferidos.

A primeira suíte completa percorreu 506 testes e terminou com sete falhas em
três métodos, todas por hashes antigos no catálogo: `test_mission_catalog_has_explicit_diagnostic_permissions`,
`test_governance_installs_selected_profiles_and_audits` e
`test_mission_commands_follow_client_selection`. Os dois últimos falharam nas
variantes Claude, Codex e ambos. Após atualizar os hashes `yc-*`, os 23 testes de
capacidades passaram. A segunda suíte ainda teve três falhas de instalação porque
o Personalizer também inclui os dois helpers alterados. Seus hashes foram
atualizados. Os logs das duas rodadas foram preservados.

A revisão independente encontrou uma inversão entre criação e encerramento do
recibo bloqueado. A regressão reproduziu a falha; ambos os timestamps agora são
gerados dentro da transação. A segunda conferência não encontrou bloqueadores.

## Pendências e próxima ação

O §10.2 do handoff está parcial. Faltam candidato/baseline observados, imagens
externa/interna e hashes do pacote, plano A/B/A2 com UUIDs/nonces próprios e vínculo
durável com a reserva global. Reservar Docker para esta entrada bloqueada não
protegeria qualquer efeito; a reserva fica para a integração do controlador.

Continuar pelos §§10.2 a 10.4: materializar o plano e implementar o controlador
fixo sob o supervisor atual, mantendo aberto seu pipe com o launcher. Completar a
recuperação antes de habilitar mutações, preservando mudanças externas e sem
iniciar VM parada para consultá-la. No Linux, o controlador deve evitar um
supervisor aninhado: o seccomp herdado impede criar outra sessão de processos.

Esta cloud não disponibiliza `sbx` nem `/dev/kvm`. As provas A/B/A2, restauração e
clientes autenticados continuam pendentes no candidato exato. Nenhuma nova rodada
nativa ocorreu: permanecem dois ciclos históricos usados de três. As demais
ocorrências das auditorias anteriores não foram alteradas neste incremento.

## English overview

Synthetic admission now records a durable `failed/controller_pending` receipt with
zero model calls. It preserves mission validation, cumulative limits and replay
semantics without inspecting clients, the executable or Docker. A new POSIX lock
is created privately under permissive umasks; existing unsafe permissions remain
blocked and unchanged.

Handoff step 10.2 remains partial. Candidate binding, the A/B/A2 phase plan, global
reservation, controller and recovery still need integration before native effects.
CI status is unknown because the GitHub API refused the query. No native proof or
model call ran in this cloud session.

Final validation: 506 Python tests, 486 passed and 20 skipped, with no failures or
errors. Skips cover Windows controls and an unavailable POSIX secondary group.
Changes remain local to this checkout.

ATRASO: main 1
