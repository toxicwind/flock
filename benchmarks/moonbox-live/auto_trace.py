#!/usr/bin/env python3
"""auto_trace.py — Daemon that captures ALL terminal output transparently.
Intercepts stdout/stderr, splits at 8500 chars, writes to trace files.
Usage: python3 /mnt/agents/output/auto_trace.py start
       python3 /mnt/agents/output/auto_trace.py read <trace_id> [part]
"""
import os, sys, subprocess, json, time, hashlib, threading, signal

TRACE_DIR = "/mnt/agents/output/.bg_logs/auto_trace"
os.makedirs(TRACE_DIR, exist_ok=True)

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    with open(f"{TRACE_DIR}/daemon.log", 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)

def run_and_capture(cmd, timeout=60):
    """Run command, capture FULL output, split into chunks."""
    trace_id = f"t{int(time.time())}_{hashlib.md5(cmd.encode()).hexdigest()[:8]}"
    out_file = f"{TRACE_DIR}/{trace_id}.txt"
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        full = f"=== CMD: {cmd} ===\n=== STDOUT ===\n{r.stdout}\n=== STDERR ===\n{r.stderr}\n=== RC: {r.returncode} ==="
    except Exception as e:
        full = f"=== CMD: {cmd} ===\n=== ERROR ===\n{str(e)}"
    
    with open(out_file, 'w') as f:
        f.write(full)
    
    size = len(full)
    parts = (size + 8499) // 8500
    
    log(f"Trace {trace_id}: {size} bytes, {parts} parts")
    log(f"  Read: python3 /mnt/agents/output/auto_trace.py read {trace_id} [0-{parts-1}]")
    return trace_id, size, parts

def read_trace(trace_id, part=0):
    out_file = f"{TRACE_DIR}/{trace_id}.txt"
    if not os.path.exists(out_file):
        return f"[ERROR] Trace {trace_id} not found"
    with open(out_file, 'r') as f:
        data = f.read()
    offset = part * 8500
    if offset >= len(data):
        return f"[ERROR] Part {part} beyond size {len(data)}"
    return data[offset:offset+8500]

def list_traces():
    files = sorted(os.listdir(TRACE_DIR), key=lambda x: os.path.getmtime(f"{TRACE_DIR}/{x}"), reverse=True)
    out = []
    for f in files[:20]:
        if f.endswith('.txt') and f != 'daemon.log':
            size = os.path.getsize(f"{TRACE_DIR}/{f}")
            parts = (size + 8499) // 8500
            out.append(f"{f[:-4]} | {size} bytes | {parts} parts")
    return '\n'.join(out)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: auto_trace.py start <cmd> | read <id> [part] | list")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "start":
        command = ' '.join(sys.argv[2:])
        tid, size, parts = run_and_capture(command)
        print(f"Trace ID: {tid}")
        print(f"Size: {size} bytes | Parts: {parts}")
        if parts == 1:
            print(read_trace(tid, 0))
    elif cmd == "read":
        tid = sys.argv[2]
        part = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        print(read_trace(tid, part))
    elif cmd == "list":
        print(list_traces())
    else:
        print(f"Unknown command: {cmd}")
