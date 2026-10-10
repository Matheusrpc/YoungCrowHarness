# Diagnóstico do YoungCrowHarness para adoção pública

Frente: crítica técnica e preparação do brainstorming arquitetural.

Nota de publicação em 7/out: este é o diagnóstico histórico da versão inicial, anterior às
correções. `setup-results.json` acompanha a branch como resumo daquela execução. As referências
a `tracked-files.txt`, `github-metadata.json`, `reproduce_setup.py` e diretórios `setup-audit-*`
identificam evidências preservadas apenas no host original. O reprodutor espera os defeitos da
versão inicial e não deve ser usado para testar a implementação atual.

O YoungCrowHarness oferece uma base compacta de instruções para Claude Code e Codex. A principal distância até a ambição proposta é transformar regras escritas em comportamentos verificáveis. O instalador apresenta falhas reproduzidas de preservação e sinalização de erro; os controles de MCP, memória e entrega ainda precisam de definição operacional.

## Escopo e método

Revisão de 1 de outubro de 2026, no commit `ceb2274b8f0a1162b9f1b2319d8974bf2c142c2a`, copiado de `https://github.com/Matheusrpc/YoungCrowHarness` para `C:/Users/rmfon/YoungCrowHarness-review-20261001`.

As referências `arquivo:linha` abaixo são relativas a essa cópia. Links do código no GitHub devem usar o commit acima para preservar a evidência. Inventário: `docs/medicoes/tracked-files.txt:1–25`.

Foram lidos os arquivos de instruções, instalador, configurações, manifesto, README e skill própria. Os SVGs e a imagem da marca foram inventariados, sem auditoria visual. Foram executados testes do instalador inalterado, com diretórios de usuário descartáveis e ferramentas externas simuladas na execução final, além de validação sintática de Bash e JSON. Nenhum arquivo original versionado foi alterado; foram acrescentados apenas materiais da revisão. Não houve push, instalação real de plugins ou alteração de produção.

A skill `diagnosing-superpowers` foi solicitada pelo usuário. Seu procedimento original investiga transcrições de sessões; aqui se aplicou o princípio de achados com evidência, adaptado à crítica do repositório pedida pelo usuário. Não foram analisadas sessões, custos de modelos ou falhas do Superpowers. Karpathy e ponytail orientaram a busca da causa e de correções pequenas. Brainstorming foi iniciado para construir o plano com o usuário, sem tratar recomendações como decisões aprovadas.

## Veredito e pontos a preservar

O estágio demonstrado é o de um template opinativo com instalação parcial, adequado como ponto de partida para alguém capaz de completar a configuração. Ainda não há evidência para apresentá-lo como um processo completo e validado da ideia à produção. Essa avaliação decorre dos placeholders de testes e fronteiras (`CLAUDE.md:38–54`), do fluxo de instalação (`setup.sh:37–97`) e da ausência de suíte e automação de CI no inventário versionado (`docs/medicoes/tracked-files.txt:1–25`).

Há fundamentos úteis: exigência de evidência, preservação de trabalho alheio, isolamento por checkout, preocupação com idempotência de gastos e estado persistido (`CLAUDE.md:8–27`; `AGENTS.md:7–12`). README bilíngue, licença MIT e uma identidade autoral estão presentes (`README.md:25–89`, `README.md:95–158`; `LICENSE:1`). Esses elementos podem ser preservados enquanto a confiabilidade melhora.

## Achados prioritários

### 1. O instalador pode criar um env que o Git não ignora

**Prioridade alta. Reproduzido.** Se o projeto já tem um `.gitignore` sem a regra `.env`, o instalador preserva esse arquivo e cria `.env` mesmo assim. A mensagem afirma que ele está protegido. O teste com um `.gitignore` contendo apenas `node_modules/` produziu `.env` visível em `git status` e não ignorado por `git check-ignore`. Só foram usados valores fictícios. Não foi demonstrado vazamento de credenciais reais.

