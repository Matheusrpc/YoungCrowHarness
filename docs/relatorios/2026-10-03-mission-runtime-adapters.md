# Diagnóstico limitado dos clientes

Frente: 2A, executor e adaptadores; YC-201–203. Entrega parcial. A fila de PBIs,
QA e publicação autônomos permanecem nas próximas frentes do [backlog](../BACKLOG.md).

O desenvolvedor escolhe modelo e esforço pelo catálogo da conta. `latest` seleciona a
recomendação do cliente naquele instante; um nome explícito fixa a escolha. `client-default`
omite a substituição de esforço. Nenhuma dessas opções permite trocar de conexão ou
reduzir o esforço silenciosamente. A configuração global continua podendo ser alterada
por missão. O diagnóstico não torna a missão executável.

## Implementação e evidência

- `client inspect`: versão, hash do executável, catálogo, esforços e tipo de login oficial.
- `client check`: manifesto autorizado, nonce fixo, reserva durável antes do processo,
  prazo e saída limitados, encerramento da árvore própria e recibo privado.
- `client runs` e `status`: consulta sem escrita, migração ou chamada de modelo.
- `client reconcile`: referências privadas por hash, confirmação de término e revisão
  explícita do efeito externo; conserva tentativas e reservas.

O esquema SQLite 2 é aditivo e transacional. As notas ficam em
`vault/local/missions/<mission-uuid>/runs/`, com microíndice e vínculo à missão.
Saída bruta e credenciais não entram nos recibos. Uma falha ao projetar o Markdown
não repete o fornecedor. Edições humanas geram conflito preservado.

Os testes determinísticos usam processos reais e um cliente fictício sem rede.
Cobrem queda antes/depois do efeito, repetição do UUID, migração abortada, conflito
de revisão, reserva de limites, timeout com descendente e preservação de processo
alheio. A prova de adoção usa a CLI instalada em consumidores novo e existente,
passando por instalação, execução, consulta, recuperação e retorno.

