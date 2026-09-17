#!/usr/bin/env python3
"""Auto-fix common syntax errors in Python files."""
import sys, re, pathlib

fixes = {
    r'TOKEN = "os\.environ\.get\(\'GITHUB_PAT\', \'\'\)"':
        'TOKEN = os.environ.get("GITHUB_PAT", "")',
    r'${GITHUB_PAT}':
        'os.environ.get("GITHUB_PAT", "")',
    r'"shell agent"':
        r'\"shell agent\"',
}

for f in pathlib.Path(".").rglob("*.py"):
    try:
        text = f.read_text()
        orig = text
        for bad, good in fixes.items():
            text = re.sub(bad, good, text)
        if text != orig:
            f.write_text(text)
            print(f"[AUTO-FIX] {f}")
    except:
        pass

print("[AUTO-FIX] Done")
