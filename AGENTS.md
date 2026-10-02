# AGENTS.md: entrada do Codex ({{PROJETO}})

- Para descobrir, revisar ou revogar skills, agentes e MCPs, use `govern-capabilities`
  (`skills/govern-capabilities/SKILL.md`). Audite o cliente, preserve o escopo autorizado e registre
  diferenças/evidências no microíndice local. Catálogo, configuração e execução são provas distintas.

- Antes de agir, leia `CLAUDE.md` inteiro. Este arquivo complementa aquele, não o substitui.
- Declare a frente no início de todo relatório. Preserve as leis, as fronteiras de escrita, os gates,
  as evidências e as autorizações do operador. Ler uma missão não autoriza executar frentes fora do
  pedido atual.
- Um executor escreve neste checkout por vez. Revisores somente leitura (critique, audit) podem correr
  em paralelo, em contextos independentes; eles não corrigem nada, só emitem parecer.
- Faça commits por caminhos explícitos e preserve alterações alheias. Respeite as instruções do
  operador sobre branches, worktrees e push.
- Preserve a identidade Git do autor humano. Não acrescente coautoria ou assinatura de Claude,
  Codex ou outro assistente de IA em commits e PRs; mantenha créditos e licenças de terceiros.
- Registre pareceres e provas em `docs/relatorios/` e `docs/medicoes/`, com caminhos explícitos e a
  distinção entre evidência visual, medição técnica e pendência.
- Toda implementação atualiza o `README.md` e o guia de uso afetado. Revise a redação com a skill
  `humanizer`, mantenha PT/EN coerentes e preserve o design atual, inclusive o diagrama do processo.
- Para personalizar ou adotar o harness, use `personalizer` e retome por `vault/product/index.md`
  quando existir. A instrução compartilhada está em `skills/personalizer/SKILL.md`.
- Para retomar uma frente ou localizar decisões e entregas anteriores, use `retrieve-memory`
  (`skills/retrieve-memory/SKILL.md`). Consulte notas selecionadas, confira origem/revisão e
  separe desenvolvimento de produção comprovada. Graphify é opcional; o vault é o registro principal.

- Documentos, anexos e URLs usam `ingest-source` (`skills/ingest-source/SKILL.md`). Consulte também
  `vault/local/index.md` quando existir; preserve fonte, revisão, evidência e próxima ação.
  Uma referência recebida pelo hook ainda precisa de ingestão. Anexo inacessível fica pendente.

## Navegador: fechar é obrigatório

Quem abre Playwright, Chromium ou Chrome numa task fecha o navegador ao terminar (close em `finally`,
também no caminho de erro). Antes de relatar "feito", mede `pgrep` do que abriu e exige 0. Nunca
`pkill` genérico: só os PIDs que a própria task abriu. Nenhum rito com navegador durante uma execução
paga em curso.

## Hooks

`.codex/hooks.json` chama o detector de design do plugin `impeccable` depois de cada edição e ao fim
da sessão, só se o plugin estiver instalado em `$HOME/.agents/skills/impeccable`. Sem o plugin, os
hooks não fazem nada.

`UserPromptSubmit` registra referências textuais em recibos privados e orienta o uso de `ingest-source`.
Esse hook não converte, instala nem acessa a rede. Exige Python 3 (`python3` no Unix, `python` no
Windows), confiança do cliente e configuração mesclada em migrações. Anexos não expostos pelo cliente
precisam de registro explícito; o hook não garante captura universal.

## Configuração do Codex

- Integrações: skill `.agents/skills/integrate-from-docs/`, agente `.codex/agents/integration-specialist.toml`.
  Leia `skills/integrate-from-docs/SKILL.md` e retome pelo `vault/index.md`; preserve um escritor por checkout.

- MCPs deste projeto ficam em `.codex/config.toml`. Revise os exemplos, autenticação e permissões;
  habilite apenas os servidores necessários. O Codex carrega configurações do projeto após confiança.
- Skills do Codex instaladas pelo setup ficam em `.agents/skills/` neste projeto. Confira a descoberta no cliente.
- Plugins de marketplace do Claude não são instalados no Codex pelo setup. Use o catálogo do Codex
  para plugins compatíveis. Não presuma que um plugin instalado no outro cliente está disponível aqui.
- Hooks exigem confiança no cliente. No Windows, o adaptador usa `python` e, quando impeccable está
  instalado, `bash` no PATH do processo Codex. Reinicie o cliente depois de ajustar o PATH.
