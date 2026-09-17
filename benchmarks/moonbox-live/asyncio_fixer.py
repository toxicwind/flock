#!/usr/bin/env python3
import os, sys

def fix_file(path):
    try:
        with open(path) as f:
            orig = f.read()
    except Exception as e:
        return False, f"read_error: {e}"

    if "BULLETPROOF_KILLER" in orig:
        return False, "already_patched"

    patched = orig

    # Fix 1: os.getpgid(proc.pid) without try
    if "pgid = os.getpgid(proc.pid)" in patched and "try:
                        pgid = os.getpgid" not in patched:
        patched = patched.replace(
            "pgid = os.getpgid(proc.pid)",
            "try:
                        pgid = os.getpgid(proc.pid)
                    except (OSError, ProcessLookupError):
                        pgid = proc.pid
                    except Exception:
                        pgid = proc.pid"
        )

    # Fix 2: os.killpg(pgid, signal.SIGKILL) without try
    if "os.killpg(pgid, signal.SIGKILL)" in patched:
        patched = patched.replace(
            "os.killpg(pgid, signal.SIGKILL)",
            "try:
                            os.killpg(pgid, signal.SIGKILL)
                        except (OSError, ProcessLookupError):
                            pass
                        except Exception:
                            pass"
        )

    # Fix 3: os.killpg(os.getpgid(proc.pid), signal.SIGKILL) inline
    if "os.killpg(os.getpgid(proc.pid), signal.SIGKILL)" in patched:
        patched = patched.replace(
            "os.killpg(os.getpgid(proc.pid), signal.SIGKILL)",
            "try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        pass
                    except Exception:
                        pass"
        )

    if patched != orig:
        with open(path, "w") as f:
            f.write(patched)
        return True, "patched"
    return False, "no_vulnerable_pattern"

patched = 0
for path in sys.argv[1:]:
    ok, reason = fix_file(path)
    if ok:
        patched += 1
        print(f"[FIXED] {path}")
    else:
        print(f"[SKIP] {path}: {reason}")
print(f"\nTotal patched: {patched}")
