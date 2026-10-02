# Fundação do YoungCrowHarness

Data: 2026-10-01

Estado: direção aprovada pelo mantenedor em 2026-10-01. O PR #1 reúne o instalador para Claude Code/Codex, o vault de integrações e o personalizer com entrevista retomável e adoção guiada. Sincronização externa de memória, governança técnica completa e orquestração autônoma continuam planejadas. O requisito R12 cobre a área de integrações. A especificação distingue a direção do produto das entregas já verificadas.

## Objetivo e público

O YoungCrowHarness deve permitir que desenvolvedores individuais e pequenos times conduzam trabalho assistido por Claude Code e Codex, desde uma ideia até uma entrega verificada. O projeto deve manter conhecimento recuperável entre sessões, governar o uso de capacidades e permitir adotar o processo em código existente.

O primeiro incremento melhora a confiabilidade do instalador atual. As demais frentes abaixo definem a direção do produto e terão especificações próprias antes da implementação. Esta especificação não autoriza publicar aplicações, instalar integrações externas ou alterar credenciais de projetos consumidores.

## Requisitos definidos com o mantenedor

| ID | Requisito |
|---|---|
| R01 | Atender desenvolvedores individuais e pequenos times com Claude Code e Codex. |
| R02 | Iniciar projetos do zero e migrar projetos ou harnesses existentes após diagnóstico. |
| R03 | Manter memória crescente em um vault compatível com Obsidian, com referências entre notas. |
| R04 | Organizar a navegação por um índice geral e microíndices por área e tema. |
| R05 | Recuperar o contexto de uma frente, suas decisões, trabalho em desenvolvimento e resultados em produção. |
| R06 | Permitir encontrar trabalho de outras instâncias e distinguir capacidades previstas das efetivamente utilizadas. |
| R07 | Catalogar agentes, skills e MCPs com finalidade, condições de uso e referências. |
| R08 | Criar uma skill personalizer que investigue a ideia e personalize o harness com perguntas fundamentadas. |
| R09 | Documentar features e dividi-las em pequenas entregas, com responsabilidades de PM, Tech Lead, implementação e revisão. |
| R10 | Avaliar Graphify e claude-mem para descoberta e continuidade de trabalho. |
| R11 | Manter o núcleo reutilizável, com configuração específica para cada projeto. |
| R12 | Reservar uma área do vault para integrações por fornecedor, com agente e skill especializados em implementar conforme documentação oficial, registrar evidências e permitir recuperação via índices e adaptadores de memória. |
| R13 | Ingerir documentos e referências acessíveis com Docling, incluindo áudio e vídeo suportados, preservar Markdown e origem no vault local e relacionar fontes, features e decisões. O conteúdo só pode ser versionado após revisão. |

## Escolhas propostas para esta direção

O vault principal ficará no repositório consumidor. Markdown, propriedades simples e links relativos permitirão consulta por agentes, GitHub e Obsidian. O conteúdo oficial continuará acessível sem um serviço de memória em execução. Índices derivados poderão ser reconstruídos a partir das fontes.

Essa localização integra a direção aprovada para o primeiro desenho do vault. O suporte a um vault central para vários projetos e a coordenação simultânea entre máquinas ficam para um desenho posterior. A primeira prova de continuidade será entre sessões usando o mesmo projeto e seu histórico versionado.

As configurações específicas de Claude Code e Codex serão pequenas adaptações de um contrato comum. A matriz de suporte deverá distinguir documentação, validação sintática e execução realmente testada. Não se presume equivalência entre hooks, permissões ou descoberta de MCPs dos dois hosts.

Graphify e claude-mem serão avaliados como integrações substituíveis. Nenhum dos dois será requisito do primeiro incremento. A compatibilidade, os custos de processamento, o isolamento dos dados e os modos de atualização deverão ser testados antes de selecionar versões suportadas.

## Duas entradas para o mesmo processo

### Projeto novo

O personalizer registra a ideia, identifica público e restrições e conduz perguntas conforme as respostas anteriores. Perguntas já respondidas em documentos não precisam ser repetidas. Dúvidas que exigem experimentação geram uma investigação delimitada, em vez de uma conclusão inventada.

O resultado é um perfil revisável: objetivos, requisitos, hipóteses, decisões, critérios de aceitação, capacidades necessárias, comandos de verificação e política de publicação. A entrevista deve poder ser interrompida e retomada. Sua conclusão depende de haver informação suficiente para a próxima entrega, não de atingir um número de perguntas.

### Projeto existente

A adoção começa com leitura de código, documentação, configurações e evidências disponíveis. O diagnóstico inventaria instruções, hooks, skills, MCPs, memórias, dependências e comandos existentes. Relata conflitos e separa comportamento observado, intenção documentada e informação desconhecida.

