
import subprocess, re
files = subprocess.check_output("grep -rl 'github_pat_[A-Za-z0-9_]{20,}' . --include='*.py' --include='*.sh' --include='*.md' 2>/dev/null | grep -v '/.git/' | grep -v '.hooks' || true", shell=True).decode().strip().split("\n")
for f in files:
    if f and Path(f).exists():
        text = Path(f).read_text()
        scrubbed = re.sub(r'github_pat_[A-Za-z0-9_]{20,}', '__GITHUB_PAT_FROM_ENV__', text)
        if scrubbed != text:
            Path(f).write_text(scrubbed)
            subprocess.run(["git", "add", f], capture_output=True)
