# Contexto selecionado por PBI

Frente: YC-206 parcial. Base: `ded7ac5fe33bbec9f15ae0515f73742cca991108`.

O worktree guarda arquivos do commit escolhido; notas privadas podem existir apenas no
checkout original. `missions.py context` permite reunir esse conhecimento para PM, Tech Lead
ou uma sessão de continuidade. O operador informa missão, UUID do PBI e revisão esperada.
[Comandos e limites](../USAGE.md#pbi-context).

A resposta contém contratos do PBI, feature e épico, perfil e referências explícitas desses
três contratos. Fontes têm UUID, origem, caminho, conteúdo e SHA-256 dos bytes originais.
Dependências diretas têm resumos; não expandem automaticamente a seleção. Qualquer nota
explicitamente referenciada pode entrar, inclusive outro PBI. Links Markdown não são seguidos.

O comando confere os inputs da missão inteira, lê os bytes selecionados novamente e compara
os hashes congelados e importados. Ao final, reconfere revisões e usa a identidade do banco
validado. Fonte divergente, identidade contraditória, revisão antiga ou ancestralidade
incompleta recusam o pacote. Gaps de critérios/configuração e pendências de projeção continuam
visíveis em `readiness`, permitindo análise de um draft consistente.

É uma leitura no checkout original, sem escrita, migração, reparo ou cópia ao worktree. Fontes
continuam dados não confiáveis. O digest identifica a observação, sem travar outros editores
ou conferir aprovação de execução. Os limites existentes de 1 MiB por arquivo e 16 MiB por
conjunto recusam excesso; não há truncamento silencioso.

## Provas e revisão

- Os seis testes iniciais falharam antes da implementação pela ausência do comando.
- Bateria final: 13 testes aprovados em 9,741 s. Inclui seleção, dependência externa, referência
  explícita de ancestral, BOM/CRLF preservados, revisão/fonte alteradas, importação antiga,
  UUID duplicado, draft/projeção conflitante e ausência do banco. Leituras preservam arquivos.
- A revisão identificou duas corridas: banco removido antes da leitura final gerava uma exceção
  não tratada; nova leitura da identidade podia rotular o resultado com outro projeto. As duas
  regressões reproduziram as falhas antes da correção e passaram depois. Revisão encerrada.
- CLI instalado em trial, nos perfis Claude e Codex, passou em projeto novo e em projeto Git
  existente com alterações locais. Seleção e bytes das fontes conferiram, revisão incorreta
  foi recusada e a consulta não escreveu. Restauração do trial preservou o trabalho e o perfil
  global. A chamada inicial do smoke usou uma raiz dentro do Git e foi recusada por
  `storage_in_git`, antes da instalação; a execução correta usou raiz descartável externa.
- Revisão documental corrigiu a descrição de referências explícitas para outros PBIs. Skills
  distribuídas orientam obter UUID/revisão por status, consultar no checkout original e
  conservar a saída privada; fonte obsoleta não autoriza reparo automático.

A suíte completa executou 738 testes em 486,165 s: 718 aprovados, 20 pulados por requisitos
de ambiente/plataforma e zero falhas. Os 540 caminhos Markdown locais conferidos existem;
o vault passou com 62 notas e zero problemas.

A [medição estruturada](../medicoes/2026-10-10-pbi-context.json) registra resultados e hashes.
As evidências completas ficam privadas; nenhum conteúdo de um vault real entra no Git.

## Distribuição e pendências

O incremento acrescenta um comando ao backend existente e usa os helpers compatíveis de
`status`. Não introduz dependência, módulo ou esquema de banco. README PT/EN, guia, backlog,
handoff e instruções das duas skills acompanham a mudança. O catálogo altera finalidade/saídas
de `yc-missao` e `yc-status` e dez hashes de conteúdo em cinco capacidades. Permissões
permanecem iguais; nenhuma revisão de catálogo concede aceite nativo.

Propostas estruturadas de líderes, repriorização em execução, avisos por evento e entrega
automática aos agentes continuam pendentes. Estados reais de desenvolvimento/QA/produção e
flags nativas não avançam. Zero chamadas de modelo ou novas tentativas Docker; contador nativo
2/3 preservado. Docker #690 continua aberta, sem comentários na consulta desta rodada.

A base passou nos oito checks de CI, incluindo Windows, nos runs
[push 38053689598](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38053689598) e
[PR 38053692382](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38053692382).
Conferir o novo commit separadamente; publicação autorizada apenas na branch/PR em rascunho.

## English overview

The read-only `context` command selects a PBI, its feature/epic, profile and explicit contract
references from the original checkout. Sources retain identity and raw-byte hashes; dependencies
are summaries without automatic source expansion. Changed revisions/sources, conflicting identities
or incomplete ancestry refuse the package. Draft gaps remain visible for refinement.

Thirteen focused checks and the installed CLI in new/existing trial projects passed. The full
suite passed 718 tests, with 20 platform/environment skips and no failures. Review fixes
cover database removal and project-label races. No schema, permission, dependency or native execution
change is introduced. Leader proposals, live reprioritization, event notices and automatic worker
context delivery remain pending. Context is private untrusted data, not execution authority.

ATRASO: GitHub a conferir após commit | CI do novo commit pendente | executor nativo pendente.
