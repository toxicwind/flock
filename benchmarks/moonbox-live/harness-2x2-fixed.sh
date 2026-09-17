#!/usr/bin/env bash
set -euo pipefail

# FIXED VERSION of launch_2x2_harness.sh
# Bug fixes:
#   1. Variable 'sub' renamed to 'subshell' to match printf usage
#   2. Strace output sanitized via Python JSON encoder instead of raw awk
#   3. JSON decode wrapped in try/except with control-char stripping

for dep in wezterm python3 strace; do
    if ! command -v "$dep" >/dev/null 2>&1; then
        echo "[-] Missing dependency: $dep" >&2
        exit 1
    fi
done

HARNESS_DIR="/tmp/wez_harness_$$"
mkdir -p "${HARNESS_DIR}"
cd "${HARNESS_DIR}"

FIFO_DELTA="${HARNESS_DIR}/delta.fifo"
FIFO_STRACE="${HARNESS_DIR}/strace.fifo"
FIFO_AST="${HARNESS_DIR}/ast.fifo"

LOG_DELTA="${HARNESS_DIR}/delta.jsonl"
LOG_STRACE="${HARNESS_DIR}/strace.jsonl"
LOG_AST="${HARNESS_DIR}/ast.json"
FINAL_JSON="${HARNESS_DIR}/telemetry_envelope.json"

mkfifo "${FIFO_DELTA}" "${FIFO_STRACE}" "${FIFO_AST}"

cleanup() {
    rm -rf "${HARNESS_DIR}"
}
trap cleanup EXIT

# --- Pane 1 (Top-Right): State Delta & Call-Frame Machine ---
cat << 'PYEOF' > "${HARNESS_DIR}/obs_delta.py"
import sys, json, re

fifo_path = sys.argv[1]
log_path = sys.argv[2]

print("\033[1;36m[PANE 1] STATE-DELTA & CALL-FRAME ENGINE\033[0m")
print("\033[90mListening on FIFO...\033[0m\n")

ctrl_re = re.compile(r'[\x00-\x1f\x7f]')

with open(fifo_path, "r") as fifo, open(log_path, "w") as log:
    for line in fifo:
        if not line.strip():
            continue
        # Strip control characters before JSON parsing
        clean = ctrl_re.sub('', line)
        log.write(clean + "\n")
        log.flush()
        try:
            d = json.loads(clean).get("frame", {})
            indent = "  " * max(0, d.get("depth", 1) - 1)
            fn = d.get("fn", "main")
            line_no = d.get("line", 0)
            sub = d.get("subshell", 0)
            exit_code = d.get("exit_prev", 0)
            cmd = d.get("cmd", "")
            print(f"\033[33m{indent}├─ [fn:{fn} | L:{line_no} | sub:{sub} | exit:{exit_code}]\033[0m \033[1;37m`{cmd}`\033[0m")
            delta = d.get("state_delta", {})
            for k, v in delta.items():
                old_val = v.get("old", "<unset>")
                new_val = v.get("new", "<unset>")
                print(f"\033[32m{indent}│  Δ {k}: \033[31m{old_val}\033[32m -> \033[1;32m{new_val}\033[0m")
        except Exception as e:
            print(f"\033[31m[PARSE ERROR] {e} -> {clean[:120]}\033[0m")

print("\n\033[90m[Stream closed. Press Enter to exit]\033[0m")
input()
PYEOF

# --- Pane 2 (Bottom-Left): Kernel Boundary & Syscall Tracer ---
# FIXED: Use Python to sanitize strace lines into proper JSON instead of raw awk
cat << 'PYEOF' > "${HARNESS_DIR}/obs_strace.py"
import sys, json, re

fifo_path = sys.argv[1]
log_path = sys.argv[2]

print("\033[1;35m[PANE 2] KERNEL BOUNDARY (SYSCALL & PROCESS ENGINE)\033[0m")
print("\033[90mListening on FIFO...\033[0m\n")

colors = {
    "EXEC": "\033[1;32m[EXEC]\033[0m",
    "PROCESS_FORK": "\033[1;34m[FORK]\033[0m",
    "MISSING_PATH": "\033[1;31m[MISSING]\033[0m",
    "PERMISSION_DENIED": "\033[1;41m[EACCES]\033[0m",
    "EXIT": "\033[1;33m[EXIT]\033[0m"
}

ctrl_re = re.compile(r'[\x00-\x1f\x7f]')

