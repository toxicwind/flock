
import subprocess, sys
files = subprocess.check_output("git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true", shell=True).decode().strip().split("\n")
for f in files:
    if f and Path(f).exists():
        subprocess.run(["ruff", "check", "--fix", f], capture_output=True)
        subprocess.run(["black", "-q", f], capture_output=True)
        subprocess.run(["git", "add", f], capture_output=True)
