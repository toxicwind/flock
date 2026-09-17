#!/usr/bin/env python3
"""autohook_v12.py - Clean utilities. NO subprocess patch. NO IPython touch."""
import os, subprocess, json, time, pathlib

OUT = pathlib.Path("/mnt/agents/output")
LOG = OUT / ".bg_logs" / "ah12.log"
CHUNK = OUT / ".moonbox_chunks"
for d in (LOG.parent, CHUNK):
    d.mkdir(parents=True, exist_ok=True)

def lg(msg, lvl="INFO"):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] [{lvl}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def chunk(data, prefix="chunk"):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    if len(data) <= 9000:
        return []
    files = []
    for i in range(0, len(data), 9000):
        fn = CHUNK / f"{prefix}_{int(time.time())}_{i:05d}.txt"
        fn.write_text(data[i:i+9000])
        files.append(str(fn))
    return files

def frun(cmd, t=8, cwd=None):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, cwd=cwd)
        dt = (time.time() - t0) * 1000
        if len(r.stdout) > 9500:
            chunk(r.stdout, "stdout")
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except Exception as e:
        return False, "", str(e)

def gsync(path, repo, branch="main"):
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    if not (p / ".git").exists():
        frun("git init", cwd=p, t=3)
        frun(f"git checkout -b {branch}", cwd=p, t=2)
    frun("git config user.email 'toxicwind@users.noreply.github.com'", cwd=p, t=2)
    frun("git config user.name 'toxicwind'", cwd=p, t=2)
    token = os.environ.get("GITHUB_PAT", "")
    remote = f"https://{token}@github.com/{repo}.git"
    frun("git remote remove origin 2>/dev/null", cwd=p, t=2)
    frun(f"git remote add origin {remote}", cwd=p, t=2)
    frun("git add -A", cwd=p, t=3)
    ok, out, err = frun(f'git commit -m "sync {time.strftime("%Y-%m-%d %H:%M")}"', cwd=p, t=3)
    if ok or "nothing to commit" in (out + err).lower():
        ok2, _, _ = frun(f"git push -u origin {branch} --force", cwd=p, t=10)
        return ok2
    return False

lg("§AUTOHOOK_V12_LOADED§")
