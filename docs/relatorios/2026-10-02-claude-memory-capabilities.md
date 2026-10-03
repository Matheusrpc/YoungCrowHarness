# Claude: retomada de memória e permissões de MCP

Frente: validação autenticada do Claude. Três sessões independentes recuperaram a memória,
reconheceram uma fonte alterada e verificaram acesso, recusa, revogação e restauração de um MCP
sintético. O ensaio também revelou referências indevidas no hook de documentos, corrigidas
nesta entrega com regressões próprias.

## Ambiente e limites da rodada

A [medição](../medicoes/2026-10-02-claude-memory-capabilities.json) contém resultados, revisões,
contagens e hashes dos registros privados. As sessões usaram Windows, Claude Code `2.1.220`,
modelo informado pelo cliente `claude-opus-5[1m]` e a assinatura Claude Max já autenticada.
O limite declarado foi três sessões de até 300 segundos; o executor limitou cada uma a 24
chamadas de ferramenta. Nenhuma API adicional foi contratada. O custo estimado pelo cliente
não é fatura nem prova de cobrança adicional; tokens agregados não medem economia de memória.

Reutilizamos o projeto sintético do [ensaio Codex](2026-10-02-memory-current-clients.md),
incluindo seu handoff, para exercitar a passagem entre clientes. Antes de cada sessão, 24
arquivos de scripts, skills e dependências foram comparados com a base
`577c2bad3c462d0528e93c99bf002a5162aa295c`, sem divergências. A correção do hook descrita abaixo
veio depois da observação; as conversas não são apresentadas como teste dessa versão corrigida.

Os clientes usaram diretórios privados e autenticação temporária, removida ao encerrar cada
processo. A inicialização nativa encontrou `retrieve-memory`, `govern-capabilities`, `karpathy`
e `ponytail` sem chamar o modelo. Durante as conversas, `dontAsk` permaneceu ativo, com comandos
específicos autorizados e uma configuração MCP exclusiva do ensaio. Não houve bypass de permissões.

## Memória e execução observadas

| Sessão | Duração / ferramentas | Memória | MCP |
|---|---|---|---|
| Gravação | 184,505 s / 22 | Graphify pronto, cinco fontes; handoff Codex recuperado e novo handoff Claude salvo | Uma leitura permitida; tentativa de escrita recusada pelo cliente, zero escritas no servidor |
| Retomada | 153,824 s / 21 | Fonte API alterada, grafo obsoleto, fallback Markdown; próxima ação corrigida | Entrada `yc` ausente da configuração/lista nativa; zero chamadas |
| Restauração | 99,002 s / 17 | Após reconstrução explícita, Graphify pronto com a nova revisão | Uma leitura permitida após restaurar a entrada |

O handoff Claude tem UUID `4c1f8e3a-7b26-4d59-9f0a-2e84c5b6d137` e SHA-256
`1bf446b262205171a8103a940c5285740afc530bd4b174f1151ed576196b3886`.
A sessão seguinte encontrou-o pelos índices e conferiu as cinco fontes. Entre as sessões,
alteramos somente a nota API: a assinatura passou a constar como validada em DEV e a próxima
ação passou de validar assinatura para testar replay. O Claude reconheceu a revisão nova
`094a652efd3e04b70585aa7cca19e7f9950a29b855d7ae52e0455b52fce56dde` e corrigiu o estado na resposta,
preservando o handoff antigo.

Nas três respostas, a API permaneceu sem publicação e o Portal ficou restrito à release sintética
`demo-1`. A decisão vigente continuou webhook, substituindo fila. Nenhuma ação funcional de
Pagamentos foi executada. A nota original foi restaurada pelo executor depois da rodada, mantendo
cópias privadas das duas revisões e das evidências. Isso não demonstra uma aplicação em produção.

