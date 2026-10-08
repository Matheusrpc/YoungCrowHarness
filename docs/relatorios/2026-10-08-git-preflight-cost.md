# Custo das verificações Git no executor

Frente: estabilidade de YC-203 no Windows, PR #24. Data: 8 de outubro de 2026.

Os recibos de `63bb229` mostram dois timeouts no fim de A2. A e B completaram
em todos os quatro percursos positivos. A coleta mede eventos persistidos, com
tempos relativos ao início do supervisor; os payloads ficam privados.

| Execução | Percurso | Resultado | Último evento relevante |
|---|---|---|---|
| [Push 37722718954](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37722718954) | v3 | timeout em 15,000 s | A2 observada em 14,904 s; faltam fechamento e coleta do guard |
| Mesmo push | v4 | completo em 14,891 s | 30 eventos de fase, 21 de rede, recuperação aprovada |
| [PR 37722722963](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37722722963) | v3 | completo em 14,781 s | 30 eventos de fase, 21 de rede, recuperação aprovada |
| Mesmo PR | v4 | timeout em 15,015 s | A2 autorizada em 14,726 s; destino do guard observado em 14,952 s |

A folga dos casos aprovados foi de 109 a 219 ms. Os eventos continuam avançando até
o teto; não há evidência de uma trava permanente. Os timestamps precedem a gravação
no registry, por isso os intervalos incluem persistência e trabalho intermediário.
Eles não isolam o tempo de Git nem do socket.

## Alteração e limites

`verify_private_storage` executava três processos `git check-ignore` por chamada,
além de `rev-parse` e `ls-files`. Agora consulta os três probes juntos e exige que
todos apareçam na resposta. Código zero sozinho seria insuficiente: o Git também
retorna zero quando apenas um caminho corresponde a uma regra.

As verificações de caminho, arquivos rastreados e repositório permanecem. Cada
chamada consulta o estado atual; não há cache. O ramo sem repositório continua
verificando as regras locais. O setup e a escrita de arquivos não mudaram.
Supervisor de 15 s, plano de 30 s, asserts e provas nativas foram preservados.

## Medição e regressões

Quinze verificações consecutivas, somente leitura, no checkout Linux:

| Medida | Antes | Depois |
|---|---|---|
| Processos Git por verificação | 5 | 3 |
| Processos nas 15 verificações | 75 | 45 |
| Mediana por verificação | 7,530 ms | 4,828 ms |

A redução de processos foi medida com chamadas reais ao Git. Os tempos Linux
não predizem o ganho Windows. O teste de limite de processos falhou antes da
alteração (`5 > 3`) e passou depois. A bateria de armazenamento executou 12 testes:
11 aprovados e uma junction Windows pulada. Cobre regra removida em cada posição,
nenhum caminho ignorado, arquivo privado rastreado, erro Git, repositório pai e
inicialização posterior do Git. A mudança das regras entre chamadas foi recusada
sem reparo ou escrita. Os cinco testes focais de rede/encerramento passaram em 6,445 s.

Revisão independente de segurança sem bloqueadores. A confirmação da suíte pública
completa executou 622 testes: 602 aprovados e 20 pulados em 240,982 s.
O CI Windows ainda precisa comprovar a conclusão dentro dos mesmos
limites; reduzir chamadas não basta para declarar o timeout resolvido.

A primeira suíte completa executou 622 testes, com 7 falhas causadas pelos hashes
antigos do helper no catálogo. Falharam o teste de contrato de missão e três
seleções de cliente em cada um dos dois testes de instalação/auditoria. O catálogo
agora registra os 18 hashes de arquivos correspondentes às nove capacidades
afetadas; contratos e permissões permanecem iguais. O revisor conferiu cada hash.
Os 23 testes de capacidades passaram; a suíte completa foi repetida com essa
correção de empacotamento. O log anterior e seus sete resultados ficam na medição.

A primeira repetição após o catálogo teve uma falha em `test_two_writers_one_digest`:
o perdedor retornou `execution_storage_unprotected`, em vez de conflito/ocupado.
A comparação de 30 execuções reproduziu essa falha e um erro de saída vazia no
baseline publicado `63bb229`; as 30 execuções com o código atual passaram. A seleção
usa outro caminho Git e suas funções não mudaram. A hipótese é uma varredura anterior
ao lock encontrar um temporário que o outro escritor renomeou; o ponto exato ainda
não foi identificado no log original. O teste mantém os mesmos critérios. Essa corrida preexistente fica
registrada como pendência. A confirmação completa passou sem mudanças no candidato;
essa rodada verde não demonstra que a corrida foi corrigida. A auditoria de capacidades
retornou saída zero, 20 observações correspondentes e 30 não verificadas.

Uma reprodução controlada, no baseline e no candidato, publicou a seleção entre a
enumeração e a inspeção do temporário. O `os.replace` real provocou `FileNotFoundError`
em `adoption_fs.inspect_permissions:288`, normalizado como `existing_storage /
inspection_failed`. Os bytes da seleção foram preservados. Isso demonstra um mecanismo
compatível com a falha, sem atribuir a ele a ocorrência aleatória nem o erro de saída
vazia. Não é teste entre dois processos nem correção. Script/recibos privados têm hashes
na medição e foram revisados de forma independente.

## Publicação e continuidade

Destino autorizado: `feat/isolated-executor`, [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
Código publicado em `25ee51d`; branch e ref do PR conferidas, main preservada.
Os cinco focais Windows passaram nos runs [push 37724707270](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37724707270)
e [PR 37724712042](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37724712042).
Ambas as etapas duraram 42 s. Às 00:57 de 8/out (America/Sao_Paulo), os seis jobs
Linux estavam aprovados; os dois Windows seguiam em armazenamento/recuperação.
Os jobs Windows completos ainda estavam em andamento na consulta;
esses tempos de etapa não substituem os tempos individuais de A/B/A2, ainda indisponíveis.
Próximo: consultar esses mesmos runs antes de abrir outra rodada. Se houver falha, usar
o ledger para localizar o trecho restante, sem aumentar o prazo. Retorno: reverter
este incremento restaura as três consultas individuais, preservando armazenamento
e recibos. Nenhum arquivo privado, credencial ou HTML bruto entra no Git.

As dependências nativas continuam: contrato local de credenciais/settings do sbx
0.46.0 e transferência das fontes/evidências originais de B. Nenhum Docker, sbx,
login ou modelo foi executado; permanecem 2/3 ciclos, com perfis bloqueados.

## English overview

Windows timelines at `63bb229` located the timeouts near A2 completion, with successful
sibling cases finishing only 109 to 219 ms below the 15-second limit. Private-storage
preflight now batches three Git ignore probes into one invocation and requires all
three paths in the response. Path, tracked-file and repository checks stay in place;
every call observes current rules without caching. Real local measurements confirm
five Git processes reduced to three per check. Security regressions and all five
focused local network/cleanup tests passed. The full local confirmation passed
602 tests with 20 skips. A preexisting intermittent concurrent-selection failure was
also reproduced on the published baseline and remains open. Both Windows focused steps passed at `25ee51d`; the full push and PR jobs remain pending. No native execution or deadline increase was performed.

ATRASO: PR #24 código publicado | CI completo Windows e aceite nativo pendentes.
