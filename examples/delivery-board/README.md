# Quadro de entregas / Delivery board

[Demonstração / Live demo](https://matheusrpc.github.io/YoungCrowHarness/) · [YoungCrowHarness](../../README.md) · [Vault](vault/index.md) · [Plano](../../docs/superpowers/plans/2026-10-03-public-pilot.md)

Este exemplo acompanha uma entrega desde a descoberta até a publicação. Os três itens de `data.json`
são fictícios; o estado real da demonstração fica no [registro de operação](vault/operations/index.md).
Node 24 executa os testes do exemplo. O instalador do harness continua independente de Node.

```bash
node --test tests/*.test.mjs
```

Execute na pasta `examples/delivery-board`. O modelo valida os dados e combina estado e busca.
A página usa controles nativos e mostra critérios e referências. O percurso local foi conferido em
1280px e 360px, com teclado, filtros vazios, limpeza e falhas de carregamento. Os dois consumidores
passaram por adoção e retorno no Windows e no Linux, com trabalho do trial preservado. Retomada nativa passou no Codex; Claude aguarda login. Publicação verificada, com revisão e hashes na operação.
As [medições e limitações](../../docs/relatorios/2026-10-03-public-pilot.md) detalham cada prova.

Para preparar uma prévia a partir da raiz do harness, escolha um destino novo fora da pasta do exemplo:

```bash
python -c "from pathlib import Path; Path('.runtime').mkdir(exist_ok=True)"
node examples/delivery-board/package.mjs .runtime/pilot-site REVISION
python -m http.server 8765 --bind 127.0.0.1 --directory .runtime/pilot-site
```

O primeiro comando cria o diretório pai da prévia, inclusive em um clone novo; funciona no Bash e no PowerShell.
Troque `REVISION` pela revisão Git de 40 caracteres obtida com `git rev-parse HEAD`. No PowerShell,
capture-a em `$revision = git rev-parse HEAD` e passe `$revision` no lugar de `REVISION`.
O gerador recusa destino existente, links de arquivo, dados inválidos e destinos dentro da origem.
Para repetir, escolha outro diretório novo. Abra `http://127.0.0.1:8765` e encerre o servidor depois da consulta.
O pacote contém apenas HTML, CSS, dois módulos, JSON revisado, a gema e `manifest.json`.
O manifesto associa hashes à revisão informada; ele não concede aprovação nem autentica o conteúdo.
Os links do vault usam a main; a prova externa conferiu os três destinos públicos.

O vault tem identidade própria e índices de produto, features, decisões, integração e operação.
Comece pelo índice geral e siga a frente. O setup não copia este exemplo para todos os consumidores.
Notas privadas em `vault/local/` ficam fora do Git. Fontes, backups e recibos nunca acompanham o site.

## English

This example follows a delivery from discovery to publication. The three entries in `data.json`
are fictional; the [operation record](vault/operations/index.md) holds the demonstration's actual state.
Run the command above from `examples/delivery-board`, with Node 24. The harness installer does not need Node.

The model validates input and combines status and search. The page was checked at 1280px and 360px,
with keyboard controls, empty results, reset and loading failures. To preview the allowed package,
run the commands above from the harness root. The first creates the parent directory, including on a fresh clone. Replace `REVISION` with the 40-character output of
`git rev-parse HEAD`; in PowerShell assign it to `$revision` and pass that variable. Choose a new
destination outside the source; existing destinations, linked files and invalid data are refused.
Open `http://127.0.0.1:8765`, then stop the server. The package contains six public files and a hash
manifest. The manifest records bytes and the supplied revision, not approval or authentication.
The external check verified all three public vault destinations.
Both consumers passed reversible adoption on Windows and Linux, with trial work preserved. Native retrieval passed in Codex; Claude needs a renewed login. Publication passed revision, hash and browser checks.
See the [evidence and limits](../../docs/relatorios/2026-10-03-public-pilot.md). The example has its own vault identity and linked
indices. Setup does not copy this example into every consumer. Private notes, source documents, receipts
and backups stay outside the public site.

## Começar do zero

1. Tenha uma cópia separada do harness, Git, Bash e Python 3. Node 24 é necessário para este quadro.
   Encerre os processos que escrevem no projeto. Escolha um pai privado fora de qualquer Git, no mesmo
   volume dos backups. O destino `meu-produto` ainda não pode existir.
2. No Bash, a partir da cópia do harness, execute o primeiro setup. Substitua os dois caminhos pelos seus:

   ```bash
   bash setup.sh /caminho/privado/meu-produto --trial --client both --backup-root /caminho/privado/backups
   ```

   No Git Bash do Windows, use caminhos como `/c/Users/voce/...`. Confira `state: installed` e guarde
   o caminho `runner` em local privado, fora do projeto. Não crie onboarding antes dessa captura.
3. Abra o consumidor no Claude Code ou Codex e peça: **“Use personalizer para adaptar este projeto à
   minha ideia. Registre respostas, limites e a primeira entrega no vault.”** O helper correspondente,
   executado na raiz do consumidor, é:

   ```bash
   python scripts/personalize.py init --mode new --run descoberta-inicial
   python scripts/personalize.py feature --slug primeira-entrega --run implementacao
   ```

   Esses comandos preparam notas; a entrevista e a implementação são trabalho do agente com você.
   O perfil guarda o problema, público, design, comandos verificados, autorização e critérios de aceite.
4. Implemente uma pequena entrega com teste, revisão e README. Neste exemplo, a primeira entrega é a
   lista; o filtro vem depois. Use os arquivos desta pasta como referência e mantenha a identidade do
   vault do seu produto. Não copie `vault/project.json` de outro projeto.
5. Retome por `vault/index.md`, o microíndice da feature e sua execução. Confira desenvolvimento,
   produção comprovada e próxima ação. Peça **“Use retrieve-memory para retomar esta frente e conferir
   suas evidências.”** Use Graphify apenas se houver seleção explícita; este percurso funciona em Markdown.

## Migrar um repositório existente

1. Encerre os escritores e use o mesmo comando de trial apontando para o repositório existente.
   Um Git independente pode ter alterações preparadas/não preparadas e arquivos ignorados. Links,
   worktrees e submódulos ficam fora do perfil atual; confira os [limites e requisitos](../../docs/USAGE.md#adocao-reversivel-pt).
2. Confira a captura e peça **“Use personalizer no modo existing. Audite código, instruções, testes,
   skills, MCPs, documentos e design; preserve as convenções do projeto.”** Execute o helper na raiz:

   ```bash
   python scripts/personalize.py init --mode existing --run auditoria-inicial
   python scripts/capabilities.py audit --client both --json
   ```

3. Registre o que preservar, adaptar ou criar em `vault/product/audit.md` e `adoption.md`. Resolva
   diferenças de configuração antes de ativar capacidades. A auditoria não inicia MCPs nem instala plugins.
   Acrescente referências ao perfil em CLAUDE/AGENTS preservando regras próprias. `--force` não substitui essa análise.
4. Escolha uma entrega pequena do seu produto, escreva o teste e implemente com revisão. Não substitua
   sua aplicação pelos arquivos deste quadro. O ensaio automatizado abaixo cria sua própria aplicação inicial
   e acrescenta o filtro, sem usar um repositório real do operador como fixture.

## Sair do experimento

Encerre os escritores. Use o `runner` externo retornado pelo setup, com os mesmos caminhos de projeto e backup:

```bash
python /caminho/runner/adoption.py --root /caminho/privado/meu-produto --backup-root /caminho/privado/backups restore --dry-run --json
# Leia a prévia; substitua DIGEST apenas depois de confirmar essa proposta.
python /caminho/runner/adoption.py --root /caminho/privado/meu-produto --backup-root /caminho/privado/backups restore --confirm DIGEST --json
```

O retorno preserva o trabalho do trial em uma cópia privada. Projeto novo volta à ausência; existente
volta ao estado capturado, incluindo Git. Mudanças após a prévia exigem nova conferência. O retorno não
remove sites publicados, dados de serviços ou configurações globais. Para interrupção, siga o
[procedimento de recuperação](../../docs/USAGE.md#adocao-reversivel-pt); conserve os backups e seus recibos.

## Reproduzir os ensaios sem chamar modelos

O ensaio usa setup, personalizer e retorno reais, com uma aplicação inicial sintética. Confirma a prévia
automaticamente apenas nas pastas descartáveis que ele próprio criou. Escolha uma raiz ainda inexistente,
fora de Git. As cópias privadas ficam preservadas para inspeção; uma repetição usa outro nome.

```bash
python -B tests/smoke_public_pilot.py --root /caminho/privado/ensaio-novo --client both
```

No Windows, execute da raiz do harness:

```powershell
python -B tests/windows_fixture_runner.py tests/smoke_public_pilot.py --root "$env:TEMP/yc-pilot-novo" --client both
```

O resultado separa testes, estado Git, restauração e preservação do perfil global de uma conversa nativa.
`model_calls: 0` não comprova que Claude ou Codex recuperaram a memória; essa prova é registrada separadamente.

## New project, migration and exit

For a new product, keep a separate harness checkout and choose private project/backup locations on the
same volume, outside every Git repository. Stop project writers. The new project directory must not exist.
Run the trial setup command above, verify `state: installed`, and keep its external `runner` path privately.
Only then start `personalizer` with `init --mode new --run initial-discovery` from the consumer root.
Ask the agent to interview you, record the product profile and define the smallest testable delivery.
The helper creates notes; it does not interview, implement or publish for you.

For an existing repository, run trial before the first adaptation. Use `init --mode existing --run initial-audit`
and the capability audit command above. Read the existing code, tests, client instructions, skills, MCPs,
documents and design. Record preserve/adapt/create decisions in the product audit and adoption notes.
Keep custom instructions and configuration; resolve differences before enabling anything. Do not replace
a real product with this example, and do not use `--force` as a migration strategy. Independent Git with
staged/unstaged changes is supported; linked paths, worktrees and submodules are outside this trial profile.

Implement a small change with a test, review and README update. Keep your product's vault identity.
Resume through the general index, the feature index and its run, or ask `retrieve-memory` to recover
the evidence and next action. Markdown works without Graphify; selecting the optional graph is explicit.

To exit, stop writers, request `restore --dry-run --json` from the external runner and review the current
proposal. Only then pass its digest to `restore --confirm DIGEST --json`. The trial work is preserved
privately; the initial new directory becomes absent again, and an existing repository returns to its
captured files and Git state. External sites, service data and global profiles are not rolled back.
See the [recovery procedure](../../docs/USAGE.md#reversible-adoption-en) for interrupted exchanges.

The automated commands above create synthetic consumers and automatically confirm restoration only for
those disposable fixtures. Use a fresh root for each run. Windows uses the existing fixture wrapper.
No model is called; successful setup and restoration do not establish native Claude/Codex retrieval.
