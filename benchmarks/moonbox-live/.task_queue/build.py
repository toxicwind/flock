import subprocess, os, time
os.environ["PATH"] = "/root/.bun/bin:" + os.environ.get("PATH", "")
os.chdir("/mnt/agents/output/app")
with open("/mnt/agents/output/.bg_logs/build.log", "w") as log:
    log.write(f"[{time.time()}] START\n")
    p1 = subprocess.run(["/root/.bun/bin/bun", "install"], capture_output=True, text=True)
    log.write(p1.stdout[-2000:] + "\n" + p1.stderr[-500:] + "\n")
    p2 = subprocess.run(["/root/.bun/bin/bun", "run", "build"], capture_output=True, text=True)
    log.write(p2.stdout[-3000:] + "\n" + p2.stderr[-500:] + "\n")
    log.write(f"[{time.time()}] DONE rc={p2.returncode}\n")
    if p2.returncode == 0:
        subprocess.run(["git", "config", "user.email", "agent@many-never-one.local"])
        subprocess.run(["git", "config", "user.name", "ManyNeverOne Agent"])
        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", f"auto: build {time.time()}"])
        subprocess.run(["git", "push", f"https://${GITHUB_PAT}", "main"], capture_output=True)
    open("/mnt/agents/output/.build_done", "w").write("done")
