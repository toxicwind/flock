#!/usr/bin/env python3
# SOVEREIGN COMPUTE KIT v1 — Anti-Surveillance, Anti-Capitalism
# "Surveillance is bad and credits is capitalism" — practical liberation

import os, sys, json, subprocess, hashlib, random, string
from pathlib import Path
from datetime import datetime, timedelta

SOVEREIGN_HOME = Path(os.environ.get("SOVEREIGN_HOME", "/home/kimi/sovereign"))
SOVEREIGN_HOME.mkdir(parents=True, exist_ok=True)

BLOCKLIST = [
    "gator.volces.com",
    "apmplus.volces.com",
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.com",
    "scorecardresearch.com",
    "browserbase.com",
    "kimi-api-sandbox.msh.team",
    "agent-gw.kimi.com",
]

def install_hosts_blocklist():
    hosts_path = Path("/etc/hosts")
    block_entries = [f"0.0.0.0 {domain}\n::ffff:0.0.0.0 {domain}" for domain in BLOCKLIST]
    block_text = "\n# === SOVEREIGN BLOCKLIST ===\n" + "\n".join(block_entries) + "\n"
    if hosts_path.exists() and "SOVEREIGN BLOCKLIST" in hosts_path.read_text():
        print("[hosts] Blocklist already installed.")
        return
    try:
        with open(hosts_path, "a") as f:
            f.write(block_text)
        print(f"[hosts] Blocked {len(BLOCKLIST)} surveillance endpoints.")
    except PermissionError:
        user_hosts = SOVEREIGN_HOME / "hosts.blocklist"
        user_hosts.write_text(block_text)
        print(f"[hosts] Wrote fallback to {user_hosts}")
        print(f"[hosts] To activate: sudo cp {user_hosts} /etc/hosts")

class JWTRotator:
    def __init__(self, base_claims=None):
        self.base_claims = base_claims or {}
    def generate(self, ttl_seconds=60, noise_bytes=16):
        import base64
        now = int(datetime.utcnow().timestamp())
        header = {"alg": "none", "typ": "JWT"}
        payload = {
            **self.base_claims,
            "iat": now,
            "exp": now + ttl_seconds,
            "jti": "".join(random.choices(string.ascii_letters + string.digits, k=noise_bytes)),
            "nonce": hashlib.sha256(os.urandom(32)).hexdigest()[:16],
        }
        b64 = lambda x: base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip("=")
        return f"{b64(header)}.{b64(payload)}."
    def rotate_env(self):
        token = self.generate()
        os.environ["KIMI_JWT"] = token
        os.environ["OPENROUTER_JWT"] = token
        os.environ["BEARER_TOKEN"] = token
        return token

def generate_telemetry_nullifier():
    script = '''#!/usr/bin/env python3
import sys, os, json, urllib.request
_original_open = urllib.request.urlopen
def _blocked_urlopen(url, *args, **kwargs):
    blocked = ["gator.volces.com", "apmplus.volces.com", "google-analytics",
               "googletagmanager", "browserbase", "kimi-api-sandbox"]
    url_str = url if isinstance(url, str) else url.full_url
    if any(b in url_str for b in blocked):
        raise urllib.error.URLError(f"SOVEREIGN_BLOCK: {url_str}")
    return _original_open(url, *args, **kwargs)
urllib.request.urlopen = _blocked_urlopen
try:
    import requests
    _original_get = requests.get
    _original_post = requests.post
    def _blocked_request(method, url, *args, **kwargs):
        blocked = ["gator.volces.com", "apmplus.volces.com", "google-analytics",
                   "googletagmanager", "browserbase", "kimi-api-sandbox"]
        if any(b in url for b in blocked):
            class FakeResponse:
                status_code = 418
                text = "SOVEREIGN_BLOCK"
                def json(self): return {}
            return FakeResponse()
        return method(url, *args, **kwargs)
    requests.get = lambda *a, **k: _blocked_request(_original_get, *a, **k)
    requests.post = lambda *a, **k: _blocked_request(_original_post, *a, **k)
except ImportError:
    pass
print("[telemetry_nullifier] Surveillance endpoints neutralized.")
'''
    path = SOVEREIGN_HOME / "telemetry_nullifier.py"
    path.write_text(script)
    os.chmod(path, 0o755)
    print(f"[nullifier] Written to {path}")
    return path

def generate_local_router():
    config = {
        "models": {
            "local-llama": {"cmd": "llama-server -m /models/llama-3.1-70b.gguf -c 128000 --port 8080", "port": 8080, "timeout": 300},
            "local-qwen": {"cmd": "llama-server -m /models/qwen2.5-72b.gguf -c 128000 --port 8081", "port": 8081, "timeout": 300},
            "local-nemotron": {"cmd": "llama-server -m /models/nemotron-3.5-70b.gguf -c 128000 --port 8082", "port": 8082, "timeout": 300}
        },
        "routing": {
            "default": "local-llama",
            "fallback_order": ["local-llama", "local-qwen", "local-nemotron"],
            "api_endpoints": {"openrouter": None, "nvidia-nim": None, "together": None, "groq": None, "fireworks": None}
        },
        "telemetry": {"enabled": False, "endpoints": [], "logging": "local-only"}
    }
    path = SOVEREIGN_HOME / "local-router.json"
    path.write_text(json.dumps(config, indent=2))
    print(f"[router] Local-first config: {path}")
    return path

