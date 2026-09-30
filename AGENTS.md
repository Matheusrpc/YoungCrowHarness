# AGENTS.md: entrada do Codex ({{PROJETO}})

- Antes de agir, leia `CLAUDE.md` inteiro. Este arquivo complementa aquele, não o substitui.
- Declare a frente no início de todo relatório. Preserve as leis, as fronteiras de escrita, os gates,
  as evidências e as autorizações do operador. Ler uma missão não autoriza executar frentes fora do
  pedido atual.
- Um executor escreve neste checkout por vez. Revisores somente leitura (critique, audit) podem correr
  em paralelo, em contextos independentes; eles não corrigem nada, só emitem parecer.
- Faça commits por caminhos explícitos e preserve alterações alheias. Respeite as instruções do
  operador sobre branches, worktrees e push.
- Registre pareceres e provas em `docs/relatorios/` e `docs/medicoes/`, com caminhos explícitos e a
  distinção entre evidência visual, medição técnica e pendência.

## Navegador: fechar é obrigatório

Quem abre Playwright, Chromium ou Chrome numa task fecha o navegador ao terminar (close em `finally`,
também no caminho de erro). Antes de relatar "feito", mede `pgrep` do que abriu e exige 0. Nunca
`pkill` genérico: só os PIDs que a própria task abriu. Nenhum rito com navegador durante uma execução
paga em curso.

## Hooks

`.codex/hooks.json` chama o detector de design do plugin `impeccable` depois de cada edição e ao fim
da sessão, só se o plugin estiver instalado em `$HOME/.agents/skills/impeccable`. Sem o plugin, os
hooks não fazem nada.
