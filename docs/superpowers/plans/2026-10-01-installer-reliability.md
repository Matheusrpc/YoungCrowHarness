# Installer Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir o instalador para preservar configurações, proteger o env, verificar a skill instalada e retornar falhas confiáveis.

**Architecture:** Manter a entrada Bash e o uso existente de Python e Git. Fazer verificações antes das escritas e manter os testes em um único arquivo Python com biblioteca padrão. As chamadas externas do instalador serão interceptadas nos testes; as operações locais de Git continuarão reais.

**Tech Stack:** Bash, Python 3 com unittest e pathlib, Git e GitHub Actions. Sem dependências Python adicionais.

**Spec:** [Fundação do YoungCrowHarness](../specs/2026-10-01-youngcrow-foundation-design.md), seção “Primeiro incremento com escopo fechado”. Aprovada pelo mantenedor em 2026-10-01. Este plano ainda aguarda revisão e escolha do método de execução.

## Global Constraints

- “O fluxo permanece baseado no instalador existente e nas dependências já utilizadas.”
- “Não haverá um serviço novo, framework de testes adicional ou instalação automática de Graphify e claude-mem neste incremento.”
- “Um `.env` existente nunca deve ser sobrescrito, inclusive com `--force`.”
- “`--sem-plugins` mantém seu significado atual de pular plugins de marketplace.”
- “Cada teste terá diretórios isolados, sem acessar a configuração pessoal ou a rede.”
- “Uma automação de CI executará essa suíte em Linux.”
- “A verificação local com Git Bash será registrada separadamente; macOS e PowerShell nativo não serão anunciados como testados sem execução correspondente.”
- Alterar somente os arquivos desta entrega. Preservar os relatórios e fixtures locais do diagnóstico fora dos commits.
- Os números de versão no manifesto não provam reprodução de plugins. Esta etapa corrige a documentação dessa limitação e fixa a skill humanizer conforme o manifesto.

## Review Focus

1. Destino dentro de um repositório pai: detectar env rastreado e ignore efetivo a partir do diretório correto. Teste na tarefa 2.
2. Ignore sem quebra de linha e com negação de env: acrescentar uma regra válida sem corromper ou duplicar o conteúdo existente. Teste na tarefa 2.
3. Diretório de skill existente pertencente a outro repositório ou com arquivo não rastreado: não confundir um HEAD herdado do diretório pai com uma instalação íntegra. Teste na tarefa 3.
4. Links simbólicos pendentes e diretórios gerenciados já ocupados por arquivos: recusar antes da primeira escrita. Teste na tarefa 1.
5. Git Bash alterando PATH e conversão de caminhos: os testes devem provar que executaram os simuladores; wrappers não podem deixar passar clone remoto ou Claude real. Teste de isolamento na tarefa 1 e execução na tarefa 4.

## Arquivos e responsabilidades

| Arquivo | Mudança |
|---|---|
| `setup.sh` | Argumentos, preflight, cópia, ignore, instalação verificada e resumo de resultado. |
| `tests/test_setup.py` | Suíte de regressão isolada, com ferramentas simuladas e repositórios Git temporários. |
| `.github/workflows/test.yml` | Executar a suíte em Linux sem credenciais de fornecedores. |
| `README.md` | Comportamento real, pré-requisitos, teste e limites de suporte em PT e EN. |
| `skills-lock.json` | Ajustar somente nota/nota em inglês para distinguir inventário de plugins de pino da skill. |

Os trechos abaixo são instruções de implementação, ainda não executadas. As linhas do instalador referem-se ao commit base `ceb2274`; localizar as funções pelo nome conforme as primeiras tarefas moverem linhas.

## Tarefa 1: Preflight e fronteiras de escrita

**Arquivos:** criar `tests/test_setup.py`; modificar `setup.sh:11-29` e a entrada da função `copiar`.

**Interfaces:** preservar `bash setup.sh DESTINO [--nome|--name NOME] [--force] [--sem-plugins|--no-plugins]`. Adicionar `falhar(mensagem)` com saída 1 e erro em stderr; argumentos inválidos saem com 2. Preflight não escreve arquivos. Testes chamam `run_setup(*args, env=None)` e recebem `subprocess.CompletedProcess[str]`.

