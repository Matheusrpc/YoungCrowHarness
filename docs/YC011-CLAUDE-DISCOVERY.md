# Conferir as quatro skills no Claude do Windows

Frente: YC-011, descoberta nativa sem prompt. Este roteiro usa o teste existente
na revisão `058be40265606ef670fa024d0d511975e26f91a1`.

**Resultado registrado:** o operador executou os dois blocos em 9/out, às 21h15 de
Brasília. [Claude 2.1.220 encontrou as quatro skills](relatorios/2026-10-09-client-skill-discovery.md#confirmação-claude-no-windows),
com zero prompts e limpeza confirmada. Os hashes enviados conferem com a revisão
fixa. Preserve o pacote e o recibo existentes; não é necessário repetir esse teste.
Os blocos abaixo documentam o procedimento executado.

O teste consulta os metadados do Claude em um projeto temporário, com perfil vazio
e MCPs desativados. Não envia conversa ao modelo e não precisa renovar o login.
Procura `yc-personalizer`, `yc-config`, `yc-missao` e `yc-status`. O resultado prova
descoberta; a aplicação dessas skills em uma missão continua pendente.

No PC usado para P06, abra o PowerShell normal. São necessários Python 3.11+ e
Git for Windows. O executável abaixo é o caminho registrado na prova anterior;
o novo recibo registra sua versão e hash atuais. Os pacotes P06 ficam preservados.

## 1. Preparar uma cópia pequena

Cole o bloco inteiro. Ele cria uma pasta nova, baixa uma revisão fixa e seleciona
somente as pastas necessárias, sem `docs/media`. Não instala dependências Python
nem npm. Se uma etapa falhar, preserve a pasta e envie a mensagem antes de repetir.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ycBase = Join-Path $env:USERPROFILE 'YoungCrowHarness-review-20261001\.runtime'
    $ycProbe = Join-Path $ycBase 'yc011-claude-discovery-058be40'
    $ycClaude = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
    if (!(Test-Path -LiteralPath $ycBase -PathType Container)) { throw 'Pasta original nao encontrada.' }
    if (!(Test-Path -LiteralPath $ycClaude -PathType Leaf)) { throw 'claude.exe nao encontrado. Envie esta mensagem.' }
    if (Test-Path -LiteralPath $ycProbe) { throw 'Pacote ja existe. Preserve a pasta e envie esta mensagem.' }
    python -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
    if ($LASTEXITCODE) { throw 'Python 3.11+ necessario.' }

    git init -q $ycProbe
    if ($LASTEXITCODE) { throw 'Criacao da copia falhou.' }
    git -C $ycProbe remote add origin https://github.com/Matheusrpc/YoungCrowHarness.git
    if ($LASTEXITCODE) { throw 'Configuracao da origem falhou.' }
    git -C $ycProbe config core.autocrlf false
    if ($LASTEXITCODE) { throw 'Configuracao de arquivos falhou.' }
    git -C $ycProbe sparse-checkout set --no-cone '/*' '!/*/' '/tests/' '/scripts/' '/skills/' '/.claude/' '/.agents/' '/.codex/' '/vault/' '/requirements/' '/docs/CLAUDE.en.md'
    if ($LASTEXITCODE) { throw 'Selecao de arquivos falhou.' }
    git -C $ycProbe fetch --depth 1 --filter=blob:none origin 058be40265606ef670fa024d0d511975e26f91a1
    if ($LASTEXITCODE) { throw 'Download falhou.' }
    git -C $ycProbe checkout --detach FETCH_HEAD
    if ($LASTEXITCODE) { throw 'Checkout falhou.' }
    New-Item -ItemType Directory -Path "$ycProbe\.runtime" | Out-Null
    Write-Output 'Pacote preparado. Agora execute o bloco 2.'
}
```

## 2. Consultar as skills uma vez

Cole este bloco depois do preparo. Ele seleciona o Bash do Git for Windows apenas
durante o teste, evitando que o Bash do WSL seja escolhido por engano. Restaura o
PATH ao terminar. Não é necessário executar `claude auth login`.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ycProbe = Join-Path $env:USERPROFILE 'YoungCrowHarness-review-20261001\.runtime\yc011-claude-discovery-058be40'
    $ycClaude = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
    $ycGit = (Get-Command git -CommandType Application -ErrorAction Stop).Source
    $ycGitBin = Join-Path (Split-Path (Split-Path $ycGit)) 'bin'
    if (!(Test-Path -LiteralPath "$ycGitBin\bash.exe" -PathType Leaf)) { throw 'Git Bash nao encontrado. Envie esta mensagem.' }
    $ycPreviousPath = $env:PATH
    try {
        $env:PATH = "$ycGitBin;$ycPreviousPath"
        python -B "$ycProbe\tests\smoke_clients.py" --discovery-only --claude $ycClaude --report "$ycProbe\.runtime\claude-discovery.json"
        if ($LASTEXITCODE) { throw 'Teste falhou. Preserve o recibo e envie a saida; nao repita.' }
    } finally {
        $env:PATH = $ycPreviousPath
    }
}
```

Envie o JSON que aparecer no terminal. O resultado esperado é `state: passed`,
`clients.claude.state: passed`, `clients.codex.state: not_run`,
`user_prompts_sent: 0`, `application_verified: false` e
`temporary_fixture_removed: true`, com as quatro skills na lista.

O recibo fica em `.runtime/claude-discovery.json` dentro da nova cópia. O comando
recusa um recibo existente. Se o terminal fechar antes do fim, preserve o arquivo,
mesmo que ele indique `running`; esse estado não comprova sucesso. Não rode P06
para investigar este teste.

## English overview

Run the two PowerShell blocks in order on the original P06 Windows PC. They require
Python 3.11+, Git for Windows and the native Claude executable at the recorded npm
installation path. The first block creates a separate sparse checkout at a fixed
revision without downloading media. The second temporarily selects Git Bash and
runs the existing metadata-only probe with a new receipt. It sends no model prompt,
uses a temporary empty profile, requires no login renewal and preserves P06 packages.
Send the resulting JSON for review. A passing discovery receipt does not establish
native skill application. Preserve any failed or interrupted receipt before retrying.

## Verificação deste roteiro / Recipe verification

Na cloud Linux, os mesmos comandos Git prepararam 152 arquivos (1.629.228 bytes
de conteúdo de trabalho), com as 80 dependências do instalador presentes e nenhum
arquivo em `docs/media`. O instalador real da fixture passou com `--client claude
--no-plugins` e removeu seus temporários. Isso valida a seleção de fontes; não é uma
execução PowerShell nem prova de descoberta pelo Claude no Windows. A execução
posterior do operador confirmou ambas, conforme o resultado registrado acima.

On Linux, the same Git sequence produced 152 working files (1,629,228 bytes), all
80 installer dependencies and no media files. The fixture's actual Claude installer
passed and cleaned up. PowerShell execution and real Claude discovery on Windows
were subsequently confirmed by the operator's terminal JSON, with matching hashes
and zero model prompts. These counts exclude Git metadata. Preserve that completed
run's package and receipt; no rerun is needed.

ATRASO: roteiro executado | descoberta Claude 0 | aplicação nativa/YC-203 pendentes.
