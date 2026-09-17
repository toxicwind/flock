#!/usr/bin/env python3
"""Monadic parallel async tailscale connection race - 8 orthogonal routes."""
import asyncio
import subprocess
import os
import signal
import time
import sys
import shlex

AUTHKEY = "tskey-auth-kyncVVKWF621CNTRL-8KZgD4QKBxByL2irLso7xBJZjFyxZw9N"
SOCKET = "/mnt/agents/tailscaled.sock"
STATE = "/mnt/agents/tailscale.state"

results = {}

async def run_cmd(name, cmd, timeout=45):
    """Run a shell command with hard shell timeout, capture ALL output."""
    print(f"[{name}] Starting...")
    # Wrap in timeout(1) so the shell kills it even if subprocess hangs
    wrapped = f"timeout {timeout} bash -c {shlex.quote(cmd)}"
    try:
        proc = await asyncio.create_subprocess_shell(
            wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        output = (stdout.decode() + "\n" + stderr.decode()).strip()
        # Print FULL output for debugging
        print(f"[{name}] OUTPUT:\n{output}\n[{name}] END OUTPUT")
        success = proc.returncode == 0 and ("Success" in output or "kimi-agent" in output or "Logged in" in output)
        results[name] = {"success": success, "output": output, "rc": proc.returncode}
        print(f"[{name}] {'SUCCESS' if success else 'FAIL'} (rc={proc.returncode})")
        return success
    except asyncio.TimeoutError:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            pass
        results[name] = {"success": False, "output": "TIMEOUT", "rc": -1}
        print(f"[{name}] TIMEOUT")
        return False
    except Exception as e:
        results[name] = {"success": False, "output": str(e), "rc": -2}
        print(f"[{name}] ERROR: {e}")
        return False

async def route1_direct():
    """Route 1: Direct up via existing daemon."""
    cmd = f'tailscale --socket={SOCKET} up --authkey="{AUTHKEY}" --hostname=kimi-agent-r1 --accept-routes --accept-dns --timeout=60s'
    return await run_cmd("route1_direct", cmd, timeout=50)

async def route2_login():
    """Route 2: Login flow instead of up."""
    cmd = f'tailscale --socket={SOCKET} login --authkey="{AUTHKEY}"'
    return await run_cmd("route2_login", cmd, timeout=50)

async def route3_fresh_daemon():
    """Route 3: Kill daemon, fresh state, fresh up."""
    cmd = f"""
pkill -9 -f tailscaled 2>/dev/null; sleep 2
rm -f {STATE} 2>/dev/null
nohup tailscaled --tun=userspace-networking --state={STATE} --socket={SOCKET} > /tmp/tailscaled_r3.log 2>&1 &
# Wait for socket to exist (daemon ready)
for i in $(seq 1 15); do
  if [ -S {SOCKET} ]; then break; fi
  sleep 1
done
timeout 40 tailscale --socket={SOCKET} up --authkey="{AUTHKEY}" --hostname=kimi-agent-r3 --accept-routes --accept-dns --timeout=30s
"""
    return await run_cmd("route3_fresh_daemon", cmd, timeout=55)

async def route4_force_reauth():
    """Route 4: Force reauth on existing daemon."""
    cmd = f'tailscale --socket={SOCKET} up --authkey="{AUTHKEY}" --hostname=kimi-agent-r4 --force-reauth --accept-routes --accept-dns --timeout=60s'
    return await run_cmd("route4_force_reauth", cmd, timeout=50)

async def route5_reset():
    """Route 5: Nuclear reset."""
    cmd = f'tailscale --socket={SOCKET} up --authkey="{AUTHKEY}" --hostname=kimi-agent-r5 --reset --accept-routes --accept-dns --timeout=60s'
    return await run_cmd("route5_reset", cmd, timeout=50)

async def route6_oauth():
    """Route 6: OAuth/web flow (no authkey)."""
    cmd = f'tailscale --socket={SOCKET} up --hostname=kimi-agent-r6 --accept-routes --accept-dns --timeout=60s'
    return await run_cmd("route6_oauth", cmd, timeout=50)

async def route7_ssh_direct():
    """Route 7: SSH direct to known host (bypass tailscale mesh)."""
    cmd = """
mkdir -p ~/.ssh
cat > ~/.ssh/awrawr_config << 'SSHEOF'
Host awrawr-pc-1
    HostName 100.72.199.93
    User toxic
    StrictHostKeyChecking accept-new
    ConnectTimeout 10
SSHEOF
ssh -F ~/.ssh/awrawr_config -o BatchMode=yes -o ConnectTimeout=10 awrawr-pc-1 "hostname" 2>&1
"""
    return await run_cmd("route7_ssh_direct", cmd, timeout=20)

async def route8_netcheck_then_up():
    """Route 8: Netcheck diagnostic then up."""
    cmd = f"""
tailscale --socket={SOCKET} netcheck 2>&1 | head -5
tailscale --socket={SOCKET} up --authkey="{AUTHKEY}" --hostname=kimi-agent-r8 --accept-routes --accept-dns --timeout=60s
"""
    return await run_cmd("route8_netcheck_then_up", cmd, timeout=55)

async def monitor_status():
    """Poll tailscale status every 2s, print if connected."""
    for i in range(30):
        await asyncio.sleep(2)
        try:
            proc = await asyncio.create_subprocess_shell(
                f'tailscale --socket={SOCKET} status 2>&1 | head -5',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            out = stdout.decode()
            if "kimi-agent" in out or "100.72.199.93" in out:
                print(f"[MONITOR] CONNECTED at t={i*2}s!")
                print(out[:300])
                return True
        except:
            pass
    return False

async def main():
    print("=" * 60)
    print("TAILSCALE CONNECTION RACE - 8 Orthogonal Routes")
    print("=" * 60)
    
    # Kill stale tailscale up processes first
    subprocess.run("pkill -9 -f 'tailscale up' 2>/dev/null", shell=True)
    time.sleep(1)
    
    # Pre-flight: ensure daemon is actually running
    print("[PREFLIGHT] Checking daemon...")
    daemon_check = subprocess.run(
        f"tailscale --socket={SOCKET} version 2>&1 | head -1",
        shell=True, capture_output=True, text=True, timeout=5
    )
    if daemon_check.returncode != 0 or "not running" in daemon_check.stderr:
        print("[PREFLIGHT] Daemon dead, restarting...")
        subprocess.run("pkill -9 -f tailscaled 2>/dev/null", shell=True)
        time.sleep(2)
        subprocess.run(
            f"nohup tailscaled --tun=userspace-networking --state={STATE} --socket={SOCKET} > /tmp/tailscaled_preflight.log 2>&1 &",
            shell=True
        )
        time.sleep(3)
    
    # Start all 8 routes + monitor concurrently
    routes = {
        "route1": asyncio.create_task(route1_direct()),
        "route2": asyncio.create_task(route2_login()),
        "route3": asyncio.create_task(route3_fresh_daemon()),
        "route4": asyncio.create_task(route4_force_reauth()),
        "route5": asyncio.create_task(route5_reset()),
        "route6": asyncio.create_task(route6_oauth()),
        "route7": asyncio.create_task(route7_ssh_direct()),
        "route8": asyncio.create_task(route8_netcheck_then_up()),
    }
    monitor = asyncio.create_task(monitor_status())
    all_tasks = list(routes.values()) + [monitor]
    
    # Race: return when first route SUCCEEDS (not just completes)
    winner = None
    while routes and not winner:
        done, pending = await asyncio.wait(
            list(routes.values()) + [monitor],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            if task == monitor:
                # Monitor finished, check if it found connection
                if await task:
                    winner = "monitor"
                break
            # Find which route this was
            for name, t in list(routes.items()):
                if t == task:
                    try:
                        if await task:
                            winner = name
                            print(f"[RACE] WINNER: {name}")
                    except:
                        pass
                    del routes[name]
                    break
            if winner:
                break
    
    # Cancel remaining
    for task in list(routes.values()) + [monitor]:
        if not task.done():
            task.cancel()
    
    # Report
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, res in sorted(results.items()):
        status = "SUCCESS" if res["success"] else "FAIL"
        print(f"{name}: {status} (rc={res['rc']})")
    
    # Final status
    print("\n" + "=" * 60)
    print("FINAL TAILSCALE STATUS")
    print("=" * 60)
    proc = await asyncio.create_subprocess_shell(
        f'tailscale --socket={SOCKET} status 2>&1 | head -10',
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    print(stdout.decode() or "No status available")

if __name__ == "__main__":
    asyncio.run(main())
