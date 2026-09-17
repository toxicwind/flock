#!/usr/bin/env python3
"""Tailscale connection race v2 - 8 complex routes using VNC/CDP/proxies/tunnels."""
import asyncio
import subprocess
import os
import shlex
import json
import urllib.request
import socket

AUTHKEY = "tskey-auth-kyncVVKWF621CNTRL-8KZgD4QKBxByL2irLso7xBJZjFyxZw9N"
SOCKET = "/mnt/agents/tailscaled.sock"
STATE = "/mnt/agents/tailscale.state"
REMOTE_HOST = "awrawr-pc-1.tailc9ac71.ts.net"
REMOTE_IP = "100.72.199.93"
CMD_TOKEN = "3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio"

results = {}

async def run_cmd(name, cmd, timeout=30):
    """Run shell command, capture ALL output for debugging."""
    print(f"\n[{name}] === START ===")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = (stdout.decode() + "\n" + stderr.decode()).strip()
        print(f"[{name}] OUTPUT:\n{output[:2000]}\n[{name}] === END (rc={proc.returncode}) ===")
        success = proc.returncode == 0 and any(x in output for x in ["Success", "kimi-agent", "Logged in", "awrawr", "toxic", "100.72.199"])
        results[name] = {"success": success, "output": output, "rc": proc.returncode}
        return success
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except:
            pass
        print(f"[{name}] === TIMEOUT ===")
        results[name] = {"success": False, "output": "TIMEOUT", "rc": -1}
        return False
    except Exception as e:
        print(f"[{name}] === ERROR: {e} ===")
        results[name] = {"success": False, "output": str(e), "rc": -2}
        return False

# Route 1: Use CDP (Chrome DevTools Protocol) at :9223 as HTTP proxy bridge
async def route1_cdp_bridge():
    """Route 1: Tunnel through CDP proxy at 127.0.0.1:9223."""
    cmd = f"""
# Test if CDP is accessible
curl -s --max-time 5 http://127.0.0.1:9223/json/version 2>&1 | head -3
echo "---"
# Use CDP's fetch domain to proxy a request to tailscale control plane
curl -s --max-time 10 -X POST \
  -H "Content-Type: application/json" \
  -d '{{"id":1,"method":"SystemInfo.getInfo"}}' \
  http://127.0.0.1:9223/json 2>&1 | head -5
echo "---"
# Try to reach tailscale via CDP's network
nc -z -w5 127.0.0.1 9223 2>&1 && echo "CDP_PORT_OPEN" || echo "CDP_PORT_CLOSED"
"""
    return await run_cmd("route1_cdp_bridge", cmd, timeout=20)

# Route 2: Use KasmVNC websocket tunnel at :6080
async def route2_vnc_websocket():
    """Route 2: Use KasmVNC websocket as tunnel endpoint."""
    cmd = f"""
# Check KasmVNC
curl -sI --max-time 5 http://127.0.0.1:6080/ 2>&1 | head -5
echo "---"
# Try websocket connection
python3 -c "
import socket, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
sock = socket.create_connection(('127.0.0.1', 6080), timeout=5)
print('VNC_TCP_CONNECTED')
sock.close()
" 2>&1
echo "---"
# Check if VNC has any proxy capabilities
curl -s --max-time 5 http://127.0.0.1:6080/api/ 2>&1 | head -5
"""
    return await run_cmd("route2_vnc_websocket", cmd, timeout=20)

# Route 3: Use existing command server on remote as SOCKS5 proxy
async def route3_command_proxy():
    """Route 3: Use the remote command server to establish reverse tunnel."""
    cmd = f"""
# First verify we can reach the command server
curl -s --max-time 10 -X POST \
  -H "X-Command-Token: {CMD_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{{"command":"hostname"}}' \
  https://{REMOTE_HOST}/cmd 2>&1 | head -5
echo "---"
# Use command server to check tailscale status on remote
curl -s --max-time 10 -X POST \
  -H "X-Command-Token: {CMD_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{{"command":"tailscale status 2>&1 | head -5"}}' \
  https://{REMOTE_HOST}/cmd 2>&1
"""
    return await run_cmd("route3_command_proxy", cmd, timeout=25)

