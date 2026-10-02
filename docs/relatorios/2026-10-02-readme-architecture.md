# README, arquitetura e plano do Docling

Frente: explicar a arquitetura do harness e preparar a execução do desenho aprovado de ingestão.
Data UTC: 2026-10-02. O mantenedor aprovou a especificação e pediu a refatoração do README, preservando o visual.

O README PT/EN agora apresenta as camadas do sistema, uma tabela de disponibilidade, a retomada pelo vault e as quatro entregas previstas para Docling. Dois diagramas novos usam a paleta e a tipografia existentes. Os seis diagramas de processo anteriores permanecem idênticos. A redação foi revisada com humanizer; karpathy e ponytail orientaram o escopo.

A especificação registra o desenho aprovado. O plano detalha sete tarefas em quatro entregas, com arquivos, interfaces, testes e documentação. O plano ainda depende da revisão do mantenedor antes de execução. Esta publicação não instala Docling, não cria a área privada de fontes e não ativa hooks de ingestão ou adaptadores de memória.

## Evidências

| Checagem | Resultado |
|---|---|
| Links e âncoras no README, especificações e plano | 76 referências locais válidas; IDs sem duplicação |
| Exemplos Python do plano | Análise sintática aprovada; não são implementação executada |
| SVGs de arquitetura | XML válido e nenhuma linha de texto excedendo a largura prevista |
| Seis fluxos anteriores | Imagens e referências preservadas; conteúdo dos SVGs idêntico à base |
| README no GitHub, revisão `007482a` | 8 imagens carregadas, visíveis e fora de seções recolhidas |
| Tela de celular | Diagrama com 324 px em viewport de 390 px, sem ultrapassar a largura; link para abrir em tamanho original |
| Vault atual | 3 notas e nenhuma ocorrência |
| CI da revisão `007482a` | [Execução aprovada](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/36954356536) |
| Navegadores da verificação | Encerrados em `finally`; 0 processos próprios restantes |

Capturas: [desktop](../medicoes/2026-10-02-readme-architecture-desktop.png) e [celular](../medicoes/2026-10-02-readme-architecture-mobile.png). A prova de largura não significa que todo o texto do diagrama seja legível sem ampliação no celular; o README também apresenta as camadas em texto e tabela.

## Revisão independente

Revisão somente leitura do intervalo `1781373b` até `007482a`: nenhum achado crítico, importante ou menor acionável. O parecer confirmou coerência PT/EN e distinção entre recursos atuais, desenho aprovado e integrações planejadas. Comparou as afirmações ao instalador, às skills e aos scripts existentes; verificou os seis SVGs anteriores, os novos XMLs e o validador.

Conversão real, captura de anexos, compatibilidade do SDK e segurança operacional de Docling ficaram fora do parecer, pois ainda não há implementação. A completude técnica do plano foi autorrevisada pelo executor; a revisão independente consultou seu escopo e estado. As medidas visuais foram obtidas pelo executor.

O [PR #5](https://github.com/Matheusrpc/YoungCrowHarness/pull/5) reúne a especificação, o plano, o README e este registro. O estado de publicação e o CI final ficam no PR.

ATRASO: main 1 (publicação pendente no momento deste registro; o estado final está no PR).