- [ ] Criar a fixture de testes com `unittest.TestCase`, `TemporaryDirectory`, uma cópia do harness e um diretório de usuário exclusivo. Descobrir Bash e Git com `shutil.which`; no Windows aceitar `C:/Program Files/Git/bin/bash.exe` e `C:/Program Files/Git/cmd/git.exe` como fallback. A ausência deve falhar com mensagem, não pular silenciosamente a suíte.

O helper de subprocesso usa timeout e captura. A conversão POSIX só é usada nos argumentos entregues ao Bash; chamadas diretas ao Git/Python usam caminhos nativos:

```python
def shell_path(path):
    value = Path(path).absolute().as_posix()
    return '/' + value[0].lower() + value[2:] if os.name == 'nt' else value

def run_setup(self, *args, env=None):
    child = self.child_env.copy()
    child.update(env or {})
    return subprocess.run(
        [self.bash, '-c',
         'export PATH="$TEST_BIN:/usr/bin:/bin"; exec /usr/bin/bash "$@"',
         'test-setup', shell_path(self.source / 'setup.sh'),
         shell_path(self.target), *args],
        env=child, cwd=self.source, capture_output=True,
        encoding='utf-8', errors='replace', timeout=30)
```

No `setUp`, criar `self.source`, `self.target`, `self.home`, `self.bin` e `self.calls` abaixo do diretório temporário. Copiar somente os arquivos retornados por `git ls-files` da raiz original, mantendo caminhos relativos; não copiar `.git`, diagnósticos locais ou dados pessoais. Escrever com `Path.write_text(..., encoding='utf-8')`. Os wrappers Bash precisam de LF e modo executável em Linux.

Definir `self.child_env` com `HOME` apontando apenas para o usuário temporário no subprocesso, `TEST_BIN`, `TEST_CALLS`, `TEST_REAL_GIT` e `TEST_PYTHON`. Desabilitar configurações globais/sistema de Git no subprocesso com `GIT_CONFIG_GLOBAL=os.devnull` e `GIT_CONFIG_NOSYSTEM=1`. Remover `MSYS_NO_PATHCONV` herdado. Nunca modificar a configuração do processo pai ou copiar tokens para a fixture.

Os wrappers `python3`, `git` e `claude` serão scripts no `self.bin`. Python encaminha para o interpretador de teste, Git encaminha para o simulador em Python e Claude apenas registra argumentos e retorna o código configurado. Usar o mesmo `tests/test_setup.py` em modo `--fake-git` para evitar arquivos de suporte adicionais. O simulador registra os argumentos como JSONL e adota estas regras:

```python
def fake_git(argv, env):
    with open(env['TEST_CALLS'], 'a', encoding='utf-8') as stream:
        stream.write(json.dumps(['git', *argv]) + '\n')
    if argv and argv[0] == 'clone':
        # O único clone permitido usa a origem local criada pelo teste.
        argv = ['clone', '-q', '--', env['TEST_UPSTREAM'], argv[-1]]
    elif 'checkout' in argv and env.get('TEST_FAIL_CHECKOUT') == '1':
        return 17
    elif any(word in argv for word in ('fetch', 'pull', 'push', 'ls-remote')):
        return 97
    return subprocess.run([env['TEST_REAL_GIT'], *argv], env=env).returncode
```

Criar `TEST_UPSTREAM` como repositório local com um `SKILL.md` e um commit usando identidade fictícia apenas por `git -c user.name=Test -c user.email=test@example.invalid commit`. Guardar o resultado de `git rev-parse HEAD` em `self.expected_commit` e atualizar o commit no manifesto da cópia da fixture. Guardar os executáveis descobertos em `self.real_git` e `self.bash`. Assim a verificação futura do pin usa Git real e não depende da rede. Antes da primeira execução, provar com `command -v git` e `command -v claude` que o Bash resolve ambos no `self.bin`; os caminhos registrados precisam permanecer na fixture.

- [ ] Acrescentar testes com saída não zero e ausência de `target/CLAUDE.md` para `--nome` sem valor, opção desconhecida, Python que retorna 127, manifesto inválido e `.claude` ocupado por um arquivo. Um teste com symlink pendente em `.env` e outro com `.claude` apontando para fora devem confirmar que um arquivo sentinela externo à pasta alvo fica idêntico. A fixture inteira continua dentro do diretório temporário. Se o Windows não permitir criar symlinks, relatar esse limite explicitamente; os casos devem rodar no CI Linux.

