#!/usr/bin/env python3
import os, sys, json, subprocess, time, socket, urllib.request, urllib.error

CONFIG_PATH = "/mnt/portal-overlay/.agent-gw.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def test_dns(hostname):
    try:
        ip = socket.getaddrinfo(hostname, None)[0][4][0]
        print(f"[DNS] {hostname} -> {ip} OK")
        return True
    except Exception as e:
        print(f"[DNS] FAILED: {e}")
        return False

def test_tcp(host, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        print(f"[TCP] {host}:{port} OK")
        return True
    except Exception as e:
        print(f"[TCP] FAILED: {e}")
        return False

def test_http(url, api_key, timeout=10):
    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "weird_x7k9m2p_bin/2.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            print(f"[HTTP] Status: {resp.status}")
            print(f"[HTTP] Response: {data[:500]}")
            return resp.status, data
    except urllib.error.HTTPError as e:
        print(f"[HTTP] HTTPError: {e.code} - {e.reason}")
        return e.code, str(e)
    except Exception as e:
        print(f"[HTTP] FAILED: {e}")
        return -1, str(e)

def test_github(pat):
    try:
        req = urllib.request.Request("https://api.github.com/user")
        req.add_header("Authorization", f"token {pat}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"[GITHUB] Authenticated as: {data.get('login', 'unknown')}")
            print(f"[GITHUB] Rate limit remaining: {resp.headers.get('X-RateLimit-Remaining', 'unknown')}")
            return True
    except Exception as e:
        print(f"[GITHUB] FAILED: {e}")
        return False

def test_worker():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect("/tmp/arc_agi_worker.sock")
        s.sendall(json.dumps({"type": "ping"}).encode())
        s.shutdown(socket.SHUT_WR)
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
        result = json.loads(resp.decode())
        print(f"[WORKER] Status: {result.get('status', 'unknown')}")
        return result.get('status') == 'pong'
    except Exception as e:
        print(f"[WORKER] FAILED: {e}")
        return False

def test_drive9():
    try:
        st = os.statvfs("/mnt/agents")
        total_gb = (st.f_frsize * st.f_blocks) / (1024**3)
        free_gb = (st.f_frsize * st.f_bfree) / (1024**3)
        print(f"[DRIVE9] Total: {total_gb:.1f}GB, Free: {free_gb:.1f}GB")
        return True
    except Exception as e:
        print(f"[DRIVE9] FAILED: {e}")
        return False

def test_cdp():
    try:
        req = urllib.request.Request("http://127.0.0.1:9223/json/version")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            print(f"[CDP] Browser: {data.get('Browser', 'unknown')}")
            print(f"[CDP] Protocol: {data.get('Protocol-Version', 'unknown')}")
            return True
    except Exception as e:
        print(f"[CDP] FAILED: {e}")
        return False

def main():
    print("=" * 60)
    print("weird_x7k9m2p_bin v2.0 - Agent Gateway Router & Tester")
    print("=" * 60)
    
    config = load_config()
    api_key = config["api_key"]
    base_url = config["base_url"]
    chat_id = config["kimi_chat_id"]
    
    print(f"[CONFIG] chat_id: {chat_id}")
    print(f"[CONFIG] base_url: {base_url}")
    
    results = {}
    hostname = base_url.replace("https://", "").split("/")[0]
    results["dns"] = test_dns(hostname)
    results["tcp"] = test_tcp(hostname, 443)
    status, data = test_http(base_url, api_key)
    results["http"] = status in [200, 401, 403, 404]
    
    pat = os.environ.get("GITHUB_TOKEN", "")
    results["github"] = test_github(pat) if pat else False
    results["worker"] = test_worker()
    results["drive9"] = test_drive9()
    results["cdp"] = test_cdp()
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for test, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {test}")
    
    all_pass = all(results.values())
    print(f"\nOverall: {'ALL SYSTEMS GO' if all_pass else 'SOME FAILURES'}")
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
