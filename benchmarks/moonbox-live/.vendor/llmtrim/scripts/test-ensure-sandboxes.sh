#!/usr/bin/env bash
# Independent-env checks for the smooth install / ensure surface.
# Each step gets its own HOME + LLMTRIM_HOME + XDG_CONFIG_HOME so real installs are untouched.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${LLMTRIM_BIN:-$ROOT/target/release/llmtrim}"
if [[ ! -x "$BIN" ]]; then
  echo "building release binary…"
  cargo build -p llmtrim --release --manifest-path "$ROOT/Cargo.toml"
fi

pass=0
fail=0
failures=()

ok() {
  echo "  OK  $1"
  pass=$((pass + 1))
}
bad() {
  echo "  FAIL $1${2:+ — $2}"
  fail=$((fail + 1))
  failures+=("$1")
}
check() {
  local name="$1"
  shift
  if "$@"; then ok "$name"; else bad "$name"; fi
}

# New sandbox: sets HOME, LLMTRIM_HOME, XDG_CONFIG_HOME, PATH, optional Claude dir.
# Usage: with_sandbox NAME [with-claude|no-claude] -- commands...
with_sandbox() {
  local name="$1"
  local mode="${2:-with-claude}"
  shift 2
  if [[ "${1:-}" == "--" ]]; then shift; fi

  local base
  base="$(mktemp -d "/tmp/llmtrim-sb-${name}.XXXXXX")"
  export HOME="$base/home"
  export LLMTRIM_HOME="$base/llmtrim"
  export XDG_CONFIG_HOME="$base/xdg"
  export CLAUDE_CONFIG_DIR="$HOME/.claude"
  export LLMTRIM_NO_UPDATE_CHECK=1
  unset DISPLAY WAYLAND_DISPLAY HTTPS_PROXY NODE_EXTRA_CA_CERTS SSL_CERT_FILE CURL_CA_BUNDLE 2>/dev/null || true
  mkdir -p "$HOME" "$LLMTRIM_HOME" "$XDG_CONFIG_HOME" "$base/bin"
  ln -sfn "$BIN" "$base/bin/llmtrim"
  export PATH="$base/bin:/usr/bin:/bin"

  if [[ "$mode" == "with-claude" ]]; then
    mkdir -p "$HOME/.claude"
    echo '{}' >"$HOME/.claude/settings.json"
  fi

  # shellcheck disable=SC2064
  trap "rm -rf '$base'; \"\$BIN\" stop >/dev/null 2>&1 || true" RETURN

  echo "== $name ($mode)  sandbox=$base"
  "$@"
  # stop any daemon this sandbox may have started
  "$BIN" stop >/dev/null 2>&1 || true
  trap - RETURN
  rm -rf "$base"
}

need_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "jq is required for sandbox assertions"
    exit 2
  }
}

need_jq
echo "BIN=$BIN ($("$BIN" --version 2>/dev/null || echo unknown))"
echo

# ── Step 1: ensure + integrations.json + opt-out ─────────────────────────────
with_sandbox s1 with-claude -- bash -c '
  set -e
  '"$BIN"' ensure -q </dev/null
  test -f "$LLMTRIM_HOME/integrations.json"
  ver=$('"$BIN"' --version | sed -n "s/.*\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p" | head -1)
  jq -e --arg v "$ver" ".last_ensured_version == \$v" "$LLMTRIM_HOME/integrations.json" >/dev/null
  # second run is fine
  '"$BIN"' ensure -q </dev/null
  # opt out of guard
  '"$BIN"' guard uninstall >/dev/null
  jq -e ".opt_out.guard == true" "$LLMTRIM_HOME/integrations.json" >/dev/null
  '"$BIN"' ensure -q </dev/null
  # guard command must not be re-wired
  if jq -e ".. | strings | select(test(\" guard$\"))" "$HOME/.claude/settings.json" >/dev/null 2>&1; then
    exit 1
  fi
  # window-sub uninstall must stick
  '$BIN' window-sub uninstall >/dev/null 2>&1 || true
  jq -e ".opt_out.window_sub == true" "$LLMTRIM_HOME/integrations.json" >/dev/null
  '$BIN' ensure -q </dev/null
  test ! -f "$HOME/.claude/skills/sub/SKILL.md" || ! grep -q llmtrim-owned-window-sub "$HOME/.claude/skills/sub/SKILL.md"

  exit 0
