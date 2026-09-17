#!/usr/bin/env python3
"""Persistent background git worker. Runs forever, auto-commits and pushes."""
import subprocess
import time
import os
import sys

PAT_FILE = "/mnt/agents/output/.bg_state/pat.env"
LOG_FILE = "/mnt/agents/output/.bg_logs/gitwatch.log"

REPOS = [
    ("/mnt/agents/output/envd-project", "toxicwind/envd-project", "master"),
    ("/mnt/agents/output/repo_kimi_team_recon", "toxicwind/repo_kimi_team_recon", "master"),
    ("/mnt/agents/output/effusion-labs", "toxicwind/effusion-labs", "main"),
    ("/mnt/agents/output/triangle-access", "toxicwind/triangle-access", "master"),
]

def load_pat():
    try:
        with open(PAT_FILE) as f:
            line = f.read().strip()
            return line.split("=", 1)[1]
    except Exception as e:
        log("PAT_LOAD_FAIL: " + str(e))
        return ""

def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG_FILE, "a") as f:
        f.write(ts + " | " + msg + "\n")
    print(ts + " | " + msg, flush=True)

def shell(cmd, cwd=None, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except Exception as e:
        return False, "", str(e)

def ensure_git(repo_path, remote, branch, pat):
    if not os.path.exists(os.path.join(repo_path, ".git")):
        shell("git init", cwd=repo_path)
        shell("git config user.name toxicwind", cwd=repo_path)
        shell("git config user.email toxicwind@users.noreply.github.com", cwd=repo_path)
    shell("git remote set-url origin https://" + pat + "@github.com/" + remote + ".git", cwd=repo_path)

def cycle():
    pat = load_pat()
    if not pat:
        log("NO_PAT")
        return
    
    for repo_path, remote, branch in REPOS:
        if not os.path.exists(repo_path):
            continue
        
        ensure_git(repo_path, remote, branch, pat)
        
        ok, out, err = shell("git status --short", cwd=repo_path)
        if not ok or not out.strip():
            continue
        
        log("CHANGES: " + remote + " | " + out.strip().replace("\n", " ")[:80])
        
        shell("git add -A", cwd=repo_path)
        ok, _, err = shell("git commit -m 'auto-bg-'" + str(int(time.time())), cwd=repo_path)
        if not ok:
            log("COMMIT_FAIL: " + remote + " | " + err[:100])
            continue
        
        ok, _, err = shell("git push origin " + branch + " --force", cwd=repo_path)
        if ok:
            log("PUSH_OK: " + remote)
        else:
            log("PUSH_FAIL: " + remote + " | " + err[:100])

def main():
    log("STARTUP: bg_worker v1")
    while True:
        try:
            cycle()
        except Exception as e:
            log("EXCEPTION: " + str(e)[:200])
        time.sleep(10)

if __name__ == "__main__":
    main()

# Auto-cleanup stale index.lock files (added after startup)
import glob
for lock in glob.glob("/mnt/agents/output/*/.git/index.lock"):
    age = time.time() - os.path.getmtime(lock)
    if age > 60:  # Older than 60 seconds = stale
        os.remove(lock)
        log("CLEANUP: removed stale lock " + lock)
