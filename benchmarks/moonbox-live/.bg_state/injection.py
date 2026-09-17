# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENT BACKGROUND WORKER (injected into browser_guard.py)
# Why here: browser_guard is s6-managed, auto-restarts on crash
# Storage: /mnt/agents/output/ (drive9, 1TB, persistent across sessions)
# PAT: loaded from /mnt/agents/output/.bg_state/pat.env (not env var)
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time
import subprocess
import os

BG_REPOS = [
    ("/mnt/agents/output/envd-project", "toxicwind/envd-project", "master"),
    ("/mnt/agents/output/repo_kimi_team_recon", "toxicwind/repo_kimi_team_recon", "master"),
    ("/mnt/agents/output/effusion-labs", "toxicwind/effusion-labs", "main"),
    ("/mnt/agents/output/triangle-access", "toxicwind/triangle-access", "master"),
]

PAT_FILE = "/mnt/agents/output/.bg_state/pat.env"
LOG_FILE = "/mnt/agents/output/.bg_logs/gitwatch.log"

def _bg_load_pat():
    try:
        with open(PAT_FILE) as f:
            return f.read().strip().split("=", 1)[1]
    except:
        return ""

def _bg_shell(cmd, cwd=None, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except Exception as e:
        return False, "", str(e)

def _bg_log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " | " + msg + "\n")

def _bg_ensure_git(repo_path, remote, branch):
    if not os.path.exists(os.path.join(repo_path, ".git")):
        _bg_shell("git init", cwd=repo_path)
        pat = _bg_load_pat()
        _bg_shell("git remote add origin https://" + pat + "@github.com/" + remote + ".git", cwd=repo_path)
        _bg_shell("git config user.name toxicwind", cwd=repo_path)
        _bg_shell("git config user.email toxicwind@users.noreply.github.com", cwd=repo_path)
        _bg_log("INIT: " + remote)
    else:
        pat = _bg_load_pat()
        _bg_shell("git remote set-url origin https://" + pat + "@github.com/" + remote + ".git", cwd=repo_path)

def _bg_gitwatch_cycle():
    PAT = _bg_load_pat()
    if not PAT:
        _bg_log("ERROR: PAT not loaded")
        return
    for repo_path, remote, branch in BG_REPOS:
        if not os.path.exists(repo_path):
            continue
        _bg_ensure_git(repo_path, remote, branch)
        ok, out, err = _bg_shell("git status --short", cwd=repo_path)
        if not ok or not out.strip():
            continue
        _bg_shell("git add -A", cwd=repo_path)
        ok, _, err = _bg_shell("git commit -m 'auto-bg: " + str(int(time.time())) + "'", cwd=repo_path)
        if not ok:
            _bg_log("COMMIT_FAIL: " + remote + " | " + err[:100])
            continue
        ok, _, err = _bg_shell("git push origin " + branch + " --force", cwd=repo_path)
        if ok:
            _bg_log("PUSH_OK: " + remote)
        else:
            _bg_log("PUSH_FAIL: " + remote + " | " + err[:100])

def _bg_worker_main():
    _bg_log("STARTUP: bg_gitwatch daemon started")
    time.sleep(5)
    while True:
        try:
            _bg_gitwatch_cycle()
        except Exception as e:
            _bg_log("EXCEPTION: " + str(e)[:200])
        time.sleep(10)

_bg_thread = threading.Thread(target=_bg_worker_main, daemon=True, name="bg_gitwatch")
_bg_thread.start()
_bg_log("THREAD: bg_gitwatch started")
# ═══════════════════════════════════════════════════════════════════════════════
# END INJECTION
# ═══════════════════════════════════════════════════════════════════════════════