Causa: `setup.sh:30–38` preserva o ignore existente; `setup.sh:50–53` cria o env sem verificar a proteção. Evidência executada: `docs/medicoes/setup-results.json:6–10`; log detalhado no diretório de execução indicado na linha 45.

Direção de correção: verificar as regras efetivas antes de gerar credenciais locais, preservar regras existentes e falhar com uma instrução específica se não puder assegurar a proteção. O caso com `.env` já rastreado também precisa ser tratado; não foi testado nesta revisão.

### 2. O lockfile não determina as versões dos plugins instalados

**Prioridade alta. Confirmado por leitura e rastreamento das chamadas.** O manifesto contém revisão e versão ativa, mas o instalador só extrai nome, marketplace e origem. A instalação não usa nem verifica as revisões declaradas. Duas instalações em datas diferentes não têm a reprodução prometida garantida pelo harness.

Fontes: `skills-lock.json:3–11`; `setup.sh:75–84`; `docs/medicoes/setup-results.json:15–25`. A promessa de reprodução está em `README.md:65`.

O humanizer tem um commit fixo no script, mas esse valor está duplicado em vez de ser lido do manifesto (`setup.sh:62–64`; `skills-lock.json:14`). Uma pasta preexistente é aceita sem inspeção (`setup.sh:60–67`).