with open(fifo_path, "r") as fifo, open(log_path, "w") as log:
    for line in fifo:
        if not line.strip():
            continue
        clean = ctrl_re.sub('', line)
        log.write(clean + "\n")
        log.flush()
        try:
            d = json.loads(clean)
            evt = d.get("kernel_event", "EVENT")
            pid = d.get("pid", "?")
            detail = d.get("detail", "")
            tag = colors.get(evt, f"[{evt}]")
            print(f"{tag} \033[90m(pid:{pid})\033[0m {detail}")
        except Exception as e:
            print(f"\033[31m[PARSE ERROR] {e} -> {clean[:120]}\033[0m")

print("\n\033[90m[Stream closed. Press Enter to exit]\033[0m")
input()
PYEOF

# --- Pane 3 (Bottom-Right): Static AST Topology & Runtime State Grapher ---
cat << 'PYEOF' > "${HARNESS_DIR}/obs_ast.py"
import sys, json

fifo_path = sys.argv[1]
log_path = sys.argv[2]

print("\033[1;32m[PANE 3] STATIC AST TOPOLOGY GRAPH\033[0m")
print("\033[90mListening on FIFO...\033[0m\n")

with open(fifo_path, "r") as fifo, open(log_path, "w") as log:
    content = fifo.read()
    if content.strip():
        log.write(content)
        log.flush()
        try:
            data = json.loads(content)
            print(json.dumps(data, indent=2))
        except Exception:
            print(content.strip())

print("\n\033[90m[Stream closed. Press Enter to exit]\033[0m")
input()
PYEOF

# 3. Resolve Root WezTerm Pane
PANE_TL="${WEZTERM_PANE:-}"
if [[ -z "${PANE_TL}" ]]; then
    if command -v jq >/dev/null 2>&1; then
        PANE_TL=$(wezterm cli list --format json | jq -r '.[0].pane_id')
    else
        PANE_TL=$(wezterm cli list | awk 'NR==2 {print $3}')
    fi
fi

# 4. Construct 2x2 Pane Matrix
PANE_TR=$(wezterm cli split-pane --pane-id "${PANE_TL}" --right -- python3 "${HARNESS_DIR}/obs_delta.py" "${FIFO_DELTA}" "${LOG_DELTA}")
PANE_BL=$(wezterm cli split-pane --pane-id "${PANE_TL}" --bottom -- python3 "${HARNESS_DIR}/obs_strace.py" "${FIFO_STRACE}" "${LOG_STRACE}")
PANE_BR=$(wezterm cli split-pane --pane-id "${PANE_TR}" --bottom -- python3 "${HARNESS_DIR}/obs_ast.py" "${FIFO_AST}" "${LOG_AST}")

# 5. Populate AST Stream (Pumps Pane 3)
python3 - << PYEOF > "${FIFO_AST}"
import json
payload = """
workload_init() {
    CLUSTER_ENV="staging"
    NODE_COUNT=4
    cat /etc/hostname > /dev/null
    cat /opt/missing/config.yaml 2>/dev/null || true
    (
        CHILD_PID="active"
        CLUSTER_ENV="isolated"
        uname -m > /dev/null
    )
    DEPLOY_STATUS="nominal"
}
workload_init
"""
nodes = []
for i, line in enumerate(payload.strip().split("\n"), 1):
    raw = line.strip()
    if not raw: continue
    t = "STATEMENT"
    if "()" in raw: t = "FUNCTION_DEF"
    elif raw in ("(", ")"): t = "SUBSHELL_SCOPE"
    elif "cat " in raw or "uname" in raw: t = "KERNEL_EXEC"
    nodes.append({"node_id": f"ast_{i}", "line": i, "type": t, "statement": raw})
print(json.dumps({"ast_topology": nodes, "status": "COMPILED"}, indent=2))
PYEOF

# 6. Top-Left Master: Run Instrumented Workload
# FIXED: Variable name 'sub' changed to 'subshell' to match printf reference
# FIXED: Strace output piped through Python JSON encoder instead of raw awk

echo -e "\033[1;34m[MASTER PANE] Driving workload through instrumentation harnesses...\033[0m"

bash -c '
shopt -s extdebug
declare -gA __VARS=()