' && ok "s1 ensure + opt-out" || bad "s1 ensure + opt-out"

# ── Step 2a: setup wires integrations ────────────────────────────────────────
with_sandbox s2a with-claude -- bash -c '
  set -e
  '"$BIN"' setup --force </dev/null >/tmp/llmtrim-setup-out.$$ 2>&1 || {
    cat /tmp/llmtrim-setup-out.$$
    exit 1
  }
  rm -f /tmp/llmtrim-setup-out.$$
  test -f "$LLMTRIM_HOME/integrations.json"
  jq -e ".statusLine.command | test(\"statusline\")" "$HOME/.claude/settings.json" >/dev/null
  jq -e ".statusLine.refreshInterval == 300" "$HOME/.claude/settings.json" >/dev/null
  jq -e ".. | strings | select(test(\"guard\"))" "$HOME/.claude/settings.json" >/dev/null
  test -f "$HOME/.claude/skills/sub/SKILL.md"
  grep -q "llmtrim-owned-window-sub" "$HOME/.claude/skills/sub/SKILL.md"
  # compact configured somewhere under XDG
  found=0
  while IFS= read -r -d "" f; do
    if grep -q "\[compact\]" "$f" 2>/dev/null; then found=1; break; fi
  done < <(find "$XDG_CONFIG_HOME" -name "config.toml" -print0 2>/dev/null || true)
  # also check HOME/.config
  while IFS= read -r -d "" f; do
    if grep -q "\[compact\]" "$f" 2>/dev/null; then found=1; break; fi
  done < <(find "$HOME" -name "config.toml" -print0 2>/dev/null || true)
  test "$found" = 1
' && ok "s2a setup wires integrations" || bad "s2a setup wires integrations"

# ── Step 2b: stale statusline rewrite ────────────────────────────────────────
with_sandbox s2b with-claude -- bash -c '
  set -e
  '"$BIN"' ensure -q </dev/null
  jq ".statusLine = {
        \"type\": \"command\",
        \"command\": \"/old/cellar/llmtrim statusline\",
        \"padding\": 0
      }" "$HOME/.claude/settings.json" >"$HOME/.claude/settings.json.tmp"
  mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
  '"$BIN"' ensure -q </dev/null
  jq -e ".statusLine.command | test(\"statusline\") and (contains(\"old/cellar\") | not)" \
    "$HOME/.claude/settings.json" >/dev/null
  jq -e ".statusLine.refreshInterval == 300" "$HOME/.claude/settings.json" >/dev/null
' && ok "s2b stale statusline rewrite" || bad "s2b stale statusline rewrite"

# ── Step 3: ensure installs statusline; foreign left alone ───────────────────
with_sandbox s3a with-claude -- bash -c '
  set -e
  echo "{}" >"$HOME/.claude/settings.json"
  '"$BIN"' ensure -q </dev/null
  jq -e ".statusLine.type == \"command\"" "$HOME/.claude/settings.json" >/dev/null
  jq -e ".statusLine.command | test(\"statusline\")" "$HOME/.claude/settings.json" >/dev/null
' && ok "s3a statusline install" || bad "s3a statusline install"

with_sandbox s3b with-claude -- bash -c '
  set -e
  printf "%s\n" "{\"statusLine\":{\"type\":\"command\",\"command\":\"my-own-statusline\"}}" \
    >"$HOME/.claude/settings.json"
  '"$BIN"' ensure -q </dev/null
  jq -e ".statusLine.command == \"my-own-statusline\"" "$HOME/.claude/settings.json" >/dev/null
' && ok "s3b foreign statusline preserved" || bad "s3b foreign statusline preserved"

