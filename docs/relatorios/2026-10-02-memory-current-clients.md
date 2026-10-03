# Memória na instalação atual: duas sessões reais do Codex

Frente: continuidade de memória. Duas sessões independentes do Codex consultaram o Graphify na
instalação atualizada. A primeira salvou um handoff; a segunda encontrou o registro pelo índice,
conferiu sua identidade e revisão e recuperou as cinco fontes. Ambas terminaram sem timeout ou
fallback. A [continuação autenticada no Claude](2026-10-02-claude-memory-capabilities.md) acrescenta
handoff, revisão alterada e permissões MCP. M04 permanece parcial: falta a prova ao vivo com
termo idêntico em outro projeto. As medições abaixo preservam esta rodada Codex.

## Instalação e método

A [medição estruturada](../medicoes/2026-10-02-memory-current-clients.json) registra hashes,
consultas e consumo informado pelo cliente. O instalador executou `--client both --no-plugins`
num projeto sintético novo, com HOME privado. Os 24 arquivos conferidos de scripts, skills e
dependências coincidem byte a byte com a revisão `25b30413dcef72ac9cac5329818fdd64b82ef39d`.
A comparação foi repetida antes de cada sessão. O corpus tem as cinco notas de
`tests/memory_fixture.py`; Graphify 0.9.73 foi instalado com Python 3.12 num runtime novo.

O ambiente usou Windows, Codex `0.158.0-alpha.2.1` e `gpt-6-astra`, com a assinatura ChatGPT
existente. O limite foi duas sessões de até 300 segundos, com pedido de até oito chamadas de
ferramenta em cada uma e nenhuma API adicional. Cada sessão concluiu um turno, em processo novo
e sem reaproveitar a conversa anterior. Os totais de tokens estão na medição; não isolam custo
de memória nem demonstram economia.

Antes das conversas, o executor nativo retornou Graphify `ready`, cinco referências e nenhum
aviso. Uma tentativa de criar um arquivo no vault foi bloqueada. Esse controle não teve turno
de modelo. Na conversa de retomada, o vault e as gerações ficaram somente para leitura;
a escrita temporária permitida ficou no runtime privado. O diretório de execução também foi
o runtime, conforme a restrição desse perfil no Windows. A sessão de gravação usou
`workspace-write`, com instrução de alterar somente o handoff e seu vínculo no índice.

## Resultado observado

| Etapa | Duração | Evidência |
|---|---:|---|
| Gravação | 165.288 s | Graphify pronto, cinco referências; somente handoff e índice local alterados |
| Retomada | 151.981 s | Graphify pronto, cinco referências; nenhuma nota alterada ou removida |
| Gerações do índice | Ambas as sessões | Todos os arquivos preservaram seus hashes |
| Vault após a prova | 12 notas | Zero problemas de validação |
| Claude Code 2.1.220 | Sem conversa | `loggedIn: false`; handoff e execução/revogação MCP pendentes |

O handoff recuperado tem UUID `de22d9d1-3d20-46ae-91d9-9ecbfcc7ed68` e SHA-256
`6107e59710e0d7796588a67d8576a4b41ba39ac6665813c6df9b54f3243db1b0`. A retomada conferiu também os UUIDs e revisões das cinco fontes.
Reconheceu API com webhook em DEV e sem publicação; Portal publicado somente na release
sintética `demo-1`; webhook como decisão vigente, fila como substituída e validação da assinatura
como próxima ação. A prova não executou essa ação nem comprovou uma aplicação real em produção.

O novo handoff foi encontrado pelo microíndice sem entrar na seleção do Graphify. O grafo continuou
com as cinco fontes escolhidas. Isso exercita a passagem desejada: salvar o resultado, vinculá-lo
ao índice e retomar pelas evidências numa sessão nova.

Na retomada, `payments` retornou zero referências; `Pagamentos`, termo das notas, retornou cinco.
Uma terceira consulta repetiu `Pagamentos` para comparar UUIDs e hashes. As três usaram Graphify,
sem avisos. Esse resultado não demonstra busca entre idiomas.

## Como repetir e limites

1. Instale o harness num projeto sintético novo, com configurações e HOME de teste separados.
   No Git Bash do Windows, confira se `python3` executa o Python instalado; o atalho da Microsoft
   Store impediu a primeira preparação deste ensaio. Foi usado um lançador local para Python 3.12.
2. Compare os scripts e skills instalados com a revisão avaliada antes de chamar o modelo.
   Prepare o corpus de `tests/memory_fixture.py`, selecione suas cinco notas e instale o Graphify.
3. Registre autenticação, permissões e limite da rodada. Confira `status`, o provedor de `query`
   e a proteção de escrita no perfil destinado à retomada.
4. Peça ao primeiro cliente um handoff com fontes, UUIDs, revisões, decisões, DEV/produção e
   próxima ação. Valide o vault e encerre a sessão.
5. Inicie outro processo sem copiar a conversa. Peça a retomada pelos índices; confira o handoff,
   suas fontes, o provedor efetivo e os hashes das notas e das gerações antes/depois.

Este ensaio cobre cinco fontes sintéticas no Windows. Não repete a avaliação de notas
desatualizadas, isolamento de outro projeto ou permissões MCP. A medição anterior de recuperação
continua em 3/4 perguntas para Graphify e 4/4 para Markdown; esta prova de continuidade não a altera.
Claude-mem continua planejado. Descoberta de skills no Claude não substitui sua execução autenticada.

As configurações dos clientes e os registros completos ficaram privados. As cópias de autenticação
foram removidas ao encerrar cada processo. O Git recebe somente este relatório, a medição sintética
e os textos de uso revisados com humanizer. O design e os diagramas existentes foram preservados.
Na conferência local, o vault do repositório passou com 65 notas e zero problemas; os 138 links
locais dos textos revisados apontam para arquivos existentes. O diff não tem erros de whitespace.
A revisão independente não encontrou P1/P2. O ajuste P3 incluiu na medição a terceira consulta
da retomada, usada para conferir hashes; os registros originais permaneceram intactos.

Esta captura antecede a publicação da documentação. O adaptador testado já está na main pelo
[PR #11](https://github.com/Matheusrpc/YoungCrowHarness/pull/11), cujo CI terminou aprovado nos três
jobs: installer, graphify-smoke e adoption-windows. Esta entrega não altera código executável;
seu retorno é reverter o commit de documentação por PR, preservando o vault local.

Próxima ação: após autenticação do Claude, provar handoff entre sessões e execução/revogação MCP
nesse cliente. Não repetir as conversas Codex dentro desta rodada já consumida.

ATRASO: main 1