Exemplo de teste, como método da mesma classe:

```python
def test_missing_name_fails_before_writes(self):
    result = self.run_setup('--nome')
    self.assertEqual(result.returncode, 2)
    self.assertFalse((self.target / 'CLAUDE.md').exists())
```

- [ ] Executar `python -m unittest discover -s tests -v` e registrar quais verificações falham no instalador original. Falhas devem demonstrar comportamento do produto, não erros dos wrappers.

- [ ] Implementar preflight antes de `mkdir -p "$TARGET"`. Validar o valor de `--nome`, rejeitar parâmetros desconhecidos e verificar executáveis necessários com `command -v`, seguido de `python3 -c 'import json, pathlib, sys'`. Confirmar os arquivos fonte, tipos JSON e commit de 40 caracteres hexadecimais do humanizer.

```bash
falhar() { printf '%s\n' "$1" >&2; exit 1; }
# No case do parser:
--nome|--name)
  [ "$#" -ge 2 ] && [ -n "$2" ] && [[ "$2" != --* ]] || {
    printf '%s\n' 'uso: --nome/--name exige um valor' >&2; exit 2;
  }
  NOME="$2"; shift 2 ;;
```

Para fronteiras, usar o Python já exigido para resolver a raiz fornecida, mas examinar cada componente interno sem resolver antecipadamente seus links. Verificar todos os caminhos gerenciados, incluindo `.env`, `.gitignore`, `.claude`, `.codex` e `docs`, antes da primeira cópia. Recusar arquivos onde se espera diretório, diretórios onde se espera arquivo, links pendentes e junctions detectáveis no Python do host. Não aceitar o próprio diretório fonte como destino.

```python
def validate_managed(root, relative):
    current = root
    parts = Path(relative).parts
    for position, part in enumerate(parts):
        current = current / part
        junction = getattr(current, 'is_junction', lambda: False)()
        if current.is_symlink() or junction:
            raise ValueError(f'link em caminho gerenciado: {relative}')
        if current.exists():
            expected_dir = position < len(parts) - 1
            if current.is_dir() != expected_dir:
                raise ValueError(f'tipo de caminho incorreto: {relative}')
```

Aplicar a mesma checagem relativa à raiz do usuário para os caminhos `.claude/skills/humanizer/SKILL.md` e `.claude/skills/humanizer-ptbr/SKILL.md`. Revalidar caminhos antes das escritas. Declarar no README que o instalador pressupõe uma execução por destino e não é um sandbox contra um processo concorrente hostil.

- [ ] Executar os testes da tarefa e confirmar os casos acima. Criar commit por caminhos explícitos: `git add -- setup.sh tests/test_setup.py` e `git commit -m 'fix: validate setup inputs before writing files'`.

## Tarefa 2: Preservar guias e proteger o env

**Arquivos:** modificar `setup.sh:30-56`; acrescentar testes em `tests/test_setup.py`.

**Interfaces:** `copiar(relativo)` mantém arquivos sem force e renderiza placeholders somente quando efetivamente copia um guia. `.gitignore` deixa de participar da substituição comum e recebe uma etapa específica de mesclagem. `.env` existente é sempre preservado.

- [ ] Acrescentar testes A01 a A05 e A11. Inicializar Git com o executável real e nunca com o wrapper. Usar o conteúdo fictício `LOCAL_SENTINEL=not-a-secret` em env existente. Comparar os bytes antes/depois, inclusive na repetição com force.

```python
def test_existing_guide_is_preserved(self):
    guide = self.target / 'CLAUDE.md'
    original = b'# Keep {{PROJETO}} literally\r\n'
    guide.write_bytes(original)
    result = self.run_setup('--sem-plugins', '--nome', 'Novo projeto')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(guide.read_bytes(), original)

def test_tracked_env_blocks_all_writes(self):
    subprocess.run([self.real_git, 'init', '-q', str(self.target)], check=True)
    dotenv = self.target / '.env'
    dotenv.write_bytes(b'LOCAL_SENTINEL=not-a-secret\n')
    subprocess.run([self.real_git, '-C', str(self.target), 'add', '--', '.env'], check=True)
    result = self.run_setup('--sem-plugins')
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse((self.target / 'CLAUDE.md').exists())
    self.assertEqual(dotenv.read_bytes(), b'LOCAL_SENTINEL=not-a-secret\n')
    self.assertNotIn('LOCAL_SENTINEL', result.stdout + result.stderr)
```

