# Launcher e fronteira MCP

Frente: executor isolado, 2A-R1. Desenvolvimento local, sem publicação.

O launcher passou em três cenários sintéticos dentro da microVM: conclusão normal,
prazo de cinco segundos e perda do transporte. Duas provas adicionais no Windows
encerraram o coordenador e o transporte `sbx` durante o trabalho; o cliente terminou
antes do prazo e recusou novo início. O builder gerenciado falhou no startup;
o [checkpoint posterior](2026-10-04-native-kit-build.md) construiu e importou o pacote
com Buildx nativo. O consumo pelo resolvedor ainda não passou. Nenhum modelo foi chamado; R1 segue incompleto,
com R2/R3 pendentes e todos os perfis nativos bloqueados.

## O que mudou

`runtime/sbx/launcher.py` grava a intenção antes de criar o contêiner e consome o início
antes de retornar o comando de execução. Uma resposta de criação perdida conserva a
incerteza; repetir a operação não cria outro recurso. Antes do início, confere imagem,
identidade, manifesto, prazo e os controles efetivos retornados pelo Docker.

O contêiner interno usa imagem por digest, root filesystem somente leitura, rede `none`,
2 CPUs, 4 GiB, 64 processos, capabilities mínimas no guardian e nenhuma no cliente.
O único bind é o controle privado dentro da VM. Healthchecks, logs do Docker, publicação
de portas e reinício automático ficam desativados. A receita atual cobre provas sem rede.

A [decisão aprovada de MCP](../superpowers/specs/2026-10-04-mcp-boundary-decision.md)
permite o gateway externo somente se o cliente e seus descendentes não conseguirem
acessá-lo. Isso precisa ser provado também com a rede do fornecedor liberada. A presença
do gateway é registrada; o campo `mcp_isolation_unverified` mantém a recusa enquanto
essa prova estiver pendente. Um recibo ou perfil fornecido pelo chamador não habilita execução.

`client environment --sandbox NOME` observa a VM existente por `ls/inspect/ls`.
Confere nome, UUID, imagem e hash do executável sem usar `sbx exec`, que iniciaria uma VM
parada. A observação de parada não certifica que o workload interno foi recolhido.

## Provas

Ambiente: Windows 11 AMD64, `sbx` 0.46.0, microVM Linux, Python 3.14.4 e Docker Engine
29.8.1. A [medição](../medicoes/launcher-boundary.json) contém hashes, tempos e limites
do resultado. O [guardian anterior](2026-10-04-guardian-protocol.md) conserva sua prova própria.

| Cenário real | Resultado observado |
|---|---|
| Conclusão normal | Saída 0, PID final 0 |
| Prazo | Saída 124 em aproximadamente 5 segundos, PID final 0 |
| Perda do transporte | Saída 125, PID final 0 |
| Segundo início das três operações | Recusa 125 antes de chamar `docker start`; estado do contêiner inalterado |

Seis testes do launcher também passaram no Linux com sincronização real de diretórios.
Os testes Windows e CI sem root verificam contratos; não comprovam permissões Linux.
No Windows, cinco suítes terminaram sem falhas: sandbox (17), launcher (6), guardian (9),
missões (27) e capacidades (23 casos, um ignorado porque o host não permitiu criar symlink).
São 81 casos aprovados e um ignorado; a suíte completa do repositório não foi executada
neste checkpoint. O vault passou com 241 notas e nenhum problema; os sete hashes da
medição foram conferidos e a auditoria do catálogo dos dois clientes retornou código 0.
A perda do transporte da tabela encerra o processo `docker start` dentro da VM.

Na continuação, dois processos separados no Windows coordenaram operações sintéticas
com prazo original de cinco segundos. Depois do evento de início do cliente, a prova
encerrou apenas o processo selecionado, por handle: primeiro `sbx.exe`, depois o
coordenador Python. O observador conferiu imagem, ID e labels do contêiner antes de
ler seu estado. Não houve chamada de modelo nem alteração do guardian/launcher.

| Falha induzida no Windows | Resultado observado |
|---|---|
| Transporte `sbx.exe` encerrado | Contêiner saiu 125, duração 0,587 s, PID 0 |
| Coordenador encerrado | Contêiner saiu 125, duração 0,436 s, PID 0 |
| Novo início das duas operações | Recusa `start_consumed`, estado inalterado |

As durações vêm de `StartedAt`/`FinishedAt` do Docker, não do tempo total da inspeção.
O transporte também já havia terminado antes da limpeza do ensaio. Esses resultados
comprovam recolhimento e recusa de repetição nos dois casos; não comprovam reconciliação
SQLite, reinício do daemon, suspensão do host ou acesso de rede permitido.

## Bloqueio no pacote