Resultados consolidados e comandos ficam em
[mission-runtime-adapters.json](../medicoes/mission-runtime-adapters.json).
Após as correções da revisão, a suíte de missões Windows passou com 81 testes em
928,776 segundos e um skip de plataforma. A suíte completa Linux passou com 343 testes
em 124,133 segundos e 13 skips. As provas instaladas passaram nos dois sistemas,
incluindo consumidores novos e existentes, recuperação e retorno do trial.
A publicação segue pelo [PR #20](https://github.com/Matheusrpc/YoungCrowHarness/pull/20),
com verificações obrigatórias antes do merge. A nota de retomada privada passou pela
validação do vault: 129 notas, nenhum problema.

## Revisão independente

A revisão apontou quatro problemas importantes. Todos entraram na mesma rodada de
correção, com reprodução anterior e teste posterior:

| Problema | Correção e prova |
|---|---|
| Timeout, queda ou saída inválida encerravam uma tentativa com possível efeito externo | Estado `uncertain` até conciliação; repetir UUID não chama de novo e outro UUID continua bloqueado |
| Falha ao atribuir o Job Object deixava o bootstrap Windows vivo | Encerrar pelo handle próprio antes de liberar qualquer cliente; fechar os recursos mesmo no caminho de falha |
| Recolher o processo Linux antes do último sinal permitia reutilização de PID/grupo | Observar com `waitid/WNOWAIT`, sinalizar o grupo próprio e só então recolher o líder |
| Um descendente de inspeção podia manter stdout aberto sem prazo de término | Reusar o supervisor também nos metadados; preservar a sequência de pedidos/respostas do protocolo |

A prova Windows do efeito inconclusivo passou em 142,671 segundos, cobrindo timeout,
queda e resposta truncada após o marcador externo sintético. A suíte do supervisor
passou com 10 testes em 15,164 segundos, um skip de plataforma. Não houve achado menor
adiado nem uma segunda revisão por outro agente.

O primeiro CI expôs dois problemas adicionais da preparação das provas: a fixture
Linux passava o link do Python em vez do executável resolvido, e cinco hashes do
catálogo usavam a identidade legada sem normalização. As fixtures e o lock foram
corrigidos; o contrato normalizado ganhou regressão própria. O CI também detectou
um arquivo local com CRLF cujo hash mudava no checkout Linux: o arquivo foi alinhado
ao LF já exigido por `.gitattributes`, e os hashes foram recalculados. A primeira prova de
retorno Windows recusou um caminho longo. A fixture agora usa uma raiz curta,
preservando a proteção de adoção.

## Matriz nativa

| Célula | Evidência | Estado |
|---|---|---|
| Codex 0.146.0, Windows, assinatura | Catálogo e status de login oficiais; ensaio local do perfil ainda anunciou `view_image` | Execução bloqueada; nenhum turno real enviado |
| Claude Code 2.1.220, Windows, assinatura | Catálogo e login oficiais; ensaio local anunciou ferramentas, MCPs, skills e plugins vazios | Execução bloqueada: precedência das políticas gerenciadas ainda sem prova; nenhum turno real enviado |
| Codex/Claude, Linux x86-64 | Supervisão e recuperação determinísticas no CI; cliente fictício | Perfil nativo não comprovado; execução bloqueada |
| API explícita, ambos | Contrato de configuração e recusas determinísticas | Indisponível: orçamento/precedência ainda sem prova completa |
| macOS e outras arquiteturas | Sem prova de contenção | Indisponível |

O ensaio de perfil aponta os clientes para um servidor HTTP local, sem credencial
real e sem cobrança. Ele examina o catálogo efetivo de ferramentas; não substitui
a conversa nativa. Codex continuou oferecendo `view_image` mesmo com
`tools.view_image=false`; `view_image_tool` foi recusada como flag desconhecida.
O diagnóstico desse binário fica bloqueado. Novos modelos não exigem alterar uma
lista fixa no código; versões/binários novos exigem prova do perfil de permissões.

O executável Claude usado no ensaio tem o hash
`af5bf1f1b2aadffc768eccd787084c6fdf9ba81624cbe96c1c6d9ac1a1550231`.
A documentação do modo seguro mantém certas políticas gerenciadas ativas. A prova
local com ferramentas vazias não certifica essa precedência em outras instalações;
por isso nenhum perfil de produção foi liberado nesta entrega.
A repetição da inspeção supervisionada recuperou o catálogo Codex. A instalação Claude
foi recusada como `unsupported_entry` por seu executável ser um hard link. A observação
anterior do catálogo permanece histórica; essa recusa atual não foi contornada.
Receber `latest` não baixa um cliente nem confirma o lançamento global mais recente.
No catálogo inspecionado, as recomendações foram `gpt-5.6-sol` e `claude-opus-5[1m]`;
esses nomes são observações, não defaults gravados no harness.

## Limites e decisões de implementação

Um diagnóstico pode confirmar apenas sua própria combinação de cliente, conta,
modelo, esforço e perfil. `runnable` e `runtime_available` continuam falsos.
Reservas anteriores contam no limite mesmo quando a execução falha. Custo ausente
continua nulo; custo informado pelo cliente não prova cobrança de assinatura.

Windows atribui um Job Object antes de liberar o cliente e encerra seus descendentes
quando o coordenador cai. Linux x86-64 herda um filtro que impede sair do grupo de
processos; um watchdog encerra o grupo após perda do coordenador. Esses mecanismos
controlam a vida dos processos, sem constituir isolamento de arquivos ou rede.
Permissões do modelo dependem de um perfil nativo comprovado.

O setup conserva os três helpers novos quando já existem, inclusive com `--force`.
Instalações mistas exigem comparação manual; incompatibilidades detectadas bloqueiam
a operação. As skills `yc-config` e `yc-status` foram exercitadas em contextos
independentes antes/depois da edição, sem executar modelos externos no diagnóstico.

Decisões tomadas durante a execução do plano:

- Reusar o checkout exclusivo e manter um escritor; risco se incorreto: interferência.
- Acrescentar Git Bash somente ao PATH dos testes; risco: diferença em outros ambientes.
- A pergunta inicial de modelo ficou pendente até a resposta do mantenedor; sem resposta,
  as provas nativas ficariam abertas. Sua resposta autorizou catálogo dinâmico e `latest`.
- Interpretar `latest` como recomendação atual da conta; risco: ela pode atrasar um lançamento.
- Usar cinco segundos no teste de descendente Windows, pois um segundo expirava durante
  o bootstrap; risco: teste mais lento. O prazo de produto permanece configurável.
- Admitir `client-default` para modelos sem controle de esforço; risco: o padrão muda
  no fornecedor, por isso o esforço observado não é inventado.
- Dar 30 segundos à fixture de execução e ao Git local e 180 segundos ao novo teste
  de instalação, após timeouts de infraestrutura; risco: testes mais lentos. Os limites
  do executor não mudaram.
- Começar a ligação da CLI enquanto a regressão do executor rodava; risco: integração
  prematura, coberta pela corrida instalada e pela revisão final.
- Usar um caminho curto fora do Git para a prova de retorno Windows; o caminho longo
  em Temp foi recusado pelo contrato de adoção, sem alterar essa proteção.
- Manter ambos os perfis nativos bloqueados após a conferência das políticas gerenciadas;
  risco: a chamada real permanece indisponível até uma prova adicional. A autorização
  do mantenedor não substitui a comprovação dos limites exigidos pelo plano.
- Reduzir ainda mais a raiz Windows da prova de retorno para acomodar os recibos aninhados;
  risco: outros caminhos de backup ainda podem ultrapassar o limite documentado.
- Resolver o caminho do Python somente nas fixtures Linux; risco: não comprova um launcher
  alternativo, que continua fora do contrato de executável nativo.
- Calcular os hashes legados pela identidade normalizada já usada na auditoria; risco:
  uma divergência de catálogo continua exigindo nova revisão, sem marcar capacidade como executada.
- Iniciar a revisão independente enquanto as provas finais ainda rodavam; risco: parecer
  sem resultado final dos testes. A integração permanece condicionada à suíte verde.
- Usar 30 segundos nos três cenários de efeito inconclusivo; cinco segundos expiravam no
  preflight Windows. Risco: prova mais lenta, sem aumentar o limite do produto.

Pontos que o revisor deixou para julgamento do executor:

- Compatibilidade real de cada modelo/cliente: fica pendente e bloqueia o perfil; custo:
  a execução nativa ainda não está disponível.
- Teto financeiro de API, autenticação e políticas gerenciadas: manter bloqueados até prova;
  custo: não há suporte API nesta entrega.
- Hooks/MCPs iniciados pelo próprio cliente durante metadados: o supervisor limita a vida
  dos processos, mas não certifica acesso a arquivos/rede; custo: políticas locais ainda
  precisam de avaliação antes de liberar qualquer perfil de execução.
- Troca concorrente de binário, política ou credencial: hashes e revalidação reduzem a janela,
  sem eliminar toda condição de corrida; custo: exige prova adicional antes de liberar o perfil.
- Fila, workers, transferência, QA, merge e deploy: permanecem nas frentes seguintes; custo:
  o diagnóstico não produz software autonomamente.
- macOS e Linux fora de x86-64: sem prova, ficam indisponíveis; custo: suporte de plataforma limitado.
- Administrador hostil, edição direta do SQLite ou relato humano falso: fora da fronteira de
  confiança do host cooperativo; custo: hashes não atestam a veracidade de uma conciliação.
- CI e consumidores instalados: exigir resultados verdes antes do merge; custo: publicação
  aguarda as provas, mesmo com os testes focados aprovados.
- Caminhos longos no trial Windows: manter a recusa e documentar backup curto; custo:
  o operador pode precisar escolher outro caminho antes do retorno.
- Checkboxes e medições intermediárias: registrar apenas aceite observado, mantendo 2A aberto;
  custo: progresso parcial não representa conclusão da esteira.
- Fontes externas: usar documentação oficial conferida pelo executor e extração privada Docling;
  custo: o parecer do revisor não recertifica a documentação do fornecedor.
- Conservar os artefatos privados desta prova para auditoria; custo: uso de disco local.
  Eles continuam ignorados pelo Git.
- Explicitar consumidor e executável no exemplo da prova nativa; custo: esses caminhos precisam
  ser informados pelo operador, sem escolher instalação ou conta implicitamente.

## Fontes consultadas

O catálogo segue o contrato nativo de [model/list do Codex](https://learn.chatgpt.com/docs/app-server).
As flags foram conferidas na [referência do Claude Code](https://code.claude.com/docs/en/cli-reference)
e na [configuração do Codex](https://learn.chatgpt.com/docs/config-file/config-reference), junto
da ajuda dos executáveis instalados. A divergência do Codex foi medida localmente.
A supervisão usa [Job Objects do Windows](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
e [seccomp do Linux](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html).
O limite do modo seguro consta nas [variáveis do Claude](https://code.claude.com/docs/en/env-vars)
e no contrato de [políticas gerenciadas](https://code.claude.com/docs/en/managed-settings).
As fontes ingeridas por Docling ficam no vault privado com origem e revisão.

2A e YC-203 continuam abertos até comprovar o caminho autenticado de cada cliente.
O próximo gate é fechar essa matriz; 2B depende dele.
