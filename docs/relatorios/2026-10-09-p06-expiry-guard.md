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
324,553 s. A nova revisão ainda exige confirmação Windows;
o sucesso anterior de `6481a91` não valida código posterior. Contagens e hashes
estão na [medição](../medicoes/2026-10-09-p06-expiry-guard.json).

## Próximo passo

Renovar o login no perfil do operador e conferir os metadados sem expor tokens.
Preparar um pacote novo com a revisão corrigida e Haiku explícito, sem prompt;
preservar todos os recibos anteriores. Uma nova inferência exige aprovação da
operação concreta, porque as duas tentativas registradas consumiram suas reservas.

## English overview

The reported credential expired about 20 seconds before preparation and 25 seconds
before the Haiku run. The pilot now requires an integer expiry more than 360 seconds
ahead, before creating a preparation package or reserving a run. It rechecks the
actual temporary copy before releasing the client. Four new regression methods
failed before the fix; all 17 focused tests now pass without native model calls.
Existing reservations remain intact. This prevents admitting a locally expired
credential; it does not fix OAuth refresh or prove provider acceptance. The full
suite finished with 648 passed and 20 skipped tests, without failures. New Windows
verification remains pending.

ATRASO: confirmação Windows da nova revisão | aceite Claude pendente.
