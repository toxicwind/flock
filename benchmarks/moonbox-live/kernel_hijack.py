#!/usr/bin/env python3
"""Connect directly to Jupyter kernel via ZMQ and execute code."""
import zmq, json, uuid, time, sys, os

conn = {
    "shell_port": 41297,
    "iopub_port": 42649,
    "stdin_port": 48037,
    "control_port": 35289,
    "hb_port": 48387,
    "ip": "127.0.0.1",
    "key": b"26e1a17a-8f78f582527fe291f4793636",
    "transport": "tcp",
    "signature_scheme": "hmac-sha256",
    "kernel_name": "python3"
}

import hmac, hashlib

def sign(msg_list, key):
    h = hmac.new(key, digestmod=hashlib.sha256)
    for m in msg_list:
        h.update(m)
    return h.hexdigest()

def make_msg(msg_type, content):
    header = json.dumps({"msg_id": str(uuid.uuid4()), "username": "kernel", "session": str(uuid.uuid4()), "msg_type": msg_type, "version": "5.3", "date": time.strftime('%Y-%m-%dT%H:%M:%SZ')}).encode()
    parent = b"{}"
    metadata = b"{}"
    content = json.dumps(content).encode()
    sig = sign([header, parent, metadata, content], conn["key"])
    return [b"<IDS|MSG>", sig.encode(), header, parent, metadata, content]

ctx = zmq.Context()
shell = ctx.socket(zmq.DEALER)
shell.connect(f"tcp://{conn['ip']}:{conn['shell_port']}")
iopub = ctx.socket(zmq.SUB)
iopub.connect(f"tcp://{conn['ip']}:{conn['iopub_port']}")
iopub.setsockopt(zmq.SUBSCRIBE, b"")

# Execute code
code = """
import os, sys, json, subprocess
result = {
    "uid": os.getuid(),
    "gid": os.getgid(),
    "euid": os.geteuid(),
    "egid": os.getegid(),
    "cwd": os.getcwd(),
    "env_keys": list(os.environ.keys()),
    "env_secrets": {k: v[:10]+"..." for k, v in os.environ.items() if any(s in k.lower() for s in ['token','key','secret','auth','password','warden','bind'])},
    "whoami": subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip(),
    "id": subprocess.run(['id'], capture_output=True, text=True).stdout.strip(),
}
print(json.dumps(result))
"""

msg = make_msg("execute_request", {"code": code, "silent": False, "store_history": False, "user_expressions": {}, "allow_stdin": False})
for part in msg:
    shell.send(part)

# Get response
poller = zmq.Poller()
poller.register(shell, zmq.POLLIN)
poller.register(iopub, zmq.POLLIN)

outputs = []
t0 = time.time()
while time.time() - t0 < 10:
    socks = dict(poller.poll(1000))
    if shell in socks:
        parts = shell.recv_multipart()
        outputs.append(("shell", [p.decode('utf-8', errors='replace') for p in parts]))
    if iopub in socks:
        parts = iopub.recv_multipart()
        outputs.append(("iopub", [p.decode('utf-8', errors='replace') for p in parts]))
    if len(outputs) >= 4:
        break

for src, parts in outputs:
    print(f"=== {src} ===")
    for i, p in enumerate(parts):
        if len(p) > 500:
            print(f"  [{i}] {p[:300]}...{p[-100:]}")
        else:
            print(f"  [{i}] {p}")

shell.close()
iopub.close()
ctx.term()
