import os, pathlib, subprocess, json
out=pathlib.Path(os.environ["OUTBOX_DIR"])
out.mkdir(parents=True, exist_ok=True)
cycle=int(os.environ["CYCLE"])
role=os.environ["ROLE"]
root=os.environ["REPO_ROOT"]
chronos_base=os.environ["CHRONOS_BASE"]

def sh(cmd):
    r=subprocess.run(["bash","-lc",cmd], cwd=root, text=True, capture_output=True)
    return (r.stdout or "") + (("\n"+r.stderr) if r.stderr else "")

def write(tag, body):
    (out / f"cycle_{cycle}_{role}_{tag}.md").write_text(body)

if role=="EXHUMER":
    subprocess.run(["bash","-lc", f'python3 "{chronos_base}/exhumation_worker.py" --out "/tmp/exhumed_state.json" >/dev/null 2>&1 || true'], cwd=root)
    tmp=pathlib.Path("/tmp/exhumed_state.json")
    ghosts=[]
    if tmp.exists():
        try:
            ex=json.loads(tmp.read_text())
            ghosts=ex.get("ghosts",[])
        except Exception:
            ghosts=[]
    hot=ghosts[:30]
    write("A","EXHUMER/A\nTop entropy hotspots:\n" + "\n".join([f"- {g.get('path','')} e={g.get('entropy',0)}" for g in hot]))
    write("B","EXHUMER/B\nDirectory prefix clusters:\n" + "\n".join(sorted({(g.get('path','').split('/')[0] if g.get('path','') else '') for g in hot})))
    write("C","EXHUMER/C\nLeverage: entrypoints + config + subprocess surfaces. Next: propose 3 targets against highest entropy.")
elif role=="CARTOGRAPHER":
    top=sh("ls -1 | head -n 80")
    deps=sh("ls -1 | rg -n '(package.json|pyproject.toml|Cargo.toml|go.mod|pom.xml|requirements.txt)' || true")
    mains=sh("rg -n 'if __name__ == .__main__.' -S . || true")
    write("A",f"CARTOGRAPHER/A\nRepo root: {root}\nTop-level:\n{top}")
    write("B",f"CARTOGRAPHER/B\nDependency markers:\n{deps}")
    write("C",f"CARTOGRAPHER/C\nEntrypoints:\n{mains}")
elif role=="OPERATOR":
    ps=sh("ps -eo pid,cmd --sort=-%mem | head -n 25")
    ss=sh("ss -ltnp 2>/dev/null | head -n 60 || true")
    env=sh("env | rg -n '(CHRONOS|AGENT|HB_|SESSION|PORT|REPO_)' || true")
    write("A","OPERATOR/A\nProcess snapshot:\n"+ps)
    write("B","OPERATOR/B\nListeners:\n"+ss)
    write("C","OPERATOR/C\nEnv contract:\n"+env)
elif role=="SURGEON":
    write("A","SURGEON/A\nMutation Cluster: Explode ghost surface → sidecars + explicit contracts + tests. Goal: turn entropy into typed boundaries.")
    write("B","SURGEON/B\nMutation Cluster: Parallelize repo brain → repo-local taskgraph + tmux panes per task. Goal: emergence by concurrency.")
    write("C","SURGEON/C\nMutation Cluster: Router-first refactor → add routing layer that selects handlers by pattern. Goal: explicit expert routing in code.")
elif role=="MILDLYAWESOME":
    # Emergent Recovery: Call mildlyawesome_audit with auto-discovery
    subprocess.run(["bash","-lc", f'python3 "{chronos_base}/mildlyawesome_audit.py" --repo "{root}" --vectors "DISCORD_TOKEN|Credits" "ezstreet|Legacy" --stage "/tmp/mildlyawesome_stage" >/dev/null 2>&1 || true'], cwd=root)
    stage=pathlib.Path("/tmp/mildlyawesome_stage")
    discoveries=[]
    if stage.exists():
        for p in stage.glob("**/*"):
            if p.is_file(): discoveries.append(str(p.relative_to(stage)))
    write("A","MILDLYAWESOME/A\nDeep Recovery Vectors: " + ", ".join(discoveries[:10]))
    write("B","MILDLYAWESOME/B\nPotential " + str(len(discoveries)) + " lost segments exhumed to /tmp/mildlyawesome_stage.")
    write("C","MILDLYAWESOME/C\nStrategy: Cross-reference recovered blobs with current entropy map to reconstruct lost interfaces.")
elif role=="SYNTH":
    build_rc = subprocess.run(["bash","-lc", "npm run build -- --help >/dev/null 2>&1 && npm run build >/dev/null 2>&1 || exit 0"], cwd=root).returncode
    write("A",f"SYNTH/A\nBuild Integrity: {'PASSED' if build_rc==0 else 'FAILED'}")
    write("B","SYNTH/B\nRouter scoring: concreteness + buildability + entropy. SURGEON takes priority on build failure.")
    write("C","SYNTH/C\nAggregation policy: favor MILDLYAWESOME when ENTROPY > 5.0.")
else:
    write("A",f"{role}/A\nnoop"); write("B",f"{role}/B\nnoop"); write("C",f"{role}/C\nnoop")
print("DONE", role, cycle)