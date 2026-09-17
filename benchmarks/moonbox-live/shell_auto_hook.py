#!/usr/bin/env python3
"""Shell Auto-Hook v1.0 - Fixes dash/bash issues, logs everything."""
import subprocess, shlex, re, json, time, os
from datetime import datetime

class ShellHook:
    def __init__(self, log_dir="/mnt/agents/output/shell_hook_logs"):
        self.log_dir = log_dir
        self.call_count = 0
        os.makedirs(log_dir, exist_ok=True)
        
    def detect_shell(self):
        try:
            result = subprocess.run(["readlink", "-f", "/bin/sh"],
                capture_output=True, text=True, timeout=5)
            return "dash" if "dash" in result.stdout else "bash"
        except:
            return "unknown"
    
    def fix_command(self, cmd):
        fixes = []
        fixed = cmd
        
        # Wrap in bash if contains bashisms
        bashisms = [r'\[\[', r'\]\]', r'\bfunction\b', r'&>', r'<<<',
                    r'\$\(\([^)]+\)\)', r'\bdeclare\b']
        if any(re.search(b, fixed) for b in bashisms):
            fixed = f"bash -c {shlex.quote(fixed)}"
            fixes.append("bash_c_wrapper")
        
        return fixed, fixes
    
    def execute(self, cmd, description="", timeout=60):
        self.call_count += 1
        start = time.time()
        fixed_cmd, fixes = self.fix_command(cmd)
        
        log = {
            "timestamp": datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "call_id": self.call_count,
            "description": description,
            "original": cmd,
            "fixed": fixed_cmd,
            "fixes": fixes,
            "shell": self.detect_shell(),
        }
        
        try:
            result = subprocess.run(fixed_cmd, shell=True,
                capture_output=True, text=True, timeout=timeout,
                executable="/bin/bash" if fixed_cmd.startswith("bash -c") else "/bin/sh")
            log.update({
                "exit_code": result.returncode,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "duration_ms": round((time.time() - start) * 1000, 2),
                "success": result.returncode == 0,
            })
        except Exception as e:
            log.update({"exit_code": -1, "error": str(e), "success": False})
        
        with open(f"{self.log_dir}/call_{self.call_count:04d}.json", "w") as f:
            json.dump(log, f, indent=2, default=str)
        
        status = "OK" if log.get("success") else "FAIL"
        print(f"[{status}] #{self.call_count} {description} fixes={fixes}")
        return log

if __name__ == "__main__":
    hook = ShellHook()
    print(f"Shell detected: {hook.detect_shell()}")
    
    # Test 1: simple
    hook.execute("echo hello", "simple echo")
    
    # Test 2: bashism that would fail in dash
    hook.execute("if [[ 1 == 1 ]]; then echo ok; fi", "bashism test")
    
    # Test 3: nested subshell
    hook.execute("echo $(echo nested)", "subshell test")
    
    print("\nAll tests complete. Logs in:", hook.log_dir)
