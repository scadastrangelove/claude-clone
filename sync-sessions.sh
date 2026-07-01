#!/usr/bin/env bash
#
# sync-sessions.sh — copy the Claude Code session list from one Claude Desktop
# profile to another.
#
# The actual transcripts live globally in ~/.claude/projects and are shared by
# every instance. But Claude Desktop keeps a per-profile, per-account *index* of
# Claude Code sessions in:
#     <profile>/claude-code-sessions/<account-uuid>/<org-uuid>/local_*.json
# A fresh profile has none, so its Claude Code session list looks empty even
# though the transcripts exist. This copies that index across.
#
# Only the account you're actually logged into will display; other accounts'
# index files are inert. Restart the target app afterwards to pick them up.
#
# Usage:
#   ./sync-sessions.sh <src-profile> <dst-profile> [account-uuid]
#
# Example:
#   ./sync-sessions.sh \
#     "$HOME/Library/Application Support/Claude" \
#     "$HOME/Library/Application Support/Claude-work"
#
set -euo pipefail

SRC="${1:?source profile dir required}"
DST="${2:?destination profile dir required}"
ACCT="${3:-}"

SRC_DIR="$SRC/claude-code-sessions"
DST_DIR="$DST/claude-code-sessions"
[[ -d "$SRC_DIR" ]] || { echo "No claude-code-sessions in source: $SRC_DIR" >&2; exit 1; }

mkdir -p "$DST_DIR"

if [[ -n "$ACCT" ]]; then
  ACCOUNTS=("$ACCT")
else
  ACCOUNTS=()
  while IFS= read -r a; do ACCOUNTS+=("$a"); done \
    < <(cd "$SRC_DIR" && find . -maxdepth 1 -mindepth 1 -type d -exec basename {} \;)
fi

for a in "${ACCOUNTS[@]}"; do
  [[ -d "$SRC_DIR/$a" ]] || { echo "skip (no such account): $a"; continue; }
  n=$(find "$SRC_DIR/$a" -name '*.json' | wc -l | tr -d ' ')
  cp -R "$SRC_DIR/$a" "$DST_DIR/$a"
  echo "copied account ${a:0:8}…  ($n sessions)"
done

echo "Done. Restart the target Claude instance to see the sessions."