As duas sessões de retomada não alteraram notas. Todas as consultas preservaram os arquivos das
gerações do índice; as reconstruções foram ações explícitas do executor entre sessões. Na primeira
sessão, cinco arquivos do vault mudaram: handoff, índice local e três arquivos de fontes gerados
pelo hook. A resposta do modelo mencionou apenas seus dois alvos de Write/Edit e contou 19 chamadas;
o fluxo de eventos registra 22. A medição preserva essas diferenças.

## O que a prova de MCP estabelece

O servidor stdio expõe `yc_read` e `yc_write`, que apenas registram chamadas e retornam
`synthetic-ok`. A leitura autorizada chegou ao servidor. A tentativa de escrita recebeu erro de
permissão no Claude Code e não chegou ao servidor. Na segunda sessão, removemos a entrada do
servidor da configuração exclusiva; ela também sumiu da lista nativa. Na terceira, restauramos
a entrada e a leitura voltou a executar. Os processos próprios encerraram, com a verificação de
limpeza do executor concluída.

O perfil combina permissões explícitas com `dontAsk`, conforme a
[documentação do fornecedor](https://code.claude.com/docs/en/agent-sdk/permissions).
Uma lista de ferramentas permitidas, sozinha, não restringe todas as ferramentas disponíveis.
A recusa foi observada no cliente instalado. Esse resultado não é prova de sandbox do sistema
operacional, revogação de credenciais do fornecedor ou segurança de um MCP externo.
Os documentos oficiais foram convertidos pelo Docling e relacionados à frente no vault privado.

Comandos de auditoria de capacidades que não estavam no perfil da sessão foram negados.
O Claude registrou a limitação; não há alegação de auditoria nativa dos digests do catálogo.

## Correção do hook de documentos

O detector aceitava qualquer trecho terminado em extensão de documento. Assim, um comando
`sha256sum` com curingas e o destino `vault/local/runs/claude-current.md` viraram duas fontes
pendentes, embora fossem instruções de operação da memória. A conversão não foi executada,
mas o cadastro acrescentou notas e vínculos desnecessários.

O hook agora ignora caminhos com `*` ou `?` e referências a Markdown dentro do `vault` do próprio
projeto. A comparação normaliza `..` sem abrir o arquivo ou seguir links. URLs, Markdown externo
ao vault e caminhos de documentos com espaços continuam no fluxo de ingestão. A mudança não
remove registros anteriores nem converte documentos automaticamente.

As novas regressões falharam antes da correção, reproduzindo os cadastros indevidos. Depois,
os dez testes de `test_source_prompt.py` passaram, incluindo execução dos comandos nativos dos
hooks de Claude e Codex a partir de subdiretório com espaços, sem alteração de arquivos para
referências internas. Os 21 testes de capacidades passaram, com um skip de privilégio de link
no Windows. O manifesto atualiza somente os dois hashes de conteúdo de `ingest-source`;
o contrato e as permissões declaradas permanecem iguais.

A conferência local encontrou 70 notas válidas no vault e 161 links locais válidos nos documentos
da entrega. A auditoria de `ingest-source` retornou `matched` nos dois clientes. Os assets dos
diagramas são idênticos à base. Essas verificações não renderizam o README nem demonstram todos
os controles de um fornecedor externo.

## Estado e próxima ação

G07 e G09 têm prova nos caminhos sintéticos dos dois clientes. A passagem básica de memória
também está demonstrada em ambos, incluindo revisão alterada e fallback no Claude. M04 permanece
parcial no plano: falta o ensaio ao vivo com termo idêntico em outro projeto. A ingestão completa
com Docling dentro de uma conversa Claude ainda é uma prova separada pendente. Claude-mem,
sincronização entre máquinas e orquestração autônoma de papéis continuam planejados.

README e guia PT/EN foram atualizados, mantendo os diagramas e o design. Esta captura antecede
a publicação da correção e da documentação. O retorno é reverter o commit por PR, preservando
as notas e os registros privados. O orçamento das três sessões foi consumido; nenhum teste
adicional de modelo foi iniciado nesta rodada.

ATRASO: main 1