A migração apresenta os arquivos e capacidades que serão preservados, adaptados ou substituídos. Cada etapa registra o estado anterior, as alterações e sua verificação. Mudanças locais devem ser recuperáveis; alterações externas precisam de procedimentos próprios, pois uma branch não restaura credenciais ou instalações globais.

Histórico ausente continua identificado como desconhecido. Estado de produção exige evidência do ambiente e da versão observada. O encerramento da adoção requer uma pequena entrega que demonstre uso das instruções, consulta ao vault, verificação e atualização da documentação.

## Memória e navegação

O índice geral aponta para produto, frentes, arquitetura, integrações, capacidades e operação. Cada área contém microíndices conforme o volume de informação justificar. O microíndice de uma frente reúne contexto atual, entregas, decisões, resultados, referências e próximos passos.

Toda nota durável precisa de identidade estável, tipo, título, origem, data de atualização e vínculo com um microíndice. Notas relacionadas usam referências cruzadas. Uma decisão compartilhada possui um registro principal, referenciado por todas as frentes que dela dependem. Uma decisão substituída aponta para sua sucessora e continua disponível no histórico.

Uma frente pode ter uma versão em produção e outra em desenvolvimento. Esses estados são registrados separadamente, com referência à entrega correspondente. A produção registra ambiente, versão, evidência e data da última verificação; uma observação antiga não é uma leitura atual do ambiente.

O agente consulta o índice geral, o microíndice e os registros relevantes. A busca direta também é permitida, desde que a nota encontrada permita recuperar seu contexto e suas fontes. Informações recuperadas de documentos, ferramentas ou sessões não podem conceder novas permissões ou substituir instruções do operador.

