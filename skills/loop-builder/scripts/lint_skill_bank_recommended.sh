#!/usr/bin/env bash
# Lint the skill-bank recommended list. Every data row must have all 8 columns, a known
# type, block tags in 1..6, a single-token license, an http(s) source, and no empty
# required cells. Exit 0 if clean, 1 if any violation, 2 on usage error. Run:
#   bash scripts/lint_skill_bank_recommended.sh [--file references/skill-bank/recommended.md]
set -u

FILE="references/skill-bank/recommended.md"
if [ "${1:-}" = "--file" ]; then FILE="${2:-}"; fi

if [ ! -f "$FILE" ]; then
  echo "lint: file not found: $FILE" >&2
  exit 2
fi

trim() {  # echo the argument with leading/trailing whitespace removed
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

violations=0
row=0
while IFS= read -r line; do
  # only markdown table rows (start with a pipe)
  case "$line" in
    \|*) : ;;
    *) continue ;;
  esac
  # skip separator rows like |---|---|
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*:?-{3,}:?[[:space:]]*\|'; then continue; fi

  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  cells=()
  for c in "${raw[@]}"; do cells+=("$(trim "$c")"); done

  # skip the header row
  if [ "${cells[0]}" = "name" ]; then continue; fi

  row=$((row + 1))
  rid="row $row (${cells[0]:-<empty>})"

  if [ "${#cells[@]}" -ne 8 ]; then
    echo "FAIL: $rid has ${#cells[@]} columns, expected 8"
    violations=$((violations + 1))
    continue
  fi

  name="${cells[0]}"; type="${cells[1]}"; blocks="${cells[2]}"; purpose="${cells[3]}"
  source="${cells[4]}"; install="${cells[5]}"; license="${cells[6]}"; synced="${cells[7]}"

  for pair in "name=$name" "purpose=$purpose" "install=$install" "synced=$synced"; do
    k="${pair%%=*}"; v="${pair#*=}"
    if [ -z "$v" ]; then
      echo "FAIL: $rid empty $k"; violations=$((violations + 1))
    fi
  done

  case "$type" in
    skill|plugin|mcp|sub-agent|workflow) : ;;
    *) echo "FAIL: $rid bad type '$type'"; violations=$((violations + 1)) ;;
  esac

  IFS=',' read -ra btoks <<< "$blocks"
  if [ "${#btoks[@]}" -eq 0 ]; then
    echo "FAIL: $rid empty blocks"; violations=$((violations + 1))
  fi
  for b in "${btoks[@]}"; do
    b="$(trim "$b")"
    case "$b" in
      1|2|3|4|5|6) : ;;
      *) echo "FAIL: $rid bad block '$b'"; violations=$((violations + 1)) ;;
    esac
  done

  if [ -z "$license" ] || printf '%s' "$license" | grep -q ' '; then
    echo "FAIL: $rid bad license '$license'"; violations=$((violations + 1))
  fi

  case "$source" in
    http://*|https://*) : ;;
    *) echo "FAIL: $rid source not a URL '$source'"; violations=$((violations + 1)) ;;
  esac
done < "$FILE"

if [ "$violations" -eq 0 ]; then
  echo "OK: skill-bank recommended list clean ($row entries)"
  exit 0
else
  echo "$violations violation(s)"
  exit 1
fi
