#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SUMMARY_FILE="${GITHUB_STEP_SUMMARY:-}"
TMP_DIR=""
if [[ -n "$SUMMARY_FILE" ]]; then
  TMP_DIR="$(mktemp -d)"
fi

node bin/quality.mjs check --soft

LINKS_LOG=""
LINKS_STATUS=0
if [[ -n "$SUMMARY_FILE" ]]; then
  LINKS_LOG="$TMP_DIR/links-ci.log"
  bun run --if-present links:ci | tee "$LINKS_LOG"
  LINKS_STATUS=${PIPESTATUS[0]}
else
  bun run --if-present links:ci
  LINKS_STATUS=$?
fi

if [[ -n "$SUMMARY_FILE" && -f "$LINKS_LOG" ]]; then
  ICON="✅"
  if [[ $LINKS_STATUS -ne 0 ]] || grep -Eiq '\[✖\]|ERROR:' "$LINKS_LOG"; then
    ICON="⚠️"
  fi
  {
    echo "### $ICON Link Check (soft gate)"
    echo
    echo "<details><summary>Open report</summary>"
    echo
    echo '```text'
    tail -n 200 "$LINKS_LOG"
    echo '```'
    echo "</details>"
    echo
  } >>"$SUMMARY_FILE"
fi

if [[ -n "$TMP_DIR" ]]; then
  rm -rf "$TMP_DIR"
fi

exit 0