O teste de ignore deve usar três conteúdos em subtests: `node_modules/\n`, `node_modules/` e `.env\n!.env\n`. Para cada fixture nova, executar duas vezes e exigir `git check-ignore --no-index .env` com retorno zero, prefixo original preservado e no máximo uma regra nova `/.env`. Repetir em `parent/project` com Git inicializado em `parent` para cobrir diretório consumidor dentro de outro checkout. Verificar que a consulta de arquivos rastreados se refere ao env do projeto correto.

- [ ] Executar testes antes da correção e observar falhas de preservação e ignore.

- [ ] Mover a substituição de placeholders para dentro do ramo que realmente copia o guia. Retirar o loop posterior que modifica todos os guias existentes. Manter `.env` fora desse fluxo.

```bash
case "$rel" in
  CLAUDE.md|AGENTS.md|docs/CLAUDE.en.md)
    python3 - "$dst" "$NOME" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding='utf-8')
p.write_text(text.replace('{{PROJETO}}', sys.argv[2]).replace('{{PROJECT}}', sys.argv[2]), encoding='utf-8')
PY
    ;;
esac
```

Antes da primeira alteração, consultar `git -C "$TARGET" ls-files --error-unmatch -- .env` se o destino pertence a um worktree Git; retorno zero impede a instalação. Distinguir ausência de repositório de falha inesperada ao consultar Git. Criar um ignore a partir do template somente se ausente; preservar os bytes de um ignore existente. Acrescentar a regra raiz no fim apenas se a proteção estiver ausente. Em pasta sem Git, exigir a regra explícita no arquivo local, sem confiar na configuração global.

```python
p = pathlib.Path(sys.argv[1])
data = p.read_bytes()
suffix = (b'' if not data or data.endswith(b'\n') else b'\n') + b'/.env\n'
with p.open('ab') as output:
    output.write(suffix)
```

Depois da mesclagem, em repositório Git, exigir `git check-ignore --no-index -q -- .env` antes de criar env. Um erro nessa verificação impede a criação do arquivo. Usar `umask 077` para evitar a janela de permissões amplas ao criar o novo arquivo e conferir a operação de cópia. Informar proteção preparada em pasta sem Git; proteção verificada apenas no caso validado. `chmod` sob Git Bash não comprova ACLs do Windows.

- [ ] Executar a suíte e verificar idempotência, caminho com espaços e force. Criar commit somente de `setup.sh` e `tests/test_setup.py`, mensagem `fix: preserve project files and protect local env`.

## Tarefa 3: Verificar skills e sinalizar falhas de plugins

**Arquivos:** modificar `setup.sh:58-100`; acrescentar testes em `tests/test_setup.py`.

**Interfaces:** humanizer usa `upstream.repo` e `upstream.commit` do manifesto fonte. Uma instalação preexistente precisa ser a raiz do repositório esperado, ter HEAD igual ao pin e estar limpa. O resultado final informa instalados, preservados, pulados e falhas.

- [ ] Acrescentar os testes A06 a A09. Para falha de checkout, usar `TEST_FAIL_CHECKOUT=1`: retorno não zero e ausência do diretório final. Executar novamente sem a falha e conferir HEAD pelo Git real. Para divergência, preparar a skill no commit anterior; para sujeira, criar um arquivo não rastreado. Em ambos os casos, comparar conteúdo antes/depois e exigir falha. Adicionar caso de diretório comum sob outro Git para impedir que o Git herde o HEAD de um repositório pai.

```python
def test_failed_checkout_does_not_activate_skill(self):
    destination = self.home / '.claude/skills/humanizer'
    failed = self.run_setup('--sem-plugins', env={'TEST_FAIL_CHECKOUT': '1'})
    self.assertNotEqual(failed.returncode, 0)
    self.assertFalse(destination.exists())
    retried = self.run_setup('--sem-plugins')
    self.assertEqual(retried.returncode, 0, retried.stderr)
    head = subprocess.check_output([self.real_git, '-C', str(destination), 'rev-parse', 'HEAD'], text=True).strip()
    self.assertEqual(head, self.expected_commit)
```

