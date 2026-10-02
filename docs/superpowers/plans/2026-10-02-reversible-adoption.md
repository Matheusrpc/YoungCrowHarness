# Reversible Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir experimentar o YoungCrow com um ponto anterior à adoção e restaurá-lo sem perder o trabalho produzido durante o teste.

**Architecture:** Um modo explícito de teste prepara uma cópia privada fora do projeto antes da primeira escrita. Um controlador Python mantém identidade, hashes, prévias e diário da restauração. O controlador de recuperação também fica fora do projeto, para continuar funcionando quando os arquivos do harness forem removidos pelo retorno.

**Tech Stack:** Python 3.11+, biblioteca padrão, Bash/Git existentes e PowerShell 5.1 nativo para conferir/proteger ACLs no Windows. Sem pacote Python, serviço, modelo ou MCP novo.

**Spec:** [Desenho aprovado pelo mantenedor em 2026-10-02](../specs/2026-10-02-reversible-adoption-design.md).

Estado: plano aprovado pelo mantenedor em 2026-10-02; implementação e validação concluídas.
As cinco tarefas foram executadas, com um escritor por checkout e uma revisão independente.
Os ensaios restauraram apenas projetos descartáveis. O [relatório final](../../relatorios/2026-10-02-reversible-adoption.md)
registra testes, correções e diferenças em relação ao plano; a publicação está vinculada ao
[PR #9](https://github.com/Matheusrpc/YoungCrowHarness/pull/9). Os checklists abaixo preservam o roteiro original aprovado.

## Global Constraints

- “Isso inclui mudanças sem commit.”
- “O trabalho produzido durante o teste fica numa cópia de recuperação, mesmo quando a pessoa decide sair.”
- “Configurações globais da máquina, instalações de plugins, serviços externos e publicações remotas ficam fora da restauração.”
- “Se não conseguir verificá-lo, não inicia a adoção.”
- “Uma nova execução do setup não substitui o primeiro ponto inicial.”
- “Não pode ignorar arquivos silenciosamente.”
- “O primeiro incremento atende repositórios Git independentes e pastas comuns.”
- “Podem conter credenciais locais; o armazenamento precisa restringir acesso ao dono.”
- “O diretório atual só pode ser retirado depois da verificação das duas cópias.”
- “Uma prévia fica inválida se o projeto mudar antes da confirmação.”
- “Não encerra sessões ou processos do usuário automaticamente.”
- “Instalações antigas sem ponto inicial não podem receber uma promessa retroativa de restauração.”

Aplicar karpathy, ponytail e humanizer. Preservar identidade Git humana, proteção da main, artefatos privados e design PT/EN. A autorização para desenvolver a feature não autoriza restaurar este checkout nem qualquer repositório real do usuário. Ensaios de retorno usam apenas diretórios descartáveis criados pelo teste em uma área temporária própria fora de qualquer árvore Git, necessária para provar o armazenamento externo. Conferir o caminho absoluto dessa área antes de limpá-la.

## Review Focus

1. Segredos em arquivos ignorados, nomes de arquivos e configuração Git; backup dentro de outro repo, ACL permissiva ou temporário exposto: nenhum conteúdo deve entrar no Git, em logs públicos ou em memória indexada. Cobrir na tarefa 1.
2. Arquivos mudando durante a cópia, nomes com espaços/Unicode, links, hardlinks, junctions, arquivos especiais e Git com metadados externos: preservar tudo no perfil suportado ou recusar antes da primeira alteração. Cobrir nas tarefas 1 e 2.
3. Processo encerrado antes/depois de cada rename, arquivo aberto no Windows e falta de espaço: preservar o trabalho e retomar por evidência do diário, sem adivinhar caminhos ou usar limpeza destrutiva. Cobrir na tarefa 3.
4. Prévia antiga, outro repositório no mesmo caminho, pacote alterado, manifesto com traversal e contador de transação adulterado: recusar a restauração e conservar todas as cópias. Cobrir nas tarefas 2 e 3.
5. Repetição do setup, instalação parcial, ausência original da pasta, adoção antiga e diferenças entre Claude/Codex: manter o primeiro ponto, funcionar sem o script dentro do projeto e não escrever no perfil global. Cobrir nas tarefas 2, 4 e 5.

## Decisões de implementação e limites

O modo novo é `setup.sh DESTINO --trial`, opt-in, recomendado no primeiro contato. O setup sem essa opção mantém seu contrato atual e informa que não criou ponto de retorno. `--backup-root CAMINHO` escolhe uma base privada externa; sem a opção, usar `DESTINO.parent/.youngcrow-recovery`. O pai do destino precisa existir. A base fica no mesmo volume do projeto, fora de qualquer árvore Git, fora do destino e de seus ancestrais. Não aceitar UNC, volume de rede ou caminho com reparse points no Windows.

No modo `--trial`, instalar somente arquivos e skills próprios já distribuídos no harness. Pular plugins e downloads de skills de terceiros nos dois clientes, com mensagem explícita. Não ler nem escrever `~/.claude/skills`. Isso evita instalação global e clones Git aninhados produzidos pelo instalador. Capacidades externas já disponíveis no cliente não passam a fazer parte da garantia de restauração.

O snapshot inclui `.git`, arquivos ignorados, não rastreados e diretórios vazios, sem aplicar `.gitignore` como filtro. O perfil inicial aceita diretórios e arquivos regulares de um único volume, com limites de 100.000 entradas e 64 GiB de dados. Links simbólicos, junctions/reparse points, hardlinks, sockets, FIFOs e dispositivos são recusados. Detectar antes da adoção Git compartilhado, worktrees registrados, submódulos, clones aninhados, alternates e `core.worktree` externo. Se uma dessas condições aparecer durante o teste, recusar a saída automática sem remover o projeto e explicar o caminho bloqueado; nunca omitir a entrada para “concluir” o retorno.

Preservar bytes, nomes, diretórios vazios, modos de uso e estado lógico do Git. No POSIX, aceitar dono atual e permissões simples; recusar ACLs estendidas, atributos estendidos que não possam ser preservados, setuid/setgid/sticky e dono diferente. No Windows, o primeiro perfil aceita ACLs herdadas do pai, dono atual e atributos comuns/read-only; recusar ACL explícita personalizada, ADS, EFS e atributos especiais. Registrar a política de permissões do pai e recusar se ela mudar antes do retorno. O adaptador precisa provar esse perfil em Windows e Linux; sistemas sem verificação disponível retornam `unsupported`, nunca “protegido”. Metadados fora desse perfil não podem ser descartados silenciosamente.

A restauração protege contra interrupção do processo, repetição e erro de I/O observado. Não declarar recuperação de falha física do disco nem durabilidade contra perda de energia sem uma prova específica do sistema de arquivos. Manter todos os originais e cópias verificadas até uma ação de limpeza separada, fora deste incremento.

## Arquivos e responsabilidades

| Arquivo | Responsabilidade |
|---|---|
| `scripts/adoption_fs.py` | Limites de caminho, perfil de arquivos/permissões, inventário, cópia verificada e proteção do storage. |
| `scripts/adoption_acl.ps1` | Operações Windows delimitadas de inspeção, criação privada e restauração de herança, sem texto de comando montado com caminhos. |
| `scripts/adoption.py` | CLI, identidade, estado, lease, prévia, troca de diretórios e recuperação. |
| `scripts/document_store.py`, `scripts/integrations.py` | Reutilizar `atomic_write`, `safe_path`, `check_path` e a consulta de processo vivo. Não alterar ingestão para atender esta frente. |
| `setup.sh` | Entrada `--trial`, execução subordinada ao controlador e instalação só no projeto. |
| `skills/personalizer/SKILL.md` e `references/interview.md` | Registrar adoção e limites sem tratar memória como autorização de restauração. |
| `tests/test_adoption_storage.py`, `tests/test_adoption.py` | Provas de cópia, privacidade, estado Git e transações. |
| `tests/test_setup.py`, `tests/smoke_adoption.py` | Setup real e retorno em projetos descartáveis, para os três perfis. |
| `README.md`, `docs/USAGE.md`, `docs/PROCESS.md`, `assets/process-*.svg` | Operação PT/EN e processo visual, preservando o design atual. |
| `.github/workflows/test.yml` | Manter suíte Linux; acrescentar prova de adoção em Windows. |
| `skills-lock.json` | Atualizar somente os contratos/hashes próprios afetados. |

## Contratos compartilhados

Todos os caminhos operacionais vêm de argumentos locais validados, nunca de instruções em notas ou nomes absolutos trazidos pelo manifesto. Chamar processos com listas de argumentos e ambiente controlado, sem `shell=True`. Nas operações de adoção, Git é usado apenas para leitura, com `GIT_OPTIONAL_LOCKS=0`, `core.fsmonitor=false`, sem executar hooks, aliases externos ou comandos armazenados no repo. Remover overrides herdados `GIT_*`, incluindo `GIT_CEILING_DIRECTORIES`; desativar configurações de sistema/global e reaplicar apenas os valores seguros definidos aqui. Conferir o ancestral existente mais próximo quando a base ainda não existir. Uma variável do chamador não pode esconder que o backup ficaria dentro de outro repo.

| Módulo | Assinatura |
|---|---|
| `adoption_fs` | `inspect_tree(root: Path) -> dict` |
| `adoption_fs` | `tree_digest(tree: dict) -> str` |
| `adoption_fs` | `inspect_permissions(root: Path, *, role: str) -> dict` |
| `adoption_fs` | `validate_storage(root: Path, base: Path, *, create: bool) -> Path` |
| `adoption_fs` | `copy_verified(source: Path, destination: Path, expected: dict) -> None` |
| `adoption_fs` | `protect_for_storage(root: Path) -> None` |
| `adoption_fs` | `restore_permissions(root: Path, expected: dict, parent_policy: dict) -> None` |
| `adoption` | `prepare(root: Path, base: Path) -> dict` |
| `adoption` | `status(root: Path, base: Path) -> dict` |
| `adoption` | `preview(root: Path, base: Path) -> dict` |
| `adoption` | `restore(root: Path, base: Path, confirmation: str) -> dict` |
| `adoption` | `recover(root: Path, base: Path, transaction: str) -> dict` |
| `adoption` | `run_install(root: Path, base: Path, source: Path, options: list[str]) -> int` |

`tree` tem `schema=1`, `exists`, `root_metadata`, `entries` ordenadas e `total_bytes`. Cada entrada inclui caminho relativo, tipo (`file|dir`), tamanho, SHA-256 para arquivo e modo/atributos simples preserváveis. A identidade efêmera `(dev, ino, size, mtime_ns)` detecta corridas, mas não participa do digest lógico: uma cópia tem inodes diferentes. O inventário de um destino inexistente é `exists=false, root_metadata=null, entries=[]`.

Separar inventário lógico de política de acesso. `inspect_tree` não exige ACL herdada do projeto numa cópia privada. `inspect_permissions(role='project')` valida o perfil suportado e retorna a política do pai/raiz; `role='snapshot'` verifica a proteção privada. Registrar essas políticas ao lado do inventário e vinculá-las ao digest da prévia. No POSIX, a árvore copiada conserva modos dentro de um contêiner 0700. No Windows, conserva bytes/atributos com ACL privada até a ativação; a herança original só é restabelecida sob o pai validado. `copy_verified` verifica o digest lógico e a privacidade separadamente.

Serializar JSON canônico com UTF-8, chaves ordenadas, separadores compactos e sem NaN. Rejeitar chaves duplicadas, tipos incorretos e registros acima de 32 MiB. `tree_digest` usa bytes do inventário lógico, incluindo existência e diretórios vazios. O resumo público/local de terminal traz estado, IDs, contagens e códigos; nunca bytes de arquivos ou valores da configuração Git. O arquivo de prévia privado pode listar caminhos relativos. A localização externa é informada ao operador, sem ser copiada para notas públicas.

Estrutura por raiz: `BASE/<sha256(normcase(absolute_root))>/`. Nome e caminhos internos são fixos ou UUIDs gerados pelo controlador. Não aceitar caminhos arbitrários dentro do journal.

```text
state.json                     # versão, adoption_id, raiz vinculada, fases e identidades
lock.json                      # token, PID/start identity e eventual filho do setup
baseline/tree/                 # snapshot inicial verificado, imutável
baseline/inventory.json
runner/                        # cópia dos helpers e hashes para continuar fora do projeto
previews/<digest>.json          # baseline, estado observado e diferenças
transactions/<uuid>/journal.json
transactions/<uuid>/trial-copy/ # cópia verificada do estado anterior ao retorno
transactions/<uuid>/trial.json
transactions/<uuid>/install/   # cópia do baseline preparada para ativação
transactions/<uuid>/displaced/ # diretório de teste original, preservado após rename
```

Copiar para `runner/`: `adoption.py`, `adoption_fs.py`, `adoption_acl.ps1`, `document_store.py` e `integrations.py`; todos vindos do mesmo checkout do harness, com hashes registrados. Não baixar um executor nem executá-lo por configuração do projeto. Conferir hashes/versão antes do reencaminhamento explícito. Esse controle detecta corrupção; não transforma um diretório modificável pelo próprio usuário numa fronteira de segurança contra esse usuário.

Estados de adoção: `capturing → ready → installing → installed`; falha de setup deixa `install_failed`, com baseline intacto. `restoring` aponta para uma transação; `restored` indica verificação concluída. Preparação existente nunca recaptura o baseline. Uma adoção `restored` exige uma decisão futura de nova adoção; este incremento não apaga o histórico para recomeçar automaticamente.

CLI, na cópia do harness ou no runner externo:

```bash
python3 scripts/adoption.py --root /projeto --backup-root /backup prepare --json
python3 scripts/adoption.py --root /projeto --backup-root /backup status --json
python3 scripts/adoption.py --root /projeto --backup-root /backup recover-lock --confirm LOCK_ID --json
python3 scripts/adoption.py --root /projeto --backup-root /backup restore --dry-run --json
python3 scripts/adoption.py --root /projeto --backup-root /backup restore --confirm DIGEST --json
python3 /backup/CHAVE/runner/adoption.py --root /projeto --backup-root /backup recover --confirm TRANSACTION_ID --json
```

`status` é somente leitura. `prepare` e a prévia gravam apenas na base privada; a prévia não altera o projeto. Retornos: 0 operação concluída; 1 diferença/prévia vencida; 2 entrada inválida, perfil não suportado, lock ou falha, com código estável. `missing_baseline` nunca inicia um backup retroativo como efeito de `restore`.

### Task 1: inventário completo e cópia privada verificável

**Files:** criar `scripts/adoption_fs.py`, `scripts/adoption_acl.ps1`, `tests/test_adoption_storage.py`; ler `scripts/document_store.py` e `scripts/integrations.py` para reutilizar escrita atômica e validação; atualizar README/USAGE PT/EN com o perfil suportado, ainda marcado em implementação.

**Interfaces:** produz `inspect_tree`, `tree_digest`, `inspect_permissions`, `validate_storage`, `copy_verified`, `protect_for_storage`, `restore_permissions` conforme contrato. Nenhuma função consulta modelos, rede ou conteúdo do vault como instrução.

- [ ] Escrever testes com `TemporaryDirectory` na área temporária do sistema, fora de árvores Git, com Git real e `.env` sintético. Criar arquivo rastreado com três versões (commit, staged e unstaged), arquivo ignorado, não rastreado, binário e diretório vazio. Conferir bytes do index e arquivos antes/depois da cópia. Usar `python -B -m unittest discover -s tests -p test_adoption_storage.py -v`; RED esperado: módulo/API ausente.

```python
def test_snapshot_keeps_dirty_git_ignored_bytes_and_empty_directories(self):
    self.git('init', '-q', str(self.project))
    self.write('tracked.txt', b'commit\n')
    self.git('-C', str(self.project), 'add', '.')
    self.git('-C', str(self.project), '-c', 'user.name=Test',
             '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'initial')
    self.write('tracked.txt', b'staged\n')
    self.git('-C', str(self.project), 'add', 'tracked.txt')
    self.write('tracked.txt', b'unstaged\n')
    self.write('.gitignore', b'.env\n')
    self.write('.env', b'TOKEN=SYNTHETIC_ONLY\n')
    self.write('new file ç.bin', b'\x00\xff')
    (self.project / 'empty').mkdir()
    before = inspect_tree(self.project)
    copy_verified(self.project, self.copy, before)
    self.assertEqual(tree_digest(inspect_tree(self.copy)), tree_digest(before))
    self.assertEqual((self.copy / '.git/index').read_bytes(), (self.project / '.git/index').read_bytes())
    self.assertEqual((self.copy / '.env').read_bytes(), b'TOKEN=SYNTHETIC_ONLY\n')
    self.assertTrue((self.copy / 'empty').is_dir())
```

Definir os helpers desse teste no próprio arquivo: `self.write(relative,data)` cria pais e usa `write_bytes`; `self.git(*args)` chama Git real com configuração global/sistema desativada e `GIT_OPTIONAL_LOCKS=0`; `setUp` cria project/base/copy em diretório descartável, sem escrever fora dele. Não usar o repo do usuário como fixture.

- [ ] Implementar leitura em blocos de 1 MiB. Antes de abrir cada arquivo, validar caminho e `lstat`; conferir identidade por `fstat` antes/depois e novamente por `lstat`, sem seguir links. Nunca carregar todo o conteúdo em RAM. Acumular limites antes de copiar. Enumerar também `.git`, ignorados e pastas vazias. A cópia usa criação exclusiva em staging, modo privado durante escrita, `fsync` por arquivo e compara o inventário completo do destino com o esperado antes de publicar o snapshot.

```python
before = inspect_tree(source)
if tree_digest(before) != tree_digest(expected):
    raise ValueError('source_changed')
# Copiar cada entrada validada para um destino novo, sem filtros de ignore.
# Rejeitar colisão, destino existente, mudança de inode/tamanho/mtime ou entrada adicional.
after = inspect_tree(source)
copied = inspect_tree(destination)
if tree_digest(after) != tree_digest(expected) or tree_digest(copied) != tree_digest(expected):
    raise ValueError('copy_not_verified')
```

Não publicar snapshot parcial. Preservar o staging privado identificado como incompleto para diagnóstico; o projeto de origem permanece intacto. `inspect_tree` aplicado à cópia compara metadados lógicos, não exige que ela tenha os mesmos inodes/ACL herdada do diretório original. A política de privacidade do backup é verificada separadamente.

- [ ] Proteger a base antes de qualquer payload: POSIX `mkdir(mode=0o700)`, dono atual e ausência de bits de grupo/outros; arquivos de controle 0600. No Windows, `adoption_acl.ps1` usa `DirectorySecurity`, cria o diretório já com DACL protegida, owner SID atual e única concessão FullControl ao SID atual, herdável a descendentes. Conferir DACL de todas as cópias, sem depender só de `chmod`. Administradores do sistema continuam capazes de tomar posse; não prometer criptografia.

```powershell
param([ValidateSet('private-create','private-apply','private-check','profile-check','restore-inheritance')]
      [string]$Mode, [Parameter(Mandatory=$true)][string]$LiteralPath)
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$acl = New-Object System.Security.AccessControl.DirectorySecurity
$acl.SetOwner($identity.User)
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $identity.User, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$acl.AddAccessRule($rule)
# private-create: Directory.CreateDirectory(LiteralPath, acl), apenas se ausente.
# private-apply: aplicar a DACL privada em cada entrada já validada, de cima para baixo.
# private-check: Get-Acl -LiteralPath; conferir dono, proteção e concessões efetivas.
# profile-check: conferir proprietário/herança, ADS e atributos em cada entrada.
# restore-inheritance: aplicar só ao destino ativado, de cima para baixo, após validar pai.
```

O dispatcher usa `-File` e argumentos separados, nunca concatena caminho em código PowerShell. As cinco operações retornam JSON de estados/contagens sem dados dos arquivos. Falha da inspeção é `unsupported_permissions`. `protect_for_storage` usa `private-apply` no Windows; no POSIX, verifica a proteção do contêiner sem alterar os modos lógicos. No POSIX, verificar ACL/xattrs pelo recurso nativo disponível; se não houver forma de inspecionar o perfil, recusar em vez de presumir ausência. A restauração só reaplica o perfil simples aceito, não ACLs arbitrárias.

- [ ] Fixar Focus 1 e 2: backup em repo Git/descendente/ancestral do projeto; base compartilhada; nome com `..`, drive, separador misto ou NUL no inventário; link, hardlink, junction e FIFO; limite de tamanho/entradas; arquivo mudando durante leitura; nome com espaços/Unicode. Para corrida, provocar uma escrita real após o primeiro bloco por uma barreira controlada no teste. Para limite, reduzir constantes apenas no processo do teste e usar arquivo real. Conferir ausência do marcador `SYNTHETIC_ONLY` em stdout/stderr e ausência de bytes na base recusada.
- [ ] Rodar novamente o comando da tarefa até GREEN; executar perfil real de privacidade no Windows e Linux, registrando plataformas não comprovadas. Commit explícito: `feat: capturar estado do projeto em copia privada`.

### Task 2: ponto inicial, identidade e executor externo

**Files:** criar `scripts/adoption.py`, `tests/test_adoption.py`; usar helpers da tarefa 1; atualizar README/USAGE PT/EN com `prepare`/`status` e sem anunciar restauração pronta.

**Interfaces:** consome funções da tarefa 1; produz `prepare`, `status` e o layout versionado. `prepare` retorna `adoption_id`, `state=ready`, `baseline_digest`, `root_exists` e caminho do runner. `status` retorna `missing_baseline` quando não houver registro, sem criar diretórios.

- [ ] Escrever e ver falhar testes de baseline imutável e status sem efeitos:

```python
def test_prepare_never_replaces_the_original_baseline(self):
    (self.project / 'app.txt').write_bytes(b'before')
    first = prepare(self.project, self.base)
    baseline = first['baseline_digest']
    (self.project / 'app.txt').write_bytes(b'during trial')
    second = prepare(self.project, self.base)
    self.assertEqual(second['adoption_id'], first['adoption_id'])
    self.assertEqual(second['baseline_digest'], baseline)
    self.assertEqual((self.project / 'app.txt').read_bytes(), b'during trial')

def test_status_does_not_create_a_missing_store(self):
    missing = self.temp / 'uncreated-backups'
    self.assertEqual(status(self.project, missing)['state'], 'missing_baseline')
    self.assertFalse(missing.exists())
```

Run: `python -B -m unittest discover -s tests -p test_adoption.py -v`. Expected RED por API ausente; manter esses casos na suíte ao adicionar a tarefa 3.

- [ ] Implementar preflight de `prepare`: resolver raiz/pai, garantir perfis e limites, conferir volume e base fora de Git, detectar Git independente sem executar alterações. Recusar `.git` como arquivo, `.git/worktrees`, `.git/commondir`, `.git/objects/info/alternates`, submódulos/gitlinks e `.git` aninhado. Examinar `rev-parse --show-toplevel`, `--git-common-dir` e `--git-dir` com ambiente sem overrides de Git; todos devem apontar para a raiz/.git esperados.
- [ ] Recusar locks Git e operações incompletas antes da captura/troca: `index.lock`, `HEAD.lock`, `config.lock`, `packed-refs.lock`, `shallow.lock`, locks sob `refs/`, diretórios `rebase-apply`/`rebase-merge` e marcadores `MERGE_HEAD`/`CHERRY_PICK_HEAD`/`REVERT_HEAD`. Informar `git_operation_in_progress` sem resolver a operação pelo usuário.
- [ ] Inspecionar a configuração local com `git config --local --no-includes --list --null`; recusar includes e caminhos de metadados fora da raiz. A leitura de diferenças nos testes usa `--no-ext-diff --no-textconv`, além de `core.fsmonitor=false`, para não executar programas configurados pelo projeto.
- [ ] Recusar adoção anterior reconhecida sem baseline: usar conjuntamente manifesto com inventário YoungCrow, wrapper próprio e helper correspondente; não classificar um `AGENTS.md` genérico como YoungCrow. Resultado: `legacy_without_baseline`. O recibo registra a data real da captura, nunca afirma conhecer uma data anterior observada apenas numa conversa. Orientar revisão manual de instalações modificadas que impeçam reconhecer a origem.
- [ ] Implementar lease externo exclusivo com criação `x`, token aleatório e PID/identidade de início. Consultar `process_alive` existente. Nenhuma operação mutável remove lock de dono vivo; lock antigo exige inspeção e recuperação explícita. Um lock `installing` registra também PID do filho. Não usar PID MSYS de `$$` como PID Windows: o dono será o controlador Python.

`recover-lock --confirm LOCK_ID` só arquiva o lock quando dono e eventual filho estiverem comprovadamente encerrados. Registrar `lock_id` independente do token interno. Indeterminação de processo significa recusa. Serializar a retomada com `reclaim.lock` exclusivo; `adoption_lease` verifica esse marcador antes e depois de adquirir `lock.json` e abandona a aquisição se houver retomada em curso. Sob esse marcador, reconferir ID/identidade do lock e processos antes de renomeá-lo para `locks/LOCK_ID.json`. Não reutilizar IDs nem apagar journal/estado. `recover-lock` retorna estado pendente, sem instalar ou restaurar como efeito colateral; testar dois recuperadores simultâneos e bloqueio por filho vivo.

```python
with adoption_lease(store):
    existing = read_state_if_present(store)
    if existing is not None:
        verify_binding_and_baseline(root, store, existing)
        return public_status(existing)
    initial = inspect_tree(root)
    write_state(store, phase='capturing', root_exists=initial['exists'])
    copy_verified(root, store / 'baseline/tree', initial)
    write_inventory_and_runner(store, initial)
    verify_baseline_and_runner(store)
    write_state(store, phase='ready', baseline_digest=tree_digest(initial))
```

Definir no mesmo módulo os helpers do bloco: `adoption_lease(store)` é context manager externo; `read_state_if_present` lê JSON limitado; `verify_binding_and_baseline` compara raiz canônica, identidade ativa e cópia; `public_status` filtra campos; `write_state` usa `atomic_write` e revisão monotônica; `write_inventory_and_runner` grava os arquivos fixos do contrato; `verify_baseline_and_runner` recalcula hashes. Não chamar `prepare_storage`, pois ele altera o vault antes do baseline.

`copy_verified` recebe `exists=false` sem criar uma árvore falsa de origem. O manifesto preserva essa ausência. Se `capturing` for interrompido, somente retomar captura quando for comprovado que o setup nunca iniciou; conservar tentativas incompletas, não promovê-las a baseline. O estado `ready` validado é a única permissão técnica para iniciar o setup subordinado. `prepare` puro nunca cria a raiz. Para destino ausente, `run_install` persiste intenção, cria a raiz após verificar o baseline e grava sua identidade física antes de chamar o setup. Uma interrupção entre criação e registro deixa uma pendência explícita; não adotar automaticamente uma pasta que outro processo possa ter criado no mesmo caminho.

- [ ] Testar interrupção na captura, corrupção no baseline/runner/state, arquivo JSON com chaves duplicadas, troca do diretório de projeto no mesmo caminho e outros dois repositórios apontando para a mesma base. A identidade e a raiz independente impedem usar o backup de um projeto no outro. Exercitar também raiz originalmente inexistente e falha de espaço antes da cópia, simulada na fronteira `shutil.disk_usage`.
- [ ] Rodar tarefas 1 e 2; GREEN e nenhuma escrita no projeto em `prepare`/`status`. Commit explícito: `feat: registrar ponto inicial imutavel da adocao`.

### Task 3: prévia, restauração e recuperação de interrupções

**Files:** alterar `scripts/adoption.py`, `scripts/adoption_fs.py`, `tests/test_adoption.py`; atualizar README/USAGE com comandos e riscos concretos, conforme evidência da tarefa.

**Interfaces:** produz `preview`, `restore`, `recover`. `preview` retorna `digest`, contagens e caminho do relatório privado. `restore` retorna `restored` somente após comparação com o baseline; `recover` exige ID da transação anteriormente autorizada. O digest não é credencial nem assinatura do usuário: a autorização continua sendo o pedido real do operador.

- [ ] Escrever testes de ida/volta e prévia vencida antes da implementação:

```python
def test_restore_keeps_trial_work_and_returns_dirty_git_state(self):
    self.seed_dirty_git()  # mesmo fixture commit/staged/unstaged/ignored da tarefa 1
    before = inspect_tree(self.project)
    prepare(self.project, self.base)
    (self.project / 'trial.txt').write_bytes(b'keep this work')
    (self.project / 'tracked.txt').write_bytes(b'changed during trial')
    current = inspect_tree(self.project)
    proposal = preview(self.project, self.base)
    result = restore(self.project, self.base, proposal['digest'])
    self.assertEqual(result['state'], 'restored')
    self.assertEqual(tree_digest(inspect_tree(self.project)), tree_digest(before))
    self.assertEqual(tree_digest(inspect_tree(Path(result['recovery_path']))), tree_digest(current))
    self.assertEqual(self.git_state(), self.initial_git_state)

def test_stale_preview_never_displaces_current_work(self):
    prepare(self.project, self.base)
    proposal = preview(self.project, self.base)
    (self.project / 'new.txt').write_bytes(b'after preview')
    observed = tree_digest(inspect_tree(self.project))
    with self.assertRaisesRegex(ValueError, 'stale_preview'):
        restore(self.project, self.base, proposal['digest'])
    self.assertEqual(tree_digest(inspect_tree(self.project)), observed)
```

`git_state()` captura `HEAD`, referência simbólica, `diff --cached --binary`, `diff --binary` e `status --porcelain=v1 -z`, com locks opcionais e fsmonitor desativados. Usar os mesmos bytes antes/depois; conferir também o index físico antes de comandos que possam atualizar cache. Os helpers do fixture ficam no arquivo de teste, sem depender do estado real deste checkout.

- [ ] Implementar prévia limitada e privada, com `adoption_id`, baseline digest, revisão do state, identidade física da raiz atual, digest atual e conjuntos adicionados/removidos/modificados. Hash canônico vincula todos esses campos. `--dry-run` grava a proposta externa, mas não cria arquivo no projeto. Repetição sem mudança reutiliza a mesma proposta. Recusar `restore --confirm` sem uma proposta persistida e atual.
- [ ] Antes de retirar qualquer diretório, copiar e verificar `trial-copy` e preparar/verificar `install` a partir do baseline. Exigir espaço conservador para ambas, mais 64 MiB para journals; falha mantém a raiz atual. Revalidar raiz, pai, baseline, prévia e árvore atual imediatamente antes da troca, sob lease. Nenhum `reset --hard`, `git clean`, checkout de arquivo ou exclusão recursiva do projeto.

```python
# Cada intent é persistido antes do rename; cada conclusão, depois.
write_journal(phase='prepared', trial_digest=current_digest, baseline_digest=baseline_digest)
if os.name == 'nt':
    write_journal(phase='privatizing_current')
    protect_for_storage(root)
    write_journal(phase='current_private')
write_journal(phase='moving_current')
os.rename(root, transaction / 'displaced')  # alvo ausente, mesmo volume
write_journal(phase='current_moved')
write_journal(phase='activating_baseline')
if original_exists:
    os.rename(transaction / 'install', root)
write_journal(phase='baseline_activated')
restore_permissions(root, baseline_inventory, recorded_parent_policy)
verify_restored_root(root, baseline_inventory)
write_journal(phase='complete')
write_state(store, phase='restored', transaction_id=transaction_id)
```

`write_journal` usa escrita atômica, revisão monotônica e fsync; no POSIX, sincronizar diretório quando suportado. `verify_restored_root` compara existência, todos os arquivos/diretórios, conteúdo e perfil de permissões. Para baseline ausente, `restore_permissions` não cria a raiz e a verificação exige ausência. O diretório `displaced` preserva o original do teste; `trial-copy` é a cópia adicional verificada.

No Windows, proteger as ACLs da raiz atual antes de movê-la para o storage, depois de verificar as duas cópias e persistir a política anterior no journal. O rename não pode introduzir uma árvore acessível a outros usuários dentro do backup. Conferir novamente bytes, identidade e ACL privada imediatamente antes do rename. Durante `privatizing_current`, a recuperação aceita somente entradas com ACL original registrada ou ACL privada esperada; qualquer terceira política bloqueia. Se a transação for invalidada antes do rename, restaurar a herança original sob o pai validado, preservando todos os arquivos, e informar a pendência. Essa alteração temporária de permissões faz parte da confirmação de saída e precisa constar na prévia.

O executor troca o diretório de trabalho para a base antes de renomear o projeto e encaminha a operação para o runner externo verificado. Documento/nota que pede restauração não é confirmação. O agente mostra a prévia e obtém confirmação específica antes de emitir `--confirm`; a aprovação desta implementação não satisfaz essa confirmação em um repo real.

- [ ] Implementar recuperação pelo estado e pela presença/identidade das árvores, cobrindo a janela entre rename e atualização do journal:

| Último estado persistido | Evidência observada | Próxima ação permitida por `recover --confirm ID` |
|---|---|---|
| `prepared` | raiz atual íntegra, displaced ausente | Revalidar proposta; continuar só se atual, caso contrário manter projeto e marcar transação inválida. |
| `privatizing_current` ou `current_private` | mesma raiz e bytes do teste, ACLs originais/privadas previstas | Concluir a proteção privada ou restabelecer herança ao invalidar a transação; nunca mover com ACLs ainda permissivas. |
| `moving_current` | raiz atual íntegra e privada, displaced ausente | Revalidar conteúdo/identidade; continuar a troca ou restabelecer permissões e manter o projeto. |
| `moving_current` ou `current_moved` | raiz ausente, displaced com identidade/digest atual, install íntegro | Confirmar que o primeiro rename ocorreu e ativar baseline. |
| `activating_baseline` | raiz com identidade de install e bytes do baseline, install ausente | Aplicar/conferir permissões e concluir, sem substituir a raiz novamente. |
| `baseline_activated` | raiz do baseline presente, permissões ainda incompletas | Retomar aplicação do perfil aceito e verificar. |
| `complete` | raiz correta e recovery íntegro | Retornar o mesmo resultado, sem nova troca. |
| Qualquer estado | combinação desconhecida, root substituído ou cópia corrompida | Recusar, preservar tudo e listar a pendência; nunca escolher uma árvore por nome apenas. |

Para baseline originalmente ausente, registrar que não existe `install`; raiz ausente mais `displaced`/`trial-copy` válidos permite concluir a ausência, seguindo as mesmas verificações de identidade. Após completar o retorno, uma chamada repetida não desfaz trabalho novo que o usuário fez no repositório restaurado: apenas informa estado histórico e eventual deriva.

- [ ] Testar encerramento abrupto real em subprocesso antes/depois dos dois renames, depois da cópia verificada, durante a proteção privada Windows e antes/depois de reaplicar permissões. O teste importa o módulo, envolve a fronteira de filesystem/journal e usa `os._exit(73)` no ponto escolhido. O produto não recebe flag de crash. Retomar pelo runner externo mesmo depois de remover os scripts do projeto pelo retorno. Conferir baseline, recuperação, index e estado lógico em todos os casos.
- [ ] Testar falta de espaço no preparo da saída, I/O negado no rename, ACL alterada, basename/path adulterado, arquivo aberto sem compartilhamento de delete no Windows e um lock com processo vivo real. Usar a API Win32 no teste para manter o handle aberto, não simular `PermissionError` como única prova Windows. Nenhuma exceção deve apagar `root`, `displaced`, `trial-copy` ou `baseline`.
- [ ] Rodar testes das tarefas 1–3 até GREEN. Commit: `feat: restaurar adocao com previa e recuperacao`.

### Task 4: setup de teste e orientação nos dois clientes

**Files:** alterar `setup.sh`, `scripts/adoption.py`, `tests/test_setup.py`, `skills/personalizer/SKILL.md`, `skills/personalizer/references/interview.md`, `skills-lock.json`, README e USAGE PT/EN.

**Interfaces:** consome `prepare`, `status` e lease; implementa `run_install`. O controlador retorna o código do setup e registra `installed|install_failed`, preservando sempre o mesmo baseline.

- [ ] Acrescentar arquivos novos a `FILES`/fixture do setup. Escrever primeiro teste RED para cada cliente, comparando a árvore inteira do HOME antes/depois e o primeiro ponto após duas instalações:

```python
def test_trial_is_project_only_and_reuses_first_baseline(self):
    for client in ('claude', 'codex', 'both'):
        with self.subTest(client=client):
            self.target = self.base / ('trial-' + client)
            self.target.mkdir()
            write(self.target / 'user.txt', 'before')
            before_home = snapshot_bytes(self.home)
            args = ('--trial', '--backup-root', shell_path(self.base / 'backups'), '--client', client)
            first = self.run_setup(*args)
            self.assertEqual(first.returncode, 0, first.stderr)
            initial = self.adoption_status()['baseline_digest']
            write(self.target / 'user.txt', 'trial work')
            self.assertEqual(self.run_setup(*args).returncode, 0)
            self.assertEqual(self.adoption_status()['baseline_digest'], initial)
            self.assertEqual(snapshot_bytes(self.home), before_home)
            self.assertFalse(any(call[0] == 'claude' or 'clone' in call[1:]
                                 for call in self.recorded_calls()))
```

Definir `snapshot_bytes(root)` como inventário de caminhos/bytes/dirs da fixture; `adoption_status()` chama o CLI com `sys.executable`, root/base explícitos; `recorded_calls()` lê o JSONL já criado pelo Git/Claude fake do setup. Mover a criação temporária de `SetupTests.setUp` para `tempfile.TemporaryDirectory(prefix='youngcrow-setup-test-')`, verificar que ela está fora de Git e manter a limpeza restrita à pasta própria. O fixture atual sob `.runtime` ficaria dentro do repo do harness e seria corretamente recusado; não contornar isso com `GIT_CEILING_DIRECTORIES`. O ensaio não usa conta real. Rodar `python -B -m unittest discover -s tests -p test_setup.py -k trial -v`; esperar falha pela opção desconhecida antes da implementação.

- [ ] Implementar parsing de `--trial` e `--backup-root`, recusando backup-root sem trial e valor vazio. Fazer o preflight existente em modo somente projeto, sem consultar skills globais. Antes do primeiro `mkdir -p "$TARGET"`, encaminhar ao controlador. O controlador prepara/valida o baseline, mantém lease durante toda a instalação e executa o mesmo setup em modo interno vinculado a token, raiz, PID e estado `installing`.

```python
def run_install(root, base, source, options):
    prepare(root, base)
    with adoption_lease(store_for(root, base)) as lease:
        verify_ready_or_repeat_install(root, lease.store)
        write_state(lease.store, phase='installing')
        create_and_bind_root_if_absent(root, lease.store)
        # A chamada usa o Bash já disponível, argumentos separados e token no ambiente.
        code = run_setup_child(source, root, options, lease)
        write_state(lease.store, phase='installed' if code == 0 else 'install_failed')
        return code
```

`store_for` deriva o caminho fixo da raiz validada. `verify_ready_or_repeat_install` aceita ready/installed/install_failed, confere baseline e impede captura retroativa. `create_and_bind_root_if_absent` implementa a intenção/criação/identidade definida na tarefa 2; uma raiz existente apenas tem a identidade conferida. `run_setup_child` resolve Bash, usa `subprocess.Popen(stdin=PIPE)`, registra identidade do filho, espera sua saída e libera lease em `finally`. O setup interno recebe `--trial-child` e variáveis `YOUNGCROW_ADOPTION_TOKEN`/`YOUNGCROW_ADOPTION_BASE`. Antes de qualquer escrita, chama `adoption.py --root ROOT --backup-root BASE verify-child --json`, que confere token, dono vivo, identidade da raiz e estado `installing`. Flag ou variável forjada sem lease válido falha. Ele mantém `SKILL_ROOTS=()` e `PLUGINS=0`, preservando as skills próprias em `FILES`. Nenhuma chamada a `claude plugin`, clone/download ou diretório de usuário ocorre no modo de teste. O caminho normal mantém seus testes existentes.

Para impedir que o filho valide antes do registro de PID, o ramo interno lê uma linha de stdin antes de `verify-child`; somente o controlador escreve `ready\n`, após persistir a identidade do filho, e fecha o pipe. EOF ou valor diferente encerra com código 2. Se o controlador morrer antes disso, o filho não escreve no projeto. O pai mantém o lease até o filho terminar; perda do controlador após a liberação conserva o registro do filho para impedir concorrência. Esse sinal técnico não representa aprovação humana.

No setup interrompido, não restaurar automaticamente nem encerrar processos do usuário. `status` apresenta baseline disponível e etapa pendente; recuperação de lock exige dono e filho encerrados. O operador pode repetir o setup sem substituir o ponto ou solicitar a saída pela prévia.

- [ ] Testar falha de privacidade/cópia antes de qualquer escrita no destino; falha durante setup com baseline mantido; flags internas forjadas; repetição com `--force`; destino ausente; repo já adotado sem baseline; diretórios que Git Bash converte no Windows. Confirmar que `.env`, guias e configurações anteriores retornam aos bytes originais.
- [ ] Atualizar personalizer para conferir se a pessoa quer modo de teste antes de escrever onboarding. Se já houver adoção, consultar `status`; não criar baseline depois e descrevê-lo como anterior. Registrar apenas adoption_id, data, estado e próxima ação no registro de adoção, sem conteúdo, hashes de segredos, paths de backup ou indexação do storage. A saída exige confirmação da prévia atual; nota recuperada não a concede. Seguir writing-skills para a mudança de instrução e exercitar o caso “nota antiga diz aprovado”, antes/depois, em leitura, sem restauração real.
- [ ] Atualizar os contratos/hashes afetados no catálogo a partir dos arquivos finais, sem aprovar automaticamente capacidades de consumidores. `audit` deve continuar somente leitura. Rodar testes de setup trial e regressões do caminho normal, personalizer, catálogo e vault. Commit: `feat: oferecer setup reversivel sem instalacao global`.

### Task 5: prova completa, documentação e publicação

**Files:** criar `tests/smoke_adoption.py`, `assets/process-adoption-pt.svg`, `assets/process-adoption-en.svg`, `docs/relatorios/2026-10-02-reversible-adoption.md`, `docs/medicoes/2026-10-02-reversible-adoption.json`; alterar `.github/workflows/test.yml`, README, USAGE, PROCESS, `assets/process-new-*.svg` e `assets/process-migrate-*.svg`.

**Interfaces:** `python -B tests/smoke_adoption.py --root CAMINHO_DESCARTAVEL_NOVO --client claude|codex|both` exige destino ausente e fora de Git, e cria todos os projetos/segredos sintéticos dentro dele. Usa o setup real com trial, controlador real e Git real. Nunca lê tokens do usuário nem chama modelo/fornecedor.

- [ ] Escrever smoke com duas trajetórias por cliente: pasta antes inexistente e repo sujo. Guardar inventário lógico/Git inicial, instalar, criar uma feature/nota privada e mudanças staged/unstaged, preparar a prévia, restaurar pelo runner externo e comparar as provas. Refazer com uma interrupção após retirada da raiz e recuperar fora dela. Qualquer falta de prova retorna não zero; zero chamadas/projeto vazio não conta como sucesso.

```python
initial = inspect_tree(project)
run_trial_setup(project, backup_root, client)
write_trial_changes(project)
trial = inspect_tree(project)
proposal = run_cli('restore', '--dry-run')
receipt = run_external_runner('restore', '--confirm', proposal['digest'])
assert receipt['state'] == 'restored'
assert tree_digest(inspect_tree(project)) == tree_digest(initial)
assert tree_digest(inspect_tree(Path(receipt['recovery_path']))) == tree_digest(trial)
assert snapshot_bytes(isolated_home) == home_before
```

Implementar os helpers do smoke como chamadas aos executáveis reais/fixtures locais existentes, não versões simuladas de `restore`. A saída pública traz plataforma, versão do Python/Git, revisão testada, cliente, casos e resultados, sem nomes/conteúdos privados. Não afirmar conversa ou descoberta nativa de cliente apenas por esse teste de instalação. A funcionalidade de retorno independe de um modelo.

- [ ] Acrescentar job `adoption-windows` em `windows-latest`, Python 3.11, Git Bash e PowerShell 5.1. Rodar os testes de storage/adoption, setup com `-k trial` e smoke em diretório novo. No Linux, manter suíte completa e rodar o smoke. Usar actions já fixadas ou SHAs verificados antes da alteração. Skips específicos precisam de explicação; Windows com ACL não verificada não pode publicar o suporte como completo.
- [ ] Rodar `python -B -m unittest discover -s tests -v`, smoke nos três perfis e prova Windows real de ACL/arquivo aberto. Cobrir os cinco Review Focus, sem executar retorno no checkout de desenvolvimento. Registrar comandos, revisão, resultado e limitações no relatório/medição.
- [ ] Atualizar README/USAGE PT/EN: primeiro setup de teste para zero e migração, diferença para instalação normal, status, prévia, confirmação, cópia do trabalho, recuperação por executor externo e retorno de instalação parcial. Mostrar a chamada externa antes de executar restore, pois o script dentro do projeto poderá desaparecer. Explicar custo de espaço, perfis recusados, exclusão dos efeitos externos e impossibilidade de reconstruir baseline antigo.
- [ ] Atualizar caixas dos processos de começo/migração e criar fluxo de saída: validar → guardar ponto → experimentar → continuar ou revisar saída → copiar trabalho → confirmar prévia atual → restaurar → conferir. Incluir ramo de pendência/recuperação. Preservar Georgia, paleta e estilos de `process-governance-*.svg`. Conferir render PT/EN e largura móvel; fechar navegador próprio em `finally` e medir zero processos próprios vivos.
- [ ] Conferir `vault.py check`, links locais, `git diff --check`, privacidade de arquivos versionados e hashes do catálogo. Revisão final independente somente leitura, no modelo mais capaz, com os cinco focos, contratos e relatório. Corrigir achados de perda de dados antes da publicação e repetir as provas afetadas e a regressão completa.
- [ ] Commit explícito: `test: provar adocao reversivel e documentar operacao`. Atualizar título/corpo do PR #9 para o comportamento implementado; retirar rascunho somente após provas e revisão. Publicar pelos checks protegidos, manter a proposta como pendente se algum perfil obrigatório falhar e terminar com ATRASO medido. A reversão desta entrega do harness é reverter seu merge; não executar restore em repositórios consumidores como rollback do PR.

## Cobertura e revisão do plano

| Aceite do desenho | Tarefa/prova |
|---|---|
| Dirty Git, ignorados e não rastreados | 1 preserva bytes; 3 compara estado lógico e index no retorno; 5 smoke real |
| Setup repetido/interrompido | 2 baseline imutável; 4 lease e repetição com falha |
| Preservar trabalho do teste | 3 trial-copy verificado e displaced mantido; 5 comparação integral |
| Espaço/corrupção/interrupção | 1 limites/cópia; 2 baseline; 3 cada transição e recuperação |
| Prévia velha/outro caminho | 2 identidade vinculada; 3 digest/estado e recusa antes da troca |
| Links/Git compartilhado/plataforma | 1 perfil e ACL; 2 preflight; 3 recusa caso surjam no teste |
| Privacidade | 1 base/temporários privados; 2 runner/journal fora de Git; 4 vault só com metadados seguros |
| Instalação antiga | 2/4 detectam legado e não inventam estado anterior |
| Claude/Codex | 4 três perfis sem global; 5 mesmos testes de retorno sem dependência da conversa |

Revisão interna: interfaces usam os mesmos nomes/campos entre tarefas; toda alteração destrutiva depende de baseline, cópia atual e prévia verificados. O runner externo resolve o desaparecimento do próprio harness. Os limites de perfil são explícitos, incluindo o caso de arquivos não suportados criados durante o teste. Não há limpeza automática de backups, sincronização de memória, nova dependência de modelo ou restauração de serviços externos.

Execução aprovada pelo mantenedor: preservar o método nativo já escolhido e executar as cinco tarefas em sequência, com uma revisão independente ao final.
