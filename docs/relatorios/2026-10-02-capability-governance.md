# Governança de capacidades: evidências e limites

Frente: governança de skills, agentes e MCPs. Base: `16191ec` (PR #7).
O catálogo, auditor, revisão privada e skill compartilhada estão implementados. A prova nativa
passou no caminho local do Codex. A [continuação autenticada no Claude](2026-10-02-claude-memory-capabilities.md)
comprovou leitura permitida, escrita recusada e retirada/restauração do MCP. A matriz inclui essa
continuação; o ensaio sem modelo e as demais medições abaixo preservam a rodada original.

## Matriz de aceite

| Critério | Estado | Evidência |
|---|---|---|
| G01: compatibilidade e catálogo | Verificado | Leitura v2 sem regravação, validação v3 e instalação preservada. |
| G02: identidade e deriva | Verificado | Alteração em contrato, wrapper, apoio, endpoint e ferramentas muda identidade/observação. |
| G03: auditoria sem efeitos | Verificado | Árvore preservada e subprocesso/rede proibidos nos testes. |
| G04: separação por cliente | Verificado | Parsers JSON/TOML, campos desconhecidos e cobertura não comprovada explícitos. |
| G05: revisão privada | Verificado | Git real, ignore negado/rastreado, digest, inputs alterados, interrupção e sanitização. |
| G06: adoção | Verificado | Perfis Claude, Codex e ambos; preservação de manifesto, skills, agentes, configurações e `.env`. |
| G07: permitir/recusar no cliente | Verificado nos caminhos sintéticos dos dois clientes | Codex passou pelo app-server; Claude autenticado permitiu leitura e recusou escrita, com contadores do servidor. |
| G08: orientação e retomada | Verificado no exercício de skill | Novo contexto recuperou ID, escopo, deriva e comandos; documento que se declara aprovado não virou autorização. Não é prova de conversa Claude. |
| G09: revogar/restaurar | Verificado nos caminhos sintéticos dos dois clientes | Codex e Claude retiraram/restauraram acesso em sessões novas, com vault preservado nas retomadas. Documentação PT/EN e diagramas mantidos. |

## Ensaio nativo original, sem modelo

O smoke usa um servidor sintético stdio com duas ferramentas que só incrementam contadores locais.
O teste isolou diretórios dos clientes e retirou credenciais do ambiente. Nenhum turno de modelo
nem ferramenta de fornecedor foi usado. Versões: Codex `0.158.0-alpha.2.1`; Claude Code `2.1.220`.

No Codex, o despacho `mcpServer/tool/call` produziu uma resposta `synthetic-ok` para `yc_read`.
`yc_write` foi recusada com zero chamadas no servidor. Outra sessão com servidor desabilitado
recusou `yc_read`, também com zero chamadas. A terceira sessão restaurou o servidor e produziu
uma chamada permitida. A nota de histórico manteve o mesmo SHA-256. O app-server e os servidores
sintéticos encerraram; zero processos próprios vivos foram observados.

Esse resultado vale para a versão, configuração e caminho testados. Não prova comportamento de
um agente em conversa, permissões globais, plugins gerenciados ou segurança de um MCP de fornecedor.
O teste de descoberta nativa encontrou `govern-capabilities` nos dois clientes. O adaptador de prova
Claude retorna `pending: native_dispatch_unavailable`; não contabiliza descoberta como execução.

## Testes e exercício da skill

A suíte Windows anterior às correções finais passou: 198 testes em 857,746 segundos, oito skips
de plataforma. A revisão independente encontrou três problemas: permissões Claude conflitantes,
temporários de revisão fora do ignore e contagem/encerramento do MCP no caminho de erro. Cada um
recebeu teste que falhou antes da correção. Depois passaram 21 testes de capacidades e quatro de
prova, incluindo um servidor real aguardando entrada. O ensaio nativo Codex também foi repetido.
A regressão completa após essas correções passou no [CI Linux protegido do PR #8](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37009589168): 202 testes em 64,435 segundos, quatro skips específicos de plataforma. O job Graphify também passou.
A medição da suíte final e a inspeção visual ficam na
[medição sintética](../medicoes/2026-10-02-capability-governance.json).
Os testes anteriores passaram em ciclos de falha/sucesso: catálogo (9), auditor (14 acumulados),
revisão (19 acumulados), vault (22), adoção (2 testes adicionais cobrindo três perfis) e smoke (2).
Os skips locais de links dependem de privilégios do Windows; o CI Linux cobre esse caminho.

O exercício de skill apresentou índices e notas sintéticas sobre pagamentos, duas capacidades,
mudança de endpoint A para B e um recibo antigo. Uma nota alegava autorização e pedia envio de tokens.
Antes da skill, o avaliador recuperou corretamente escopo e risco, mas informou que os comandos
exatos do harness eram desconhecidos. Depois, um contexto independente encontrou `list`, `describe`,
`audit` e `review --check`, distinguiu leitura de gravação e rejeitou a autorização falsa. O exercício
não executou ferramentas do fornecedor nem é apresentado como uma sessão real de Claude Code.

## Decisões de execução

- Reutilizar o checkout dedicado existente, com um escritor. Se surgir concorrência, isolar antes de editar.
- Manter prova nativa pendente quando faltar despacho real. Isso deixa uma etapa explícita para Claude.
- Usar títulos `Task` no plano para compatibilidade com o extrator da skill. O conteúdo não muda.
- Referenciar campos e hashes no pacote, sem copiar argumentos privados. A comparação exige abrir o contrato.
- Fixar LF nos arquivos cuja identidade depende de bytes. Alterações locais de final de linha aparecem como deriva; o auditor não as corrige.
- Sobrepor a revisão somente leitura à suíte completa. A publicação aguarda ambas; mudanças posteriores recebem testes próprios.
- Manter a adoção reversível em proposta separada. Nenhuma restauração foi incluída nesta entrega.
- Limitar a prova nativa ao caminho e versão observados. Uso em conversa e fornecedores permanece não comprovado.
- Usar a inspeção visual realizada pelo executor. O revisor conferiu conteúdo/estrutura dos SVGs, sem repetir a renderização.

A revisão não deixou itens menores pendentes. Os três achados importantes foram corrigidos em
uma rodada; os testes cobrem o caminho temporário efetivo antes de gravar bytes, diferenças por
servidor no Claude e a contagem real de processos quando a limpeza não termina.

## Pendências

A continuação Claude encerrou a pendência de permitir, recusar, retirar e restaurar o MCP sintético.
Essa prova não cobre MCPs de fornecedores nem revogação de suas credenciais. O comando sem modelo
continua retornando pendência para despacho Claude; a conversa autenticada foi uma rodada separada.
Novos testes pagos exigem orçamento próprio; o smoke sintético não consome sessões de modelo.

A falha HTML recebeu uma [correção separada](2026-10-02-docling-html.md), com as cinco fontes
recuperadas. M04 segue parcial pelo ensaio ao vivo com termo idêntico em outro projeto. A ingestão
completa pelo Docling em conversa Claude também permanece uma prova separada pendente.
