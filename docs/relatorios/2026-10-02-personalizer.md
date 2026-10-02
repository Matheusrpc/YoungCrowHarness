# Personalizer, adoção e processo do README

Frente: personalização do YoungCrowHarness para um produto, com retomada pelo vault.
Data UTC: 2026-10-02. No ambiente do mantenedor: 2026-10-01, America/Sao_Paulo.
Base anterior: `bab2fdc8757e3a0411f01dc2ab06304a92cf3502`.

O personalizer está disponível para Claude Code e Codex. A skill recupera contexto, entrevista o
operador, audita um projeto existente e adapta os guias dentro do escopo autorizado. O comando
`scripts/personalize.py` cria os registros; a leitura do código e a entrevista são feitas pelo agente.

O vault ganhou índices de produto, features, decisões e operação. Perfil, adoção, auditoria,
entrevistas e execuções recebem identidades estáveis. O modo de adoção fica em `onboarding.json`;
repetir o mesmo comando preserva as notas e evita repetir links. Desenvolvimento e produção têm
campos separados. O projeto usa a mesma identidade do vault de integrações.

O [README](../../README.md#processo-pt) e o [guia de uso](../USAGE.md#personalizer-pt) explicam
projeto novo, adoção e retomada. O processo em Mermaid mostra responsabilidades, decisões,
revisão, publicação autorizada e recuperação. O diagrama completo é expansível para manter a
página legível. Assets e estrutura visual foram preservados; a prosa PT/EN passou por humanizer.
AGENTS, CLAUDE e a skill passam a exigir atualização do README em cada implementação.

## Verificação local

| Verificação | Resultado observado |
|---|---|
| Suíte completa antes dos ajustes da revisão | 53 testes em Windows/Git Bash e Python 3.14.4: 49 aprovados; 4 casos de symlink sem privilégio, cobertos pelo CI Linux. |
| Regressão após os ajustes | 16 testes de personalizer e integrações: 14 aprovados; 2 skips de symlink. Os três novos testes falharam antes das correções. |
| Codex 0.146.0 | `personalizer` e `integrate-from-docs` descobertos pelo carregador real; agente de integração no catálogo de ferramentas da requisição ao modelo fictício local. |
| Claude Code 2.1.220 | Skills e agente encontrados na inicialização SDK; configuração MCP reconhecida sem conexão ao fornecedor. |
| Validação de skills | Instrução compartilhada e duas entradas nativas aprovadas pelo validador de skills. |
| Mermaid 12.0.0 em Chrome/Playwright | Diagramas PT/EN analisados e renderizados, 20 nós cada. Captura PT inspecionada visualmente. Navegador encerrado; zero processos do perfil de teste restantes. |

Os testes nativos usam usuário temporário. Não houve chamada paga de modelo, instalação de plugins
reais ou conexão MCP. Eles comprovam descoberta/configuração no escopo observado, não a qualidade
de execução dos modelos dos dois clientes. Os testes automatizados podem ser repetidos com
`python3 -m unittest discover -s tests -v`; o ensaio de clientes está em `tests/smoke_clients.py`.

## Ensaio de uso e recuperação

Um agente separado usou a skill em um projeto fictício de agenda local para barbeiros. O projeto
tinha Python, uma função `book`, um teste e um README que recomendava `npm test` sem `package.json`.
O operador simulado autorizou uma entrega de cancelamento local; hosting e produção permaneceram
desconhecidos. Esse ensaio avalia o fluxo da skill, não uma sessão real com cliente ou fornecedor.

A entrevista `initial-discovery` foi salva como pausada e retomada com o mesmo ID. O agente recuperou
respostas confirmadas, registrou as dúvidas e corrigiu o comando do README após inspecionar o projeto.
A feature `cancel-booking` definiu retorno do cliente, liberação do horário e `KeyError` para horário
inexistente. A implementação usou `dict.pop`, preservando `book` e o conteúdo do design.

O piloto registrou 1 teste no baseline, 2 falhas esperadas antes da implementação e 4 testes aprovados
ao final. O exemplo Python do README também foi executado. A primeira revisão ficou marcada como
própria. Depois, um revisor independente partiu do índice do vault e recuperou contexto, feature,
resultados, evidências, próximo passo e produção desconhecida. Ele repetiu os 4 testes e recompôs
o diff, que coincidiu com o registrado. O snapshot normaliza quebras de linha e não serve como prova
de preservação byte a byte do design.

O ensaio sem a skill já respeitava as respostas e a pausa, mas propunha um documento avulso. Com
personalizer, entrevista, perfil e entrega seguiram os mesmos índices e identificadores do harness.
As fixtures e capturas locais ficaram em `.runtime/personalizer-eval` e `.runtime/process-*.png`;
não fazem parte dos arquivos instalados no projeto consumidor.

## Achados e correções

1. Uma instalação anterior preserva `integrations.py`. A primeira implementação exigia um argumento
   novo desse helper e falhava na adoção. O personalizer agora usa a assinatura original e altera
   apenas seu metadado de origem; não exige substituir guias ou executar setup com force.
2. Um índice somente leitura permitia criar notas antes de falhar ao acrescentar links. Os índices
   que receberão links passam pela conferência de acesso antes da criação dos registros.
3. Um hardlink de índice permitia alterar outro caminho do mesmo arquivo. A validação compartilhada
   recusa hardlinks; o personalizer também os verifica antes de acrescentar links, inclusive com o
   helper anterior preservado pelo instalador.

O revisor reconferiu os três casos com o helper atual e com o arquivo real do commit base: seis
cenários aprovados, incluindo criação de feature e origem correta. Não encontrou novos problemas
nas correções examinadas.

O fluxo continua exigindo um escritor por checkout. A conferência prévia cobre falhas previsíveis;
não promete uma transação de filesystem diante de falha de disco ou alteração concorrente.

## Limites e próximo passo

Graphify e claude-mem ainda não são instalados nem sincronizados automaticamente. Os papéis de PM,
Tech Lead e revisão são responsabilidades documentadas, sem orquestrador autônomo. Publicação e
produção não foram exercitadas neste piloto.

O próximo incremento deve avaliar a recuperação e atualização da memória externa usando essas
notas como fonte, com isolamento entre projetos e retorno ao vault quando o serviço estiver indisponível.
O [contrato do personalizer](../superpowers/specs/2026-10-02-personalizer-design.md) delimita esta entrega.