Direção de correção: tornar o manifesto a fonte efetiva de resolução; verificar identidade e conteúdo instalado; registrar divergências. A documentação oficial distingue a origem de um plugin do pino por `ref` ou `sha`: [fontes de plugins](https://code.claude.com/docs/en/plugin-marketplaces#choose-a-plugin-source). Fixar apenas o catálogo não prova que todas as dependências transitivas estão fixadas.

### 3. Falhas de plugins terminam com sucesso operacional

**Prioridade alta. Reproduzido.** O simulador fez todas as chamadas de marketplace e instalação falharem. O script emitiu avisos, retornou código zero e terminou com “Pronto”. Os avisos existem, mas automações não conseguem distinguir esse resultado de uma instalação íntegra pelo código de saída.

Fontes: `setup.sh:83–97`; `docs/medicoes/setup-results.json:12–26`.

Direção de correção: distinguir componente obrigatório, opcional e explicitamente pulado; agregar resultados e retornar falha quando um requisito obrigatório não for satisfeito. Verificar pré-requisitos antes das primeiras cópias também evitaria instalações parcialmente aplicadas (`setup.sh:27–43`).

### 4. Uma falha ao selecionar a revisão deixa uma instalação parcial aceita na retomada

**Prioridade alta. Reproduzido com Git simulado.** O clone simulado criou o diretório e o checkout simulado falhou. O script continuou. Na segunda execução, a existência da pasta bastou para pular o Git; nenhuma nova tentativa ou verificação de revisão ocorreu.

Fontes: `setup.sh:60–67`; `docs/medicoes/setup-results.json:28–36`. Este teste confirma o fluxo de erro do instalador, não uma falha atual do repositório upstream.

Direção de correção: concluir a instalação em uma área temporária, validar a revisão e só então ativá-la. Pasta existente precisa de verificação, não apenas teste de existência.

### 5. Arquivos preservados ainda podem ser modificados sem force

**Prioridade média. Reproduzido.** A função de cópia informa que manteve um guia existente, mas a substituição de placeholders roda depois sobre todos os guias. Um `CLAUDE.md` preexistente contendo `{{PROJETO}}` foi alterado sem `--force`.

Fontes: `setup.sh:30–46`; `docs/medicoes/setup-results.json:10`.

Direção de correção: renderizar apenas arquivos criados ou explicitamente autorizados para substituição. Uma evolução posterior deve prever migrações e apresentar o diff antes de modificar configurações existentes.

### 6. Regras de segurança não possuem execução correspondente no harness

**Lacuna de arquitetura. Confiança alta no escopo dos arquivos.** Os dois arquivos de hooks contêm chamadas ao detector de design do impeccable e aceitam sua ausência. Eles não implementam as restrições de escrita, o teto de gastos ou o gate de publicação descritos no guia. Isso não prova que o host esteja desprotegido: permissões nativas, configurações externas e proteções do GitHub não foram auditadas.

Fontes: `.claude/settings.json:3–24`; `.codex/hooks.json:3–26`; `CLAUDE.md:10–23`; `AGENTS.md:23–25`.

Direção de correção: identificar para cada regra quem a aplica, onde a decisão é registrada e qual teste demonstra seu cumprimento. Uma regra no prompt não deve ser apresentada como uma barreira técnica. Restrições importantes precisam existir também no host, nas credenciais e no ambiente de entrega apropriado.

### 7. A configuração de MCP é uma lista de conexões, sem política de uso

**Lacuna em relação ao objetivo solicitado.** O arquivo lista n8n e Cloudflare por URL. Não descreve ferramentas permitidas, ambientes, acesso a dados, responsável pela conexão ou condições para ações de escrita. O exemplo do n8n ainda requer substituição de domínio.

Fontes: `.mcp.json:1–12`; `README.md:49–50`. Não foram chamados esses servidores nem auditadas suas permissões reais.

Direção para o brainstorming: definir quais capacidades são necessárias por tarefa, como credenciais e aprovações são concedidas, e como registrar ações sem registrar segredos. A documentação oficial de [segurança do MCP](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) é referência para os limites de confiança e autorização; a existência de uma conexão não demonstra autorização segura.

### 8. Falta um contrato de continuidade entre sessões

**Lacuna em relação ao objetivo solicitado.** O guia manda persistir o estado, mas não define estrutura, pontos de atualização, recuperação, conflitos ou verificação de validade. As instruções de início só encaminham ao guia principal. Não há implementação de memória no inventário auditado.

Fontes: `CLAUDE.md:18–19`, `CLAUDE.md:44–54`; `AGENTS.md:3–12`; `docs/medicoes/tracked-files.txt:1–25`.

Direção para o brainstorming: separar estado atual da tarefa, decisões justificadas e evidências históricas; recuperar apenas o necessário e manter referências verificáveis. Uma memória útil precisa admitir correção, expiração e descarte. Texto recuperado de arquivos ou ferramentas não deve ganhar autoridade para alterar as regras do projeto.

“Infinita” deve significar, como objetivo de produto a confirmar, armazenamento extensível independente da sessão. Não deve prometer retenção ilimitada, recuperação perfeita ou contexto sem limites. Primeiro é preciso demonstrar retomada correta de uma tarefa em uma sessão nova; o mecanismo de indexação vem depois dessa necessidade comprovada.

### 9. Publicação imediata precisa de condições explícitas

**Risco de desenho, não incidente observado.** A lei 8 associa passar no QA a publicar na mesma janela e considera o trabalho aberto até estar em produção. O guia não define autorização por ambiente, revisão independente, execução de migrações, observação após deploy ou procedimentos de rollback. O AGENTS preserva as autorizações do operador, mas a relação entre essa obrigação e a lei de publicação fica implícita.

Fontes: `CLAUDE.md:22–42`; `AGENTS.md:4–6`. Nenhuma publicação foi executada ou observada.

Direção para o brainstorming: tornar explícitas as condições que permitem promover uma mudança e as condições que encerram uma tarefa de pesquisa, documentação ou implementação sem deploy. Automação de produção depende da política acordada, do ambiente e das evidências.

### 10. O suporte a dois agentes ainda carece de demonstração equivalente

**Lacuna de validação.** O instalador escreve skills em `~/.claude/skills`, usa `claude plugin` e termina instruindo a abrir `claude`. Copia hooks do Codex, mas não há teste versionado de carregamento, execução e resultado dos dois hosts.

Fontes: `setup.sh:58–97`; `.codex/hooks.json:1–29`; `docs/medicoes/tracked-files.txt:1–25`.

Os quatro JSONs são sintaticamente válidos, mas isso não valida o esquema dos hosts nem confirma que os eventos serão disparados. Não se conclui que os hooks do Codex são incompatíveis; sua execução permanece não verificada. Também não foram testados Linux, macOS, PowerShell nativo ou ACLs do Windows. O ambiente usado foi Windows com Git Bash e Python 3.14.4.

Direção de correção: publicar uma matriz pequena de versões e ambientes realmente testados, com configuração e teste de fumaça por agente. A instalação global de skills e plugins deve ter escopo visível e ser uma escolha deliberada (`setup.sh:59`; `skills-lock.json:6–18`).

### 11. A confiança pública precisa de provas de uso e manutenção

**Lacuna de adoção.** O inventário não contém testes, workflows de CI, exemplo completo, CONTRIBUTING ou SECURITY. No instante da consulta, a API pública retornou zero execuções de Actions, lista vazia de topics e `is_template=false`. Isso não determina a existência de proteções privadas ou testes externos.

Fontes: `docs/medicoes/tracked-files.txt:1–25`; `docs/medicoes/github-metadata.json:1–9`. O README explica instalação e configuração manual (`README.md:35–67`), mas não apresenta um caso completo com resultado verificável.

Direção para evolução: documentar limites e suporte; mostrar uma instalação limpa e uma adoção em projeto existente; demonstrar uma tarefa retomada em outra sessão e uma entrega com verificações. Medir tempo até o primeiro resultado, intervenção humana, sucesso de retomada e retrabalho ajudaria a avaliar impacto. Essas métricas ainda não foram medidas. Comparações futuras precisam manter tarefas, modelo e condições comparáveis; estrelas não substituem evidência de utilidade.

## Resultados executados e limites

| Verificação | Resultado observado |
|---|---|
| Sintaxe Bash do instalador original | Aceita pelo Git Bash |
| Leitura dos quatro JSONs | Válida; esquemas dos hosts não validados |
| Instalação com skills preexistentes simuladas | Criou os arquivos e retornou zero |
| Projeto com ignore preexistente sem env | Env ficou visível ao Git |
| Guia existente com placeholder | Modificado sem force |
| Falha em todas as instalações de plugins simuladas | Avisos, código zero e mensagem final de pronto |
| Clone simulado seguido de checkout com falha | Diretório parcial mantido e aceito na próxima execução |

Resultados: `docs/medicoes/setup-results.json:1–47`. Reprodutor: `docs/medicoes/reproduce_setup.py`. Os testes mantêm fixtures em `docs/medicoes/`; não executam correções no produto. A execução final usou exclusivamente os simuladores nas chamadas externas do setup. Duas tentativas anteriores exigiram ajustes no próprio ambiente de teste: conversão de caminhos e precedência do PATH do Git Bash. Na segunda tentativa, o Git real baixou a skill pública humanizer para o diretório descartável; não alterou a instalação pessoal. As pastas dessas tentativas foram preservadas e não fundamentam os resultados finais.

Não houve auditoria completa de segredos ou histórico, avaliação de ataques com modelos, teste dos MCPs remotos, execução real dos plugins, inspeção das regras de proteção do GitHub, benchmark de custo ou análise de sessões. Portanto, este parecer não certifica segurança nem eficácia em produção.

## Encaminhamento ao brainstorming

A transformação é arquitetural e precisa ser dividida em entregas avaliáveis. A ordem sugerida pelo diagnóstico é corrigir a instalação antes de ampliar integrações, definir controles com responsáveis claros, demonstrar continuidade de trabalho e só então ampliar a distribuição com provas públicas. É uma recomendação de prioridade, não um plano de implementação aprovado.

O usuário escolheu desenvolvedores individuais e pequenos times com Claude Code e Codex como público do primeiro lançamento. O objetivo refletido para o brainstorming é permitir adotar o harness em um projeto, retomar trabalho em outra sessão e avançar até produção com verificações claras. O plano seguinte deverá comparar abordagens, explicitar trade-offs e definir critérios de aceitação com esse público em mente.

Não há atribuição de defeito ao Superpowers. Sua presença no manifesto (`skills-lock.json:9`) não prova participação em nenhum incidente. O diagnóstico do repositório está registrado; o desenho e o plano permanecem em construção com o usuário.
