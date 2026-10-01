#!/usr/bin/env bash
# YoungCrowHarness · setup.sh
# Copia o harness (CLAUDE.md, AGENTS.md, hooks, .mcp.json, .env.example, .gitignore) para um projeto
# e instala os plugins e skills listados em skills-lock.json. Nunca imprime nem grava segredo.
#
# Copies the harness into a project and installs the plugins and skills from skills-lock.json.
# Never prints or writes a secret.
#
# Uso / usage:
#   bash setup.sh <pasta-do-projeto> [--nome "Nome do Projeto"] [--force] [--sem-plugins]
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"; NOME=""; FORCE=0; PLUGINS=1
shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --nome|--name)
      if [ $# -lt 2 ] || [ -z "$2" ] || [[ "$2" == --* ]]; then
        echo "uso / usage: --nome/--name exige um valor / requires a value" >&2; exit 2
      fi
      NOME="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --sem-plugins|--no-plugins) PLUGINS=0; shift ;;
    *) echo "argumento desconhecido / unknown argument: $1"; exit 2 ;;
  esac
done
if [ -z "$TARGET" ]; then
  echo "uso: bash setup.sh <pasta-do-projeto> [--nome \"Nome\"] [--force] [--sem-plugins]"; exit 2
fi
falhar() { printf '%s\n' "$1" >&2; exit 1; }
for ferramenta in python3 git mkdir cp chmod mv mktemp; do
  command -v "$ferramenta" >/dev/null 2>&1 || falhar "dependência ausente / missing dependency: $ferramenta"
done
python3 -c 'import json, pathlib, sys' || falhar 'python3 indisponível / unavailable'
# Preflight is read-only. Resolve the requested root, then reject links inside it.
python3 - "$TARGET" "$HARNESS_DIR" "$HOME" <<'PY'
import json, pathlib, re, sys

def check_path(root, relative):
    current = root
    parts = pathlib.Path(relative).parts
    for i, part in enumerate(parts):
        current = current / part
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise ValueError('link em caminho gerenciado / linked managed path: ' + relative)
        if current.exists() and current.is_dir() != (i < len(parts) - 1):
            raise ValueError('tipo de caminho incorreto / wrong path type: ' + relative)

try:
    target, source, user = [pathlib.Path(p).resolve() for p in sys.argv[1:]]
    if target == source or target == target.parent:
        raise ValueError('destino inválido / invalid destination')
    if target.exists() and not target.is_dir():
        raise ValueError('destino não é diretório / destination is not a directory')
    files = ('CLAUDE.md', 'AGENTS.md', '.mcp.json', '.env.example', '.gitignore',
             '.codex/hooks.json', '.claude/settings.json', 'skills-lock.json', 'docs/CLAUDE.en.md')
    for name in files:
        if not (source / name).is_file():
            raise ValueError('fonte ausente / missing source: ' + name)
        check_path(target, name)
    check_path(target, '.env')
    for name in ('humanizer', 'humanizer-ptbr'):
        check_path(user, '.claude/skills/' + name + '/SKILL.md')
    if not (source / 'skills/humanizer-ptbr/SKILL.md').is_file():
        raise ValueError('fonte ausente / missing source: humanizer-ptbr')
    manifest = json.loads((source / 'skills-lock.json').read_text(encoding='utf-8'))
    skill = manifest['skills_de_usuario']['humanizer']['upstream']
    if not re.fullmatch(r'[0-9a-f]{40}', skill['commit']):
        raise ValueError('commit inválido / invalid skill commit')
    if not isinstance(skill['repo'], str) or not skill['repo'].startswith('https://') or any(c.isspace() for c in skill['repo']):
        raise ValueError('origem inválida / invalid skill source')
    for name, plugin in manifest['plugins'].items():
        for value in (name, plugin['marketplace']):
            if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', value):
                raise ValueError('identificador inválido / invalid plugin identifier')
        if not isinstance(plugin.get('origem'), str):
            raise ValueError('origem inválida / invalid plugin source')
    existing = target
    while not existing.exists():
        existing = existing.parent
    if not existing.is_dir():
        raise ValueError('diretório pai inválido / invalid parent directory')
except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
    # Never echo arbitrary manifest values or file contents.
    print('preflight falhou / failed: ' + (str(error) if type(error) is ValueError else type(error).__name__), file=sys.stderr)
    sys.exit(1)
PY
TARGET="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_posix())' "$TARGET")"
EXISTING="$TARGET"
while [ ! -d "$EXISTING" ]; do EXISTING="$(dirname "$EXISTING")"; done
IN_GIT=0
if GIT_PROBE="$(LC_ALL=C git -C "$EXISTING" rev-parse --is-inside-work-tree 2>&1)"; then
  [ "$GIT_PROBE" = true ] || falhar 'destino sem worktree Git / destination has no Git worktree'
  IN_GIT=1
  if git --literal-pathspecs -C "$EXISTING" ls-files --error-unmatch -- "$TARGET/.env" >/dev/null 2>&1; then
    falhar '.env rastreado pelo Git; resolva antes de instalar / tracked .env; resolve before installing'
  else
    [ "$?" -eq 1 ] || falhar 'falha ao verificar env rastreado / cannot check tracked env'
  fi
