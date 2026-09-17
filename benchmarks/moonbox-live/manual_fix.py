import sys, os

def fix_file(path):
    with open(path) as f:
        content = f.read()
    
    # Simple fix: wrap os.killpg in try/except
    if "os.killpg" in content and "except (OSError, ProcessLookupError)" not in content:
        content = content.replace(
            "os.killpg(pgid, signal.SIGKILL)",
            "try:\n                        os.killpg(pgid, signal.SIGKILL)\n                    except (OSError, ProcessLookupError):\n                        pass\n                    except Exception:\n                        pass"
        )
        content = content.replace(
            "os.killpg(os.getpgid(proc.pid), signal.SIGKILL)",
            "try:\n                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)\n                    except (OSError, ProcessLookupError):\n                        pass\n                    except Exception:\n                        pass"
        )
        with open(path, "w") as f:
            f.write(content)
        return True
    return False

for path in sys.argv[1:]:
    if os.path.exists(path):
        if fix_file(path):
            print(f"[FIXED] {path}")
        else:
            print(f"[SKIP] {path}")
    else:
        print(f"[MISSING] {path}")
