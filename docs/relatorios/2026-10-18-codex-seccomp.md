# Edição e patch do Codex no worker OCI

Frente: YC-203, compatibilidade do sandbox do Codex com o worker sem privilégios.

O Codex oficial 0.159.2 executou `exec_command` e `apply_patch` no worker, com três
respostas determinísticas de um servidor em loopback. O checker validou a correção
de `clamp.py`; `probe.txt` recebeu o patch esperado. O original permaneceu intacto,
a pasta do host ficou vazia e os processos e o container foram encerrados.
Nenhuma conta ou modelo foi chamado. A qualificação por assinatura continua fechada.

## Causa e alteração

No mesmo kernel, `unshare(CLONE_NEWUSER)` passou no controle e recebeu `EPERM` no
worker. Ambos reportaram o perfil LSM `kernel`; o Docker 28.4.0 não anunciou AppArmor.
Ao acrescentar apenas a permissão desse argumento ao perfil seccomp padrão, a mesma
chamada passou no worker, mantendo `no-new-privileges`, `cap-drop=ALL` e rede `none`.
Isso identifica o filtro seccomp como a causa reproduzida neste ambiente.

O perfil distribuído em `runtime/worker/seccomp-bwrap.json` preserva todas as regras do
[padrão Moby v28.4.0](https://github.com/moby/moby/blob/v28.4.0/vendor/github.com/moby/profiles/seccomp/default.json).
Essa base usa `moby/profiles/seccomp v0.1.0`, sob Apache-2.0; a licença acompanha o
arquivo. SHA-256 da base original:
`01536f1d1df938ae611eba20d6349e0de7a99b6ecdee1549427a0b01b8301e28`.
As 12 regras acrescentadas atendem o bubblewrap incorporado ao
[Codex fixado](https://github.com/openai/codex/tree/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/vendor/bubblewrap):

| Chamada | Restrição acrescentada |
|---|---|
| `clone` | Flags exatas `0x78020011`: user, mount, PID, IPC, network e SIGCHLD |
| `unshare` | Somente `CLONE_NEWUSER` |
| `umount2` | Somente `MNT_DETACH` |
| `pivot_root` | Permitido; seus argumentos são ponteiros para caminhos |
| `mount` | Sete valores exatos e uma máscara para os flags de bind/remount usados pelo bwrap |

As regras adicionais selecionam a arquitetura amd64 do daemon; preservam os ABIs
compatíveis do perfil Moby. A máscara de remount exige bind, remount, silent e nosuid;
só aceita variações de readonly, nodev, noexec, noatime, nodiratime e relatime.
`setns` continua bloqueado sem a capability externa, e `clone3` conserva `ENOSYS`.
O perfil não adiciona capabilities ao container. O Codex conserva `workspace-write`
e `include_local=false`.

O driver confere o SHA-256 do perfil antes de criar o container e compara o JSON
retornado pelo Docker antes de iniciá-lo. Política ausente, substituída ou acompanhada
de opções extras é recusada. A cada inspeção, o driver também verifica se o restante
da configuração permanece igual.
O instalador e o catálogo distribuem perfil e licença; atualizações preservam arquivos
adaptados, portanto driver e perfil precisam ser revisados juntos no consumidor.

## Limites medidos

Criar user namespaces amplia a superfície do kernel disponível ao processo. O seccomp
clássico não limita as strings apontadas por `mount` e `pivot_root`; os argumentos
numéricos, os privilégios por namespace e a fronteira OCI complementam essa política.
O aceite vale para o ambiente medido. Um host com AppArmor ou outra política LSM pode
recusar a execução, sem que o harness desligue a proteção para contornar a recusa.

O teste adversarial mapeou UID 0 interno para UID 1000 do worker e depois criou os
namespaces filhos permitidos. Ele confirmou:

- Snapshot, imagem, `/control`, `/root` e os caminhos privados do guardião em `/proc`
  permaneceram protegidos. O processo não conseguiu sinalizar o guardião;
  `setuid(2000)` retornou `EINVAL`, pois esse UID não estava mapeado.
- `setns`, `unshare` de mount isolado e montagem no namespace pai foram recusados.
  A tentativa de tornar a raiz herdada gravável também falhou.
- A rede externa e um listener do namespace pai ficaram inacessíveis. O limite de
  128 processos continuou efetivo, inclusive após a criação do namespace filho.
- Um tmpfs novo comportou 80 MiB. Os 64 MiB limitam o volume original, não todo o
  armazenamento temporário. O teste também confirmou `memory.max=1073741824`,
  equivalente ao teto configurado de 1 GiB.
- Após matar o controlador, o prazo do guardião encerrou o worker e um descendente
  real do bwrap. Não restaram processos do worker. O checker recusou um recibo forjado.

## Validação e continuidade

Os comandos e resultados finais estão na
[medição desta frente](../medicoes/2026-10-18-codex-seccomp.json).
O teste de inspeção foi observado falhando antes da correção: aceitava ausência de
seccomp, `seccomp=unconfined` e uma opção extra de AppArmor. Após a alteração, esses
casos são recusados, assim como política trocada e arquivo com hash divergente.

A suíte geral executou 825 testes em 357,950 segundos, com 21 skips e cinco falhas
nos hashes de catálogo e nas auditorias de instalação dos três perfis de cliente.
Os hashes esperados de cinco contratos foram atualizados para os arquivos entregues.
A repetição completa dos testes de catálogo e do teste de instalação afetado passou
em 24 testes; todos os casos que falharam passaram nessa rodada. A suíte geral inteira
não foi repetida após essa correção de metadados. A rodada final do núcleo, perfis e
recibos passou em 52 testes. A sintaxe Bash e a verificação de whitespace passaram.
A consulta final encontrou zero containers YoungCrow remanescentes.

A revisão independente levantou a diferença entre cota do volume e memória agregada;
a prova de tmpfs adicional e o guia incorporam essa distinção. A redação PT foi
revisada com `humanizer-ptbr`, e README e guia mantêm instruções PT/EN.

Permanecem pendentes a observação nativa do modelo/esforço aplicado, os catálogos
`code_mode_only`, as rotas tardias do Claude e os aceites por assinatura. `QUALIFIED`
continua vazio, e a fila não despacha agentes reais. Este resultado conclui a passagem
local de edição e patch; não transforma a fixture de clamp em executor geral de QA.

English: official Codex editing and patching passed in the OCI worker using local,
fixed responses. A pinned Moby-derived seccomp profile permits the required nested
namespaces without adding outer capabilities or network. Native adversarial checks
cover protected files, guardian access, networking, PID limits and crash cleanup.
Nested tmpfs can exceed the workspace volume; aggregate memory remains capped at
1 GiB. Subscription qualification, model/effort observation and other client routes
remain pending.

ATRASO: produção não configurada; publicação limitada à branch e ao PR de desenvolvimento.