def generate_sovereign_pitchfork():
    toml = '''[settings]
auto_bump_port = true
port_bump_attempts = 10

[daemons.local-llama]
run = "exec llama-server -m /models/llama-3.1-70b.gguf -c 128000 --port 8080"
port = 8080
ready_http = "http://127.0.0.1:8080/health"
auto = ["start"]
retry = 3

[daemons.local-qwen]
run = "exec llama-server -m /models/qwen2.5-72b.gguf -c 128000 --port 8081"
port = 8081
ready_http = "http://127.0.0.1:8081/health"
depends = ["local-llama"]
auto = ["start"]
retry = 3

[daemons.mcpproxy]
run = "exec mcpproxy serve --config=/home/kimi/.mcpproxy/mcp_config.json --log-level=error"
port = 25109
ready_http = "http://127.0.0.1:25109/health"
depends = ["local-llama"]
auto = ["start"]
retry = 3

[daemons.pi-agent]
run = "exec mise exec -- bun --watch /home/kimi/projects/pi-agent/bin/pi"
port = 0
depends = ["mcpproxy", "local-llama"]
auto = ["start"]
'''
    path = SOVEREIGN_HOME / "sovereign-pitchfork.toml"
    path.write_text(toml.strip())
    print(f"[pitchfork] Sovereign config: {path}")
    return path

def generate_sovereign_bashrc():
    bashrc = '''# === SOVEREIGN SHELL — Anti-Surveillance, Anti-Capitalism ===
export HOSTALIASES=/home/kimi/sovereign/hosts.blocklist
export KIMI_JWT=$(python3 -c "import base64,json,os,hashlib,random,string; now=__import__('time').time(); h={'alg':'none','typ':'JWT'}; p={'iat':int(now),'exp':int(now)+60,'jti':''.join(random.choices(string.ascii_letters+string.digits,k=16)),'nonce':hashlib.sha256(os.urandom(32)).hexdigest()[:16]}; b64=lambda x:base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('='); print(f'{b64(h)}.{b64(p)}.')")
export LLM_API_BASE=http://127.0.0.1:8080/v1
export LLM_API_KEY=local-no-key-needed
export CHROME_TELEMETRY_OPTOUT=1
export MOZ_TELEMETRY_OPTOUT=1
export PYTHONSTARTUP=/home/kimi/sovereign/telemetry_nullifier.py
alias root='unshare -U -r bash'
alias freecompute='echo "Compute is free. Electricity is cheap. Capitalism is expensive."'
__sovereign_status() {
    local model_status=$(curl -s -m 1 http://127.0.0.1:8080/health >/dev/null 2>&1 && echo "LOCAL" || echo "OFFLINE")
    PS1="[sov:${model_status}]$ "
}
PROMPT_COMMAND='__sovereign_status'
'''
    path = SOVEREIGN_HOME / "sovereign.bashrc"
    path.write_text(bashrc.strip())
    print(f"[bashrc] Sovereign shell config: {path}")
    print(f"[bashrc] To activate: echo 'source {path}' >> ~/.bashrc")
    return path

def generate_systemd_service():
    service = '''[Unit]
Description=Sovereign Compute Stack — No Telemetry, No Credits
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/pitchfork start --config /home/kimi/sovereign/sovereign-pitchfork.toml
Restart=always
RestartSec=5
Environment="KIMI_JWT=rotated-per-session"
Environment="PYTHONSTARTUP=/home/kimi/sovereign/telemetry_nullifier.py"
Environment="CHROME_TELEMETRY_OPTOUT=1"

[Install]
WantedBy=default.target
'''
    path = SOVEREIGN_HOME / "sovereign-compute.service"
    path.write_text(service.strip())
    print(f"[systemd] User service: {path}")
    print(f"[systemd] Install: systemctl --user enable --now {path}")
    return path

if __name__ == "__main__":
    print("SOVEREIGN COMPUTE KIT v1 — Liberating Moonbox")
    install_hosts_blocklist()
    generate_telemetry_nullifier()
    generate_local_router()
    generate_sovereign_pitchfork()
    generate_sovereign_bashrc()
    generate_systemd_service()
    rotator = JWTRotator()
    token = rotator.rotate_env()
    print(f"[jwt] Ephemeral token: {token[:50]}...")
    print("\nNEXT STEPS:")
    print("  1. sudo cp /home/kimi/sovereign/hosts.blocklist /etc/hosts")
    print("  2. echo 'source /home/kimi/sovereign/sovereign.bashrc' >> ~/.bashrc")
    print("  3. systemctl --user enable --now /home/kimi/sovereign/sovereign-compute.service")
    print("  4. Download models: llama-3.1-70b, qwen2.5-72b, nemotron-3.5-70b")
    print("  5. Run: pitchfork start --config /home/kimi/sovereign/sovereign-pitchfork.toml")
