#!/usr/bin/env python3
"""Deep scan every readable file and save to .logjson format."""
import os, json, base64, binascii, stat
from pathlib import Path
from datetime import datetime

TARGETS = [
    "/mnt/portal-overlay",
    "/mnt/agents/output",
    "/app",
    "/opt",
    "/run/service",
    "/etc/s6",
]

OUT = Path("/mnt/agents/output/.bg_logs/deep_scan.logjson")
OUT.parent.mkdir(parents=True, exist_ok=True)

SKIPPED = {"/proc", "/sys", "/dev", "/tmp", "/mnt/agents/output/.bg_logs"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB max per file

def is_text(data):
    try:
        data.decode('utf-8')
        return True
    except:
        return False

def scan_file(fpath):
    try:
        st = os.stat(fpath)
        size = st.st_size
        
        if size > MAX_SIZE:
            return {"path": str(fpath), "size": size, "skipped": "too_large"}
        
        with open(fpath, "rb") as f:
            raw = f.read()
        
        result = {
            "ts": datetime.now().isoformat(),
            "path": str(fpath),
            "size": size,
            "mode": oct(st.st_mode),
            "uid": st.st_uid,
            "gid": st.st_gid,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
        }
        
        if is_text(raw):
            result["type"] = "text"
            result["content"] = raw.decode('utf-8', errors='replace')
        else:
            result["type"] = "binary"
            result["hex_preview"] = binascii.hexlify(raw[:256]).decode()
            result["base64"] = base64.b64encode(raw[:1024]).decode()
        
        return result
    except PermissionError:
        return {"path": str(fpath), "error": "permission_denied"}
    except Exception as e:
        return {"path": str(fpath), "error": str(e)}

def main():
    count = 0
    with open(OUT, "w") as outf:
        for base in TARGETS:
            base = Path(base)
            if not base.exists():
                continue
            for root, dirs, files in os.walk(base):
                # Skip certain dirs
                dirs[:] = [d for d in dirs if not any(str(Path(root)/d).startswith(s) for s in SKIPPED)]
                for fname in files:
                    fpath = Path(root) / fname
                    result = scan_file(fpath)
                    outf.write(json.dumps(result, default=str) + "\n")
                    count += 1
                    if count % 1000 == 0:
                        print(f"Scanned {count} files...")
    print(f"Done. Scanned {count} files. Output: {OUT}")

if __name__ == "__main__":
    main()