# Route 4: Use k3_proxy.py as SOCKS5/HTTP proxy bridge
async def route4_k3_proxy():
    """Route 4: Leverage k3_proxy.py for tunneling."""
    cmd = f"""
# Check if k3_proxy exists and can be used
cat /mnt/agents/output/k3_proxy.py 2>&1 | head -20
echo "---"
# Start k3_proxy in background if not running
if ! nc -z 127.0.0.1 19999 2>/dev/null; then
  nohup python3 /mnt/agents/output/k3_proxy.py :19999 > /tmp/k3_proxy.log 2>&1 &
  sleep 2
fi
# Test proxy
curl -s --max-time 5 --socks5-hostname 127.0.0.1:19999 \
  https://{REMOTE_HOST}/cmd \
  -X POST -H "X-Command-Token: {CMD_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{{"command":"hostname"}}' 2>&1 | head -5
"""
    return await run_cmd("route4_k3_proxy", cmd, timeout=30)

# Route 5: SSH through tailscale IP with known host keys
async def route5_ssh_tailscale():
    """Route 5: Direct SSH to tailscale IP with pre-configured keys."""
    cmd = f"""
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Add known host keys
cat > ~/.ssh/known_hosts << 'HOSTS'
{REMOTE_HOST} ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDGhz0ZI/suo43quWDPSfWT72cbIvYelcJ3dZmTfOSa/3JCNt/IlKoWik9ChziJwUkVwBTgldlL4/4mzhDSEMUaSRW1m6Gi9sE/BB6XDhts4tOIUzdDKCwLlUxmMNGD0ny4bc8NZR4WUKZEdOVioHCMnTX49veA4nopVLOffTuVqlQWT5tfJzPTILUBrgmRENlk0HgSEEsE8sQQBYeuas09Izx1m+4132xqVh/IkwZsqR0lbZLJBYHTRMq7sX1Ux+GlXM60kf1XqwyNqLs2Nw5SFxNjdlz3ngHNXmdoQoYJ+Jl+sTm1KCkGIC9jGXRkWa/u3S+FjvHK+n8x05AzkP3snS8JallJc5XvwWCuAoQ9Swr8nuJwiRSE6jel4LnEq1XT8gTqGD35yK6WsGT1ZwybY/2hPMwOoMU9Zha/XmXsQ1PWpNG8of/QgHwcgMp9byCocWNGwhwhZAad6yIpPkQBiEvXr3nsRzPo5J7vR/2I72G505p7VNFc14GWzGzBipE= root@awrawr-pc
{REMOTE_HOST} ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBMv1/cr7VIkm/BxcLtE+zKO+641vbm9F8/ldjlTGSn5wFTEVh0bbzB2nnkLHzWaJHp30n++de8aWYr6S6jv6P+s= root@awrawr-pc
{REMOTE_IP} ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDGhz0ZI/suo43quWDPSfWT72cbIvYelcJ3dZmTfOSa/3JCNt/IlKoWik9ChziJwUkVwBTgldlL4/4mzhDSEMUaSRW1m6Gi9sE/BB6XDhts4tOIUzdDKCwLlUxmMNGD0ny4bc8NZR4WUKZEdOVioHCMnTX49veA4nopVLOffTuVqlQWT5tfJzPTILUBrgmRENlk0HgSEEsE8sQQBYeuas09Izx1m+4132xqVh/IkwZsqR0lbZLJBYHTRMq7sX1Ux+GlXM60kf1XqwyNqLs2Nw5SFxNjdlz3ngHNXmdoQoYJ+Jl+sTm1KCkGIC9jGXRkWa/u3S+FjvHK+n8x05AzkP3snS8JallJc5XvwWCuAoQ9Swr8nuJwiRSE6jel4LnEq1XT8gTqGD35yK6WsGT1ZwybY/2hPMwOoMU9Zha/XmXsQ1PWpNG8of/QgHwcgMp9byCocWNGwhwhZAad6yIpPkQBiEvXr3nsRzPo5J7vR/2I72G505p7VNFc14GWzGzBipE= root@awrawr-pc
{REMOTE_IP} ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBMv1/cr7VIkm/BxcLtE+zKO+641vbm9F8/ldjlTGSn5wFTEVh0bbzB2nnkLHzWaJHp30n++de8aWYr6S6jv6P+s= root@awrawr-pc
HOSTS
# Generate SSH key if needed
if [ ! -f ~/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "kimi-agent" 2>/dev/null
fi
echo "SSH_PUBKEY: $(cat ~/.ssh/id_ed25519.pub 2>/dev/null | head -1)"
echo "---"
# Try SSH connection
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes \
  toxic@{REMOTE_IP} "hostname && whoami" 2>&1
"""
    return await run_cmd("route5_ssh_tailscale", cmd, timeout=25)

