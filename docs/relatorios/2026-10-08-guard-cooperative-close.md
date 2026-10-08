# Encerramento cooperativo do helper

Frente: corrigir o reset que invalida a prova de recusa de rede no Windows.

O CI de `f3e091d` identificou `ConnectionResetError` no observador upstream:
conexão aceita, zero bytes contados, EOF ausente e observação incompleta. Houve
cinco recibos no [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37769831009)
e três no [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37769835804).
Os seis jobs Linux passaram; os dois Windows reprovaram nos focais. Contagem zero
com observação incompleta continua insuficiente para aprovar o teste.

Quando persistir `guard_destination` falha, o controlador recusa o ACK e fecha o
canal. `Channel.close` permite agora até 100 ms após EOF para o helper fechar seus
sockets. A espera consome o estágio existente de 200 ms: `terminate` usa somente
o saldo, e `kill` conserva sua espera de 200 ms. O prazo da execução também limita
a graça; prazo expirado segue direto para encerramento forçado. Os joins e a
contenção da árvore de processos permanecem iguais.

Uma regressão com filho real falhou antes da mudança: SIGTERM interrompeu o filho
cooperativo antes de seu marcador de limpeza. Com a alteração, ele recebe EOF,
grava o marcador e termina com exit 0. Outro filho ignora EOF e, em POSIX, SIGTERM;
o supervisor comprova seu recolhimento. O teste com relógio controlado verifica
prazo curto, prazo expirado e consumo de 180 ms antes do cálculo da graça.

O negativo de rede oferece 13 bytes e repete oito tentativas independentes, exigindo
zero bytes até EOF e observador coletado depois de fechar o guard. Qualquer falha
reprova. A persistência recusada não libera ACK; o controle positivo exige 13 bytes.
O workflow Windows inclui os dois novos testes de encerramento na etapa focal.

O revisor independente aprovou o orçamento e a contenção. O catálogo atualiza
somente dez hashes de conteúdo dos cinco contratos afetados, após review/check;
permissões e hashes dos contratos ficam iguais. A medição registra os hashes de
fontes, testes e recibos: [evidência](../medicoes/2026-10-08-guard-cooperative-close.json).

QA integral: 640 testes em 262,122 s, com 620 aprovados e 20 pulados, sem falhas
ou erros. Os dois revisores aprovaram a alteração; dez observações do catálogo
correspondem às fontes atuais. CI da correção: verificar após publicação.
Nenhum Docker, sbx, cliente
autenticado ou modelo foi executado. O contador nativo continua 2/3,
`proof_accepted=false`, com perfis bloqueados.

## English overview

Both Windows runs at `f3e091d` exposed a reset before EOF in the upstream observer.
The controller now gives helpers up to 100 ms to clean up after input EOF, sharing
the existing 200 ms termination stage and respecting the execution deadline.
Forced termination, kill and process containment remain available. Refused
persistence never releases an ACK, and incomplete byte observations still fail.

Real-child regressions cover cooperative cleanup and forced collection. Controlled
clock cases cover short/expired deadlines and time already spent closing input.
Full QA passed 620 tests with 20 skips in 262.122 s, without failures or errors.
Both reviewers approved the change. Correction CI must be checked after publication;
native acceptance remains pending.

ATRASO: QA local 0 | CI verde 1 | executor nativo: validação pendente.
