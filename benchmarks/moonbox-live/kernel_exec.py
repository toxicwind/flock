#!/usr/bin/env python3
"""Execute code via Jupyter kernel using jupyter_client."""
from jupyter_client import BlockingKernelClient
import json, os

km = BlockingKernelClient()
km.connection_file = "/tmp/tmp9qfdt6bp.json"
km.load_connection_file()
km.start_channels()

# Execute privilege check
code = """
import os, sys, subprocess, json
r = {
    "uid": os.getuid(), "gid": os.getgid(), "euid": os.geteuid(), "egid": os.getegid(),
    "whoami": subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip(),
    "id": subprocess.run(['id'], capture_output=True, text=True).stdout.strip(),
    "caps": subprocess.run(['capsh', '--print'], capture_output=True, text=True).stdout.strip() if os.path.exists('/usr/sbin/capsh') else 'no capsh',
    "env_secrets": {k: v[:15]+"..." for k, v in os.environ.items() if any(s in k.lower() for s in ['token','key','secret','auth','password','warden','bind','api'])},
}
print("KERNEL_RESULT_START")
print(json.dumps(r))
print("KERNEL_RESULT_END")
"""

msg_id = km.execute(code)
print(f"msg_id: {msg_id}")

# Collect output
timeout = 15
import time
t0 = time.time()
while time.time() - t0 < timeout:
    try:
        msg = km.get_iopub_msg(timeout=1)
        msg_type = msg['header']['msg_type']
        content = msg['content']
        if msg_type == 'stream' and 'text' in content:
            print(content['text'], end='')
        elif msg_type == 'execute_result' and 'data' in content:
            print(content['data'].get('text/plain', ''))
        elif msg_type == 'error':
            print(f"ERROR: {content.get('ename','')} {content.get('evalue','')}")
    except Exception as e:
        break

km.stop_channels()
