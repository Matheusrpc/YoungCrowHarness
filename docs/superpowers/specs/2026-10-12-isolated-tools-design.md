# Clientes oficiais com ferramentas isoladas

> Desenho histórico recuperado em 17/out/2026. O plano detalhado e a medição original
> não foram recuperados integralmente. A situação atual está no
> [relatório da retomada](../../relatorios/2026-10-17-codex-workspace.md).

Frente: YC-203. Arquitetura aprovada pelo mantenedor em 12/out/2026: “Ok vamos la”,
em resposta à revisão deste desenho, incluindo a fronteira OCI com kernel compartilhado.
O mantenedor autorizou rever a obrigatoriedade de Docker Sandboxes, conservando
isolamento e Claude Code/Codex por assinatura. Esta proposta concretiza essa revisão;
não declara um executor implementado nem autoriza chamadas de modelo.

## Entrega e escolha proposta

**Manter os clientes oficiais e seus logins na camada confiável. Executar comandos,
edições e testes em um contêiner descartável, sem rede e sem credenciais.** O primeiro
resultado será uma tarefa pequena que gere arquivos alterados, teste executado e
recibo recuperável, uma vez em cada cliente. A fila completa de PBIs continua fora
deste primeiro aceite.

| Alternativa | Avaliação |
|---|---|
| Cliente oficial + ferramentas isoladas | Recomendada para qualificação: retira autenticação e tráfego do fornecedor do ambiente que executa código; interfaces oficiais existem nos dois clientes |
| sbx com instalação fixa | Reaproveita mais do isolador antigo, mas exige endpoint protegido, autorização de rede permanente e manutenção; a [revisão anterior](../../relatorios/2026-10-09-executor-alternatives.md) já identifica essas pendências |
| VM própria para controle | Oferece fronteira adicional, mas acrescenta provisionamento e ciclo de vida; nenhuma plataforma local correspondente está validada |

**Mudança de segurança explícita:** o primeiro worker usa isolamento OCI do Docker
Engine, compartilhando o kernel Linux, em lugar de uma microVM. O kernel, o daemon,
o supervisor e os clientes oficiais são confiáveis. O modelo, o projeto e os comandos
gerados são não confiáveis. OCI não oferece a mesma fronteira de uma microVM.
Administrador hostil e falha do kernel ficam fora desta proteção. A aprovação deste
desenho inclui essa mudança; ela não decorre apenas de trocar o nome do backend.

O alvo inicial de qualificação é Linux x86_64 com Docker Engine. O desenvolvimento
cloud atual tem Engine 28.4.0 e Codex 0.159.2, sem Claude, sbx ou `/dev/kvm`.
Isso permite preparar a prova; não certifica isolamento ou autenticação.
Uso local continua sendo a direção do produto. Windows Home, Docker Desktop e
runner remoto não ganham suporte por consequência de uma prova Linux.

## Fronteira e fluxo

1. O coordenador reserva um UUID e persiste manifesto, prazo, hashes e intenção antes
   de criar recursos. Usa diretório de controle privado, separado do checkout de trabalho.
2. O worker recebe somente o pacote selecionado e revisado, por cópia. Não monta o
   checkout original, `.git`, HOME, vault completo, banco, tokens ou socket Docker.
   A entrada rejeita caminhos escapando da raiz, links e arquivos especiais.
3. O cliente oficial roda no controle confiável. Seu login permanece ali, pelo fluxo
   do fornecedor; não se copia o cache de outra conta ou ambiente. O código do projeto
   não é executado no controle e suas configurações não são carregadas como configuração
   confiável do cliente. Apenas ferramentas explicitamente roteadas ficam disponíveis.
4. As ferramentas executam no worker sem rede, sem capacidades adicionais, com
   `no_new_privs`, namespaces PID/IPC privados, raiz somente leitura e espaço gravável
   limitado. O projeto inicial usa dependências já presentes na imagem, fixada por
   digest; instalações ficam no setup.
