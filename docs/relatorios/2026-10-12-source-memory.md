# Fontes e memória: correções para a main

Frente: uso cotidiano de fontes e memória. Recorte da auditoria de 12/out já
implementada em `feat/isolated-executor`, agora isolado sobre a main
`e966e7e06dd30bbd039be839887f8d6de31c32f4` na branch `fix/source-memory-usability`.

## Comportamento

O hook `UserPromptSubmit` devolve orientação fixa para ingestão autorizada, sem
criar arquivos, fontes ou pendências. Não copia prompt, URLs ou tokens para o
contexto. Palavras como “anexo” ou “attach” isoladas não acionam o hook. Entrada
acima de 1 MiB recebe diagnóstico; recibos históricos permanecem disponíveis.
Ingestão e registro de fonte inacessível continuam ações explícitas.

A busca Markdown compara palavras inteiras, sem distinguir maiúsculas, com peso
triplo no título. Ignora uma lista curta de palavras funcionais PT/EN; uma consulta
sem termos úteis retorna vazia sem iniciar Graphify. Termos como C, R e Go continuam
pesquisáveis. `relate` aceita citações literais com ampersand e colchetes, além da
forma escapada legada. Decodifica uma camada para comparação, preservando bytes e
hashes das fontes; código citado continua cercado por fence.

Em novas instalações, o hook Claude usa `python3` no Unix e `python` no Windows.
Configurações existentes permanecem intactas mesmo com `--force`; a migração é
explícita. README e guia mantêm PT/EN e diagramas. Nove capacidades têm novos hashes
de conteúdo; somente o limite textual de `ingest-source` muda. Arquivos declarados
e permissões permanecem iguais.

## Verificação

Antes do transplante, as regressões reproduziram escrita pelo hook, busca de “API”
em “capital”, recusa de citações válidas e seleção incorreta do interpretador Unix.
Após as correções, passaram 71 testes focados, com dois skips de plataforma entre
os 73 casos coletados. A suíte completa final executou 342 casos: 328 passaram e 14 foram pulados,
sem falhas ou erros. Uma revisão independente não encontrou problemas no código,
documentação ou evidências. [Medição](../medicoes/2026-10-12-source-memory.json).

O ensaio instalado usa o runner de adoção existente em dois consumidores
descartáveis, novo e Git com alterações locais, com perfil `both`. Os comandos
dos dois hooks preservaram o retrato de arquivos. Os módulos instalados aceitaram
a citação literal, preservaram a fonte e consultaram palavras inteiras; 18
observações obrigatórias do catálogo corresponderam. A restauração preservou o
estado inicial, o trabalho do trial e o perfil do usuário nos dois casos.
Conversão usa fixture sintética; zero chamadas de modelo.

O primeiro recálculo de hashes usou registros brutos com `legacy_ref`, causando
`contract_difference`. A correção usa o catálogo normalizado pelo próprio auditor;
as 18 observações voltaram a `matched`. Os registros desse diagnóstico ficam nos
logs locais, sem ocultar a falha inicial.

## Diagnóstico do piloto no CI

No commit `3f4a3ca`, o piloto passou localmente e no push, mas falhou no
[job do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38218642573/job/114709257804).
Após publicar a rede, o log pôde ser lido: a etapa de adoção emitiu apenas
`public_pilot_smoke_failed`. A causa histórica permanece desconhecida.

O commit `fd07e32` acrescenta tipo de exceção e até quatro localizações de arquivo/linha
permitidos, sem mensagem, argumentos, caminhos completos ou valores locais.
A regressão de diagnóstico falhou antes e passou depois; o ensaio instalado passou
novamente nos consumidores novo/existente, perfil `both`, sem chamadas de modelo.
Revisão independente do ajuste sem achados. O piloto passou no
[push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38240709971/job/114782330754)
e no [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38240715463/job/114782338443)
desse commit. Esses sucessos não identificam a causa da falha anterior.
Os demais checks e a integração devem ser conferidos no PR #27.

## Limites e continuidade

Plugins opcionais, template MCP, redução geral do README, avisos, pausa/retomada
e executor permanecem fora deste recorte. O checkout original foi preservado.
Não houve execução nativa de Claude/Codex, conversão real com Docling, instalação
de Graphify, nova prova Docker ou repetição de P06. Este incremento não conclui
YC-203. Nenhum navegador foi aberto; Pages não é alvo desta mudança.

Próximo passo: revisar o PR e seus checks antes da integração. Retorno, se a
mudança for integrada: reverter somente seu commit por novo PR, mantendo recibos
e fontes locais. Configurações instaladas anteriormente exigem revisão manual.

**English.** Source hooks now guide explicit intake without writing files.
Markdown retrieval matches whole words; literal evidence quotes preserve source
bytes. New Claude configurations select the host's Python command. Local installed
checks use synthetic conversion and make no model calls. Native executor acceptance,
Windows execution and integration remain separate from this local evidence.

ATRASO: GitHub integração pendente | CI remoto pendente | Pages não aplicável
