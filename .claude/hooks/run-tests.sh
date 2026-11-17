#!/usr/bin/env bash
# Hook Stop : lance les tests des sous-projets modifiés. Bloque la fin (exit 2) si un test échoue.
# "Aucun test collecté" n'est pas un échec.
set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

changed=$( { git diff --name-only HEAD 2>/dev/null || git diff --name-only; git ls-files --others --exclude-standard; } | sort -u)
[ -z "$changed" ] && exit 0

fail=0; report=""
run() { # $1 = label, $2.. = commande
  local label=$1; shift
  out=$("$@" 2>&1); code=$?
  # pytest : 5 = aucun test collecté
  if [ $code -ne 0 ] && ! { [ "$label" = "pytest" ] && [ $code -eq 5 ]; }; then
    fail=1; report+=$'\n'"[$label] échec (code $code) :"$'\n'"$(echo "$out" | tail -40)"
  fi
}

if echo "$changed" | grep -qE '^(apps|packages)/' && [ -f package.json ]; then
  run "js-tests" pnpm -r --if-present test
fi
for d in pipeline services/rag eval; do
  if echo "$changed" | grep -q "^$d/" && [ -f "$d/pyproject.toml" ]; then
    run "pytest" uv run --project "$d" pytest -q "$d"
  fi
done

if [ $fail -ne 0 ]; then
  echo "Des tests échouent, corrige avant de terminer :$report" >&2
  exit 2
fi
exit 0
