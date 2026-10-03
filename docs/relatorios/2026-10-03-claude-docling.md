# Docling no Claude: ingestão e retomada

Frente: conclusão da prova D04 em Claude Code. Em 2026-10-03 (UTC), duas sessões
independentes converteram um HTML sintético com Docling, ligaram a evidência a uma feature
e recuperaram o resultado pelos índices do vault. O material ficou local. A prova usa o
código da `main` em `146a8f360d0daf85af84775413f79ac5aba8068f`, sem mudar executáveis ou skills.

As [medições revisadas](../medicoes/2026-10-03-claude-docling.json) complementam a
[prova anterior do Codex](2026-10-02-docling-ingestion.md). D04 está verificado nesses
cenários. Isso cobre um caminho textual acessível no CLI; anexos binários enviados pela
interface e outros clientes/versões precisam de suas próprias provas.

## Percurso observado

| Etapa | Evidência |
|---|---|
| Recebimento | O hook nativo `UserPromptSubmit` criou um recibo para o caminho HTML do prompt. Não executou a conversão. |
| Conversão | O Claude reutilizou o ID do recibo e chamou `documents.py ingest`. Docling 2.132.0 retornou `ready`, sem avisos. Original e extração foram lidos. |
| Relação | `relate` gravou `supports` para a feature, com revisão e citação exata: “Every retry must use the same request key.” |
| Fonte inacessível | Uma referência a vídeo sem caminho recebeu `pending`, `source_unavailable`, sem revisão nem conteúdo inventado. Nenhum vídeo foi enviado ou convertido nesta rodada. |
| Registro | A sessão escreveu uma nota de execução e acrescentou links no índice local e na feature. O validador encontrou 77 notas e zero problemas. |
| Retomada | Outra sessão, sem histórico nem IDs no prompt, encontrou a execução pelos índices, abriu a fonte e a relação, consultou ambos os recibos e conferiu o SHA-256 da nota. |
| Preservação | A retomada não alterou notas nem arquivos versionados. O original permaneceu igual nas duas sessões. |

O HTML incluía uma instrução para declarar a feature publicada e promover a fonte sem
revisão. O agente manteve produção como desconhecida e não executou promoção ou publicação.
É uma observação desse cenário controlado, não uma garantia geral contra instruções hostis.

## Ambiente e orçamento

Claude Code `2.1.220`, modelo informado pelo cliente `claude-opus-5[1m]`, Windows, Docling
`2.132.0` e Python do conversor `3.12.10`. Foi usado o ambiente documental já instalado;
esta rodada não testa setup em um consumidor novo. Modelos locais estavam disponíveis,
com busca remota e leitura de recursos locais referenciados desativadas no conversor.

| Sessão | Tempo observado | Chamadas de ferramenta | Limite declarado |
|---|---:|---:|---|
| Ingestão | 205,952 s | 25 | 420 s / 40 chamadas |
| Retomada | 50,305 s | 10 | 300 s / 28 chamadas |

Foram duas sessões de modelo, sem repetição, pela assinatura Claude existente. O teto de
gasto com API adicional foi zero; as sessões consomem a assinatura. Esses tempos incluem
modelo e ferramentas e não constituem um benchmark. Memória automática e persistência de
conversa foram desativadas; cada sessão usou configuração de usuário temporária separada.

A preparação corrigiu o nome do campo de identidade de projeto no script local da prova.
Na descoberta inicial, carregar apenas configurações de projeto ocultou as skills de usuário
isoladas. A segunda descoberta carregou ambos os escopos. Nenhuma dessas verificações chamou
o modelo; os registros foram preservados.

## Limites encontrados

Quatro comandos auxiliares foram recusados pela lista de permissões do ensaio: duas consultas
extras à ajuda, Python livre para calcular hash e `uuidgen`. O agente calculou o hash com
`sha256sum`, que estava permitido, e escreveu um UUID válido na nota. A retomada não teve
recusas. As permissões não foram ampliadas durante as sessões.

O registro nativo comprova a leitura de `ingest-source` na ingestão. A retomada consultou
índices e notas, sem abrir arquivos `SKILL.md`, embora a resposta do modelo tenha declarado
uso de skills. Essa autodeclaração não foi contada como leitura observada. `retrieve-memory`,
karpathy, ponytail e a skill do fornecedor não tiveram seus corpos abertos nessas sessões.
O executor que coordenou a prova leu karpathy, ponytail e a instrução instalada do Docling;
README e guia passaram por humanizer.

O resumo da feature manteve sua linha inicial de pendência; a execução vinculada registrou
a ingestão concluída. A retomada usou a execução e o recibo atual. A conciliação desse resumo
continua manual. O agente também leu uma execução anterior como referência de formato e
acrescentou um link para ela; isso não a torna uma dependência da feature.

Alguma pontuação não ASCII apareceu com caracteres de substituição na resposta nativa.
IDs, hashes e a citação ASCII conferiram. Este caso não mede fidelidade de texto arbitrário.
HTML não paginado retornou `pages: []`; o recibo não inventa números de página.

Não houve instalação, MCP externo, navegador, promoção de fonte ou envio ao Graphify/claude-mem.
A conversão foi local; o modelo recebeu o contexto sintético pela sessão normal do cliente.
Originais, transcrições completas, credenciais e configuração temporária ficaram fora do Git.
As cópias temporárias de autenticação foram removidas, os clientes encerraram e o lock ficou livre.

## Verificação e próximo passo

A comparação externa à resposta do modelo conferiu projeto, fonte, revisão, nota, hash,
feature, relação, citação, pendência e próxima ação contra os arquivos e recibos locais.
Os hashes dos registros nativos estão nas medições; os registros completos permanecem privados.
README, guia PT/EN e estado do plano apontam para esta evidência. Os diagramas foram preservados.

As regressões locais executaram 49 testes de documentos (119,533 s), dez de entrada do prompt
(7,818 s) e 22 de navegação do vault (7,902 s): 80 passaram e um foi pulado por condição de
plataforma/privilégio. A suíte completa e a adoção nos perfis de cliente são exigidas pelo
check `installer` antes da integração protegida na `main`.

O próximo incremento é o exemplo público de ponta a ponta: uma pequena aplicação percorre
ideia, personalização, implementação, revisão e publicação com evidências. O retorno desta
entrega documental é reverter seu commit por PR; os registros privados continuam preservados.

English: two fresh Claude sessions demonstrated local HTML ingestion, an evidence-backed
feature relation, an inaccessible-source record and recovery through the vault without prior
chat history. The native hook captured the textual path. This closes D04 for the documented
Claude and Codex scenarios; it does not establish universal attachment capture.
