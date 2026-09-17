#!/usr/bin/env python3
"""
Save all history.db from /tmp/nim-bench-* into project data folder
Converts to consolidated.json for pretty HTML
"""
import pathlib, glob, sqlite3, gzip, json, csv, shutil
from collections import defaultdict

base_dirs = glob.glob("/tmp/nim-bench-*")
if not base_dirs:
    print("No /tmp/nim-bench-* found, using /mnt/data/nim-bench-dashboard as demo")
    base_dirs = ["/tmp"]

out_data = pathlib.Path(__file__).parent.parent / "data"
out_data.mkdir(parents=True, exist_ok=True)

# Copy all dbs
all_dbs = []
for bd in base_dirs:
    bd = pathlib.Path(bd)
    for f in bd.rglob("*__history.db*"):
        if f.suffix == ".py":
            continue
        dest = out_data / f.name
        if not dest.exists():
            try:
                shutil.copy2(f, dest)
                print(f"Saved {f} -> {dest}")
            except Exception as e:
                print(f"skip {f}: {e}")
        all_dbs.append(dest)
    # also check dbs folder
    for f in (bd / "dbs").glob("*") if (bd / "dbs").exists() else []:
        dest = out_data / f.name
        if not dest.exists():
            shutil.copy2(f, dest)
        all_dbs.append(dest)

# Also check /mnt/data/nim-bench-dashboard/data
for f in pathlib.Path("/mnt/data/nim-bench-dashboard/data").glob("*"):
    all_dbs.append(f)

# Deduplicate
all_dbs = list(set(all_dbs))
print(f"Total DBs collected: {len(all_dbs)}")

# Parse manifest.csv if exists
manifest = []
for bd in base_dirs:
    mc = pathlib.Path(bd) / "manifest.csv"
    if mc.exists():
        with open(mc) as csvf:
            reader = csv.DictReader(csvf)
            for r in reader:
                manifest.append(r)

# Consolidated JSON
consolidated = {
    "repos": [],
    "models": [],
    "summary": {}
}

for db_file in all_dbs:
    if db_file.suffix == ".py":
        continue
    repo = db_file.name.split("__")[0] if "__" in db_file.name else db_file.stem
    tmp = None
    try:
        path = db_file
        if str(db_file).endswith(".gz"):
            tmp = pathlib.Path(str(db_file)+".tmp")
            with gzip.open(db_file, 'rb') as gz:
                tmp.write_bytes(gz.read())
            path = tmp
        con = sqlite3.connect(str(path))
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        
        runs = 0
        results = 0
        if "runs" in tables:
            cur.execute("SELECT COUNT(*) FROM runs")
            runs = cur.fetchone()[0]
        if "model_results" in tables:
            cur.execute("SELECT COUNT(*) FROM model_results")
            results = cur.fetchone()[0]
        
        # models
        avgs = []
        if "models" in tables:
            try:
                cur.execute("""
                    SELECT m.name, AVG(mr.response_time) as avg_rt, COUNT(*) as n,
                           AVG(mr.tokens_generated) as avg_tok, AVG(mr.total_tokens) as avg_total
                    FROM model_results mr
                    JOIN models m ON mr.model_id = m.id
                    WHERE mr.response_time IS NOT NULL
                    GROUP BY m.name
                    ORDER BY avg_rt ASC
                    LIMIT 50
                """)
                for name, rt, n, tok, total in cur.fetchall():
                    avgs.append({"model": name, "avg_rt": rt, "count": n, "avg_tok": tok, "repo": repo})
            except Exception as e:
                print(f"join fail {db_file}: {e}")
        else:
            try:
                cur.execute("SELECT model, AVG(response_time) as avg_rt, COUNT(*) as n FROM model_results WHERE response_time IS NOT NULL GROUP BY model ORDER BY avg_rt ASC LIMIT 50")
                for name, rt, n in cur.fetchall():
                    avgs.append({"model": name, "avg_rt": rt, "count": n, "repo": repo})
            except:
                pass
        
        consolidated["repos"].append({
            "repo": repo,
            "file": db_file.name,
            "runs": runs,
            "results": results,
            "tables": tables,
            "top_models": avgs[:10]
        })
        consolidated["models"].extend(avgs)
        con.close()
        if tmp and tmp.exists():
            tmp.unlink()
    except Exception as e:
        print(f"ERR {db_file}: {e}")

# Write JSON
(out_data / "consolidated.json").write_text(json.dumps(consolidated, indent=2))
(out_data / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"Wrote {out_data / 'consolidated.json'} with {len(consolidated['repos'])} repos")

# Also copy original markdown
src_md = pathlib.Path("/mnt/data/nim-bench-consolidated.md")
if src_md.exists():
    (out_data / "original_consolidated.md").write_bytes(src_md.read_bytes())

print("Done - run bun dev to launch")