Listagens mecânicas devem ser geradas quando possível. Resumos explicativos são revisados junto das entregas. O comando `scripts/vault.py check` verifica metadados, identidades duplicadas, referências locais quebradas, vínculos com microíndices e navegação a partir do índice geral. A checagem de encerramentos sem evidências continua planejada; o comando atual não certifica a veracidade de texto livre nem estado de produção. Veja o [contrato de uso](../../USAGE.md#vault-check-pt).

## Documentação e execução de integrações

A área `vault/integrations/` reunirá microíndices por fornecedor e integração. Cada registro liga documentação oficial e sua versão às decisões do projeto, código, testes, execuções, capacidades utilizadas e estados separados de desenvolvimento e produção.

O papel `integration-specialist`, com a skill `integrate-from-docs`, recebe o objetivo e a documentação do fornecedor, recupera o histórico, verifica as instruções aplicáveis à versão escolhida, implementa no escopo autorizado e registra os resultados. Fontes inacessíveis, instruções conflitantes ou versões incompatíveis ficam explícitas; exemplos do fornecedor não concedem permissões sobre ambientes ou credenciais.

O [contrato da área de integrações](2026-10-01-integration-knowledge-design.md) define organização, fluxo, memória, entregas e critérios de aceite. O núcleo local já oferece índices, notas sob demanda, agente/skill nos dois clientes e exportação com IDs/revisões. Graphify e claude-mem, quando habilitados e verificados, deverão indexar relações e observações com caminho de retorno ao vault. A sincronização automática continua como requisito para futuros adaptadores.

## Capacidades e registros de execução

O catálogo descreve a finalidade de cada papel, skill e MCP, quando utilizá-lo, suas dependências, origem, versão e permissões. Agentes carregam descrições resumidas para descobrir capacidades e abrem instruções completas apenas quando necessárias.

Cada entrega declara as capacidades previstas e o motivo. Cada execução registra as capacidades utilizadas, a identidade da execução, os resultados e suas evidências. Versões ou identidades indisponíveis ficam declaradas como desconhecidas. Capacidade recomendada não equivale a capacidade utilizada nem a autorização concedida.

A instalação de uma skill e a descoberta de um MCP são eventos diferentes da permissão para executar ações. O desenho de governança deverá definir o responsável por aplicar cada controle: host, credencial, verificação local ou ambiente de publicação. Instruções em linguagem natural não serão descritas como barreiras técnicas.

## Esteira de produto

| Responsabilidade | Saída verificável |
|---|---|
| PM | Problema, prioridade, resultado esperado e critérios de aceitação. |
| Tech Lead | Decisões técnicas, dependências e divisão em entregas pequenas. |
| Especialista em integrações | Fontes oficiais verificadas, integração implementada conforme a versão aplicável, testes e documentação ligada à frente. |
| Implementação | Mudança de código, testes pertinentes e documentação atualizada. |
| Revisão | Parecer sobre o diff, requisitos, evidências e riscos. |
| Publicação | Promoção autorizada, versão implantada, observação e recuperação. |

Os papéis podem ocorrer em sessões distintas, sem exigir vários agentes ativos continuamente. A independência da revisão deve ser explicitada quando exigida. Uma entrega passa por definição, preparação, implementação e revisão. Publicação se aplica quando fizer parte de seu escopo e houver autorização para o ambiente. Pesquisa e documentação podem terminar sem deploy.

## Primeiro incremento com escopo fechado

### Problema

O instalador atual preserva um ignore existente e cria `.env` sem conferir sua proteção. Também substitui placeholders de guias que informou preservar, aceita diretórios de skills sem verificar sua revisão e retorna sucesso depois de falhas na instalação de plugins.

As causas podem ser verificadas no commit auditado: [preservação e renderização](https://github.com/Matheusrpc/YoungCrowHarness/blob/ceb2274b8f0a1162b9f1b2319d8974bf2c142c2a/setup.sh#L30), [criação do env](https://github.com/Matheusrpc/YoungCrowHarness/blob/ceb2274b8f0a1162b9f1b2319d8974bf2c142c2a/setup.sh#L50), [skills](https://github.com/Matheusrpc/YoungCrowHarness/blob/ceb2274b8f0a1162b9f1b2319d8974bf2c142c2a/setup.sh#L58) e [plugins](https://github.com/Matheusrpc/YoungCrowHarness/blob/ceb2274b8f0a1162b9f1b2319d8974bf2c142c2a/setup.sh#L73).

### Comportamento esperado

1. Validar argumentos, ferramentas necessárias, manifesto e limites dos caminhos de destino antes de alterar arquivos. Um nome sem valor deve produzir uma mensagem de uso e código de falha.
2. Preservar os bytes dos guias existentes sem `--force`. Aplicar substituições somente a guias criados ou explicitamente substituídos. Um `.env` existente nunca deve ser sobrescrito, inclusive com `--force`.
3. Preservar regras existentes do `.gitignore`. Quando a regra raiz `/.env` precisar ser acrescentada, registrar essa alteração específica. Em um repositório Git, confirmar que o arquivo está efetivamente ignorado e não rastreado antes de criar um novo env. Se estiver rastreado, falhar com orientação sem remover arquivos do índice automaticamente.
4. Em uma pasta ainda sem Git, preparar a regra raiz de ignore antes de criar `.env`, sem inicializar um repositório no lugar do usuário. A mensagem deve distinguir proteção preparada de proteção efetivamente verificada pelo Git. Nesse cenário, a prova será inicializar Git na fixture de teste e verificar o ignore.
5. Recusar caminhos de arquivos gerenciados ou diretórios intermediários que sejam links simbólicos e possam redirecionar uma escrita para fora do destino. Links no caminho fornecido pelo usuário devem ser resolvidos antes da avaliação da raiz. A matriz de suporte deve declarar os limites dessa verificação em cada sistema testado.
6. Resolver o commit da skill humanizer a partir do manifesto. Uma instalação nova deve ser preparada em área temporária, verificada e só então ativada. Se existir uma instalação divergente ou modificada, preservá-la e retornar uma instrução de resolução, sem reset ou exclusão automáticos.
7. Diferenciar componentes instalados, preservados e pulados. Falha em uma operação de instalação solicitada retorna código diferente de zero e identifica a etapa. A ausência de Claude pode continuar pulando plugins, mas deve aparecer explicitamente no resumo. `--sem-plugins` mantém seu significado atual de pular plugins de marketplace.
8. Declarar as alterações no escopo do usuário durante a instalação de skills e plugins. Não anunciar instalação completa quando restar uma operação solicitada com falha. Logs e testes usam valores fictícios e não imprimem credenciais.
9. Atualizar a documentação bilíngue para refletir o comportamento implementado e seus limites.

O fluxo permanece baseado no instalador existente e nas dependências já utilizadas. Não haverá um serviço novo, framework de testes adicional ou instalação automática de Graphify e claude-mem neste incremento. `--force` continuará substituindo guias e configurações explicitamente gerenciados, mas não apagará regras existentes de ignore nem sobrescreverá credenciais.

### Limites da reprodução de plugins

O manifesto atual declara versões e revisões que o instalador não aplica aos plugins de marketplace. Este incremento deve remover a promessa de reprodução integral e explicar a limitação nos dois idiomas. A instalação da skill humanizer será verificada contra o commit do manifesto. A resolução imutável dos plugins de marketplace pertence à frente de governança de capacidades, com desenho e testes próprios; não será simulada apenas pela presença de números no manifesto.

### Critérios de aceitação

| ID | Cenário | Resultado exigido |
|---|---|---|
| A01 | Instalação em pasta nova com dependências simuladas | Arquivos esperados, placeholders preenchidos, proteção de env preparada e resumo correto. |
| A02 | Projeto Git com ignore existente sem env | Regras preservadas, env ignorado e ausência de valores reais nos logs. |
| A03 | Env já rastreado pelo Git | Falha antes das alterações gerenciadas; conteúdo e índice preservados. |
| A04 | Guia existente contendo placeholders, sem force | Conteúdo permanece idêntico. |
| A05 | Duas execuções válidas seguidas | Configuração e credenciais preservadas; sem regras duplicadas de ignore. |
| A06 | Falha simulada no checkout da skill | Instalação incompleta não é ativada; nova execução pode tentar novamente. |
| A07 | Skill preexistente na revisão incorreta ou com modificações | Diretório preservado; divergência reportada; código de falha. |
| A08 | Falha simulada em instalação de plugin | Resumo identifica o problema e código final é diferente de zero. |
| A09 | Plugin pulado por opção ou falta de Claude | Motivo declarado sem apresentar o componente como instalado. |
| A10 | Dependência ausente ou argumento incompleto | Falha compreensível antes de alterações. |
| A11 | Destino com espaços e force sobre arquivos existentes | Argumentos preservados, env intacto e regras de ignore conservadas. |
| A12 | Escrita gerenciada atravessa link simbólico | Operação recusada; destino externo permanece intacto. |

Os testes de regressão exercitarão o instalador real com Git e Claude simulados apenas nas operações externas. As verificações de ignore usarão Git real em repositórios descartáveis. Cada teste terá diretórios isolados, sem acessar a configuração pessoal ou a rede. A suíte deverá reproduzir as falhas pertinentes antes das correções e passar depois.

Uma automação de CI executará essa suíte em Linux. A verificação local com Git Bash será registrada separadamente; macOS e PowerShell nativo não serão anunciados como testados sem execução correspondente. Validação de JSON será descrita como sintaxe, não como prova de carregamento pelos hosts.

## Sequência das próximas frentes

| Ordem | Frente | Evidência necessária para encerrá-la |
|---|---|---|
| 1 | Instalador confiável | Critérios A01 a A12 demonstrados no escopo suportado. |
| 2 | Vault, índices e retomada | Uma sessão nova recupera uma frente e distingue desenvolvimento de produção; inclui área de integrações com fontes e microíndices. |
| 3 | Catálogo e governança de capacidades | Descoberta, resolução de versões e permissões verificadas por host; inclui integration-specialist e integrate-from-docs. |
| 4 | Personalizer e adoção | Entrevista retomável e migração de um projeto existente com alterações rastreáveis. |
| 5 | Integrações de memória | Comparação de recuperação, atualização, isolamento, custo e fallback; recuperação de integrações por fornecedor, tema e execução sem perder a referência ao vault. |
| 6 | Esteira e exemplo público | Uma feature percorre definição, entrega, revisão e publicação autorizada com evidências. |

Essa sequência organiza o produto. O [plano do instalador](../plans/2026-10-01-installer-reliability.md) registra o primeiro incremento. As demais frentes terão contratos próprios; o contrato de integrações acrescenta R12 sem acoplar sua implementação às correções já entregues do instalador.

O mantenedor acrescentou R13 e escolheu armazenamento local com publicação revisada. A [proposta de ingestão com Docling](2026-10-02-docling-ingestion-design.md) detalha o fluxo, a privacidade e as relações entre fontes. Seu desenho está em revisão; conversão e captura nos clientes ainda não foram implementadas.

O [contrato do personalizer](2026-10-02-personalizer-design.md) cobre a frente 4 e acrescenta índices de produto, features, decisões e operação à frente 2. A skill conduz a entrevista e a auditoria; o comando cria e preserva os registros. O [relatório do piloto](../../relatorios/2026-10-02-personalizer.md) registra a retomada de uma entrevista e uma entrega local. Esse ensaio não valida publicação em produção nem encerra as frentes 3, 5 e 6.

## Referências de desenho

- [Graphify](https://github.com/Graphify-Labs/graphify): candidato a descoberta estrutural e consulta de relações.
- [claude-mem](https://github.com/thedotmack/claude-mem): candidato a captura e recuperação de observações de sessões.
- [grill-me](https://www.aihero.dev/skills-grill-me): referência de investigação por perguntas; o personalizer acrescenta persistência e personalização do projeto.
- [Armazenamento do Obsidian](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data) e [links internos](https://help.obsidian.md/Linking+notes+and+files/Internal+links): base de interoperabilidade do vault.

As ferramentas candidatas foram consultadas durante o diagnóstico; sua integração com o YoungCrowHarness ainda não foi testada.
