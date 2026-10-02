# Continuidade entre sessões e consulta sem escrita no índice

Frente: memória entre sessões. Duas sessões independentes do Codex recuperaram o estado de uma
fixture de Pagamentos. O ensaio revelou uma escrita auxiliar do Graphify que causava timeout no
Windows com permissões restritas. A correção passou no SDK real e no executor nativo do Codex.
M04 continua parcial: a conversa após a correção e a execução autenticada no Claude ainda faltam.

## O que foi medido

O [registro estruturado](../medicoes/2026-10-02-memory-continuity.json) contém resultados, hashes,
versões e consumo informado pelo cliente. A base do repositório era
`289dda3256fe1f2705926edfb98e71c112675bc8`. O ambiente usou Windows, Codex
`0.158.0-alpha.2.1`, `gpt-6-astra`, Graphify `0.9.73` e a assinatura ChatGPT existente.
O limite desta rodada foi duas sessões de até 240 segundos, com pedido de até oito chamadas de
ferramenta por sessão e nenhuma API adicional. Ambas concluíram um turno. Os processos pertencentes
ao ensaio foram encerrados; nenhuma terceira conversa foi iniciada.

A fixture já existia de uma rodada anterior. Na conferência final, quatro dos seis arquivos
comparados diferiam da base: `memory.py`, `document_store.py`, `vault.py` e a skill
`retrieve-memory`. Os hashes estão na medição. As conversas abaixo comprovam o comportamento dessa
instalação; os controles posteriores usam o código atual diretamente e não substituem uma nova
conversa com uma instalação atualizada.

| Etapa | Resultado observado |
|---|---|
| Sessão de gravação, 224,563 s | Graphify retornou cinco referências; o agente conferiu UUIDs/revisões, gravou o handoff e vinculou-o ao índice local |
| Sessão nova, 180,883 s | Encontrou o handoff pelo índice, conferiu seu UUID/hash e as cinco fontes; nenhuma nota alterada ou removida |
| Consulta na sessão nova | `payments` terminou em `worker_timeout`, com fallback vazio; `Pagamentos` teve o mesmo aviso, mas o Markdown devolveu as cinco referências |
| Controle nativo antes da correção | Escrita de um arquivo de teste no vault bloqueada; consulta ao código atual terminou em fallback por timeout |
| Controle nativo após a correção | Mesmo perfil restrito: Graphify `ready`, cinco referências, nenhum aviso e escrita no vault bloqueada |
| Claude Code 2.1.220 | `loggedIn: false`; nenhuma conversa nem prova de execução/revogação MCP iniciada |

Os registros nativos mostram cinco comandos e uma edição na primeira sessão, e seis comandos na
segunda. Contadores de tokens agregam as interações do turno; não medem isoladamente o custo da
memória nem demonstram economia em relação a outra solução.

O handoff recuperado tem UUID `c64dc38d-90bd-4b8b-a562-b301dd7ca0d4` e SHA-256
`0df06f3cb8ca3cdbf7a15de19d808b9db2526a6be4de0673e82e5e4804bfb565`. A resposta distinguiu API com
webhook em DEV, API sem publicação e Portal publicado apenas na release sintética `demo-1`.
Reconheceu webhook como decisão vigente, fila como substituída e validação de assinatura como
próxima ação. Isso não comprova uma aplicação real em produção.

O texto gerado na primeira sessão disse que nenhum arquivo temporário foi criado. Essa afirmação
é imprecisa: o adaptador cria e remove uma requisição privada. O registro original foi preservado
como evidência, com esta ressalva. A segunda sessão declarou o fallback em vez de repetir a alegação
anterior de sucesso do Graphify.

## Causa e correção

O dispatcher da CLI Graphify chama `_touch_query_stamp`, que tenta escrever `cache/last_query_stamp`
ao lado de `graph.json`. Quando o cache já existe e a geração está protegida contra escrita, o
Python no Windows pode repetir a tentativa de criar um arquivo temporário até o worker atingir
seu limite de 30 segundos. A captura de pilha mostrou `tempfile._mkstemp_inner`,
`graphify.paths._atomic_replace` e `_touch_query_stamp`; aumentar o tempo de espera não resolve
a escrita fora do escopo.

O adaptador agora chama o motor `_query_graph_text` da versão fixada, em memória. Mantém busca BFS,
profundidade 2, orçamento 1000, direção dos links, identificação das fontes e limite de tamanho
do grafo. Não chama o dispatcher que grava o marcador. A requisição do worker continua temporária
e privada. Nenhuma permissão de cliente ou contrato de capacidade foi ampliado.

Essa função é interna ao pacote. A versão continua fixada em `0.9.73`; uma atualização precisa
passar pela prova com o SDK real. O manifesto foi atualizado somente nos hashes de conteúdo de
`retrieve-memory`, para Claude e Codex. O hash do contrato foi preservado.

## Como conferir

Prepare um projeto sintético descartável com as notas de `tests/memory_fixture.py`, instale o
runtime opcional e rode:

```bash
python tests/smoke_memory.py --root CAMINHO_DA_FIXTURE --provider graphify
```

O teste agora compara os arquivos das gerações antes e depois de cada consulta. Antes da correção,
falhou com `Query wrote outside its private runtime`. Depois, passaram as oito consultas, a
preservação das gerações, os títulos iguais e os casos existentes de recuperação/fallback. O mesmo
teste integra o CI com Graphify real. Não usa conta de modelo.

No controle nativo local, o diretório de execução foi `.operacao-local/memory/runtime/`, com leitura
do filesystem e escrita somente nesse runtime, rede desativada e aprovações em `never`. A prova
usou `command/exec` do app-server, sem turno de modelo, e confirmou que um arquivo de teste não
podia ser criado no vault. Configurações e diretórios do cliente ficaram isolados na área privada
de evidências; as cópias de autenticação usadas nas duas conversas foram removidas ao encerrá-las.
A [documentação oficial de permissões](https://learn.chatgpt.com/docs/permissions) foi ingerida
com Docling e ligada à frente no vault local. O ensaio não altera a configuração global do usuário.

Antes da próxima conversa real, prepare a fixture a partir da mesma revisão do código avaliado,
confira os hashes dos scripts/skills e registre autenticação, permissões e orçamento. Depois da
gravação, encerre o escritor e inicie outro processo/sessão sem copiar a conversa. Confira o
provedor efetivo, as revisões das notas e a próxima ação. `status: ready` não substitui o resultado
de `query`; um índice presente pode ter um worker que falha.

## Estado de entrega

As 16 regressões de memória passaram após o ajuste, com dois skips por falta de privilégio para
links simbólicos no Windows. A prova com o SDK real passou nas oito consultas e nos casos de
recuperação existentes. O perfil restrito passou no controle nativo sem turno de modelo.

Esta captura registra a correção local para revisão, antes de sua publicação. README e guia PT/EN
foram atualizados; os diagramas e o design foram preservados. Fontes e transcrições permanecem
privadas; o Git recebe a medição sintética e este relatório. O retorno é reverter o commit da
correção por PR, preservando as notas e aceitando novamente o limite do dispatcher anterior.

Próxima ação: atualizar a instalação de prova, repetir a conversa Codex com o adaptador corrigido
numa nova rodada limitada e, após autenticação, validar handoff e permissões MCP no Claude. O teste
nativo corrigido não fecha M04 nem os aceites de execução do Claude.

ATRASO: main 1
