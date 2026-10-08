# Leituras de missão e observação de egress

Frente: custo da consulta de missão e confiabilidade da prova local de recusa de rede.

Para uma missão existente, `mission_status` executava cinco preflights, com 15 processos Git por consulta.
Agora agrupa as consultas SQL adjacentes de revisões, eventos e projeções, mantendo
três preflights e nove processos: redução de 40% na quantidade de processos Git.
O banco é reaberto depois de ler os arquivos de entrada; a leitura final das
execuções do cliente continua independente. Não há cache, nova API ou alteração
dos prazos do produto. A medição local não estabelece redução percentual do tempo
no Windows nem uma leitura atômica de todos os arquivos e registros.

A fixture de recusa de rede guardava a contagem num arquivo escrito pelo próprio
helper que seria encerrado. Uma interrupção entre truncar e gravar podia deixar
o arquivo vazio. Agora um observador no controlador aceita a conexão, conta os
bytes e exige EOF. A conclusão ocorre depois de encerrar o guard; a thread precisa
estar coletada antes de consumir o resultado. Erros e timeouts invalidam a prova.

O negativo oferece 13 bytes junto ao pedido SOCKS e exige zero bytes recebidos
pelo observador. O controle positivo usa o mesmo observador e exige 13 bytes.
Essa validação percorre guard, supervisor, processos e sockets locais. Os modos
usados pela fixture de rede v3/v4 continuam compatíveis.

## Regressões e revisão

Seis novos testes de status cobrem o limite de processos, igualdade por UUID/código,
ausência de escrita, regras privadas alteradas durante/depois de consultas,
revisão concorrente de item e banco removido/substituído durante leitura de inputs.
Os dois testes de egress foram fortalecidos com payload e observação completa.
O CI Windows executa cinco desses casos cedo, junto aos sete focais existentes.

O teste de custo falhou contra o status do baseline com `15 not less than or equal
to 9`. A prova de substituição do banco orientou a preservação da reabertura após
inputs. Dois revisores independentes aprovaram o diff final; o cleanup do observador
fecha o listener após o join e só contabiliza payload após `sendall` retornar.

O catálogo atualiza somente os dez hashes de conteúdo dos cinco contratos que
distribuem `missions.py`, para Claude e Codex. A revisão privada foi conferida
antes da alteração; permissões e hashes dos contratos permaneceram iguais. As
dez observações correspondem ao conteúdo atual na auditoria offline. Isso não
representa execução ou aceite desses clientes.

Resultados completos e hashes estão na
[medição desta revisão](../medicoes/2026-10-08-mission-read-stability.json).

- Suíte integral: 636 testes, 616 aprovados e 20 pulados, sem falhas/erros em 243,735 s.
- Seleção focal do CI: 12 aprovados em 7,526 s.
- Catálogo: 11 aprovados, com dez observações de conteúdo correspondentes na auditoria.
- Consumidor instalado, perfis Claude/Codex: projeto novo e existente passaram;
  replay manteve um despacho, timeout/crash exigiram reconciliação e o retorno
  preservou o trabalho do trial e o perfil global. Zero chamadas de modelo.

## CI e limites da conclusão

O baseline `c8e7f0b46be74a4cfe8c63b77b302b0cb04bf6da` passou nos oito jobs:
[push 37760885128](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37760885128)
e [PR 37760891582](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37760891582).
Os quatro percursos Windows positivos v3/v4 da suíte levaram 9,734 a 13,078 segundos.

As falhas anteriores de timeout e recibo continuam intermitentes. O traceback da
falha histórica de egress não foi obtido; a corrida reproduzida não prova sua causa.
O CI de `b106bc5` terminou com sete de oito jobs aprovados:
[push 37765970236](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37765970236)
e [PR 37765976349](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37765976349).
Os 12 focais passaram nos dois Windows. O Windows do PR passou integralmente;
o do push falhou no teste de recusa do recibo de destino. O supervisor coletou a
árvore, com exit 1 em 0,313 s, stdout vazio e 445 bytes de stderr. A página pública
não mostrou a exceção. Os percursos v3/v4 passaram em ambos, entre 11,562 e 12,453 s.

O complemento de diagnóstico emite um único JSON após cleanup, antes das asserções
que rejeitam a observação incompleta. Anota somente conexão aceita, EOF, conclusão,
contagem limitada de bytes e código de erro permitido. As asserções e o exit 1
continuam ativos. O negativo percorre oito tentativas independentes; não há retry
que transforme uma falha em sucesso. Passaram sete testes de anotação e 17 de
egress, incluindo JSON inválido e campos privados no caminho de falha. Este
complemento não altera fontes do produto. O CI seguinte, em `f3e091d`, confirmou
`ConnectionResetError` antes de EOF nos dois Windows. A correção do encerramento
está no [relatório específico](2026-10-08-guard-cooperative-close.md).

Nenhum Docker, sbx, cliente autenticado ou modelo foi executado. Contador nativo
2/3, perfis bloqueados e `proof_accepted=false` preservados. Contratos externos do
sbx 0.46.0 e a evidência nativa original de B continuam pendentes.

## English overview

Mission status now uses nine Git processes instead of fifteen by sharing adjacent
SQL queries. It reopens storage after input files and preserves the independent
final client-run read. Six regressions cover cost, read-only behavior, private
storage changes, concurrent revisions, and database removal/replacement.

The egress refusal fixture observes upstream bytes from the controller, outside
the terminated helper. The negative case offers 13 bytes and requires zero received
through EOF; the positive control requires 13 bytes. Both require collection after
guard shutdown. Native acceptance and the historical Windows failure cause remain
unproven. CI at `b106bc5` passed seven of eight jobs: PR Windows passed, while push
Windows failed the destination refusal test. Both v3/v4 flows passed. The follow-up
emits selected observation fields before the unchanged failing assertions and
exercises eight independent refusals. Seven annotation tests and 17 egress tests
passed locally. Follow-up CI at `f3e091d` confirmed a reset before EOF on both
Windows runs. See the [shutdown fix](2026-10-08-guard-cooperative-close.md#english-overview).

ATRASO: implementação local 0 | CI verde 1 | executor nativo: validação pendente.
