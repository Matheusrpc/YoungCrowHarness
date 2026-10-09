# Revisão do runner histórico de memória

Frente: preparação do lote A, retomada Claude do piloto público. Base: `e0ae21c`.

Os dois fontes históricos foram recebidos e lidos em 9/out. Eles recuperam o
procedimento anterior, mas não atendem ainda ao lote aprovado de uma sessão Claude,
300 segundos e 24 ferramentas. Não executar os originais nem apagar marcadores
do ensaio de 3/out. Nenhum cliente nativo foi iniciado nesta revisão.

## Achados que impedem a execução

| Fonte e linhas | Constatação | Correção necessária |
|---|---|---|
| `public-pilot-native.py`, 132 a 154 | Conta ferramentas por eventos já emitidos. Um `result` encerra a leitura antes da checagem de orçamento. Após detectar o limite, ainda aguarda até três segundos antes de fechar o Job Object | Limitar antes de admitir cada ferramenta; impor o prazo independentemente da leitura dos eventos; encerrar o job ao atingir o teto |
| `public-pilot-native.py`, 87, 132, 155 a 168 | Se o processo já terminou ao consultar `poll`, a contagem pode continuar em zero. O recibo usa `completed` mesmo sem validar sucesso do resultado | Reconciliar todos os eventos finais e distinguir sucesso, falha, limite e resultado ausente |
| `verify-pilot-native.py`, 9, 25, 31 e 37 | Lê resultado, eventos e recibo exclusivamente do Codex. Aceita até 305 segundos | Validar os artefatos da tentativa Claude, resultado de sucesso, leituras efetivas, UUIDs, hashes e tetos aprovados; preservar a prova histórica Codex |
| `public-pilot-native.py`, 16, 35 a 62, 72 a 76 | Usa diretório fixo do ensaio anterior e dependências locais da preparação de 3/out. O marcador exclusivo impede repetição da mesma tentativa | Preparar consumidor novo para o lote A, registrar revisão e identidade da tentativa antes da chamada; conservar os marcadores antigos |
| `public-pilot-native.py`, 91 a 93 e 159 a 167 | A cópia temporária da credencial e a leitura do hash acontecem antes do bloco de limpeza | Cobrir toda a etapa pelo encerramento garantido e verificar remoção, sem transportar credenciais para a cloud |

O Job Object existe no helper `scripts/documents.py`: associa o processo suspenso
antes de liberá-lo e configura encerramento dos descendentes ao fechar o job.
Esse recurso pode ser reutilizado; não resolve sozinho a admissão de ferramentas.
As permissões de leitura `Read,Glob,Grep` não restringem por si só o caminho ao
consumidor. O próximo pacote deve conferir também o escopo dos caminhos e os
comandos de hash permitidos. Instrução no prompt não comprova isolamento do host.

## Verificação realizada

Três sondas locais executaram somente as instruções de contagem e decisão extraídas
das linhas 143, 144 e 148, com eventos e relógio sintéticos. Os scripts completos
não foram importados nem executados; não houve credenciais, rede ou modelos.

| Entrada sintética | Resultado do trecho original |
|---|---|
| 25 eventos de ferramenta sem resultado final | `budget_limit`, já com 25 eventos observados |
| Os mesmos 25 eventos com resultado final | `completed`, com 25 eventos observados |
| Resultado final aos 301 segundos | `completed` |

Isso demonstra a ordem incorreta da checagem, sem afirmar que houve excesso numa
execução nativa anterior. A prova histórica Codex registrou sete chamadas e
189,994 segundos; esta auditoria não altera esse resultado. A tentativa histórica
Claude terminou com erro de OAuth e continua distinta da nova tentativa autorizada.

As identidades dos fontes e os resultados estão na
[medição da campanha](../medicoes/2026-10-09-test-campaign.json). Os arquivos originais
e as referências dos anexos permanecem privados. Revisão independente somente leitura:
`review_p06_sources`. Nenhuma suíte de produto repetida por esta alteração documental.

## Próxima ação

Corrigir apenas o ensaio P06 e seu verificador para a tentativa Claude do lote A.
Reutilizar o controle de processos existente, testar localmente a recusa da 25ª
ferramenta, timeout, replay, falha de autenticação e rejeição de resultados incompletos
antes da sessão nativa. A escolha de executável/modelo e a compatibilidade no Windows
ainda precisam ser conferidas. O login reportado pelo operador não prova inferência.

A aprovação do lote A permanece vigente, com o horário combinado de 10/out às
18h30 em America/Sao_Paulo. Os achados são pré-condições técnicas; não justificam
pedir a mesma aprovação novamente, repetir Codex ou aumentar os limites. Não há
execução ou lembrete automático agendado. O lote B mantém seus bloqueios próprios.

## English overview

The two historical P06 sources were recovered and reviewed. Event polling does not
enforce a preventive tool limit, terminal results bypass the budget check, and the
verifier reads only Codex artifacts. The old attempt and its receipts must remain
intact. Three synthetic branch probes confirmed the budget-check ordering issue;
no native client was launched and no historical overrun is claimed. Block A remains
approved, pending correction and Windows validation of the bounded Claude proof.

ATRASO: auditoria concluída | runner Claude por corrigir | prova nativa pendente.
