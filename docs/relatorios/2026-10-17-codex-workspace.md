# Retomada do executor e workspace do Codex

Frente: YC-203, recuperação do trabalho e compatibilidade do workspace OCI.
Rodada de 17/out/2026 no horário de São Paulo, 18/out em UTC.

O worker usa um diretório real no caminho esperado pelo Codex. O ensaio de edição
com o cliente oficial passou da recusa do symlink, mas ainda falha ao criar os
namespaces internos do sandbox. `QUALIFIED` continua vazio; a execução por assinatura
e a fila de agentes reais não foram liberadas.

## Recuperação

O ambiente retomou na branch `work`, em `f8f14f5`, sem o commit local `f55155d`
nem as alterações da sessão anterior. Esse commit não estava no remoto e não foi
encontrado entre os objetos recuperáveis do Git. A branch existente
`feat/isolated-executor`, em `ca37910`, permaneceu disponível.

Os diffs preservados no histórico disponível permitiram recuperar o núcleo OCI, os perfis,
o coordenador, a correção do contexto do piloto e a supervisão por namespace.
Antes de qualquer ajuste novo, seis arquivos do supervisor e de seus testes
coincidiram com os hashes registrados na sessão anterior. Os 47 testes de worker,
perfis e recibos passaram nessa cópia recuperada.

A recuperação é parcial: não reconstitui todas as alterações locais anteriores.
O plano detalhado foi truncado no histórico disponível; os JSONs das medições antigas
também não foram recuperados. Os relatórios antigos receberam essa ressalva.
Os resultados desta rodada são novas provas, vinculadas aos arquivos atuais.

Um teste de instalação encontrou uma regra que os diffs do working tree não
recuperaram: `--force` sobrescrevia os novos helpers OCI já adaptados pelo usuário.
A reprodução em projeto descartável falhou antes da correção. A regra de preservação
foi restaurada para os quatro scripts e `runtime/worker/*`, como previa a alteração
registrada no índice Git da sessão anterior. A prova de atualização foi repetida.

## Correção e evidência nativa

O CLI `codex exec` 0.159.2 aplica o mesmo cwd ao controle e ao ambiente remoto.
O `cwd` de `environments.toml` define o diretório do processo de transporte no host;
não fornece uma raiz remota independente. A fonte foi conferida no commit oficial
[`ff6aec96948b70d94983af2641a6b67c94faeff5`](https://github.com/openai/codex/tree/ff6aec96948b70d94983af2641a6b67c94faeff5),
em `exec/src/lib.rs`, `core/src/environment_selection.rs` e
`exec-server/src/environment_toml.rs`, sob `codex-rs`.

O worker agora monta um tmpfs de 64 MiB em `/tmp/youngcrow-UUID/cwd` e usa esse
caminho como `HOME`. Importação, exportação, MCP e exec-server usam o diretório real.
O host conserva uma pasta privada separada. O ancestral no worker pertence ao root
e não permite escrita pelo UID 1000. O teste distingue esse mount do `/tmp` de
16 MiB e exerce sua capacidade. O checker continua em `/snapshot`, como UID 2000.

A imagem também inclui o `codex-resources/bwrap` do pacote oficial. O build verifica
seu SHA-256 antes e depois da cópia. O Codex mantém sua própria verificação do recurso.
Nenhuma capability, rede, bind mount ou exceção de seccomp foi adicionada;
`sandbox_mode=workspace-write` e `include_local=false` permanecem configurados.

| Ensaio com respostas fixas locais | Resultado observado |
|---|---|
| Imagem recuperada | Recusa de `.git` porque o cwd atravessava um symlink gravável |
| Diretório real, imagem sem recurso adicional | Recusa porque `bwrap` estava ausente |
| Diretório real e `bwrap` oficial | `No permissions to create a new namespace` |
| Worker e MCP, sem cliente de modelo | Edição, limites, isolamento, snapshot e prazo após queda passaram |
| Codex exec-server por RPC | Leitura/escrita e coleta passaram; não prova o agente completo |
| Inicialização do Codex sob supervisão | Catálogo disponível, árvore encerrada e worker removido |

`tests/smoke_codex_workspace.py` exige execução de `exec_command` e `apply_patch`,
conteúdo final exato, original intacto e ausência de escrita no diretório do host.
O ensaio permanece reprovado neste ambiente e não emite um recibo de sucesso.
As respostas vêm de um servidor em loopback, com metadados embarcados de `gpt-5.5`;
não houve chamada de modelo, login ou uso de assinatura.

## Validação e próximo corte

A suíte geral executou 826 testes em 361,172 segundos: 806 passaram e 20 foram
ignorados por dependerem de outro ambiente. Não houve falhas ou erros. A rodada
focada passou em 50 testes, incluindo os três testes novos acrescentados após a
descoberta da suíte geral. Os dois testes de preservação do instalador também
passaram após a correção. Nenhum container desta frente permaneceu criado.

Comandos, hashes, resultados da suíte e observações nativas estão na
[medição desta retomada](../medicoes/2026-10-17-codex-workspace.json).
A revisão independente do delta não encontrou regressão concreta. A redação PT
foi revisada com `humanizer-ptbr`; o guia de uso mantém instruções PT/EN.

O próximo corte é qualificar a compatibilidade entre o sandbox nativo do Codex e
a fronteira OCI, antes de repetir a edição completa. O erro observado não identifica,
sozinho, qual camada de política negou a criação dos namespaces. Não há evidência
que justifique desligar o sandbox ou tornar o container privilegiado.
O Codex também recusa o fallback Landlock legado para execução com restrição de
filesystem: `linux-sandbox/src/linux_run_main.rs` exige bubblewrap para isolar os
sockets do app-server. Portanto, esse fallback não preserva o contrato atual.
Depois permanecem a observação nativa de modelo/esforço, as demais rotas expostas
e os dois aceites por assinatura. A seleção do produto não foi substituída.

English: the recovered worker now uses a real, bounded workspace and includes the
pinned official bwrap resource. Native worker, MCP, Codex RPC and supervised startup
checks passed. Full Codex editing still fails because namespace creation is denied
inside the container. Qualification remains closed; no model or account was used.

ATRASO: produção não configurada; sem deploy nesta frente.
