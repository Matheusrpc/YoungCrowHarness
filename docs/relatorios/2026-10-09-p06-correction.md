# Ensaio Claude com admissão preventiva de ferramentas

Frente: correção delimitada do lote A de P06. Base: `91be370`.

O ensaio histórico verificava o orçamento depois dos eventos e aceitava somente
resultados Codex. `tests/pilot_claude.py` prepara um consumidor novo, reserva uma
única tentativa e verifica os artefatos Claude. O código fica nas ferramentas de
teste; o instalador e os perfis bloqueados do executor permanecem com seus contratos.

`PreToolUse` admite até 24 ferramentas, uma a uma, antes de responder ao cliente.
Recusa a próxima solicitação e encerra o processo. Somente leituras no consumidor
e hashes sobre caminhos literais fotografados são permitidos. O controlador roda
dentro de `mission_process.supervise`, que já contém a árvore, impõe o prazo e
confere encerramento. O supervisor compartilhado não precisou mudar.

O marcador exclusivo precede os efeitos. O pacote vincula código, helper ACL do
Windows, executável, modelo/esforço e contexto; alterar o preparo impede a execução.
Falhas de autenticação ou limpeza não provocam repetição. A cópia temporária da
credencial tem limpeza protegida desde a cópia, e a saída recebida fica preservada
antes do parsing ou da conferência final de autenticação. Encerramento abrupto do
processo principal ainda exige reconciliar arquivos próprios e o marcador.

O verificador exige sucesso Claude, uma sessão, um prompt, reconciliação das
ferramentas, conteúdo lido, hashes retornados e arquivos preservados. Os marcadores
texto/binário do `sha256sum` são aceitos. O handoff precisa citar a operação atual
e a última retomada, além da feature, decisão e implementação. O estado automático
é `evidence_verified_pending_semantic_review`: interpretação das notas e aceite
nativo continuam exigindo revisão, sem transformar campos preenchidos em prova.

## Verificação e revisão

Treze regressões cobrem recusa da 25ª ferramenta, caminhos e comandos inválidos,
alteração de arquivo, replay, falha na cópia da credencial, autenticação indisponível,
timeout, resposta incompleta, hashes e integridade do pacote. O cliente fictício
conversa por subprocessos usando o protocolo; não importa nem chama Claude.
O CI Windows ganhou uma etapa para essas mesmas provas sem modelo.

Os testes foram escritos antes dos trechos correspondentes e falharam pelos
comportamentos ausentes. A revisão independente identificou e corrigiu transporte
de texto Windows, configurações ancestrais, preservação de falhas, retorno dos hashes
e cobertura dos arquivos executáveis no manifesto. Não se acrescentou dependência.

Uma primeira suíte coincidiu com alterações do fixture e não serve como verificação
final. Ela também registrou falha em
`test_deadline_reaps_descendants_in_the_existing_supervisor`, por ausência de
`helper.pid`; o caso passou isoladamente sem mudança de código ou prazo.
Não se atribui uma causa final a esse resultado intermitente. A rodada final usa
os fontes congelados; contagens, duração e hashes estão na
[medição](../medicoes/2026-10-09-p06-correction.json).

O protocolo foi conferido no SDK oficial que embarca CLI 2.1.220, revisão
`cadaa636a221f14e587a2e21a9b9532ce60adba3`. Fontes e comandos no
[guia P06](../P06-CLAUDE.md). O argumento `--setting-sources=` reproduz o SDK
para desativar configurações de filesystem e carregamento de CLAUDE.md; as três
skills são lidas explicitamente. Isso não comprova descoberta automática de toda
a instalação nem isolamento geral de filesystem/rede.

## Próxima ação

No Windows, executar somente `prepare` pelo guia. Confirmar versão, assinatura,
inicialização e limpeza sem enviar prompt ao modelo. A tentativa `run` continua
reservada para 10/out às 18h30 em America/Sao_Paulo, dentro da aprovação existente.
Nenhum cliente nativo foi iniciado nesta cloud. Não houve agendamento automático,
repetição Codex, novo ciclo Docker ou alteração da main.

## English overview

The P06 test runner now gates tools before execution, reuses the existing process
supervisor, preserves one-attempt receipts and verifies Claude evidence. Thirteen
local regression cases exercise a subprocess protocol fixture without model calls.
Successful integrity verification still requires semantic review. Windows preparation
and the approved native session remain pending; this does not enable Docker profiles.

ATRASO: correção local verificada | preparação Windows pendente | aceite Claude pendente.