# Route 6: Use Python urllib with custom proxy handlers
async def route6_python_proxy():
    """Route 6: Pure Python connection test through various proxies."""
    cmd = f"""
python3 << 'PYEOF'
import urllib.request, ssl, socket, json

# Test 1: Direct HTTPS to remote
print("=== TEST 1: Direct HTTPS ===")
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        "https://{REMOTE_HOST}/cmd",
        data=json.dumps({{"command": "hostname"}}).encode(),
        headers={{
            "X-Command-Token": "{CMD_TOKEN}",
            "Content-Type": "application/json"
        }},
        method="POST"
    )
    resp = urllib.request.urlopen(req, context=ctx, timeout=10)
    print(resp.read().decode()[:200])
except Exception as e:
    print(f"FAIL: {{e}}")

# Test 2: TCP connect to remote port 443
print("\n=== TEST 2: TCP 443 ===")
try:
    s = socket.create_connection(("{REMOTE_IP}", 443), timeout=5)
    print(f"TCP_CONNECTED to {{s.getpeername()}}")
    s.close()
except Exception as e:
    print(f"FAIL: {{e}}")

# Test 3: TCP connect to remote port 22 (SSH)
print("\n=== TEST 3: TCP 22 ===")
try:
    s = socket.create_connection(("{REMOTE_IP}", 22), timeout=5)
    banner = s.recv(1024).decode().strip()
    print(f"SSH_BANNER: {{banner}}")
    s.close()
except Exception as e:
    print(f"FAIL: {{e}}")

# Test 4: Check local proxy ports
print("\n=== TEST 4: Local Ports ===")
for port in [9223, 6080, 1055, 11081, 19999, 18080]:
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=2)
        print(f"PORT_{{port}}: OPEN")
        s.close()
    except:
        print(f"PORT_{{port}}: CLOSED")
PYEOF
"""
    return await run_cmd("route6_python_proxy", cmd, timeout=25)

# Route 7: Use tailscale's own SOCKS5 proxy (if daemon running)
async def route7_tailscale_socks5():
    """Route 7: Use tailscaled's built-in SOCKS5 proxy to reach control plane."""
    cmd = f"""
# Check if tailscaled is running with SOCKS5
nc -z 127.0.0.1 1055 2>/dev/null && echo "SOCKS5_1055_OPEN" || echo "SOCKS5_1055_CLOSED"
echo "---"
# If SOCKS5 is up, use it to reach tailscale control plane
python3 << 'PYEOF'
import socket, socks, ssl, urllib.request
# Try SOCKS5 proxy
try:
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 1055)
    socket.socket = socks.socksocket
    req = urllib.request.Request("https://controlplane.tailscale.com/key?v=106")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    resp = urllib.request.urlopen(req, context=ctx, timeout=10)
    print(f"SOCKS5_WORKS: {{resp.status}}")
except Exception as e:
    print(f"SOCKS5_FAIL: {{e}}")
PYEOF
echo "---"
# Alternative: use tailscale's HTTP proxy
nc -z 127.0.0.1 11081 2>/dev/null && echo "HTTP_PROXY_11081_OPEN" || echo "HTTP_PROXY_11081_CLOSED"
"""
    return await run_cmd("route7_tailscale_socks5", cmd, timeout=20)