As receitas `runtime/sbx/youngcrow.yaml` e `youngcrow.dockerfile` usam base AMD64 por
digest e copiam somente guardian/launcher. O entrypoint padrão recusa execução por
usuário comum. O pacote ainda não instala clientes nem contém perfil habilitado e não
faz parte do setup dos projetos consumidores.

`sbx kit validate` reconheceu o diretório como v3, mas informou que esse caminho de
validação não tem builder configurado. A criação pelo diretório, caminho descrito pelo
[fornecedor](https://docs.docker.com/ai/sandboxes/customize/author/distribute/), tentou
usar o builder oficial. Seu pedido de 8 GiB excedeu o limite local de 5,765 GiB.

Criar esse mesmo builder com `--cpus 2 --memory 4g`, sem workspace, skills ou rede,
resolveu o limite de memória. O comando retornou 0, acompanhado de aviso de falha de
startup com código 32. Esse retorno não foi aceito como build bem-sucedido.

O kernel observado na VM de prova é 7.0.14: `binfmt_misc` ausente da lista de filesystems,
`CONFIG_BINFMT_MISC=m` e diretório de módulos ausente. O builder oficial tenta montar
esse filesystem para QEMU. O conjunto é compatível com a
[issue Docker #643](https://github.com/docker/sbx-releases/issues/643), marcada como correção
aguardando release na consulta. Isso sustenta a hipótese local; não é uma prova do stderr
do hook, que o runtime não retornou. O builder foi observado parado, com identidade
preservada. Nenhum kernel, hook do fornecedor ou backend foi substituído.

A inspeção da [candidata oficial `v0.47.0-rc2`](https://github.com/docker/sbx-releases/releases/tag/v0.47.0-rc2)
ocorreu sem instalação. O MSI foi conferido
contra o SHA-256 publicado; seu kernel extraído é idêntico ao instalado, com
`CONFIG_BINFMT_MISC=m`. O SBOM consultado descreve os executáveis de um arquivo tar,
não o conteúdo completo do MSI. A inspeção adicional do rootfs ficou inconclusiva:
7-Zip não reconheceu EROFS, e a VM não conseguiu criar o loop device para uma montagem
somente leitura. Portanto, não afirmamos que a candidata reproduz o defeito nem que
o corrige. A imagem oficial do builder mantém o mesmo digest e o hook de montagem.
A medição registra os hashes e esses limites. Nenhuma atualização foi aplicada.

## Próxima ação

Retomar pelo [checkpoint do build nativo](2026-10-04-native-kit-build.md): o pacote já foi
construído e importado, mas falta consumi-lo pelo resolvedor com HTTPS confiável.
Depois, provar rede permitida com sentinelas
negadas, inacessibilidade MCP, reinício do daemon durante execução e semântica de suspensão.
OAuth e os diagnósticos reais de Claude/Codex dependem dessas provas e da integração R2.

## English overview

The trusted launcher passed three unpaid microVM scenarios: completion, a five-second
deadline and transport loss. All three repeated starts were refused before Docker start;
the containers remained stopped with PID zero. Six launcher unit tests passed in Linux.
Five Windows suites completed with 81 passing cases and one symlink case skipped due to
host permissions. The full repository suite was not run at this checkpoint. The vault
check covered 241 notes with no issues; all seven measurement hashes matched.
The host observer uses `ls/inspect/ls` and never infers workload reaping from VM state alone.

The approved MCP amendment allows a manager-side gateway only after proving that the
client and descendants cannot reach it, including with provider networking enabled.
That proof remains pending; native profiles stay empty.

At this checkpoint the recipe was unbuilt; the [later native build](2026-10-04-native-kit-build.md#english-overview)
produced and imported it. The official builder's 8 GiB default exceeded this host's
5.765 GiB limit. An explicit 4 GiB builder was created but its startup failed with code 32.
Observed kernel/module facts are consistent with Docker issue #643, without proving the
unavailable hook stderr. The builder was stopped. R1 remains incomplete; R2/R3 have not
started. The current dependency is consuming the package through a trusted HTTPS registry, followed by networking,
MCP, daemon restart, suspension and authentication proofs.

Two additional Windows probes killed the `sbx.exe` transport and the Python coordinator
after dispatch started. Both containers exited 125 before the original five-second
deadline, with PID zero, and refused another start without changing state. Their Docker
lifetimes were 0.587 and 0.436 seconds. These results do not establish SQLite recovery,
daemon restart, host suspension or allowed-provider networking.

The official v0.47.0-rc2 MSI was hash-checked and inspected without installation. Its
kernel is byte-identical to the installed kernel and still uses modular binfmt support.
Rootfs inspection was inconclusive; candidate compatibility has not been established.
The current official builder image and its mount hook are unchanged. No update was applied.

ATRASO: main 1
