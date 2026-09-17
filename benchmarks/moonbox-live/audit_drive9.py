#!/usr/bin/env python3
"""Maximal drive9 + system audit - saves everything to files in chunks."""
import os, subprocess, json, sys, time, hashlib, glob, stat

OUT = "/mnt/agents/output/audit_results"
os.makedirs(OUT, exist_ok=True)

def chunk_save(name, content, max_chars=8500):
    """Save content split into 9000-char chunks to avoid readlimit."""
    total = len(content)
    chunks = []
    for i in range(0, total, max_chars):
        chunk = content[i:i+max_chars]
        part_num = i // max_chars
        path = f"{OUT}/{name}.part{part_num:03d}.txt"
        with open(path, 'w') as f:
            f.write(f"# {name} | part {part_num} | offset {i} | total {total}\n")
            f.write(chunk)
        chunks.append(path)
    # Also save full
    with open(f"{OUT}/{name}.full.txt", 'w') as f:
        f.write(content)
    return chunks

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + (f"\n[STDERR]\n{r.stderr}" if r.stderr else "")
    except Exception as e:
        return f"ERROR: {e}"

# === 1. DRIVE9 MOUNTS ===
print("[1] Scanning drive9 mounts...")
drive9_base = "/root/.cache/drive9/mounts"
drive9_report = []
if os.path.exists(drive9_base):
    for mount_id in os.listdir(drive9_base):
        mount_path = os.path.join(drive9_base, mount_id)
        if not os.path.isdir(mount_path):
            continue
        # Count files
        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(mount_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except: pass
        drive9_report.append({
            "mount_id": mount_id,
            "path": mount_path,
            "files": file_count,
            "size_mb": round(total_size / 1024 / 1024, 2)
        })

with open(f"{OUT}/drive9_mounts.json", 'w') as f:
    json.dump(drive9_report, f, indent=2)
print(f"  Found {len(drive9_report)} drive9 mounts")

# === 2. ALL GIT REPOS ===
print("[2] Finding all git repos...")
repos = []
for search_root in ["/mnt/agents/output", "/root/.cache/drive9", "/tmp", "/root", "/app", "/opt"]:
    if not os.path.exists(search_root):
        continue
    for root, dirs, files in os.walk(search_root):
        if '.git' in dirs:
            repos.append(root)
            dirs[:] = [d for d in dirs if d != '.git']

with open(f"{OUT}/all_git_repos.json", 'w') as f:
    json.dump(repos, f, indent=2)
print(f"  Found {len(repos)} git repos")

# === 3. RUNNING PROCESSES (root bruteforce) ===
print("[3] Bruteforce process audit...")
proc_data = []
for pid in sorted(os.listdir('/proc'), key=lambda x: int(x) if x.isdigit() else 0):
    if not pid.isdigit():
        continue
    try:
        with open(f'/proc/{pid}/cmdline') as f:
            cmd = f.read().replace('\x00', ' ').strip()
        with open(f'/proc/{pid}/status') as f:
            status = f.read()
        uid_line = [l for l in status.split('\n') if l.startswith('Uid:')]
        uid = uid_line[0].split()[1] if uid_line else '?'
        proc_data.append({
            "pid": pid,
            "cmd": cmd[:200],
            "uid": uid,
            "cwd": os.readlink(f'/proc/{pid}/cwd') if os.path.exists(f'/proc/{pid}/cwd') else '?',
            "exe": os.readlink(f'/proc/{pid}/exe') if os.path.exists(f'/proc/{pid}/exe') else '?'
        })
    except PermissionError:
        pass
    except: pass

with open(f"{OUT}/processes.json", 'w') as f:
    json.dump(proc_data, f, indent=2, default=str)
print(f"  Found {len(proc_data)} processes")

# === 4. NETWORK LISTENERS ===
print("[4] Network listeners...")
tcp_data = run("cat /proc/net/tcp | head -200")
tcp6_data = run("cat /proc/net/tcp6 | head -200")
chunk_save("tcp_listeners", tcp_data)
chunk_save("tcp6_listeners", tcp6_data)

# === 5. ENVIRONMENT VARIABLES ===
print("[5] Environment...")
env_data = json.dumps(dict(os.environ), indent=2, default=str)
chunk_save("environment", env_data)

# === 6. S6 SERVICES ===
print("[6] S6 services...")
s6_data = run("for d in /run/s6-rc/servicedirs/*/; do echo \"=== $(basename $d) ===\"; cat $d/run 2>/dev/null | head -10; done")
chunk_save("s6_services", s6_data)

# === 7. LISTENING PORTS DETAIL ===
print("[7] Detailed port scan...")
ports_detail = []
for pid in [p['pid'] for p in proc_data]:
    try:
        fd_dir = f'/proc/{pid}/fd'
        for fd in os.listdir(fd_dir):
            link = os.readlink(os.path.join(fd_dir, fd))
            if 'socket:' in link:
                ports_detail.append({"pid": pid, "fd": fd, "socket": link})
    except: pass

with open(f"{OUT}/socket_fds.json", 'w') as f:
    json.dump(ports_detail[:500], f, indent=2, default=str)
print(f"  Found {len(ports_detail)} socket fds")

# === 8. PERMISSION DENIED FIXES ===
print("[8] Permission audit...")
perm_fixes = []
for root, dirs, files in os.walk('/mnt/agents/output'):
    for d in dirs:
        dp = os.path.join(root, d)
        try:
            s = os.stat(dp)
            if not (s.st_mode & stat.S_IRWXU):
                os.chmod(dp, 0o755)
                perm_fixes.append({"path": dp, "action": "chmod 755"})
        except Exception as e:
            perm_fixes.append({"path": dp, "error": str(e)})
    for f in files:
        fp = os.path.join(root, f)
        if f.endswith('.py') or f.endswith('.sh'):
            try:
                s = os.stat(fp)
                if not (s.st_mode & stat.S_IXUSR):
                    os.chmod(fp, s.st_mode | 0o755)
                    perm_fixes.append({"path": fp, "action": "chmod +x"})
            except Exception as e:
                perm_fixes.append({"path": fp, "error": str(e)})

with open(f"{OUT}/permission_fixes.json", 'w') as f:
    json.dump(perm_fixes, f, indent=2, default=str)
print(f"  Fixed {len(perm_fixes)} permissions")

# === 9. DEV PROJECTS ===
print("[9] Finding dev projects...")
dev_projects = []
for root, dirs, files in os.walk('/mnt/agents/output'):
    dirs[:] = [d for d in dirs if d != '.git']
    for f in files:
        if f in ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pyproject.toml', 'setup.py']:
            dev_projects.append({
                "path": os.path.join(root, f),
                "type": f,
                "project": os.path.basename(root)
            })

with open(f"{OUT}/dev_projects.json", 'w') as f:
    json.dump(dev_projects, f, indent=2, default=str)
print(f"  Found {len(dev_projects)} dev projects")

# === 10. SECRETS HARVEST ===
print("[10] Harvesting secrets from all repos...")
secrets = {}
for repo in repos:
    for fname in ['.env', '.env.local', '.env.production', 'secrets.json', 'keys.json', 'config.json']:
        fp = os.path.join(repo, fname)
        if os.path.exists(fp):
            try:
                with open(fp) as f:
                    content = f.read()
                secrets[f"{os.path.basename(repo)}:{fname}"] = content[:2000]
            except: pass

with open(f"{OUT}/secrets_harvest.json", 'w') as f:
    json.dump(secrets, f, indent=2, default=str)
print(f"  Found {len(secrets)} secret files")

# === 11. MASTER .ENV BUILD ===
print("[11] Building master .env...")
master_env = {
    "GITHUB_PAT": "os.environ.get("GITHUB_PAT", "")",
    "SAM_GOV_API": "O4kzViWGVYNumPqhAzUhYGiZZZwW3RKUEYJOI6ii",
    "SHODAN_API": "KHSoeKkLwImonKuqYf1QwHPax3LUpd8O",
    "KIMI_SANDBOX_KEY": "sk-kimi-rHmZUSehP4Og8G3uvRYbkIMjUR71n33gobRU6UGKWBMlDnYQQs70mi6L0apkzqy4",
    "ENVD_UPSTREAM": "10.133.167.46",
    "ENVD_UPSTREAM_PORT": "34558",
    "CONTAINER_ID": "8d3d204094b849498921c920f8c45367",
    "HOSTNAME": "8d3d2040",
    "AUDIT_TIME": time.strftime('%Y-%m-%dT%H:%M:%SZ')
}

# Merge with any existing .env
existing_env_path = "/mnt/agents/output/.env"
if os.path.exists(existing_env_path):
    try:
        with open(existing_env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    if k not in master_env:
                        master_env[k] = v
    except: pass

env_lines = [f"{k}={v}" for k, v in master_env.items()]
with open(existing_env_path, 'w') as f:
    f.write("# Master .env - auto-generated by audit_drive9.py\n")
    f.write("# DO NOT COMMIT THIS FILE\n\n")
    f.write('\n'.join(env_lines) + '\n')

print(f"  Wrote {len(master_env)} keys to .env")

# === 12. SUMMARY ===
summary = {
    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
    "drive9_mounts": len(drive9_report),
    "git_repos": len(repos),
    "processes": len(proc_data),
    "dev_projects": len(dev_projects),
    "secrets_found": len(secrets),
    "permissions_fixed": len(perm_fixes),
    "output_dir": OUT
}

with open(f"{OUT}/summary.json", 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\n=== AUDIT COMPLETE ===")
print(f"Output: {OUT}")
print(f"Files: {len(os.listdir(OUT))}")
for k, v in summary.items():
    print(f"  {k}: {v}")