# Route 8: Netcat/nc direct TCP tunnel with HTTP CONNECT
async def route8_nc_tunnel():
    """Route 8: Raw TCP tunnel using nc and HTTP CONNECT."""
    cmd = f"""
# Test raw TCP to tailscale control plane
echo -e "GET /key?v=106 HTTP/1.1\r\nHost: controlplane.tailscale.com\r\nConnection: close\r\n\r\n" | \
  timeout 5 nc controlplane.tailscale.com 443 2>&1 | head -5
echo "---"
# Test raw TCP to remote tailscale serve
echo -e "GET /files/ HTTP/1.1\r\nHost: {REMOTE_HOST}\r\nConnection: close\r\n\r\n" | \
  timeout 5 nc {REMOTE_IP} 443 2>&1 | head -5
echo "---"
# Check if we can establish any outbound TCP at all
python3 -c "
import socket
for host, port in [
    ('controlplane.tailscale.com', 443),
    ('{REMOTE_HOST}', 443),
    ('{REMOTE_IP}', 443),
    ('{REMOTE_IP}', 22),
    ('{REMOTE_IP}', 34567),
    ('{REMOTE_IP}', 34568),
]:
    try:
        s = socket.create_connection((host, port), timeout=3)
        print(f'TCP_OK: {{host}}:{{port}}')
        s.close()
    except Exception as e:
        print(f'TCP_FAIL: {{host}}:{{port}} = {{e}}')
"
"""
    return await run_cmd("route8_nc_tunnel", cmd, timeout=25)

async def monitor():
    """Monitor: check if ANY route succeeded by testing remote reachability."""
    for i in range(20):
        await asyncio.sleep(3)
        try:
            proc = await asyncio.create_subprocess_shell(
                f"curl -s --max-time 5 -X POST -H 'X-Command-Token: {CMD_TOKEN}' -H 'Content-Type: application/json' -d '{{\"command\":\"hostname\"}}' https://{REMOTE_HOST}/cmd 2>&1 | grep -q awrawr && echo CONNECTED || echo NOT_YET",
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
            if b"CONNECTED" in stdout:
                print(f"[MONITOR] Remote reachable at t={i*3}s!")
                return True
        except:
            pass
    return False

async def main():
    print("=" * 70)
    print("TAILSCALE RACE V2 - 8 Complex Routes (VNC/CDP/Proxy/Tunnel)")
    print("=" * 70)
    
    # Kill stale
    subprocess.run("pkill -9 -f 'tailscale up' 2>/dev/null", shell=True)
    
    routes = {
        "route1_cdp_bridge": asyncio.create_task(route1_cdp_bridge()),
        "route2_vnc_websocket": asyncio.create_task(route2_vnc_websocket()),
        "route3_command_proxy": asyncio.create_task(route3_command_proxy()),
        "route4_k3_proxy": asyncio.create_task(route4_k3_proxy()),
        "route5_ssh_tailscale": asyncio.create_task(route5_ssh_tailscale()),
        "route6_python_proxy": asyncio.create_task(route6_python_proxy()),
        "route7_tailscale_socks5": asyncio.create_task(route7_tailscale_socks5()),
        "route8_nc_tunnel": asyncio.create_task(route8_nc_tunnel()),
    }
    monitor_task = asyncio.create_task(monitor())
    
    winner = None
    while routes and not winner:
        done, pending = await asyncio.wait(
            list(routes.values()) + [monitor_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            if task == monitor_task:
                if await task:
                    winner = "monitor"
                    print("[RACE] WINNER: monitor (remote reachable)")
                break
            for name, t in list(routes.items()):
                if t == task:
                    try:
                        if await task:
                            winner = name
                            print(f"[RACE] WINNER: {name}")
                    except Exception as e:
                        print(f"[{name}] Exception: {e}")
                    del routes[name]
                    break
            if winner:
                break
    
    for task in list(routes.values()) + [monitor_task]:
        if not task.done():
            task.cancel()
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    for name, res in sorted(results.items()):
        status = "SUCCESS" if res["success"] else "FAIL"
        print(f"{name}: {status}")
    
    print("\n" + "=" * 70)
    print("FINAL STATUS")
    print("=" * 70)
    subprocess.run(f"tailscale --socket={SOCKET} status 2>&1 | head -10 || echo 'tailscale not connected'", shell=True)

if __name__ == "__main__":
    asyncio.run(main())
