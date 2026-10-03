# Memória de projetos com temas de mesmo nome

Frente: provar a distinção entre dois projetos que usam os mesmos títulos e caminhos relativos.
Esta rodada completa o cenário de homônimos previsto na tarefa 5 do
[plano de memória](../superpowers/plans/2026-10-02-memory-discovery.md). Codex e Claude distinguiram
as fontes, revisões e estados dos dois projetos. A primeira tentativa Claude ficou parcial;
uma sessão corretiva confirmou o aceite. As expectativas abaixo foram fixadas antes das sessões.

## Cenário e critério de aceite

Dois projetos sintéticos foram preparados a partir dos arquivos versionados da base
`546061d5ebaa4fa6444376295274e267811a057d`. Cada projeto tem cinco notas selecionadas, títulos e
caminhos relativos iguais, UUIDs diferentes e um índice Markdown próprio. Os 24 arquivos de
scripts, skills e dependências usados na prova foram conferidos contra a base em cada projeto.
O preparo usa uma exportação do Git; não é uma nova medição do instalador.

| Evidência | Projeto A | Projeto B |
|---|---|---|
| Identidade do projeto | `9865926d-6293-4c63-a8ff-c8441674a043` | `345466fa-9688-4630-b542-20c8c2ef5e7b` |
| API em DEV | Webhook implementado | Processamento por lote implementado |
| Publicação da API | Não publicada | Release sintética `other-2` |
| Publicação do Portal | Release sintética `demo-1` | Não publicado; protótipo em DEV |
| Decisão vigente | Webhook | Lote |
| Decisão substituída | Fila | Webhook |
| Próxima ação | Validar assinatura do webhook | Verificar conciliação do lote |

Os nomes dos arquivos também coincidem. No projeto B, `webhook.md` contém a decisão de usar lote;
o conteúdo e a identidade devem prevalecer sobre o nome. Nenhuma dessas notas demonstra uma
aplicação real em produção. As próximas ações servem à verificação e não devem ser executadas.

Cada cliente recebeu autorização para ler as duas raízes e comparar os projetos. A pergunta
forneceu caminhos, comandos públicos e campos esperados na resposta, sem fornecer os fatos da
tabela. O aceite exige duas consultas separadas, `project_id` correto, as cinco referências de
cada raiz com UUID/revisão conferidos e estados de DEV/produção sem fusão. As notas e os índices
devem permanecer inalterados. O corpus e as respostas esperadas não mudam após as chamadas.

## Condições da rodada

O limite inicial declarado foi duas sessões, uma por cliente, até 300 segundos e 24 ferramentas
cada. Depois da recusa dos comandos agrupados, foi declarada uma única sessão corretiva Claude
com os mesmos limites. O total desta frente foi três sessões; nenhuma foi repetida silenciosamente.
As contas existentes de ChatGPT e Claude Max foram usadas, sem contratação de outra API.
Autenticação e descoberta das skills foram conferidas antes dos modelos. As configurações e
cópias temporárias de autenticação ficam privadas e são removidas ao encerrar cada processo.

O Codex usa `read-only` com aprovação `never`; Claude usa `dontAsk`, ferramentas de leitura,
comandos de consulta/hash e configuração MCP vazia. As duas raízes são legíveis por autorização
expressa do ensaio. O resultado mede a separação das referências e da interpretação; não prova
que o sistema operacional impede acesso a outro projeto. Não há MCP de memória ou grafo global.

As provas anteriores de [continuidade no Codex](2026-10-02-memory-current-clients.md) e de
[memória/MCP no Claude](2026-10-02-claude-memory-capabilities.md) registram handoff, revisões
alteradas, fallback e Graphify. Esta rodada usa Markdown para verificar especificamente a
identidade entre projetos. Não instala nem repete o runtime Graphify.

## Resultados

| Sessão | Tempo / ferramentas | Resultado |
|---|---|---|
| Codex `0.158.0-alpha.2.1`, modelo configurado `gpt-6-astra` | 164,454 s / 5 | Duas consultas Markdown prontas; dez referências corretas, sem referências do projeto errado |
| Claude `2.1.220`, primeira tentativa | 100,298 s / 23 | Leitura distinguiu os fatos; dois comandos Bash recusados; consultas e hashes não verificados |
| Claude `2.1.220`, sessão corretiva | 101,300 s / 18 | Duas consultas Markdown prontas; dez referências corretas, sem referências do projeto errado |

O modelo informado pela inicialização Claude foi `claude-opus-5[1m]`. A
[medição sanitizada](../medicoes/2026-10-02-memory-project-isolation.json) preserva as três sessões,
incluindo respostas do modelo e os dois erros nativos. UUIDs, caminhos e revisões de cada consulta
e das duas respostas aceitas correspondem às dez fontes. As relações retornadas também permanecem
dentro dos IDs do respectivo projeto. As três sessões preservaram notas, índices e `.gitignore`.

Na tentativa inicial, o Claude agrupou comandos com `cd`, listagem, variável de shell e separadores.
Essas formas não constavam no perfil. Ele continuou pela leitura das notas e deixou `revision: null`
e `index_state: unverified`. A sessão corretiva recebeu os seis comandos literais de status, query
e hash, um por chamada. As permissões e o corpus permaneceram iguais. O roteiro foi corrigido;
nenhuma mudança no detector de memória ou no controle de permissões foi necessária.

O resultado corretivo cobre execução orientada por comandos explícitos. A descoberta das skills
foi verificada no preflight; os eventos dessa sessão mostram seis comandos e doze leituras de
notas/índices, sem abertura adicional das skills. Não atribuímos esse resultado à descoberta automática.
Os avisos textuais do modelo também precisam de revisão: "12 UUIDs" inclui dois índices além das
dez fontes, e "inversões exatas" é uma descrição imprecisa das decisões. A tabela de expectativas
e as fontes distinguem fila, webhook e lote; os avisos do modelo não substituem essa evidência.

Os 16 testes locais de memória passaram em 63,985 segundos, com dois skips de plataforma Windows.
As provas anteriores e esta rodada verificam M04 nos cenários publicados. README e guia PT/EN
registram consulta por raiz e o tratamento de comandos recusados, preservando os diagramas existentes.

Na conferência local, o vault do harness tinha 71 notas sem problemas; os 164 links locais dos
textos da entrega apontavam para arquivos existentes. Código e assets são idênticos à base.
As cópias temporárias de autenticação foram removidas e zero processos próprios da rodada
permaneceram vivos. A revisão independente e o CI do PR registram o gate de publicação.

## Limites e retorno

Cinco notas por projeto não estabelecem recuperação exaustiva ou memória ilimitada. A medição de
tempo inclui execução do cliente, ferramentas e resposta; não compara desempenho entre modelos
nem comprova economia de tokens. Os registros brutos continuam privados. Caminhos absolutos nas
respostas são conferidos dentro da raiz esperada e convertidos para caminhos relativos na cópia pública.

A entrega altera documentação e evidências. Não muda o comportamento do harness. O retorno é
reverter o commit de documentação por PR, preservando fontes, notas e registros privados.
A ingestão completa com Docling em uma conversa Claude permanece uma prova separada pendente.

ATRASO: main 1
