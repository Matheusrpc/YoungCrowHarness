# Primeira entrega: instalador e guia de adoção

Frente: confiabilidade do instalador e documentação de uso do YoungCrowHarness.

Entrega disponível no [PR #1](https://github.com/Matheusrpc/YoungCrowHarness/pull/1). Esta etapa implementa o primeiro incremento da [especificação](../superpowers/specs/2026-10-01-youngcrow-foundation-design.md), conforme o [plano](../superpowers/plans/2026-10-01-installer-reliability.md). O [guia de uso](../USAGE.md) cobre setup do zero, adoção manual de projeto existente e operação diária em português e inglês.

## Resultado

O setup valida entradas e caminhos antes das cópias; preserva guias existentes e `.env`; acrescenta proteção ao ignore; recusa `.env` rastreado; verifica a revisão e o estado da skill humanizer; ativa novas instalações somente após validação; retorna falhas de plugins como execução incompleta. Os assets do design system permaneceram intactos.

Estado de desenvolvimento: implementado, testado e revisado em branch dedicada. Estado de produção: nenhuma aplicação foi publicada; a integração do PR à branch principal é uma etapa posterior.

## Evidências

| Verificação | Resultado |
|---|---|
| Windows / Git Bash / Python 3.14 | 26 testes executados: 24 aprovados e 2 pulados por ausência de privilégio de symlink. |
| Linux / GitHub Actions | [26/26 aprovados](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/36941731261), incluindo symlinks, no commit `da84c1c`. |
| Sintaxe | Bash e JSON válidos; `git diff --check` sem erros. |
| Documentação | Links locais e referências a assets conferidos; assets sem alterações. |
| Revisão independente | Sem achados críticos ou importantes; uma observação menor abaixo. |

As regressões foram reproduzidas antes das correções: quatro falhas de validação inicial, oito de preservação/proteção e seis de instalação/verificação. Uma falha adicional identificou CRLF produzido pelo Python nativo do Windows em valores consumidos pelo Bash; a saída usada nesses valores passou a ter quebras LF explícitas.

Os testes usam Git local, usuário temporário e chamadas simuladas de rede/plugins. Não instalaram plugins reais nem acessaram MCPs reais. As evidências acima validam o instalador, não o funcionamento integral dos hosts ou de serviços externos.

| Critério | Evidência na suíte |
|---|---|
| A01 instalação nova | `test_new_project_then_git_ignores_env`, `test_full_install_and_repeat` |
| A02 ignore existente | `test_existing_ignore`, `test_ignore_missing_newline`, `test_ignore_negated_env` |
| A03 env rastreado | `test_tracked_env_blocks_all_writes`, `test_env_tracked_in_parent_repo` |
| A04 guias preservados | `test_existing_guide_is_preserved` |
| A05 repetição | `test_full_install_and_repeat` e repetição dos casos de ignore |
| A06 recuperação de checkout | `test_checkout_failure_can_retry` |
| A07 divergência de skill | `test_existing_skill_wrong_revision_is_preserved`, `test_existing_skill_dirty_is_preserved`, `test_existing_skill_cannot_inherit_parent_git` |
| A08 falhas de plugin | `test_plugin_failures_are_nonzero` |
| A09 componentes pulados | `test_plugins_skipped_explicitly`, `test_plugins_skipped_without_claude` |
| A10 preflight | argumentos, Python indisponível, manifesto inválido e pai ocupado por arquivo |
| A11 espaços e force | todas as fixtures usam caminho com espaços; `test_force_preserves_env_and_ignore` |
| A12 links | `test_dangling_env_link_is_rejected`, `test_directory_link_cannot_write_outside_project` |

## Decisões de execução e limites

1. Reutilizado o clone isolado e a branch existentes. Evitou novo checkout; se o isolamento estivesse errado, haveria risco de interferência, mitigado pelo único escritor e pela revisão somente leitura.
2. Controle de tarefas mantido manualmente porque os auxiliares da skill podem não interpretar cabeçalhos em português. Custo potencial: trabalho adicional de conferência; commits, testes e este relatório registram a conclusão.
3. Incluídos os guias bilíngues pedidos pelo mantenedor, preservando o design system. Custo: manter as duas versões sincronizadas.
4. Operações de Git ficaram em Bash e manipulação de arquivos em Python. Isso evita incompatibilidade entre Python nativo e wrappers do Git Bash; o custo de uma premissa incorreta seria corrigir a portabilidade, coberta pelos dois ambientes testados.
5. Validação real de plugins, hooks e MCPs permanece fora desta suíte. Custo: cada consumidor deve confirmar seu cliente e suas permissões antes de depender dessas integrações.
6. Versões de plugins de marketplace seguem como inventário. Custo: instalações podem variar ao longo do tempo; o README e o manifesto explicitam esse limite.
7. Vault, personalizer, Graphify, claude-mem e auditoria automática continuam no desenho de próximas entregas. Custo: a adoção e continuidade atuais dependem do rito manual documentado.
8. macOS e PowerShell nativo seguem sem verificação. Custo: suporte nesses ambientes exigirá uma execução própria.
9. O resultado Linux foi confirmado pelo executor após a revisão estática: 26/26 aprovados no run ligado acima.
10. Mantida a premissa documentada de uma execução por destino, sem proteção contra um processo hostil alterando caminhos entre preflight e escrita. A revalidação imediatamente antes de cada escrita prevista no plano não foi adicionada. Custo: não usar o instalador como fronteira de isolamento entre usuários/processos não confiáveis.
11. Humanizer-ptbr existente é preservada, sem validação integral nem atualização automática. Custo: o usuário precisa avaliar e atualizar sua cópia conscientemente.
12. Falhas tardias não desfazem etapas já concluídas. Custo: a execução pode deixar arquivos de projeto e componentes previamente instalados; o guia explica a repetição e o código de erro.
13. Preservação visual conferida por estrutura, referências e ausência de mudanças nos assets, sem nova renderização. Custo: diferenças de renderização do Markdown podem requerer ajuste posterior.

## Observação menor adiada

Se `.gitignore` já contém `/.env` antes de outras linhas, o instalador pode acrescentar a mesma regra no final. Isso é desnecessário, mas mantém a proteção e não cresce em repetições sem outras mudanças. Melhorar a detecção de proteção já efetiva e adicionar esse caso à suíte em uma entrega futura.

## Agentes, skills e ferramentas utilizados

Um implementador escreveu no checkout; um revisor independente examinou o intervalo `034bfb0..da84c1c` em modo somente leitura. Skills utilizadas na execução: karpathy, ponytail, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, verification-before-completion e finishing-a-development-branch, com planejamento e contexto recuperados dos documentos aprovados. O GitHub recebeu branch, PR e workflow de testes; a ferramenta do aplicativo vinculou o PR à conversa. Nenhum MCP de produto ou provedor de memória foi provisionado.

## Próxima frente

Detalhar a primeira entrega do vault e do personalizer a partir da especificação: índice geral, microíndices, identificadores, referências entre registros, estado em desenvolvimento/produção e distinção entre capacidades necessárias e efetivamente usadas. O novo trabalho deve retomar estes documentos e as pendências do PR, sem depender do histórico desta conversa.