__probe_delta() {
    local exit_code=$?
    local lineno="${BASH_LINENO[0]}"
    local fn="${FUNCNAME[1]:-main}"
    local subshell="${BASH_SUBSHELL}"
    local depth="${#FUNCNAME[@]}"
    local cmd="${BASH_COMMAND}"

    [[ "${cmd}" == *"__probe_delta"* ]] && return 0

    local delta=""
    for v in $(compgen -v); do
        [[ "$v" =~ ^(BASH_|COMP_|EPOCH|PIPESTATUS|_|__VARS) ]] && continue
        local val="${!v:-}"
        if [[ "${__VARS[$v]-__UNSET__}" != "${val}" ]]; then
            delta+="\"$v\":{\"old\":\"${__VARS[$v]-<unset>}\",\"new\":\"${val}\"},"
            __VARS[$v]="${val}"
        fi
    done

    printf "{\"frame\":{\"fn\":\"%s\",\"line\":%d,\"depth\":%d,\"subshell\":%d,\"exit_prev\":%d,\"cmd\":\"%s\",\"state_delta\":{%s}}}\n" \
        "${fn}" "${lineno}" "${depth}" "${subshell}" "${exit_code}" "${cmd//\"/\\\"}" "${delta%,}" > "'"${FIFO_DELTA}"'"
}
trap "__probe_delta" DEBUG

# Write strace converter to temp file (avoids bash -n false positive on multi-line quotes)
cat << 'PYSTRACE' > "${HARNESS_DIR}/strace_converter.py"
import sys, json, re
ctrl = re.compile(r'[\x00-\x1f\x7f]')
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    pid = line.split()[0] if line.split() else '?'
    detail = ctrl.sub('', line)
    evt = 'EVENT'
    if 'execve(' in line: evt = 'EXEC'
    elif 'openat(' in line and 'ENOENT' in line: evt = 'MISSING_PATH'
    elif 'openat(' in line and 'EACCES' in line: evt = 'PERMISSION_DENIED'
    elif 'clone' in line or 'clone3' in line: evt = 'PROCESS_FORK'
    elif 'exit_group(' in line: evt = 'EXIT'
    print(json.dumps({'kernel_event': evt, 'pid': pid, 'detail': detail}))
PYSTRACE

python3 -u "${HARNESS_DIR}/strace_converter.py" < <(strace -f -q -e trace=clone,clone3,execve,openat,exit_group -e signal=none -s 128 -o /dev/stdout bash -c "
    workload_init() {
        CLUSTER_ENV=\"staging\"
        NODE_COUNT=4
        sleep 0.2
        cat /etc/hostname > /dev/null
        cat /opt/missing/config.yaml 2>/dev/null || true
        (
            CHILD_PID=\"active\"
            CLUSTER_ENV=\"isolated\"
            uname -m > /dev/null
        )
        DEPLOY_STATUS=\"nominal\"
    }
    workload_init
") > "'"${FIFO_STRACE}"'"
'

# 7. Aggregate JSON Logs into Telemetry Envelope & Copy to Clipboard
sleep 0.5

python3 - << PYEOF
import json, time, os, re

def read_jsonl(p):
    if not os.path.exists(p): return []
    out = []
    ctrl = re.compile(r'[\x00-\x1f\x7f]')
    with open(p, "r") as f:
        for line in f:
            if not line.strip(): continue
            try:
                out.append(json.loads(ctrl.sub('', line)))
            except:
                pass
    return out

def read_json(p):
    if not os.path.exists(p): return {}
    with open(p, "r") as f:
        try: return json.load(f)
        except: return {}

envelope = {
    "schema": "telemetry_2x2_v1",
    "timestamp": int(time.time() * 1000),
    "observers": {
        "pane_1_delta": read_jsonl("${LOG_DELTA}"),
        "pane_2_syscalls": read_jsonl("${LOG_STRACE}"),
        "pane_3_ast": read_json("${LOG_AST}")
    }
}

with open("${FINAL_JSON}", "w") as out:
    json.dump(envelope, out, indent=2)
PYEOF

# 8. Push to Clipboard
CLIP_STATUS="FAILED"
if command -v wl-copy >/dev/null 2>&1; then
    wl-copy < "${FINAL_JSON}"
    CLIP_STATUS="wl-copy (Wayland)"
elif command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard < "${FINAL_JSON}"
    CLIP_STATUS="xclip (X11)"
elif command -v xsel >/dev/null 2>&1; then
    xsel --clipboard --input < "${FINAL_JSON}"
    CLIP_STATUS="xsel"
fi

echo "========================================================="
echo -e "\033[1;32m[+] 2x2 Grid Orchestration Complete.\033[0m"
echo -e "[+] Clipboard Status: \033[1;36m${CLIP_STATUS}\033[0m"
echo -e "[+] Direct JSON Artifact: \033[1;33m${FINAL_JSON}\033[0m"
echo "========================================================="
