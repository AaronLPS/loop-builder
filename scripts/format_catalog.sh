#!/usr/bin/env bash
# Pure formatter for Tier-2 catalogs. Reads "name<TAB>path-to-SKILL.md" lines on
# stdin and writes a markdown table to stdout: a header row, a separator, then one
# row per entry "| name | one-line description |". The description is read from the
# SKILL.md YAML frontmatter `description:` field, collapsed to a single line; any '|'
# is replaced with '/'; a missing/empty description becomes "(no description)".
# No network, no file writes — this is the unit-tested core of the catalog builder.
set -u

extract_desc() {  # $1 = path to a SKILL.md ; echoes the raw description (may be empty)
  awk '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/  { exit }
    infm {
      if (indesc) {
        if ($0 ~ /^[[:space:]]+/) { line=$0; sub(/^[[:space:]]+/,"",line); desc=desc " " line; next }
        else { indesc=0 }
      }
      if ($0 ~ /^description:[[:space:]]*/) {
        val=$0; sub(/^description:[[:space:]]*/,"",val)
        if (val ~ /^[|>][+-]?[[:space:]]*$/) { indesc=1; next }
        desc=val; next
      }
    }
    END { gsub(/^[\047"]+|[\047"]+$/,"",desc); print desc }
  ' "$1"
}

printf '| name | description |\n'
printf '|------|-------------|\n'
while IFS=$'\t' read -r name path; do
  [ -z "$name" ] && continue
  d="$(extract_desc "$path")"
  d="$(printf '%s' "$d" | tr '\n|' ' /' | tr -s ' ')"
  d="${d#"${d%%[![:space:]]*}"}"; d="${d%"${d##*[![:space:]]}"}"
  [ -z "$d" ] && d="(no description)"
  printf '| %s | %s |\n' "$name" "$d"
done
