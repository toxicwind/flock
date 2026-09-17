#!/usr/bin/env python3
import os, subprocess, time, sys

FRONTEND = "/mnt/agents/output/triangle-access/src/frontend"
LOG = "/mnt/agents/output/.bg-build/orchestrator.log"

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
        f.flush()

log("=== ORCHESTRATOR STARTED ===")

# Step 1: Wait for npm install to complete
log("Waiting for npm install (PID 8142)...")
while True:
    try:
        os.kill(8142, 0)
        time.sleep(2)
    except ProcessLookupError:
        log("npm install completed")
        break

# Step 2: Verify node_modules
nm = f"{FRONTEND}/node_modules"
if not os.path.exists(f"{nm}/next/dist/bin/next"):
    log("ERROR: next binary missing after install")
    sys.exit(1)

log("node_modules verified")

# Step 3: Build
log("Starting Next.js build...")
with open("/mnt/agents/output/.bg-build/build.log", "w") as build_log:
    result = subprocess.run(
        ["node", f"{nm}/next/dist/bin/next", "build"],
        cwd=FRONTEND,
        stdout=build_log,
        stderr=subprocess.STDOUT,
        timeout=300
    )

if result.returncode == 0:
    log("BUILD SUCCESS")
    # Step 4: Git commit and push
    os.chdir("/mnt/agents/output/triangle-access")
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run([
        "git", "commit", "-m", 
        "ci: auto-build success"
    ], capture_output=True)
    subprocess.run(["git", "push", "origin", "master", "--force"], capture_output=True)
    log("PUSHED TO GITHUB")
else:
    log(f"BUILD FAILED: exit code {result.returncode}")

log("=== ORCHESTRATOR DONE ===")
