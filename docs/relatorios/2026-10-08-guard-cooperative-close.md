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
correspondem às fontes atuais.

O commit `9cb3729` terminou com sete dos oito jobs aprovados: seis Linux e o
[Windows do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37771069579).
Os testes de EOF e as oito recusas independentes passaram nos dois Windows.
No PR, os 14 focais passaram em 65 s, a suíte completa de missões em 421 s e a
adoção diagnóstica final em 167 s. Os quatro percursos positivos v3/v4 do PR
levaram de 9,329 a 9,516 s.
No [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37771064158),
o fluxo v4 atingiu o limite de
15,047 s, com árvore recolhida. A fase A ficou 7.098 ms entre persistir
`dispatch_authorization` e registrar `guard_request`. Depois desse pedido, chegou
a `observed` em 380 ms e completou o fechamento. A fase B começou; A2 não começou.

A lacuna precede `Channel.close`; os registros não identificam sua causa.
Próximo diagnóstico: comparar o `at_ms` já emitido no pedido do guard com a hora
do registro. Se necessário, medir autorização persistida, entrada/imports de
`injection_exchange`, conexão e handshake SOCKS. O timeout v4 permanece aberto.
Nenhum Docker, sbx, cliente
autenticado ou modelo foi executado. O contador nativo continua 2/3,
`proof_accepted=false`, com perfis bloqueados.

Retorno: reverter `9cb3729` restaura o encerramento anterior junto com os hashes
do catálogo. A mudança permanece no PR #24 em rascunho; `main` não foi alterada.

## English overview

Both Windows runs at `f3e091d` exposed a reset before EOF in the upstream observer.
The controller now gives helpers up to 100 ms to clean up after input EOF, sharing
the existing 200 ms termination stage and respecting the execution deadline.
Forced termination, kill and process containment remain available. Refused
persistence never releases an ACK, and incomplete byte observations still fail.

Real-child regressions cover cooperative cleanup and forced collection. Controlled
clock cases cover short/expired deadlines and time already spent closing input.
Full QA passed 620 tests with 20 skips in 262.122 s, without failures or errors.
Both reviewers approved the change. At `9cb3729`, six Linux jobs passed and both
Windows runs passed EOF/refusal tests. PR Windows passed all 14 focused tests,
the full mission suite and final diagnostic adoption. Seven of eight jobs passed.
Push Windows timed out in the separate v4 flow:
the 7.098 s gap precedes the first recorded SOCKS request and channel shutdown.
Its cause and native acceptance remain pending.

ATRASO: QA local 0 | CI verde 1 | executor nativo: validação pendente.
