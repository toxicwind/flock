#!/usr/bin/env python3
"""git_push_module.py - Modular auto-push with _git persistence.
Usage: python3 git_push_module.py <folder> <repo_name> [branch]
"""
import os, sys, subprocess, json, time, pathlib, shutil

TOKEN = os.environ["GITHUB_PAT"]

def run(cmd, cwd=None, t=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, cwd=cwd)
        return r.returncode == 0, (r.stdout or ""), (r.stderr or "")
    except Exception as e:
        return False, "", str(e)

def restore_git(project_dir):
    """Restore .git from _git/ if exists."""
    d = pathlib.Path(project_dir)
    git_dir = d / ".git"
    backup_dir = d / "_git"

    if backup_dir.exists() and not git_dir.exists():
        shutil.copytree(backup_dir, git_dir)
        return True
    return False

def backup_git(project_dir):
    """Backup .git to _git/ after push."""
    d = pathlib.Path(project_dir)
    git_dir = d / ".git"
    backup_dir = d / "_git"

    if git_dir.exists():
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(git_dir, backup_dir)
        return True
    return False

def push_folder(folder, repo_name, branch="main"):
    d = pathlib.Path(folder).resolve()
    if not d.exists():
        print(f"[!] Folder not found: {d}")
        return False

    t0 = time.time()

    # Step 1: Restore git metadata
    restored = restore_git(d)

    # Step 2: Init if no .git
    git_dir = d / ".git"
    if not git_dir.exists():
        run("git init", cwd=d, t=5)
        run(f"git checkout -b {branch}", cwd=d, t=3)

    # Step 3: Config
    run("git config user.email 'toxicwind@users.noreply.github.com'", cwd=d, t=2)
    run("git config user.name 'toxicwind'", cwd=d, t=2)
    run("git config --add safe.directory '*'", cwd=d, t=2)

    # Step 4: Remote
    remote_url = f"https://{TOKEN}@github.com/toxicwind/{repo_name}.git"
    run("git remote remove origin 2>/dev/null", cwd=d, t=2)
    run(f"git remote add origin {remote_url}", cwd=d, t=2)

    # Step 5: Fetch origin to check if repo has content
    ok, out, err = run("git fetch origin main --depth=1 2>&1", cwd=d, t=8)
    has_origin = ok and "fatal" not in err.lower()

    # Step 6: If repo exists on origin and we have no commits, pull first
    if has_origin:
        commits = run("git log --oneline -1 2>/dev/null", cwd=d, t=2)
        if not commits[0]:  # No local commits
            run("git pull origin main --allow-unrelated-histories --depth=1 2>/dev/null || true", cwd=d, t=8)

    # Step 7: Stage and commit
    run("git add -A", cwd=d, t=5)
    ok, out, err = run(f'git commit -m "sync: {time.strftime("%Y-%m-%d %H:%M")}"', cwd=d, t=5)
    committed = ok or "nothing to commit" in (out + err).lower()

    # Step 8: Push
    ok, out, err = run(f"git push -u origin {branch} --force 2>&1", cwd=d, t=15)
    pushed = ok or "Everything up-to-date" in out or "Everything up-to-date" in err

    # Step 9: Backup git metadata
    backup_git(d)

    # Step 10: Remove .git to avoid drive9 conflicts
    if git_dir.exists():
        shutil.rmtree(git_dir)

    dt = (time.time() - t0) * 1000
    result = {
        "folder": str(d),
        "repo": repo_name,
        "branch": branch,
        "restored": restored,
        "committed": committed,
        "pushed": pushed,
        "ms": round(dt, 2),
        "stderr": err[:200] if err else "",
    }

    print(json.dumps(result, indent=2))
    return pushed

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 git_push_module.py <folder> <repo_name> [branch]")
        sys.exit(1)
    push_folder(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "main")
