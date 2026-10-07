# Onde executar / Where to run

## Português

O terminal aberto define onde o YoungCrow trabalha. Abra a pasta local no VS Code ou
a pasta do servidor pelo Remote SSH. No servidor ficam repositório, vault privado e banco
local. O operador prepara o SSH e autentica Claude Code/Codex naquele host pelos mecanismos
oficiais. Login no desktop não comprova login remoto.

Para começar do zero, escolha uma pasta cujo pai exista. Para migrar, use a pasta do
projeto existente. Execute o setup de uma cópia separada do harness. No Windows, use
Git Bash; `python` pode substituir `python3` conforme a instalação.

```bash
# Trial: baseline antes de personalizar; backups no mesmo volume e fora de Git.
bash /path/YoungCrowHarness/setup.sh /path/project --trial --client both --backup-root /path/private-backups --execution-location local

# Normal: sem ponto de retorno inicial. Use dedicated no terminal do runner.
bash /path/YoungCrowHarness/setup.sh /path/project --client both --execution-location dedicated --no-plugins
```

`--client claude`, `codex` e `both` usam os mesmos contratos. O trial instala apenas
arquivos do projeto. No setup normal, `--no-plugins` evita plugins de marketplace;
o download das skills previstas continua fazendo parte da instalação.

Depois do setup, na raiz do projeto:

```bash
python3 -B scripts/missions.py environment show --json
python3 -B scripts/missions.py environment configure --location dedicated --expected-digest DIGEST_ATUAL --json
python3 -B scripts/missions.py client environment --executable /path/to/sbx --json
```

Use o digest retornado pela consulta para uma mudança autorizada. `none` só vale quando
não há registro. Nesse caso, a consulta retorna `local/default`, sem gravar. O setup salva
`.operacao-local/execution/selection.json` com proteção privada e exclusão do Git.
Reinstalar sem flag mantém escolha e data; uma flag divergente recusa antes de copiar.
`--force` preserva seleção e helpers personalizados. Em conflito ou lock ocupado, consulte
novamente; não apague estado para forçar a troca.

Leia `phases` e `gaps`: cada consulta externa mantém limite de 30 segundos e 8 MiB.
Um timeout identifica uma consulta inconclusiva, sem provar bloqueio de rede. Etapas
independentes ainda podem produzir resultado. A consulta não inicia VM, instala dependências
ou autentica clientes. `runtime_profile_unverified` continua bloqueando execução; configuração
e planejamento estão disponíveis. Nenhum perfil de execução está certificado nesta versão.

O Personalizer lê preferência e respostas existentes antes de perguntar. Registre escolha,
origem e data no perfil, diferenciando padrão sugerido de resposta confirmada. Só configure
mudança autorizada. Reutilize cliente/modelo/effort por papel e não peça segredos. Selecionar
`dedicated` no computador local não conecta ao servidor nem transfere uma missão.

Após desconexão, reabra o mesmo host e consulte `yc-status` e recibos antes de executar
novamente. Fechar o editor não garante persistência. Supervisor, recuperação e transferência
de responsabilidade ainda têm entregas pendentes. Git não transporta o vault privado.
Agentes isolados continuam sem chaves/socket SSH, agent forwarding ou controle remoto do host.

No trial, conserve o caminho do runner de restauração retornado pelo setup. Use seu
`restore --dry-run --json` e confirme o digest atual antes de restaurar. Uma instalação sem
baseline não recupera retrospectivamente o estado original. `incompatible_recovery_runner`
preserva um restaurador antigo: encerre aquele trial pelo runner original antes da nova adoção.
Não substitua seus arquivos. `incompatible_helper` pede comparação e mesclagem dos helpers;
o setup conserva conteúdo humano.

## English

Open the project locally in VS Code or open the server folder through Remote SSH. Commands
operate on that host; repository, private vault and SQLite remain there. The operator prepares
SSH access and authenticates each official client on the host. Desktop login is not remote login.

Use the trial command above for an empty destination or an existing repository. Keep backups
on the same volume, outside Git, and run setup from a separate harness checkout. Trial captures
the baseline before selection or notes and installs bundled files only. Normal setup has no
initial restore point. `--no-plugins` skips marketplace plugins; declared skill downloads still
apply. On Windows use Git Bash and your Python 3 command. Select `claude`, `codex` or `both`.

`environment show --json` is read-only. Missing selection reports `local/default` without
creating state. Setup saves a private, Git-ignored preference. Use the current digest to
authorize a change; `none` applies only to an absent record. Reinstallation preserves choice
and timestamp, including with `--force`; a conflicting flag refuses before copying files.
Busy locks and stale digests require a fresh read, never deletion of state.

Diagnostics report bounded phases: external queries retain their 30-second, 8-MiB limits.
A timeout does not certify a network boundary. No VM starts, login, installation or model
calls occur. Empty execution profiles keep autonomous execution blocked even when prerequisites
are observed. Planning and configuration remain usable.

Personalizer reads preference and existing answers first, records source/date in the profile,
and changes selection only when authorized. Reuse role/client/model/effort choices; never ask
for secrets. Selecting `dedicated` does not connect or move an active mission. After disconnect,
consult `yc-status` and receipts on the same host. Persistence and ownership transfer still
require their own milestones. Git does not transport the private vault. Operator SSH grants
no SSH access to sandboxed agents.

For trial exit, keep the external restore runner, preview the return and confirm its current
digest. An incompatible older runner is preserved: use its original restore procedure before
a new adoption. Customized helpers are also preserved; compare and merge them when the CLI
reports `incompatible_helper`. Setup does not certify a remote server or native client execution.
