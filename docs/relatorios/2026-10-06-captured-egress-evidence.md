# Coleta da fase B validada offline

Frente: executor isolado / YC-203, R1. Candidato local; integração nativa pendente.

O coletor separado reconhece a mensagem real de recusa que o Docker registrou na fase B.
Os onze testes locais passaram. Usamos a linha preservada do daemon e a janela registrada
do transporte; os snapshots de política do teste são sintéticos. Os snapshots originais
continuam indisponíveis, e o recibo da operação consumida continua inconclusivo.

## O que mudou

`captured_egress.py`, na área privada de ensaios, grava os snapshots completos de política
antes e depois do transporte. Antes do despacho, também salva a identidade da operação,
o hash do código informado pelo chamador, a posição e o hash do prefixo do log. Depois,
preserva a resposta do cliente e as novas linhas da sandbox examinada, com hashes dos
arquivos. O prefixo do log é lido para conferir continuidade; seu conteúdo não é copiado.

A recusa exige guard ausente, cliente B sem resposta HTTP, erro esperado e um único
evento do `HTTP Proxy Logger` na janela do transporte. Sandbox, versão, destino e as
três menções à porta devem corresponder. O reconhecimento está restrito ao formato
Windows observado no Docker Sandboxes 0.46.0. Um erro genérico de rede não passa.

O diretório é privado e de uso único. Falta de snapshot, falha de gravação, rotação,
truncamento ou dados incompletos impedem aceite. Limites: prefixo de 64 MiB e trecho novo
de 1 MiB. O arquivo fica fechado durante o transporte para permitir a rotação no Windows.
Uma exceção do transporte conserva os registros disponíveis e retorna sem aceite.

## Verificação

Os testes cobrem a mensagem real, preservação dos snapshots e hashes, exclusão do
histórico anterior, identidade/tempo/porta/destino divergentes, evento duplicado,
erro genérico, resposta HTTP inesperada, prazo expirado, transporte interrompido,
rotação/truncamento do log e falhas de armazenamento. A regressão inicial falhou antes
da implementação. O teste de rotação revelou o bloqueio causado pelo arquivo aberto;
a versão final fecha o arquivo entre as leituras e passou nesse caso.

O teste também confirma os hashes dos quatro recibos originais. Mesmo atribuindo B à
recusa na cópia de teste, o classificador existente mantém `inconclusive` sem A2.
Nenhum critério de aceite foi removido.

A suíte agregada passou em **91 testes**, sem falhas, erros ou skips; inclui os onze
testes do candidato. As contagens se sobrepõem e não devem ser somadas.

## Revisão e correção final

O revisor independente apontou um achado importante: falhar ao sincronizar o manifesto
final poderia deixar um arquivo legível indicando aceite. A regressão reproduziu o
problema. Agora o manifesto é gravado e sincronizado como pendente, e só então renomeado
para `evidence.json`. A verificação final inclui essa falha de armazenamento.

O parecer original pediu essa correção; não houve segunda revisão. A resolução foi
verificada pelo teste de regressão e pela suíte agregada. Integração nativa e a prova
A/B/A2 continuam fora do aceite desta correção offline.

## Limites e próxima ação

Este candidato recebe funções de leitura e transporte; os testes fornecem arquivos e
respostas locais. Não há entrada de execução nativa ou alteração no controlador usado
pela operação anterior. Não houve consulta ao Docker, requisição externa, reinício, alteração de rede
ou chamada de modelo pelo ensaio nesta correção. Não há comando para o operador executar agora.

Continuação: a [ligação ao controlador](2026-10-06-integrated-egress-controller.md) foi
validada offline, preservando os limites e a recuperação existentes. Falta preparar
a entrada da prova completa A/B/A2 com escopo explícito. A prova real continua pendente;
R1 permanece parcial, perfis bloqueados e R2/R3 não iniciados. Produção não publicada.

[Resultado nativo preservado](2026-10-06-corrected-egress-proof.md) ·
[Panorama](2026-10-06-panorama-executor.md) ·
[Medição](../medicoes/captured-egress-evidence.json)

## English overview

A separate collector passed eleven offline tests using the preserved Windows daemon event
and recorded transport window. Policy snapshots in the replay are synthetic; the original
snapshots remain unavailable. It saves full snapshots, operation context, a log cursor,
transport outcome and appended sandbox events in a private, single-use directory.
Only one explicit refusal matching the source, sandbox, version, destination, endpoint
and transport window can pass. Generic errors, stale/duplicate events, missing evidence
and log replacement cannot establish refusal.

The reviewer found a final-write failure that could leave an acceptance file. A failing
regression reproduced it; the manifest is now flushed as pending before publication.
The final aggregate suite passed 91 tests, including the eleven candidate tests, with
no failures, errors or skips. These counts overlap.
No Docker command, external request, restart, executor model call or native controller change
occurred. The consumed operation stays inconclusive and still lacks A2. Controller integration
subsequently passed offline validation; next, prepare the native entry.
The native A/B/A2 proof remains pending. No operator command is needed now. R1 remains partial and unpublished.

ATRASO: main 1
