# Entrega: vault e especialista de integrações

Frente: R12 / integration-vault. Branch: `docs/youngcrow-foundation`, PR #1.

## Resultado

O setup instala índices de vault, skill compartilhada e entradas nativas para o especialista nos clientes selecionados. `scripts/integrations.py init` cria fornecedor, serviço, fontes, implementação, operação e execução, com links entre os índices. Preserva conteúdo existente; `--force` do setup não substitui notas do vault.

`export` gera um envelope local com identidade de projeto, UUIDs das notas, caminhos e hashes SHA-256. IDs permanecem estáveis ao renomear notas; duplicatas são recusadas. A saída fica `pending`: não transmite dados nem confirma indexação. O vault funciona sem serviço externo; Graphify e claude-mem têm um procedimento de handoff na skill, mas ainda não têm adaptadores automáticos validados.

## Evidência técnica

- Testes do vault: criação, repetição sem alterações, preservação de índice customizado, novas execuções, slugs inválidos, conflitos de caminho, projeto isolado, revisão alterada, renomeação e ID duplicado. O teste de symlink depende de privilégio no Windows e roda no Linux CI.
- Testes do instalador: componentes comuns e nativos, modos Claude/Codex/both, preservação com force e conflito de vault antes de qualquer escrita, além das regressões anteriores.
- Codex CLI 0.146.0: carregador real encontrou `integrate-from-docs`; a chamada inicial para um modelo **fictício local em loopback** expôs `integration-specialist` no catálogo de ferramentas de agentes. Nenhum modelo pago ou serviço de produção foi chamado.
- Claude Code 2.1.220: inicialização do protocolo SDK encontrou a skill e o agente, sem enviar turno de usuário ao modelo. Configurações MCP foram reconhecidas sem conexão.
- Os três arquivos de entrada da skill passaram no `quick_validate.py` com Python em UTF-8. A checagem padrão inicial do validador falhou por usar CP1252 no Windows; `-X utf8` resolveu a leitura, sem alterar os arquivos.
- Links locais das notas/documentação conferidos; sintaxe Bash e `git diff --check` verificados. Assets do design system sem alterações.

## Ensaio comportamental

Baseline sem skill: agente lidou corretamente com fonte inacessível e produção não comprovada, mas criou uma organização própria em `docs/integrations/`, sem o contrato compartilhado de IDs, índices e projeções.

Com a skill, um avaliador independente trabalhou em fixture isolada. Leu documentação fictícia local ExamplePay v2, implementou um cliente Python stdlib e passou em **7 testes com mocks**. Persistiu fontes, feature, decisão, implementação, operação, capacidades e execuções. O verificador da fixture conferiu **12 notas e 55 links**, IDs únicos e hashes de código/testes preservados.

Na execução seguinte, o cenário forneceu fonte v3 inacessível, versões divergentes e alegação antiga de produção. O avaliador registrou bloqueios, manteve a implementação v2 e produção **desconhecida**, sem inventar contrato ou verificar serviço externo. Graphify e claude-mem ficaram separadamente `unsupported`. O exportador atual também leu as 8 notas da integração resultante e retornou `pending`.

Um segundo agente recuperou fonte, adaptações, desenvolvimento, produção, testes, capacidades e próximo passo lendo apenas as notas. Na revisão de código identificou dois problemas materiais: links essenciais faltantes em índice de serviço existente e junctions não rejeitadas pelo fallback do Python 3.11. Ambos ganharam testes que falharam antes da correção; a proteção passou a usar os atributos de reparse do Windows, sem depender do método introduzido em Python 3.12, e os links faltantes são acrescentados preservando a prosa. O caminho de compatibilidade foi emulado no runtime atual; não foi executado Python 3.11 real no Windows.

O ensaio prova comportamento controlado e recuperação documental; não prova compatibilidade com um fornecedor real nem execução de modelo dentro de cada cliente. A descoberta nativa e o comportamento da skill são verificações separadas.

## Limites e operação

O guia PT/EN explica instalação do zero, adoção em repo existente, comandos, invocação e retomada. Migrações ainda exigem revisão humana dos guias/configurações preservados. A exportação contém o texto selecionado e não é um scanner de segredos: revise antes de transmitir. Serviços independentes devem começar com uma identidade própria; clones do mesmo produto compartilham `vault/project.json`.

I01–I03 têm o núcleo local disponível; I04 (adaptadores com sincronização, isolamento e invalidação comprovados) permanece pendente. I05 está coberto para falhas locais e comportamento da skill; falhas reais de provedores serão verificadas com os adaptadores. Personalizer e o restante da esteira de produto não pertencem a esta entrega.

Fontes de formato consultadas: [agentes Claude](https://code.claude.com/docs/en/sub-agents) e [agentes Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents). Candidatos de memória: [Graphify](https://github.com/Graphify-Labs/graphify) e [índice oficial claude-mem](https://docs.claude-mem.ai/llms.txt); nenhuma compatibilidade automática foi inferida dessas páginas.

ATRASO: produção do produto não aplicável | integração na main pendente de merge do PR #1.