5. Após parada comprovada, arquivos resultantes voltam para quarentena com limites de
   tamanho, caminhos e hashes validados. O extrator recusa traversal, links simbólicos,
   hard links, dispositivos e FIFOs. Logs e testes produzidos pelo agente são evidência
   não confiável; o teste de aceite é executado por comando fixo no worker. Nada é aplicado ao original
   automaticamente. O recibo aponta o pacote, diff e resultado observado.

O transporte entre controle e worker usa pipes locais e argumentos fixados pelo
coordenador. Comandos do modelo vão como dados para o worker, nunca como shell no host.
Não há listener de rede público, credencial do fornecedor no transporte ou novo proxy OAuth.
O primeiro corte usa um worker por operação, em série, na instalação Docker local.
Operações de controle usam o ID completo observado, imagem e configuração conferidas,
nunca apenas nome ou prefixo. Volumes anônimos criados pelo Engine são registrados
com o contêiner; recursos existentes não são adotados por coincidência de nome.

## Adaptadores dos clientes

**Codex:** usar o `exec-server` oficial dentro do worker, conectado por stdio ao
cliente confiável. A versão instalada 0.159.2 tem configuração de ambientes com
`program/args` e `include_local=false`; o ambiente padrão será explicitamente o worker.
`apply_patch` e `view_image` usam o filesystem selecionado nessa revisão. O modo
de registro cloud `exec-server --remote` não integra esta proposta.

O servidor de ferramentas e seus subprocessos rodam como usuário sem privilégios,
distinto do guardian. Nunca usar o usuário root padrão de `docker exec` para eles.
Falha ou desaparecimento do worker deve encerrar a operação, sem ambiente local alternativo.

**Claude Code:** usar a CLI normal por assinatura, com ferramentas internas removidas
por `--tools ""`, configuração restrita e apenas um servidor MCP explicitamente
selecionado por `--strict-mcp-config`. Esse servidor oferece uma ferramenta de execução
no worker; leitura e edição de arquivos acontecem pelo mesmo caminho. O adaptador
transporta chamadas, sem implementar um agente, cliente de modelos ou SDK de autenticação.

`--restricted` está documentado a partir de 2.1.248, mas versões posteriores corrigiram
rotas de ferramentas carregadas depois da inicialização. Logo, o mínimo documental não
é versão certificada. Selecionar e fixar uma versão publicada com as correções aplicáveis
faz parte da qualificação. Não usar `--bare`, que não atende ao login por assinatura
documentado; não supor que `--safe-mode` permita o MCP necessário.

**Nos dois clientes:** hooks, plugins, apps, subagentes, navegação, busca e demais
rotas locais ficam ausentes ou desabilitados de forma verificável. Hooks do Codex
continuam locais mesmo com ambiente remoto. Configuração gerenciada que impeça o
perfil gera recusa; não é ignorada ou removida. O inventário inclui ferramentas
carregadas tardiamente e operações de retomada, não apenas o catálogo inicial.
Logins, modelo e esforço são observados sem imprimir segredos. API ou provedor
alternativo não são fallback. Preservar proxy e CA exigidos pelo ambiente de controle.

## Prazo, persistência e recuperação

Reaproveitar reserva e diário de `mission_execution.py`, recibos de `mission_runs.py`,
supervisão do cliente em `mission_process.py` e partes independentes do guardian atual.
O launcher específico de sbx não deve ser tratado como adaptador OCI pronto.

O guardian do worker roda como PID 1 com controle inacessível ao usuário das ferramentas.
Impõe o mesmo prazo absoluto do manifesto, independentemente do cliente e coordenador.
O supervisor do cliente oficial também encerra sua árvore. A prova deve incluir
processos iniciados por `docker exec`, descendentes, perda do pipe e queda do coordenador.
Recursos não usam reinício automático. Nenhum mecanismo renova o prazo ao reconectar.

