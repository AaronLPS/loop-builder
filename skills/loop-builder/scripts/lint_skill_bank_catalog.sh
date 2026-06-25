#!/usr/bin/env bash
# Lint a skill-bank catalog file: every data row must have exactly 2 columns, a name in
# <key>:<slug> form (contains a colon), and a non-empty description. Exit 0 clean,
# 1 violations, 2 usage error. Run:
#   bash scripts/lint_skill_bank_catalog.sh --file references/skill-bank/catalog/<key>.md
set -u

FILE=""
if [ "${1:-}" = "--file" ]; then FILE="${2:-}"; fi
if [ -z "$FILE" ]; then echo "usage: lint_skill_bank_catalog.sh --file FILE" >&2; exit 2; fi
if [ ! -f "$FILE" ]; then echo "catalog-lint: file not found: $FILE" >&2; exit 2; fi

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

violations=0
row=0
while IFS= read -r line; do
  case "$line" in \|*) : ;; *) continue ;; esac
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*:?-{3,}:?[[:space:]]*\|'; then continue; fi
  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  cells=()
  for c in "${raw[@]}"; do cells+=("$(trim "$c")"); done
  if [ "${cells[0]}" = "name" ]; then continue; fi
  row=$((row + 1))
  rid="row $row (${cells[0]:-<empty>})"
  if [ "${#cells[@]}" -ne 2 ]; then
    echo "FAIL: $rid has ${#cells[@]} columns, expected 2"; violations=$((violations + 1)); continue
  fi
  name="${cells[0]}"; desc="${cells[1]}"
  case "$name" in
    *:*) : ;;
    *) echo "FAIL: $rid name '$name' is not <key>:<slug>"; violations=$((violations + 1)) ;;
  esac
  if [ -z "$desc" ]; then echo "FAIL: $rid empty description"; violations=$((violations + 1)); fi
done < "$FILE"

if [ "$violations" -eq 0 ]; then
  echo "OK: catalog clean ($row entries)"; exit 0
else
  echo "$violations violation(s)"; exit 1
fi
