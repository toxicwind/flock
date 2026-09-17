#!/usr/bin/env python3
"""Permission fixer - unhide and chmod everything for kimi user."""
import os, stat, subprocess

BASE = "/mnt/agents/output"

def fix_all():
    for root, dirs, files in os.walk(BASE):
        for d in dirs:
            dpath = os.path.join(root, d)
            try:
                os.chmod(dpath, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
            except:
                pass
        for f in files:
            fpath = os.path.join(root, f)
            try:
                os.chmod(fpath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
            except:
                pass
    print("Permissions fixed for all files under", BASE)

if __name__ == "__main__":
    fix_all()