# ── Step 4: doctor --fix ────────────────────────────────────────────────────
with_sandbox s4 with-claude -- bash -c '
  set -e
  echo "{}" >"$HOME/.claude/settings.json"
  # doctor alone should fail (gaps / no daemon)
  set +e
  '"$BIN"' doctor >/dev/null 2>&1
  d1=$?
  set -e
  test "$d1" -ne 0
  '"$BIN"' doctor --fix </dev/null >/dev/null 2>&1 || true
  jq -e ".statusLine.command | test(\"statusline\")" "$HOME/.claude/settings.json" >/dev/null
  test -f "$HOME/.claude/skills/sub/SKILL.md"
' && ok "s4 doctor --fix" || bad "s4 doctor --fix"

# ── Step 5: help surface (3 verbs; hidden power-user cmds) ───────────────────
with_sandbox s5 no-claude -- bash -c '
  set -e
  help=$('"$BIN"' --help)
  echo "$help" | grep -q "setup"
  echo "$help" | grep -q "update"
  echo "$help" | grep -q "ensure"
  echo "$help" | grep -q "doctor"
  # top-level list should not advertise these as Get started lines
  ! echo "$help" | grep -E "^  statusline  " >/dev/null
  ! echo "$help" | grep -E "^  guard  " >/dev/null
  ! echo "$help" | grep -E "^  compact  " >/dev/null
  # still invokable
  '"$BIN"' statusline --help >/dev/null
  '"$BIN"' guard --help >/dev/null
  '"$BIN"' compact --help >/dev/null
' && ok "s5 help surface" || bad "s5 help surface"

# ── Step 6: non-interactive ensure does not require tray download ────────────
with_sandbox s6 with-claude -- bash -c '
  set -e
  unset DISPLAY WAYLAND_DISPLAY
  '"$BIN"' ensure -q </dev/null
  # sibling tray next to release binary is unrelated; we only assert ensure succeeds
  test -f "$LLMTRIM_HOME/integrations.json"
' && ok "s6 ensure without tray download" || bad "s6 ensure without tray download"

# ── Step 7: /sub installed; window-sub hidden ────────────────────────────────
with_sandbox s7 with-claude -- bash -c '
  set -e
  '"$BIN"' ensure -q </dev/null
  test -f "$HOME/.claude/skills/sub/SKILL.md"
  grep -q "llmtrim-owned-window-sub" "$HOME/.claude/skills/sub/SKILL.md"
  jq -e ".hooks.SessionStart" "$HOME/.claude/settings.json" >/dev/null
  jq -e ".hooks.SessionEnd" "$HOME/.claude/settings.json" >/dev/null
  ! '"$BIN"' --help | grep -qi "window-sub"
' && ok "s7 /sub install + window-sub hidden" || bad "s7 /sub install + window-sub hidden"

# ── Step 8a: no Claude → no settings writes ──────────────────────────────────
with_sandbox s8a no-claude -- bash -c '
  set -e
  '"$BIN"' ensure -q </dev/null
  test ! -d "$HOME/.claude"
  test -f "$LLMTRIM_HOME/integrations.json"
' && ok "s8a no-claude silent" || bad "s8a no-claude silent"

# ── Step 8b: full ensure matrix (all pieces at once) ─────────────────────────
with_sandbox s8b with-claude -- bash -c '
  set -e
  '"$BIN"' ensure </dev/null >/dev/null
  jq -e ".statusLine.refreshInterval == 300" "$HOME/.claude/settings.json" >/dev/null
  jq -e ".. | strings | select(test(\"guard\"))" "$HOME/.claude/settings.json" >/dev/null
  test -f "$HOME/.claude/skills/sub/SKILL.md"
  test -f "$LLMTRIM_HOME/integrations.json"
  # update reminder path (package channel) should not crash
  '"$BIN"' update 2>/dev/null | head -20 >/dev/null || true
' && ok "s8b full ensure matrix" || bad "s8b full ensure matrix"

echo
echo "========"
echo "passed=$pass failed=$fail"
if (( fail > 0 )); then
  echo "failures:"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi
echo "all sandbox steps passed"
exit 0
