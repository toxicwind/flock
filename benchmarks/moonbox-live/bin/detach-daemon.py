#!/usr/bin/env python3
import os, sys, subprocess, signal

def daemonize(cmd, logfile="/dev/null"):
    """Proper double-fork daemon that survives parent death."""
    # First fork
    pid = os.fork()
    if pid > 0:
        os._exit(0)  # Parent exits immediately
    
    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
    
    # Second fork
    pid = os.fork()
    if pid > 0:
        os._exit(0)  # First child exits
    
    # Grandchild is now fully detached
    # Redirect stdio
    si = open(os.devnull, 'r')
    so = open(logfile, 'a+')
    se = open(logfile, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    
    # Execute
    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: detach-daemon.py <command> [args...]")
        sys.exit(1)
    daemonize(sys.argv[1:])
