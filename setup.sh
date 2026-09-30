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
    --nome|--name) NOME="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --sem-plugins|--no-plugins) PLUGINS=0; shift ;;
    *) echo "argumento desconhecido / unknown argument: $1"; exit 2 ;;
  esac
done
if [ -z "$TARGET" ]; then
  echo "uso: bash setup.sh <pasta-do-projeto> [--nome \"Nome\"] [--force] [--sem-plugins]"; exit 2
fi
mkdir -p "$TARGET"; TARGET="$(cd "$TARGET" && pwd)"
[ -n "$NOME" ] || NOME="$(basename "$TARGET")"

copiar() {  # copiar <relativo>: nunca sobrescreve sem --force
  local rel="$1" src="$HARNESS_DIR/$1" dst="$TARGET/$1"
  if [ -e "$dst" ] && [ "$FORCE" != 1 ]; then echo "  mantido  $rel (já existe; use --force para trocar)"; return; fi
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; echo "  copiado  $rel"
}

echo "== YoungCrowHarness → $TARGET  (projeto: $NOME)"
for f in CLAUDE.md AGENTS.md .mcp.json .env.example .gitignore .codex/hooks.json .claude/settings.json skills-lock.json docs/CLAUDE.en.md; do
  copiar "$f"
done
# nome do projeto nos guias (substituição em lugar, sem arquivo temporário)
for f in CLAUDE.md AGENTS.md docs/CLAUDE.en.md; do
  if [ -f "$TARGET/$f" ]; then
    python3 - "$TARGET/$f" "$NOME" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
p.write_text(t.replace("{{PROJETO}}", sys.argv[2]).replace("{{PROJECT}}", sys.argv[2]), encoding="utf-8")
PY
  fi
done
# .env local, nunca versionado
if [ ! -f "$TARGET/.env" ]; then
  cp "$TARGET/.env.example" "$TARGET/.env"; chmod 600 "$TARGET/.env"
  echo "  criado   .env (600) a partir do .env.example: preencha à mão; ele está no .gitignore"
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
