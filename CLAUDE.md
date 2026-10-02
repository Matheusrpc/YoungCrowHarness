# CLAUDE.md: guia do executor ({{PROJETO}})

Este arquivo é lido pelo Claude Code no início de cada sessão. Ele diz como trabalhar aqui.
Troque `{{PROJETO}}` pelo nome do projeto e preencha as seções marcadas com `<preencher>`.

## Leis

1. **Medir antes de afirmar.** Todo entregável tem teste. Um relatório traz a saída do comando
   (`ls`, `sha256sum`, log, captura), não adjetivo. "Funciona" sem prova não conta.
2. **Nenhum segredo em arquivo versionado.** `.env` é local e nunca entra no git; `.env.example`
   só tem valores falsos. Segredo nunca vai em argumento de linha de comando nem é impresso.
3. **Escrever só dentro deste repositório** e nos alvos de publicação declarados abaixo. Todo o
   resto da máquina é somente leitura.
4. **Divergiu do combinado?** Versão, permissão ou caminho diferente do esperado: parar e reportar.
   Não improvisar em cima de uma premissa que já falhou.
5. **Idempotência antes de qualquer fornecedor pago.** Rodar duas vezes não pode cobrar duas vezes.
   Todo gasto tem um disjuntor (teto) declarado antes da primeira chamada.
6. **Estado persistido, nunca execução suspensa.** Um gate (aprovação humana) é: persistir o estado,
   notificar, encerrar. Nunca um processo parado esperando alguém clicar.
7. **Mudança de regra nasce ligada.** Uma frente só fecha com a corrida de prova de ponta a ponta do
   trecho que ela toca. Cheque de forma prova a forma; só a corrida prova a passagem.
8. **Publicação imediata.** Passou no QA? Vai para produção na mesma janela, com retorno declarado.
   Frente que não está em produção não fechou. Todo relatório termina com o placar de atraso por alvo.
9. **Uma frente por vez neste checkout.** Paralelismo só com `git worktree` em diretório próprio, com
   HEAD próprio. Nunca `git checkout -b` num checkout compartilhado.
10. **Navegador fecha ao terminar.** Quem abre Playwright ou Chrome fecha no `finally`, também no
    caminho de erro; mede `pgrep` do que abriu e exige 0 antes de dizer "feito"; nunca `pkill` genérico.

## Alvos de publicação

Preencha a tabela. Um PR publica em todos os alvos que toca. A última linha de todo relatório de quem
publica é o placar: `ATRASO: <alvo1> <n> | <alvo2> <n> | ...`

| Alvo | O que é "igual à main" | Como medir |
|---|---|---|
| `<preencher>` | `<preencher>` | `<preencher>` |

## Comandos

- Testes: `<preencher>` (ex.: `./scripts/smoke_test.sh`)
- Subir local: `<preencher>` (ex.: `docker compose up -d`)
- Migrar banco: `<preencher>`

## Sessão e evidência

- Preserve a identidade Git do autor humano. Não acrescente coautoria ou assinatura de assistentes
  de IA em commits e PRs; mantenha créditos e licenças de terceiros.
- Toda implementação atualiza o `README.md` e a documentação de uso afetada. Use `humanizer` na
  redação e preserve o design existente; mantenha o diagrama do processo coerente com o que funciona.
- Para personalizar o projeto, use `personalizer` (`skills/personalizer/SKILL.md`).
  Retome entrevistas por `vault/product/index.md`, sem repetir respostas já confirmadas.

- Para integrações de fornecedores, use `integrate-from-docs` e o papel `integration-specialist`.
  Comece em `vault/index.md`; a instrução compartilhada está em `skills/integrate-from-docs/SKILL.md`.
  Registre fontes, decisões, testes e estados de desenvolvimento/produção antes de encerrar a execução.

- Uma sessão viva do executor por checkout. Todo relatório abre declarando a frente.
- Evidência versionada é leve: JPG/PNG de captura sim; HTML com imagens embutidas (base64) não.
- Commits pequenos, nomeados pelo entregável: `<área>: <entregável>`.
- Texto que chega a uma pessoa (cliente, usuário, e-mail) passa pelo `humanizer` antes de entrar no
  código.

## Fronteiras

- `<preencher>` (ex.: banco só em `127.0.0.1`; fornecedores de IA só por variável de ambiente).