O wrapper Claude deve registrar a chamada e retornar `TEST_CLAUDE_EXIT`, por padrão zero. Separar falha no marketplace de falha no install com `TEST_CLAUDE_FAIL_STAGE=marketplace|install`. O teste exige código não zero e ausência de anúncio de instalação completa. Nos testes de plugins pulados, verificar zero chamadas ao Claude: com `--sem-plugins` e com wrapper ausente do PATH controlado. O launcher não deve herdar o diretório de um Claude pessoal.

- [ ] Executar a suíte e confirmar que os testes detectam a aceitação de skill divergente e o falso sucesso do instalador original.

- [ ] Carregar origem, pin e versão declarada do humanizer a partir do manifesto já validado no preflight. Remover o SHA duplicado do script. Verificar uma instalação existente antes de efetuar alterações de projeto: raiz real do Git igual à pasta da skill, HEAD igual ao commit e `git status --porcelain --untracked-files=all` vazio. Confirmar que `SKILL.md` existe. Preservar divergências e dar uma mensagem de resolução, sem executar reset.

Para nova instalação, criar staging com nome aleatório dentro de `.claude/skills`, clonar e fazer checkout ali, validar e mover para o nome final apenas se ainda estiver ausente. Registrar o caminho exato de staging. Limpar apenas essa área, após conferir sua raiz e recusar symlink; nunca remover uma pasta de skill preexistente. Se uma etapa falhar, propagar o erro.

```bash
git clone -q -- "$SKILL_REPO" "$STAGE" || falhar 'Falha ao obter humanizer'
git -C "$STAGE" checkout -q --detach "$SKILL_COMMIT" || falhar 'Falha ao selecionar revisao do humanizer'
[ "$(git -C "$STAGE" rev-parse HEAD)" = "$SKILL_COMMIT" ] || falhar 'Revisao inesperada do humanizer'
[ -f "$STAGE/SKILL.md" ] || falhar 'SKILL.md ausente'
[ ! -e "$SK/humanizer" ] && [ ! -L "$SK/humanizer" ] || falhar 'Destino da skill foi ocupado'
mv -- "$STAGE" "$SK/humanizer"
```

Integrar uma rotina de saída que limpe somente o staging não ativado. Para `humanizer-ptbr`, manter a política existente de preservar diretório já instalado, informando que sua atualização automática está fora deste incremento.

- [ ] Retirar `|| true` das instalações solicitadas. Agregar falhas do marketplace/install e evitar o pipeline que colocaria contadores num subshell. Usar process substitution para consumir a lista validada de plugins, executando o loop no shell principal. Cada falha registra a etapa e o plugin; não imprimir saídas brutas de ferramentas que possam conter credenciais.

```bash
FALHAS=0
# No corpo do loop existente de plugins:
if ! claude plugin marketplace add "$origem" >/dev/null 2>&1; then
  printf 'falhou marketplace: %s\n' "$mkt" >&2
  FALHAS=$((FALHAS + 1))
elif ! claude plugin install "$nome@$mkt" >/dev/null 2>&1; then
  printf 'falhou plugin: %s\n' "$nome" >&2
  FALHAS=$((FALHAS + 1))
else
  printf 'instalado plugin: %s\n' "$nome"
fi
# Após o loop e o resumo:
[ "$FALHAS" -eq 0 ] || exit 1
```

Falha de atualização de marketplace continua sendo falha solicitada, mesmo se existir cache. Diferenciar configuração manual do impeccable de uma tentativa de instalação que falhou. Documentar que o alcance das instalações inclui o usuário, e que alterações globais não são revertidas pelo Git do projeto.

- [ ] Executar a suíte, conferir os registros dos simuladores e criar commit dos dois arquivos: `fix: verify skill revisions and report install failures`.

## Tarefa 4: Verificação contínua e documentação de suporte

**Arquivos:** criar `.github/workflows/test.yml`; modificar `README.md` e textos explicativos de `skills-lock.json`. Ajustar `tests/test_setup.py` somente se necessário à execução nos dois ambientes previstos.

**Interfaces:** comando único `python -m unittest discover -s tests -v`; CI sem plugins reais e sem segredos. Registrar suporte por ambiente e distinguir teste de instalação de teste do host Claude/Codex.

- [ ] Acrescentar um teste de sucesso completo na fixture e um de sintaxe Bash/JSON. O teste completo verifica que os nove arquivos copiados existem, que os guias novos receberam o nome e que uma repetição preserva os arquivos locais. Inicializar Git real em uma fixture antes sem Git e confirmar que `.env` é ignorado.

