#!/usr/bin/env python3
# ultimate_git.py — FUSE-safe git operations for moonbox
# Never uses tmp, never bare, auto-init, no manual steps ever again

import os, sys, subprocess, pathlib, json, time, hashlib

DOT = pathlib.Path("/mnt/agents/dot")
LOG = []
def log(msg):
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    line = f"[{ts}] {msg}"
    LOG.append(line)
    print(line, flush=True)

# ── CONFIG ──
PAT = os.environ.get("GH_PAT") or os.environ.get("MOONBOX_PAT") or ""
GITHUB_USER = "toxicwind"
PREFIX = "moonbox"

# ── FUSE-SAFE GIT INIT ──
def init_git(work_tree):
    """Initialize a FUSE-safe git repo. Idempotent."""
    wt = pathlib.Path(work_tree)
    gd = wt / "_git"

    # If _git exists and has HEAD, it's already init'd
    if (gd / "HEAD").exists() and (gd / "config").exists():
        log(f"GIT_ALREADY_INIT:{wt.name}")
        return True

    # Create _git structure manually (no git init, avoids FUSE temp file issues)
    log(f"GIT_INIT:{wt.name}")

    for sub in ["objects/info", "objects/pack", "refs/heads", "refs/tags", "hooks", "info"]:
        (gd / sub).mkdir(parents=True, exist_ok=True)

    # HEAD
    (gd / "HEAD").write_text("ref: refs/heads/main\n")

    # config (FUSE-safe settings)
    config = """[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true
    preloadindex = false
    fsyncobjectfiles = false
[init]
    defaultBranch = main
"""
    (gd / "config").write_text(config)

    # description
    (gd / "description").write_text(f"moonbox repo for {wt.name}\n")

    # info/exclude
    (gd / "info" / "exclude").write_text("""# git ls-files --others --exclude-from=.git/info/exclude
# Lines that start with '#' are comments.
*.log
*.tmp
""")

    # index file — empty index
    # Git needs a valid index. We'll create it via git command with proper env
    env = {
        **os.environ,
        "GIT_DIR": str(gd),
        "GIT_WORK_TREE": str(wt),
    }

    # Use git update-index to create index
    r = subprocess.run(["git", "update-index", "--refresh"], env=env, capture_output=True)
    if r.returncode != 0:
        # Create empty index manually
        import struct
        # Git index format: DIRC + version(4) + entries(0) + SHA1
        index_data = b'DIRC' + struct.pack('>III', 2, 0, 0)
        # Add SHA1 of header (simplified — git will rebuild)
        index_data += b'\x00' * 20
        with open(gd / "index", "wb") as f:
            f.write(index_data)

    log(f"GIT_INIT_DONE:{wt.name}")
    return True

# ── FUSE-SAFE ADD/COMMIT/PUSH ──
def git_op(work_tree, *args):
    """Run git command with FUSE-safe env."""
    wt = pathlib.Path(work_tree)
    gd = wt / "_git"

    if not (gd / "HEAD").exists():
        init_git(wt)

    env = {
        **os.environ,
        "GIT_DIR": str(gd),
        "GIT_WORK_TREE": str(wt),
        "GIT_AUTHOR_NAME": f"moonbox-{os.uname().nodename[:8]}",
        "GIT_AUTHOR_EMAIL": f"moonbox@{os.uname().nodename}.local",
        "GIT_COMMITTER_NAME": f"moonbox-{os.uname().nodename[:8]}",
        "GIT_COMMITTER_EMAIL": f"moonbox@{os.uname().nodename}.local",
        "GIT_ASKPASS": "/bin/false",
        "GIT_TERMINAL_PROMPT": "0",
    }

    cmd = ["git"] + list(args)
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if r.returncode != 0 and r.stderr:
        log(f"GIT_ERR:{wt.name}:{' '.join(args)}:{r.stderr[:100]}")
    else:
        log(f"GIT_OK:{wt.name}:{' '.join(args)}")

    return r.returncode == 0, r.stdout, r.stderr

# ── AUTO-REMOTE ──
def ensure_remote(work_tree, repo_name=None):
    """Ensure GitHub remote exists. Create if needed."""
    wt = pathlib.Path(work_tree)
    if not repo_name:
        repo_name = f"{PREFIX}-{wt.name}-{time.strftime('%Y%m%d')}"

    # Check if remote exists
    ok, out, err = git_op(wt, "remote", "get-url", "origin")
    if ok:
        log(f"REMOTE_EXISTS:{wt.name}")
        return True

    # Create repo on GitHub
    log(f"REMOTE_CREATE:{repo_name}")
    headers = {
        "Authorization": f"token {PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = json.dumps({"name": repo_name, "private": True, "auto_init": False})

    r = subprocess.run(
        ["curl", "-s", "-m10", "-H", f"Authorization: token {PAT}",
         "-H", "Accept: application/vnd.github.v3+json",
         "-d", data, "https://api.github.com/user/repos"],
        capture_output=True, text=True
    )

    if r.returncode == 0 and '"id"' in r.stdout:
        log(f"REMOTE_CREATED:{repo_name}")
    else:
        log(f"REMOTE_CREATE_ERR:{r.stderr[:100] if r.stderr else r.stdout[:100]}")

    # Add remote
    remote_url = f"https://toxicwind:{PAT}@github.com/toxicwind/{repo_name}.git"
    git_op(wt, "remote", "add", "origin", remote_url)
    return True

# ── AUTO-PUSH ──
def autopush(work_tree, message=None):
    """Add all, commit, push. Fully automatic."""
    wt = pathlib.Path(work_tree)
    if not message:
        message = f"autopush:{int(time.time())}:{wt.name}"

    log(f"AUTOPUSH_START:{wt.name}")

    # Init if needed
    init_git(wt)

    # Ensure remote
    ensure_remote(wt)

    # Add all
    git_op(wt, "add", "-A")

    # Commit (may fail if nothing to commit, that's ok)
    ok, out, err = git_op(wt, "commit", "-m", message, "--quiet")

    # Push
    ok, out, err = git_op(wt, "push", "origin", "main", "--force", "--quiet")
    if ok:
        log(f"AUTOPUSH_OK:{wt.name}")
        return True
    else:
        log(f"AUTOPUSH_FAIL:{wt.name}:{err[:100] if err else 'unknown'}")
        return False

# ── MAIN ──
def main():
    if len(sys.argv) < 2:
        print("Usage: ultimate_git.py <command> [args...]")
        print("Commands: init <dir>, add <dir>, commit <dir> <msg>, push <dir>, autopush <dir>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        for d in sys.argv[2:]:
            init_git(d)
    elif cmd == "autopush":
        for d in sys.argv[2:]:
            autopush(d)
    elif cmd == "autopush-all":
        # Push all dirs under /mnt/agents
        for d in pathlib.Path("/mnt/agents").iterdir():
            if d.is_dir() and d.name != "dot":
                autopush(d)
    elif cmd == "init-all":
        for d in pathlib.Path("/mnt/agents").iterdir():
            if d.is_dir():
                init_git(d)
    else:
        # Pass through to git
        work_tree = sys.argv[2]
        git_args = sys.argv[3:]
        ok, out, err = git_op(work_tree, *git_args)
        print(out)
        if err:
            print(err, file=sys.stderr)
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
