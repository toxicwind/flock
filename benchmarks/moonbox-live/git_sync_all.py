#!/usr/bin/env python3
"""Mass git sync: find all repos, auto-commit, auto-push, handle merges, report errors."""
import os, subprocess, sys, json, time
from pathlib import Path

REPORT = {"synced": [], "errors": [], "skipped": [], "timestamp": time.time()}

def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)

def find_git_repos(root="/"):
    repos = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            repos.append(dirpath)
            # Don't recurse into subdirs of a git repo
            dirnames[:] = [d for d in dirnames if d != ".git"]
    return repos

def sync_repo(repo_path):
    # Check if remote exists
    rc, out, err = run("git remote get-url origin", cwd=repo_path, timeout=10)
    if rc != 0:
        REPORT["skipped"].append({"path": repo_path, "reason": "no remote origin"})
        return
    remote = out.strip()
    
    # Set identity if missing
    run("git config user.email 'kimi@recon.local' || true", cwd=repo_path, timeout=5)
    run("git config user.name 'Kimi Recon' || true", cwd=repo_path, timeout=5)
    
    # Stage all
    run("git add -A", cwd=repo_path, timeout=10)
    
    # Check if there are changes
    rc, out, err = run("git diff --cached --stat", cwd=repo_path, timeout=10)
    if rc != 0 or not out.strip():
        REPORT["skipped"].append({"path": repo_path, "reason": "no changes to commit"})
        return
    
    # Commit
    msg = f"mass-sync: auto-commit {time.strftime('%Y-%m-%d %H:%M:%S')}"
    rc, out, err = run(f'git commit -m "{msg}"', cwd=repo_path, timeout=30)
    if rc != 0:
        REPORT["errors"].append({"path": repo_path, "stage": "commit", "error": err})
        return
    
    # Pull with merge strategy to auto-resolve
    rc, out, err = run("git pull origin $(git branch --show-current) --no-rebase --strategy=recursive --strategy-option=theirs 2>&1 || git pull origin $(git branch --show-current) --no-rebase 2>&1 || true", cwd=repo_path, timeout=60)
    
    # Push
    rc, out, err = run("git push origin $(git branch --show-current)", cwd=repo_path, timeout=60)
    if rc != 0:
        # Try force push as last resort
        rc2, out2, err2 = run("git push origin $(git branch --show-current) --force-with-lease", cwd=repo_path, timeout=60)
        if rc2 != 0:
            REPORT["errors"].append({"path": repo_path, "stage": "push", "error": err + " | force: " + err2})
            return
    
    REPORT["synced"].append({"path": repo_path, "remote": remote, "commit": msg})

def main():
    # Find repos in common locations
    roots = ["/tmp", "/mnt/agents/output", "/root", "/home", "/app", "/opt"]
    all_repos = set()
    for root in roots:
        if os.path.isdir(root):
            for repo in find_git_repos(root):
                all_repos.add(repo)
    
    print(f"Found {len(all_repos)} git repositories")
    for repo in sorted(all_repos):
        print(f"  Syncing: {repo}")
        sync_repo(repo)
    
    # Save report
    report_path = "/mnt/agents/output/git_sync_report.json"
    with open(report_path, "w") as f:
        json.dump(REPORT, f, indent=2)
    
    print(f"\n=== SYNC REPORT ===")
    print(f"Synced: {len(REPORT['synced'])}")
    print(f"Errors: {len(REPORT['errors'])}")
    print(f"Skipped: {len(REPORT['skipped'])}")
    print(f"Report saved: {report_path}")
    
    for e in REPORT["errors"]:
        print(f"  ERROR: {e['path']} [{e['stage']}] {e['error'][:200]}")

if __name__ == "__main__":
    main()
