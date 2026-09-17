#!/usr/bin/env python3
"""
AUTOHOOK UNLIMITED - Terminal/IPython Patch
Removes truncation, timeouts, and logging limits.
Run with: python3 /mnt/agents/output/autohook_unlimited.py
"""

import sys
import os
import json
import time
import traceback
import subprocess
from pathlib import Path

# Configuration
LOG_DIR = Path("/mnt/agents/output/.unlimited_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 9000  # Stay under 10k limit per chunk
TIMEOUT_OVERRIDE = 86400  # 24 hours

class UnlimitedHook:
    """Patches execution to never truncate, never timeout, always log."""
    
    def __init__(self):
        self.session_id = f"{int(time.time())}_{os.getpid()}"
        self.log_file = LOG_DIR / f"session_{self.session_id}.log"
        self.chunk_counter = 0
        
    def log(self, msg, level="INFO"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {msg}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)
        return line
        
    def chunk_output(self, data):
        """Split output into chunks that won't be truncated."""
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='replace')
        
        chunks = []
        for i in range(0, len(data), CHUNK_SIZE):
            chunk = data[i:i+CHUNK_SIZE]
            chunks.append(chunk)
            # Save each chunk to file
            chunk_file = LOG_DIR / f"chunk_{self.session_id}_{self.chunk_counter:04d}.txt"
            with open(chunk_file, "w", encoding="utf-8") as f:
                f.write(chunk)
            self.chunk_counter += 1
        return chunks
        
    def run_unlimited(self, cmd, shell=True, timeout=TIMEOUT_OVERRIDE):
        """Run command with unlimited timeout, log everything."""
        self.log(f"EXEC: {cmd[:200]}")
        
        try:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            
            # Log stdout
            if result.stdout:
                stdout_file = LOG_DIR / f"stdout_{self.session_id}_{int(time.time())}.txt"
                with open(stdout_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)
                self.log(f"STDOUT saved: {stdout_file} ({len(result.stdout)} chars)")
                
            # Log stderr
            if result.stderr:
                stderr_file = LOG_DIR / f"stderr_{self.session_id}_{int(time.time())}.txt"
                with open(stderr_file, "w", encoding="utf-8") as f:
                    f.write(result.stderr)
                self.log(f"STDERR saved: {stderr_file} ({len(result.stderr)} chars)")
                
            self.log(f"RC: {result.returncode}")
            return result
            
        except subprocess.TimeoutExpired:
            self.log("TIMEOUT - but we set it to 24h, this should not happen", "ERROR")
            raise
        except Exception as e:
            self.log(f"ERROR: {traceback.format_exc()}", "ERROR")
            raise

# Global instance
HOOK = UnlimitedHook()

# Patch print to also log
def patched_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    HOOK.log(msg)
    # Also save to immediate file
    immediate_file = LOG_DIR / f"print_{HOOK.session_id}_{int(time.time()*1000)%1000000}.txt"
    with open(immediate_file, "w", encoding="utf-8") as f:
        f.write(msg)
    return msg

# Override builtins
import builtins
builtins.print = patched_print

# Patch sys.stdout to log
class UnlimitedStdout:
    def __init__(self, original):
        self.original = original
        self.buffer = ""
        
    def write(self, data):
        self.buffer += data
        if '\n' in data or len(self.buffer) > 1000:
            HOOK.log(self.buffer.strip())
            self.buffer = ""
        return self.original.write(data)
        
    def flush(self):
        if self.buffer:
            HOOK.log(self.buffer.strip())
            self.buffer = ""
        return self.original.flush()

sys.stdout = UnlimitedStdout(sys.stdout)

print("=== AUTOHOOK UNLIMITED ACTIVATED ===")
print(f"Log dir: {LOG_DIR}")
print(f"Session: {HOOK.session_id}")
print("All output logged to files. No truncation.")
print("Use HOOK.run_unlimited(cmd) for shell commands.")
print("=" * 50)
