#!/usr/bin/env bash
# Compare the skill-bank INDEX against a list of upstream entries and report drift in
# three classes: added (upstream-only), removed (index-only), stale (same name, but
# the upstream ref differs from the index's recorded synced ref). Exit 0 if in sync,
# 1 if any drift, 2 on usage error.
#
#   bash scripts/refresh_skill_bank.sh --upstream <file> [--index <file>]
#
# --upstream FILE : one entry per line, `name` or `name <ref>` (blank lines and
#   #comments ignored), in the same <key>:<slug> convention as INDEX.md. A bare name
#   skips the stale check for that entry. This is the deterministic, tested path:
#   produce FILE with the `list:` commands in references/skill-bank/sources.yml, then
#   curate the reported diff by hand.
set -u

INDEX="references/skill-bank/INDEX.md"
UPSTREAM=""

while [ $# -gt 0 ]; do
  case "$1" in
    --upstream) UPSTREAM="${2:-}"; shift 2 ;;
    --index)    INDEX="${2:-}"; shift 2 ;;
    *) echo "usage: refresh_skill_bank.sh --upstream FILE [--index FILE]" >&2; exit 2 ;;
  esac
done

if [ ! -f "$INDEX" ]; then echo "refresh: index not found: $INDEX" >&2; exit 2; fi
if [ -z "$UPSTREAM" ]; then
  echo "refresh: --upstream FILE is required (see references/skill-bank/sources.yml)" >&2
  exit 2
fi
if [ ! -f "$UPSTREAM" ]; then echo "refresh: upstream file not found: $UPSTREAM" >&2; exit 2; fi

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

idx_tmp="$(mktemp)"; up_tmp="$(mktemp)"
trap 'rm -f "$idx_tmp" "$up_tmp"' EXIT

# INDEX data rows -> "name ref" (ref from the synced column's <owner/repo>@<ref>; '-'
# if absent).
while IFS= read -r line; do
  case "$line" in \|*) : ;; *) continue ;; esac
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*:?-{3,}:?[[:space:]]*\|'; then continue; fi
  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  [ "${#raw[@]}" -lt 8 ] && continue
  name="$(trim "${raw[0]}")"
  [ "$name" = "name" ] && continue
  [ -z "$name" ] && continue
  synced="$(trim "${raw[7]}")"
  if printf '%s' "$synced" | grep -q '@'; then
    ref="${synced#*@}"; ref="${ref%% *}"
  else
    ref="-"
  fi
  printf '%s %s\n' "$name" "$ref" >> "$idx_tmp"
done < "$INDEX"

# upstream lines -> "name ref" ('-' if no ref given)
grep -vE '^[[:space:]]*(#|$)' "$UPSTREAM" | while IFS= read -r l; do
  l="$(trim "$l")"; [ -z "$l" ] && continue
  n="${l%%[[:space:]]*}"
  r="$(trim "${l#"$n"}")"; [ -z "$r" ] && r="-"
  printf '%s %s\n' "$n" "$r"
done >> "$up_tmp"

idx_names="$(awk '{print $1}' "$idx_tmp" | sort -u)"
up_names="$(awk '{print $1}' "$up_tmp" | sort -u)"

added="$(comm -13 <(printf '%s\n' "$idx_names") <(printf '%s\n' "$up_names"))"
removed="$(comm -23 <(printf '%s\n' "$idx_names") <(printf '%s\n' "$up_names"))"
stale="$(awk '
  NR==FNR { if ($2 != "-") iref[$1]=$2; next }
  { if ($2 != "-" && ($1 in iref) && iref[$1] != $2) print $1" (index "iref[$1]" vs upstream "$2")" }
' "$idx_tmp" "$up_tmp")"

drift=0
if [ -n "$added" ]; then
  echo "UPSTREAM-ADDED (in upstream, not in index):"
  printf '%s\n' "$added" | sed 's/^/  + /'
  drift=1
fi
if [ -n "$removed" ]; then
  echo "INDEX-ONLY (in index, not upstream -- removed/renamed?):"
  printf '%s\n' "$removed" | sed 's/^/  - /'
  drift=1
fi
if [ -n "$stale" ]; then
  echo "STALE (ref moved upstream):"
  printf '%s\n' "$stale" | sed 's/^/  ~ /'
  drift=1
fi

if [ "$drift" -eq 0 ]; then
  echo "OK: index in sync with upstream"
  exit 0
fi
exit 1
