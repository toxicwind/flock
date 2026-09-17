#!/usr/bin/env python3
"""batch_push.py - Parallel push multiple repos."""
import os, sys, subprocess, json, time, concurrent.futures

TOKEN = os.environ["GITHUB_PAT"]

def push_one(args):
    folder, repo, branch = args
    t0 = time.time()
    cmd = f"python3 /mnt/agents/output/git_push_module.py '{folder}' '{repo}' '{branch}'"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        dt = (time.time() - t0) * 1000
        try:
            data = json.loads(r.stdout)
            data["batch_ms"] = round(dt, 2)
            return data
        except:
            return {"repo": repo, "status": "parse_fail", "stdout": r.stdout[:200], "ms": round(dt, 2)}
    except Exception as e:
        return {"repo": repo, "status": "exception", "error": str(e)}

def main():
    # Read repo list from argv or stdin
    repos = []
    if len(sys.argv) > 1:
        # argv: folder,repo,branch folder,repo,branch
        for arg in sys.argv[1:]:
            parts = arg.split(",")
            if len(parts) >= 2:
                repos.append((parts[0], parts[1], parts[2] if len(parts) > 2 else "main"))
    else:
        # Auto-discover from /mnt/agents/output
        import pathlib
        out = pathlib.Path("/mnt/agents/output")
        for d in out.iterdir():
            if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_"):
                if (d / "README.md").exists() or (d / "package.json").exists() or (d / "pyproject.toml").exists():
                    repos.append((str(d), d.name, "main"))

    print(f"§BATCH§ Pushing {len(repos)} repos with {min(4, len(repos))} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(repos))) as ex:
        results = list(ex.map(push_one, repos))

    for r in results:
        status = "OK" if r.get("pushed") else "FAIL"
        print(f"[{status}] {r.get('repo','?')} in {r.get('batch_ms', r.get('ms',0)):.0f}ms")

    # Save report
    out = pathlib.Path("/mnt/agents/output/.bg_logs")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"batch_push_{int(time.time())}.json").write_text(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()