else
  case "$GIT_PROBE" in
    *'not a git repository'*) ;;
    *) falhar 'falha ao verificar repositório / cannot inspect repository' ;;
  esac
fi
mkdir -p "$TARGET"; TARGET="$(cd "$TARGET" && pwd -P)"
[ -n "$NOME" ] || NOME="$(basename "$TARGET")"

copiar() {  # copiar <relativo>: nunca sobrescreve sem --force
  local rel="$1" src="$HARNESS_DIR/$1" dst="$TARGET/$1"
  if [ -e "$dst" ] && [ "$FORCE" != 1 ]; then echo "  mantido  $rel (já existe; use --force para trocar)"; return; fi
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; echo "  copiado  $rel"
  case "$rel" in
    CLAUDE.md|AGENTS.md|docs/CLAUDE.en.md)
      python3 - "$dst" "$NOME" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
p.write_text(t.replace("{{PROJETO}}", sys.argv[2]).replace("{{PROJECT}}", sys.argv[2]), encoding="utf-8")
PY
      ;;
  esac
}

echo "== YoungCrowHarness → $TARGET  (projeto: $NOME)"
for f in CLAUDE.md AGENTS.md .mcp.json .env.example .codex/hooks.json .claude/settings.json skills-lock.json docs/CLAUDE.en.md; do
  copiar "$f"
done
# Ignore rules are merged even with --force. Never replace a consumer's rules.
[ -f "$TARGET/.gitignore" ] || cp "$HARNESS_DIR/.gitignore" "$TARGET/.gitignore"
python3 - "$TARGET/.gitignore" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); data = p.read_bytes()
# A final root rule overrides earlier negations and stays idempotent.
if not data.splitlines() or data.splitlines()[-1] != b'/.env':
    with p.open('ab') as output:
        output.write((b'' if not data or data.endswith(b'\n') else b'\n') + b'/.env\n')
    print('  mesclado / merged: .gitignore (/.env)')
PY
if [ "$IN_GIT" = 1 ]; then
  git -C "$TARGET" check-ignore --no-index -q -- .env || falhar '.env não protegido / not ignored'
  echo '  .env: proteção Git verificada / Git ignore verified'
else
  echo '  .env: ignore preparado; verifique após git init / ignore prepared; verify after git init'
fi
# .env local, nunca versionado
if [ ! -f "$TARGET/.env" ]; then
  (umask 077; cp "$TARGET/.env.example" "$TARGET/.env"; chmod 600 "$TARGET/.env")
  echo '  criado / created: .env (600 onde suportado / where supported)'
else
  echo "  mantido  .env"
fi

# skills de usuário
SK="$HOME/.claude/skills"; mkdir -p "$SK"
if [ ! -d "$SK/humanizer" ]; then
  if command -v git >/dev/null; then
    git clone -q https://github.com/blader/humanizer "$SK/humanizer" \
      && git -C "$SK/humanizer" checkout -q 9862685f575c65a8247f90369951df1b3416e3d6 \
      && echo "  skill    humanizer 3.0.0 (blader/humanizer @ 9862685f) → $SK/humanizer" \
      || echo "  AVISO    não consegui clonar blader/humanizer; instale à mão"
  fi
else echo "  mantido  $SK/humanizer"; fi
if [ ! -d "$SK/humanizer-ptbr" ]; then
  cp -r "$HARNESS_DIR/skills/humanizer-ptbr" "$SK/humanizer-ptbr"; echo "  skill    humanizer-ptbr → $SK/humanizer-ptbr"
else echo "  mantido  $SK/humanizer-ptbr"; fi

# plugins de marketplace (só se o Claude Code estiver instalado)
if [ "$PLUGINS" = 1 ] && command -v claude >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  echo "== plugins (claude plugin marketplace add + install)"
  python3 - "$HARNESS_DIR/skills-lock.json" <<'PY' | while read -r nome mkt origem; do
import json, sys
d = json.load(open(sys.argv[1]))
for nome, p in d["plugins"].items():
    o = p.get("origem") or ""
    if "/" in o and " " not in o:
        print(nome, p["marketplace"], o)
PY
    claude plugin marketplace add "$origem" >/dev/null 2>&1 || true
    if claude plugin install "$nome@$mkt" >/dev/null 2>&1; then echo "  plugin   $nome ($origem)"; else echo "  AVISO    $nome: instale à mão: claude plugin install $nome@$mkt"; fi
  done
  echo "  nota     impeccable vem de diretório local no manifesto: instale do upstream do plugin à mão"
else
  echo "== plugins: pulados (sem 'claude' no PATH ou --sem-plugins). Veja skills-lock.json"
fi

cat <<FIM

Pronto. Próximos passos / next steps:
  1. cd "$TARGET" && \$EDITOR .env          # valores reais, só aqui
  2. \$EDITOR CLAUDE.md                     # troque cada <preencher> pelo seu projeto
  3. \$EDITOR .mcp.json                     # URLs dos seus MCPs (sem token no arquivo)
  4. claude                                 # abre o Claude Code já com o harness

☧ Ora et labora ☧ et coda </>
FIM