Uma operação autoriza no máximo uma invocação do cliente, até 120 segundos, com
modelo/esforço previamente escolhidos; uma tarefa pode conter várias requisições internas
do cliente nesse intervalo. O harness não relança uma operação incerta. Repetir UUID
retorna o recibo ou conflito, sem novo despacho. Só liberar a reserva após comprovar
fim da árvore do cliente, fim do worker e identidade dos recursos encerrados.
Encerrar a CLI limita a execução local; não comprova cancelamento do cálculo já
aceito pelo fornecedor. O recibo não promete essa garantia.

Não prometer encerramento pontual durante suspensão arbitrária da máquina inteira.
O primeiro perfil exige host sem suspensão durante a operação; suspensão ou estado
de runtime inconclusivo invalida o aceite e exige reconciliação, sem retomada automática.
Cancelamento e recuperação nunca iniciam um worker parado nem param recursos alheios.

O novo contrato terá versão própria. Planos, recibos e recuperação sbx v1–v4 continuam
com suas regras originais; não reinterpretar evidência antiga. O contador sbx permanece
2/3, sem ensaio novo nesta investigação. O novo desenho retira escritas/restauração de
settings e injeção de credenciais do caminho proposto; não declara esses contratos
antigos resolvidos. Perfis existentes continuam bloqueados.

## Aceite do primeiro incremento

- Prova sem modelo, nas versões exatas: ler, editar e testar no worker; recusar
  sentinelas externas, rede, credenciais, sockets e acesso ao controle. Cobrir cada
  ferramenta exposta e qualquer caminho local, inclusive na falha do transporte.
- Provar prazo e encerramento com descendentes, queda de cliente/coordenador/bridge,
  worker interrompido e indisponibilidade do daemon; ausência de observação é incerteza,
  nunca sucesso. Mesmo UUID não executa de novo.
- Depois, uma tarefa de código por cliente autenticado: corrigir um defeito delimitado
  num pacote descartável, obter diff e passar o teste fixo que falhava antes. O teste
  fica fora dos arquivos editáveis do agente; o original permanece preservado.
- Conferir pedido versus modelo/esforço/autenticação observados e coletar o resultado
  com estado final. Só os perfis provados são candidatos à liberação; a entrega conjunta
  exige ambos. Sem deploy, instalação de infraestrutura paga ou merge do PR #24.

A primeira implementação deve ligar esse fluxo ao diagnóstico e aos recibos existentes,
sem criar um framework de backends. Se qualquer cliente conservar uma rota local que
não possamos fechar, sua qualificação para e o desenho volta para revisão. Não se
compensa essa falha copiando tokens para o worker ou removendo o isolamento.

## Evidência desta decisão

Investigação de código e documentação, com dois agentes revisores somente leitura.
Nenhum contêiner, modelo ou login foi iniciado. `codex --version`, `codex exec-server
--help` e `docker version` foram consultas de metadados; não testes de isolamento.
As medições originais (`2026-10-12-isolated-tools-design.json`) registravam versões,
fontes e hashes. Desenvolvimento: desenho aprovado, implementação pendente; produção: não verificada.

- Codex [release 0.159.2](https://github.com/openai/codex/releases/tag/rust-v0.159.2),
  revisão `ff6aec96948b70d94983af2641a6b67c94faeff5`:
  [exec-server](https://github.com/openai/codex/blob/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/exec-server/README.md),
  [ambientes](https://github.com/openai/codex/blob/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/exec-server/src/environment_toml.rs),
  [hooks locais](https://github.com/openai/codex/blob/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/core/src/hook_runtime.rs#L249).
- Codex [login por assinatura](https://developers.openai.com/codex/auth/).
- Claude [flags da CLI](https://code.claude.com/docs/en/cli-reference.md),
  [autenticação](https://code.claude.com/docs/en/authentication.md) e
  [changelog consultado](https://github.com/anthropics/claude-code/blob/3deb873687379f0c199a69fdaccc65f0865f7a29/CHANGELOG.md).

Próximo gate registrado nesta versão: revisão do plano de implementação
(`2026-10-12-isolated-tools.md`, não recuperado integralmente).
Nenhum requisito de assinatura ou
exclusão de credenciais do trabalho não confiável é dispensado por esta proposta.
