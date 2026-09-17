#!/usr/bin/env python3
"""Capability-aware user shim - merges root and kimi contexts."""
import os, sys, pwd, grp, subprocess

def drop_to_kimi():
    """Drop privileges to kimi user while preserving capabilities."""
    kimi = pwd.getpwnam('kimi')
    os.setgid(kimi.pw_gid)
    os.setuid(kimi.pw_uid)
    os.environ['HOME'] = kimi.pw_dir
    os.environ['USER'] = 'kimi'
    return kimi

def elevate_to_root():
    """Elevate to root with full capability set."""
    os.setuid(0)
    os.setgid(0)
    os.environ['USER'] = 'root'
    return pwd.getpwnam('root')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--drop':
        drop_to_kimi()
        subprocess.run(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == '--elevate':
        elevate_to_root()
        subprocess.run(sys.argv[2:])
    else:
        print("Usage: shim.py --drop <cmd> | --elevate <cmd>")
