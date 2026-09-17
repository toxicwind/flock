#!/usr/bin/env python3
"""fast_discover.py - BFS directory scan, no find command."""
import os, pathlib, json, time, concurrent.futures

def scan_dir(root, max_depth=2):
    """Fast BFS scan using os.scandir (C-level, no find subprocess)."""
    root = pathlib.Path(root)
    dirs, files = [], []
    q = [(root, 0)]
    while q:
        p, d = q.pop(0)
        if d > max_depth:
            continue
        try:
            with os.scandir(p) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        dirs.append(entry.path)
                        q.append((entry.path, d + 1))
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry.path)
        except (PermissionError, OSError):
            pass
    return dirs, files

def classify_project(path):
    """Detect project type by manifest files."""
    p = pathlib.Path(path)
    manifests = {
        "node": ("package.json",),
        "python": ("pyproject.toml", "setup.py", "requirements.txt"),
        "rust": ("Cargo.toml",),
        "go": ("go.mod",),
        "git": (".git",),
    }
    for ptype, files in manifests.items():
        if any((p / f).exists() for f in files):
            return ptype
    return None

def discover_projects(root="/mnt/agents/output", max_depth=2):
    t0 = time.time()
    dirs, files = scan_dir(root, max_depth)
    dt = (time.time() - t0) * 1000

    projects = []
    for d in dirs:
        p = pathlib.Path(d)
        ptype = classify_project(p)
        if ptype and p.name not in (".git", "__pycache__", "node_modules", ".bg_logs", ".bg_state"):
            projects.append({"path": str(p), "name": p.name, "type": ptype})

    return {
        "scan_ms": round(dt, 2),
        "dirs": len(dirs),
        "files": len(files),
        "projects": projects,
    }

if __name__ == "__main__":
    result = discover_projects()
    print(json.dumps(result, indent=2))
