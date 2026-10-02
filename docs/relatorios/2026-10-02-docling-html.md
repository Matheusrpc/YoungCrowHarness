# Recuperação da ingestão HTML

Frente: ingestão HTML. Base: `1bd7d55`. Correção: `37ff864`.

As cinco páginas oficiais guardadas na preparação da governança passaram de `failed` para
`ready`. Cada fonte manteve seu ID, a URL de origem e os bytes do original. Uma segunda ingestão
reutilizou a nova revisão. Os recibos anteriores continuam disponíveis no armazenamento privado.
Veja os hashes e resultados na [medição](../medicoes/2026-10-02-docling-html.json).

## Causa e correção

O Docling 2.132.0 preenche `HTMLBackendOptions.source_uri` com o caminho recebido quando a
entrada é um arquivo. Assim, links da página são resolvidos contra a pasta da cópia preservada.
A reprodução anterior da primeira fonte registrou `Path traversal blocked` para `/llms.txt`.
Nesta rodada, as cinco cópias falharam novamente antes da correção.

O adaptador passa HTML/HTM como `DocumentStream`, usando os bytes do original e leitura limitada
a 100 MiB mais um byte para detectar excesso. O SDK mantém as referências sem atribuir a pasta
local como origem. O filtro existente do vault torna destinos relativos e locais inativos;
links HTTP(S) explícitos continuam clicáveis. Rede, leitura de recursos locais, busca de imagens
e renderização continuam desabilitadas. Não houve troca de versão nem instalação de dependências.

## Provas

Ambiente local: Windows, Python 3.12.10, Docling 2.132.0 e docling-core 2.99.0.

| Verificação | Resultado |
|---|---|
| Regressão com SDK real antes da correção | Falhou como esperado: `failed`, `incomplete_conversion`. |
| Mesma regressão após a correção | `ready`, texto e tabela preservados; zero acessos ao arquivo de controle ou conexões de rede. |
| Neutralização de links no vault | Quatro rótulos escapados; as quatro verificações falham sobre a saída bruta sem o filtro. |
| Documentos, armazenamento e revisão | 49 testes passaram em 145,060 segundos. |
| Instalação e auditoria após atualizar o catálogo | Um teste, três perfis (Claude, Codex e ambos), passou em 55,077 segundos. |
| Reprocessamento das fontes | Cinco `ready`, títulos conferidos, originais e origem preservados, cache reutilizado. |
| Navegação | Vault: 60 notas, zero problemas. Documentação afetada: 129 links locais, nenhum destino ausente. |

Fontes reprocessadas: documentação de MCP e configuração do Codex; permissões, MCP e skills
do Claude Code. A prova usou as cópias já guardadas, sem baixar versões novas. A conferência
dos títulos demonstra recuperação do conteúdo esperado; não certifica fidelidade integral da página.

O teste reproduzível é `python tests/smoke_docling_html.py`, com o ambiente Docling do projeto
instalado. Ele é opt-in e usa o SDK real; a suíte padrão de testes não instala o Docling.
O controle de acesso observado é do processo Python e das opções do SDK, não um isolamento
de código nativo pelo sistema operacional. As fontes e extrações ficaram locais, sem promoção pública.

## Revisão e operação

O revisor independente encontrou uma asserção que aceitava o Markdown bruto porque o SDK
normalizava os destinos dos links. A asserção foi corrigida para exigir rótulos escapados,
verificada por mutação e executada novamente com o SDK. O parecer final não deixou achados pendentes.

A primeira regressão completa no [CI](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37058888732)
rodou 254 testes, com 11 skips de plataforma, e falhou nos três perfis de
`test_governance_installs_selected_profiles_and_audits`. O catálogo ainda esperava os bytes do
conversor anterior. Os dois hashes de arquivos de `ingest-source` foram atualizados após revisar
a diferença; contrato e permissões permaneceram iguais. A auditoria voltou a indicar `matched`
para Claude e Codex. Esse resultado de auditoria não substitui uma prova de execução nos clientes.

README e guia de uso PT/EN explicam o comportamento dos links e como repetir uma ingestão
com o mesmo ID. Os diagramas e o design foram preservados. O microíndice privado registra as
cinco fontes, revisões, hashes das notas, relações `used-in`, capacidades usadas e próxima ação.

O [PR #10](https://github.com/Matheusrpc/YoungCrowHarness/pull/10) reúne a entrega. A regressão
completa no CI está em andamento. Produção ainda não confirmada neste registro.
Para retornar ao comportamento anterior, reverta o commit da correção pelo fluxo de PR;
isso preserva o histórico local das fontes e volta a expor a falha de conversão.

M04 de memória, consulta Graphify dentro do Codex e execução nativa no Claude continuam pendentes
de suas próprias provas. Esta correção encerra somente a falha de ingestão HTML.

ATRASO: main 1
