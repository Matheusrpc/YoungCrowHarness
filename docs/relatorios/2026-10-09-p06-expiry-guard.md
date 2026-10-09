# Recusa de credencial vencida no piloto Claude

Frente: admissão do teste P06. Base: `681035e`.

Os metadados enviados pelo operador mostram que o arquivo de login foi atualizado
pela manhã e venceu antes do teste. Horários de 9/out em America/Sao_Paulo:

| Evento | Horário |
|---|---|
| Arquivo de credenciais atualizado | 09h51min56s |
| Validade informada em `expiresAt` | 17h51min56s |
| Início do preparo Haiku | 17h52min16s |
| Início da execução Haiku | 17h52min21s |

O preparo começou 19,936753 s após o vencimento; a execução, 25,441313 s depois.
Havia refresh token no arquivo, sem overrides de token/chave nem proxy nos campos
de ambiente consultados. Isso não prova validade do refresh token nem ausência de
outras configurações de rede. A causa de sua rejeição pelo fornecedor permanece
desconhecida. A falha de admissão do runner foi comprovada: ele aceitava o preparo
e reservava a tentativa mesmo com `expiresAt` já vencido.

## Correção

O runner agora exige `expiresAt` inteiro, em milissegundos Unix, com mais de
360 segundos de validade pelo relógio local. Esse prazo cobre os 300 segundos
do ensaio com uma margem de 60 segundos. A checagem ocorre antes de criar o pacote
no preparo e antes de reservar uma execução. A cópia temporária é conferida
novamente antes de liberar o processo do cliente.

Metadados ausentes, inválidos ou insuficientes interrompem o fluxo com um motivo
fixo, sem imprimir tokens ou o conteúdo do arquivo. A correção não renova o login,
não muda o modelo nem acrescenta chamadas ao fornecedor.

Uma recusa na checagem anterior à reserva não cria `started.json`. Se houver
mudança na cópia depois de reservar, o cliente continua bloqueado e o marcador
permanece. Nenhum marcador consumido é removido, inclusive os das tentativas
anteriores. Pacotes antigos mantêm seus arquivos e hashes; não recebem edição
manual nem troca do runner preparado.

Esta é uma checagem de validade declarada. Ela não comprova que o fornecedor
aceitará o token, não impede revogação externa nem corrige a renovação OAuth.

## Verificação

Os quatro novos testes falharam antes da correção, com dez falhas contando os
subcasos. A suíte focada passou depois: 17 testes em 3,338 s. Ela cobre vencimento,
margem insuficiente, limite exato, metadados inválidos, recusa da cópia alterada e
expiração entre preparo e execução. Credenciais são fictícias; o cliente nativo
não foi chamado. Os testes conferem a ausência de pacote/reserva nos caminhos
recusados antes desses efeitos e a preservação da credencial original.

A suíte completa terminou: 668 testes, 648 aprovados e 20 pulados, sem falhas, em
324,553 s. Contagens e hashes estão na
[medição](../medicoes/2026-10-09-p06-expiry-guard.json).

## Confirmação no Windows

O operador enviou a saída da revisão `47a8150`: os 17 testes passaram em 12,776 s.
Após concluir `claude auth login`, preparou o pacote separado com
`--model claude-haiku-5-5`. O preparo terminou em 4,968794 s, às 22h13min18s UTC,
com estado `prepared_no_model_prompt`, zero prompts, saída 0, árvore encerrada,
cópia temporária removida e bytes da credencial original preservados.

A operação é `164e5438-0cac-4089-845c-f1e3cc60db04`; o SHA-256 de `setup.json` é
`45ec8706433bbe3866c17d79d963df7e3617eaaf224ca15f4c27a24e87ea8ac4`.
São evidências relatadas pelo operador. O preparo passou pelas checagens locais de
validade e autenticação, mas não realizou inferência nem comprova refresh OAuth.

No CI, o [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37996841986)
teve três jobs aprovados e falha em `adoption-windows`, na etapa de diagnóstico de
rede, seleção e limpeza, antes de P06. A anotação identifica
`test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`.
O [run do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37996847736)
ainda estava em andamento na consulta. Não há alegação de CI integralmente verde.

## Próximo passo

O pacote está preparado para revisão: uma sessão, um prompt, até 300 segundos e
24 ferramentas, esforço `medium`, Haiku explícito, assinatura existente e nenhuma
API adicional. A operação acima ainda não tem autorização para inferência. As duas
tentativas anteriores consumiram suas reservas; preservar seus recibos e marcadores.
Após aprovação, executar somente este pacote e revisar o resultado de memória.

## English overview

The reported credential expired about 20 seconds before preparation and 25 seconds
before the Haiku run. The pilot now requires an integer expiry more than 360 seconds
ahead, before creating a preparation package or reserving a run. It rechecks the
actual temporary copy before releasing the client. Four new regression methods
failed before the fix; all 17 focused tests now pass without native model calls.
Existing reservations remain intact. This prevents admitting a locally expired
credential; it does not fix OAuth refresh or prove provider acceptance. The full
suite finished with 648 passed and 20 skipped tests, without failures. The operator
subsequently reported all 17 Windows tests passing in 12.776 seconds on `47a8150`.
After interactive login, preparation completed in 4.968794 seconds with zero
prompts and confirmed cleanup. The new operation awaits approval for inference.
The push CI failed in an earlier Windows cleanup test; its P06 step was skipped.
The PR run was still in progress when checked.

ATRASO: aprovação da nova sessão e aceite Claude pendentes | CI Windows pendente.