```python
def test_source_syntax(self):
    subprocess.run([self.bash, '-n', shell_path(self.source / 'setup.sh')], check=True)
    for relative in ('skills-lock.json', '.mcp.json', '.claude/settings.json', '.codex/hooks.json'):
        json.loads((self.source / relative).read_text(encoding='utf-8'))
```

- [ ] Criar o workflow com checkout imutável e permissões mínimas. O SHA abaixo foi obtido do ref `refs/tags/v4` do repositório oficial durante o planejamento; ele identifica a versão consultada, não uma promessa de ser a versão mais recente.

```yaml
name: Installer tests
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  installer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
      - name: Check Bash syntax
        run: bash -n setup.sh
      - name: Run isolated regression tests
        run: python3 -m unittest discover -s tests -v
```

- [ ] Atualizar o README PT/EN: dependências, preservação de arquivos, exceção explícita de mesclagem do ignore, proteção do env, comportamento de force, componentes pulados, alterações no usuário e códigos de falha. Remover afirmação absoluta de ausência de segredos e substituir por orientação de proteção verificada. Explicar que a suíte usa ferramentas simuladas e não valida hooks ou acessos aos MCPs reais.

Usar estes textos para substituir a descrição do manifesto na tabela e atualizar `nota`/`note_en` de forma consistente:

```text
PT: Inventário dos plugins e origem das skills. O instalador verifica o commit da skill humanizer; as versões dos plugins de marketplace ainda não são fixadas por este manifesto.
EN: Plugin inventory and skill sources. The installer verifies the humanizer skill commit; this manifest does not yet pin marketplace plugin versions.
```

Adicionar instruções de teste e uma tabela de suporte em que Linux CI fica “aguarda primeira execução” até existir um run real. Git Bash local só fica “verificado” depois de executar a suíte. macOS e PowerShell nativo ficam “não verificados”. Se symlinks não puderem ser exercitados no Windows, nomear os testes pulados e a razão. Não afirmar compatibilidade dos hooks a partir de JSON válido.

- [ ] Executar `python -m unittest discover -s tests -v` no host Windows/Git Bash, `git diff --check` e inspeção do diff completo. Ler todas as falhas e skips. Caso haja Linux disponível, executar lá; caso não haja, esperar o run do workflow antes de declarar Linux verificado. Não instalar um novo ambiente só para satisfazer esse rótulo.
- [ ] Confirmar que o diff contém somente os arquivos planejados. Criar commit por caminhos explícitos: `ci: check installer regressions and document support`.

## Cobertura e encerramento

| Critério da especificação | Tarefa |
|---|---|
| A01 instalação nova | 2 e 4 |
| A02 ignore existente | 2 |
| A03 env rastreado | 2 |
| A04 guia preservado | 2 |
| A05 idempotência | 2 e 4 |
| A06 falha de checkout | 3 |
| A07 skill divergente | 3 |
| A08 falha de plugin | 3 |
| A09 componente pulado | 3 |
| A10 preflight | 1 |
| A11 espaços e force | 2 |
| A12 links simbólicos | 1 |

As quatro tarefas pertencem à primeira entrega. As demais frentes R03 a R10 continuam na especificação de produto; não são promessas de implementação neste plano. R01, R02 e R11 recebem aqui apenas a base de instalação, sem afirmar que seus fluxos completos estão prontos.

Antes de concluir, conferir cada critério contra uma saída de teste, revisar o diff e registrar limitações de ambiente. Não usar o resultado de mocks para afirmar que plugins, MCPs ou hosts reais funcionaram. Nenhum deploy faz parte desta entrega.

## Revisão do plano e execução

Revisão interna do plano: critérios A01 a A12 mapeados, cinco casos adicionais distribuídos pelas tarefas, contratos de entrada/saída preservados e arquivos delimitados. Os testes e trechos de implementação ainda não foram executados.

Recomendação: execução nativa nesta conversa, porque as tarefas alteram sequencialmente o mesmo instalador e compartilham a mesma fixture de teste, seguida de uma revisão independente do conjunto. A alternativa é um implementador e um revisor separados por tarefa, com custo maior de contexto. O mantenedor deve escolher o método após revisar o plano ou seu resumo na conversa.
