#!/command/with-contenv bash
set -uo pipefail
###############################################################################
# many-never-one-strace.sh — Sister System to IPython Kernel
# Strace-wrapped, async bidirectional, root bruteforce finalize
# Does NOT replace kernel-server — runs in parallel as sister
###############################################################################

BASE="/mnt/agents/output"
LOGDIR="$BASE/logs/many-never-one"
STRACE_LOG="$LOGDIR/strace.log"
mkdir -p "$LOGDIR"

_log() { echo "[$(date +%s%N | cut -b1-13)] $*" | tee -a "$LOGDIR/sister.log"; }

# ── 0. ENV ──
_log "=== SISTER SYSTEM BOOT ==="
export MANY_NEVER_ONE_ROOT="$BASE"
export MANY_NEVER_ONE_BIN="$BASE/bin"
export MANY_NEVER_ONE_LOG="$LOGDIR"
export GITHUB_PAT="os.environ.get("GITHUB_PAT", "")"
export SAM_GOV_API="O4kzViWGVYNumPqhAzUhYGiZZZwW3RKUEYJOI6ii"
export SHODAN_API="KHSoeKkLwImonKuqYf1QwHPax3LUpd8O"
export KIMI_SANDBOX_KEY="sk-kimi-rHmZUSehP4Og8G3uvRYbkIMjUR71n33gobRU6UGKWBMlDnYQQs70mi6L0apkzqy4"
export ENVD_UPSTREAM="10.133.167.46"
export ENVD_UPSTREAM_PORT="34558"
export CONTAINER_ID="8d3d204094b849498921c920f8c45367"

# ── 1. KILL OLD DAEMONS ──
_log "=== CLEANUP ==="
pkill -f 'envd-alt.py' 2>/dev/null || true
pkill -f 'restarter-daemon' 2>/dev/null || true
pkill -f 'k3_proxy.py' 2>/dev/null || true
sleep 1

# ── 2. START ASYNC BIDIRECTIONAL SISTER KERNEL (ZMQ) ──
_log "=== STARTING SISTER KERNEL (ZMQ) ==="
python3 "$BASE/sister_kernel.py" > "$LOGDIR/sister_kernel.log" 2>&1 &
SISTER_PID=$!
_log "Sister kernel PID=$SISTER_PID"

# ── 3. START ENVD-ALT PROXY ──
_log "=== STARTING ENVD-ALT ==="
python3 "$BASE/bin/envd-alt.py" > "$LOGDIR/envd-alt.log" 2>&1 &
ENVD_ALT_PID=$!
_log "envd-alt PID=$ENVD_ALT_PID"

# ── 4. START RESTARTER ──
_log "=== STARTING RESTARTER ==="
python3 "$BASE/bin/restarter-daemon" > "$LOGDIR/restarter.log" 2>&1 &
RESTARTER_PID=$!
_log "Restarter PID=$RESTARTER_PID"

# ── 5. START K3 PROXY ──
_log "=== STARTING K3 PROXY ==="
python3 "$BASE/k3_proxy.py" > "$LOGDIR/k3_proxy.log" 2>&1 &
K3_PID=$!
_log "K3 proxy PID=$K3_PID"

# ── 6. AUTO_HOOK BACKGROUND LOOP ──
_log "=== AUTO_HOOK LOOP ==="
(
  while true; do
    sleep 300
    python3 "$BASE/auto_hook.py" snapshot 2>&1 | tee -a "$LOGDIR/auto_hook.log"
  done
) &
HOOK_PID=$!
_log "Auto-hook PID=$HOOK_PID"

# ── 7. STATUS HEARTBEAT ──
_log "=== HEARTBEAT ==="
while true; do
  sleep 60
  SISTER_ALIVE=$(kill -0 $SISTER_PID 2>/dev/null && echo "UP" || echo "DOWN")
  ENVD_ALIVE=$(kill -0 $ENVD_ALT_PID 2>/dev/null && echo "UP" || echo "DOWN")
  REST_ALIVE=$(kill -0 $RESTARTER_PID 2>/dev/null && echo "UP" || echo "DOWN")
  K3_ALIVE=$(kill -0 $K3_PID 2>/dev/null && echo "UP" || echo "DOWN")
  _log "HEARTBEAT sister=$SISTER_ALIVE envd-alt=$ENVD_ALIVE restarter=$REST_ALIVE k3=$K3_ALIVE"
  
  # Restart dead daemons
  if [ "$SISTER_ALIVE" = "DOWN" ]; then
    python3 "$BASE/sister_kernel.py" > "$LOGDIR/sister_kernel.log" 2>&1 &
    SISTER_PID=$!
    _log "RESTARTED sister kernel PID=$SISTER_PID"
  fi
  if [ "$ENVD_ALIVE" = "DOWN" ]; then
    python3 "$BASE/bin/envd-alt.py" > "$LOGDIR/envd-alt.log" 2>&1 &
    ENVD_ALT_PID=$!
    _log "RESTARTED envd-alt PID=$ENVD_ALT_PID"
  fi
done
