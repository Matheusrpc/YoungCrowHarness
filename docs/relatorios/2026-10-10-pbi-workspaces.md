# Preparo e liberação de diretórios Git por PBI

Frente: YC-205 parcial. Base: `1cb1fb285b4bb6e69449c6ed9103a2cd8453b7c1`.

O operador pode pedir `workspace prepare`, consultar o registro salvo e liberar um
worktree próprio. A preparação fixa missão/PBI e suas revisões, commit base completo,
branch e caminho. Alterações staged, unstaged e arquivos novos do checkout original
permanecem intactos. O diretório novo contém os arquivos versionados da base.

A implementação admite até três reservas de workspace e uma por PBI. Esse teto é do
preparo de diretórios; não representa o consumo de `max_active_pbis` ou de slots de
agente. A futura admissão em desenvolvimento/QA precisa aplicar seus próprios limites.

## Recuperação e preservação

O banco privado salva a intenção antes das mutações Git. Uma transação de referências
cria a branch e um marcador opaco de propriedade. A operação usa o supervisor existente,
com identidade do processo persistida antes de liberar seu comando. Retry exige que o
processo anterior tenha encerrado. Nenhum lock nativo é removido automaticamente.

A retomada confere diretório, metadados administrativos, branch, marcador e checkout
completo. Um pedido admitido conserva seu contrato congelado após revisões da missão;
um novo pedido exige preparação atual. O replay concluído devolve o recibo histórico,
mesmo depois da liberação, sem recriar o diretório. Status consulta apenas estado salvo.

Release recusa conteúdo staged/unstaged, não rastreado e ignorado, flags de índice que
ocultem mudanças, HEAD destacado, branch trocada e identidade substituída. Usa remoção
Git sem força, mantém branch/commits e registra o último commit observado. O operador
precisa encerrar outros escritores: o lock do harness não exclui clientes Git externos.
Não há garantia de comparação e remoção globalmente atômicas contra esses clientes.

Queda entre criar a pasta vazia e salvar sua identidade fica ambígua. Checkout parcial,
locks remanescentes e recursos substituídos exigem diagnóstico, preservando os arquivos.
Não há adoção automática de pasta/branch alheias nem limpeza por `reset`, `clean` ou `prune`.

O perfil recusa metadados redirecionados, submódulos, clones shallow/partial, checkout
sparse, includes e filtros externos. Hooks, fsmonitor, lazy fetch e manutenção automática
são desativados nos comandos Git. Destinos de objetos, refs, reflogs e worktrees passam
por verificação de caminhos. O preparo usa `.runtime/workspaces/`, ignorado pelo setup.

## Provas e revisão

- Nove testes iniciais falharam pela ausência do módulo antes da implementação.
- Bateria final de workspace: 20 testes aprovados em 21,493 s, com Git real em projetos
  descartáveis. Inclui concorrência de dois processos, replay, perdas de ACK após criação
  de refs/worktree e remoção, base inválida, recurso alheio, substituição, conteúdo sujo,
  alterações ocultas por flags do índice, hooks, filtros, links e revisão posterior da missão.
- CLI instalado em modo trial para ambos os clientes: preparo, trabalho com commit real,
  liberação, replay histórico e preservação do checkout original passaram. O worktree ativo
  bloqueou o retorno; após release, o preview foi aceito e branch/commit continuaram presentes.
  A restauração genérica não foi ampliada. Retorno completo ao baseline reverte também as
  branches posteriores; esse efeito continua dependendo da aprovação específica do retorno.
- Fila criada pelo código anterior `1cb1fb2` no esquema 5 foi lida, migrada e avançada pelo
  CLI instalado após o preparo do workspace. Recibo anterior preservado. Leitor antigo
  recusou esquema 6. Helpers ausente/incompleto recusados sem escrita; status permaneceu
  somente leitura. Estados reais de desenvolvimento/QA/produção não avançaram.
- Revisão independente encontrou três problemas: referência simbólica podia redirecionar
  a criação, mudança de missão impedia retomar intenção pendente e metadados Git internos
  podiam redirecionar uma escrita. Todos corrigidos. Reproduções independentes confirmaram
  recusa de links em objects/fanout antes do Git, preservando o destino externo.
- Revisão das skills mostrou falta de orientação para workspaces; após atualização, os
  cenários prepare/status/release, recuperação após revisão e retorno trial ficaram cobertos.
  Corrigidos link não distribuído, divergência PT/EN sobre schema e descrição de configuração.

A suíte ampla executou 724 testes em 428,775 s: 704 aprovados, 20 pulados por requisitos
de plataforma/ambiente, zero falhas. Sua coleta antecedeu o último guard de compatibilidade:
o helper antigo de fila também declarava versão 3, mas ocultava sessões ao receber schema 6.
O novo marcador de esquema recusa essa mistura. A regressão falhou antes da correção e
passou depois. O pacote instalado confirmou recusa do helper real antigo em status/step,
preservando o projeto. Os 96 testes de missão/fila/catálogo passaram em 46,652 s após
esse ajuste final, além dos 20 testes de workspace. Navegação: 534 caminhos locais
conferidos, zero ausentes; vault: 61 notas, zero problemas.

A [medição estruturada](../medicoes/2026-10-10-pbi-workspaces.json) registra a conclusão da
suíte completa e os hashes do código. [Comandos e limites](../USAGE.md#pbi-workspaces).

## Distribuição e limites da entrega

SQLite passa a esquema 6 na primeira reserva aceita. Leituras e replay concluído não
migram; fila e diagnósticos continuam legíveis, e escritores antigos são recusados.
Atualizar os cinco helpers indicados no guia, catálogo e instruções. O instalador conserva
arquivos existentes para comparação, inclusive o novo helper, mesmo com `--force`.

Cinco contratos do catálogo mudaram com a inclusão do helper, além dos dez hashes de
conteúdo. `yc-missao` declara o escopo Git solicitado; `yc-status` conserva escrita vazia.
As permissões de rede, credenciais e entradas nativas não foram ampliadas. A atualização
do catálogo não prova execução ou autorização efetiva de um cliente nativo.

A fila fixture não chama estes comandos. YC-205 continua parcial até sua conexão com
execução real. Agentes, QA independente, integração, publicação e aceite nativo continuam
pendentes. Zero chamadas de modelo ou novas tentativas Docker; contador nativo permanece 2/3.
A base passou nos oito checks de CI; conferir separadamente o CI do novo commit.

## English overview

Explicit local PBI workspace preparation now pins mission/PBI revisions, a full base
commit, an owned branch and directory. Original checkout changes are preserved. The
existing process supervisor records ownership before Git mutations. Interrupted requests
resume their frozen intent only when ownership and a complete checkout can be verified.
Completed replay returns the original receipt without recreating released resources.

Release requires a clean owned worktree and retains its branch/commits. External writers
must be stopped; the coordinator does not provide a global atomic deletion guarantee.
Ambiguous creation, partial checkout or changed resources remain preserved for diagnosis.
Active worktrees still block trial return preview; releasing clean owned worktrees allows
preview again. A full baseline restore is a separate action that also reverts later branches.

The installed CLI passed this lifecycle with real Git and preserved a queue created by the
previous schema-5 implementation. Schema 6 retains queue/diagnostic history and rejects old
readers. Five capability contracts changed; status remains read-only and no network or
credential permission was expanded. These are workspace operations only: real agents,
integration and native executor acceptance remain pending.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
