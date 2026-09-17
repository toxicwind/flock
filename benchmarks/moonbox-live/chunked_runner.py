#!/usr/bin/env python3
"""
chunked_runner.py - Auto-hook wrapper that prevents response clipping.
Usage: python3 chunked_runner.py "your shell command here"
       python3 chunked_runner.py --file /path/to/large_output.txt
       python3 chunked_runner.py --json '{"key": "value"}'

If output > 8000 chars, auto-splits into numbered chunks in /tmp/chunks/
and returns metadata + first chunk. Subsequent chunks can be read via --read.
"""

import sys
import os
import json
import subprocess
import hashlib
import argparse
import importlib
from pathlib import Path
from datetime import datetime

CHUNK_DIR = Path("/tmp/chunks")
MAX_CHUNK = 7500  # Leave headroom for 10000 limit

def auto_install(module_name: str):
    """Auto-install missing module via pip and retry import."""
    print(f"[!] ModuleNotFoundError: {module_name}", file=sys.stderr)
    print(f"[*] Attempting pip install...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-input", module_name],
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode != 0:
        print(f"[!] pip install failed: {result.stderr[:200]}", file=sys.stderr)
        return False
    print(f"[+] Installed {module_name}, retrying import...", file=sys.stderr)
    importlib.invalidate_caches()
    return True

def import_with_retry(module_name: str):
    """Import module, auto-install if missing."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        if auto_install(module_name):
            return importlib.import_module(module_name)
        raise

def ensure_dir():
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

def chunk_string(data: str, size: int = MAX_CHUNK) -> list:
    """Split string into chunks, preferring line boundaries."""
    chunks = []
    while data:
        if len(data) <= size:
            chunks.append(data)
            break
        # Find last newline before size limit
        split_at = data.rfind('\n', 0, size)
        if split_at == -1:
            split_at = size
        chunks.append(data[:split_at])
        data = data[split_at:].lstrip('\n')
    return chunks

def save_chunks(data: str, prefix: str = "chunk") -> dict:
    """Save data as numbered chunks, return metadata."""
    ensure_dir()
    chunks = chunk_string(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = hashlib.sha256(data[:256].encode()).hexdigest()[:8]
    basename = f"{prefix}_{timestamp}_{uid}"
    
    paths = []
    for i, chunk in enumerate(chunks):
        path = CHUNK_DIR / f"{basename}_{i:03d}.txt"
        path.write_text(chunk, encoding='utf-8')
        paths.append(str(path))
    
    meta = {
        "basename": basename,
        "total_chunks": len(chunks),
        "total_bytes": len(data.encode('utf-8')),
        "total_chars": len(data),
        "paths": paths,
        "first_chunk_preview": chunks[0][:500] + "..." if len(chunks[0]) > 500 else chunks[0]
    }
    # Save metadata
    meta_path = CHUNK_DIR / f"{basename}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    meta["meta_path"] = str(meta_path)
    return meta

def run_command(cmd: str) -> dict:
    """Run shell command, capture output, auto-chunk if too long."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = f"=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}\n=== EXIT CODE ===\n{result.returncode}"
    
    if len(combined) > MAX_CHUNK:
        meta = save_chunks(combined, prefix="cmd")
        return {
            "status": "chunked",
            "message": f"Output chunked into {meta['total_chunks']} files (total {meta['total_chars']} chars)",
            "meta": meta,
            "first_chunk": combined[:MAX_CHUNK]
        }
    else:
        return {
            "status": "ok",
            "output": combined
        }

def read_chunk(basename: str, index: int = 0) -> str:
    """Read a specific chunk by basename and index."""
    pattern = f"{basename}_{index:03d}.txt"
    for f in CHUNK_DIR.glob(f"{basename}_*.txt"):
        if f.name == pattern:
            return f.read_text(encoding='utf-8')
    return f"ERROR: Chunk {index} for {basename} not found"

def list_chunks() -> list:
    """List all available chunk sets."""
    ensure_dir()
    metas = sorted(CHUNK_DIR.glob("*_meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [json.loads(m.read_text()) for m in metas[:20]]

def main():
    parser = argparse.ArgumentParser(description="Chunked output runner")
    parser.add_argument("command", nargs="?", help="Shell command to run")
    parser.add_argument("--file", help="Chunk an existing file instead of running command")
    parser.add_argument("--json", help="Chunk a JSON string")
    parser.add_argument("--read", help="Read chunk by basename")
    parser.add_argument("--index", type=int, default=0, help="Chunk index to read")
    parser.add_argument("--list", action="store_true", help="List available chunks")
    parser.add_argument("--clean", action="store_true", help="Clean old chunks")
    args = parser.parse_args()
    
    if args.list:
        chunks = list_chunks()
        print(json.dumps(chunks, indent=2))
        return
    
    if args.read:
        print(read_chunk(args.read, args.index))
        return
    
    if args.clean:
        for f in CHUNK_DIR.glob("*"):
            f.unlink()
        print("Cleaned all chunks")
        return
    
    if args.file:
        data = Path(args.file).read_text(encoding='utf-8', errors='replace')
        meta = save_chunks(data, prefix="file")
        print(json.dumps({"status": "chunked", "meta": meta}, indent=2))
        return
    
    if args.json:
        data = args.json
        meta = save_chunks(data, prefix="json")
        print(json.dumps({"status": "chunked", "meta": meta}, indent=2))
        return
    
    if args.command:
        result = run_command(args.command)
        print(json.dumps(result, indent=2))
        return
    
    parser.print_help()

if __name__ == "__main__":
    main()
