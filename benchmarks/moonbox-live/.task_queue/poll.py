import urllib.request, json, time
PAT = "${GITHUB_PAT}"
while True:
    try:
        req = urllib.request.Request("https://api.github.com/repos/toxicwind/effusion-labs/actions/runs?per_page=1", headers={"Authorization": f"token {PAT}"})
        resp = urllib.request.urlopen(req, timeout=10).read().decode()
        d = json.loads(resp)
        r = d.get("workflow_runs", [{}])[0]
        line = f"[{time.time()}] {r.get('status','?')} | {r.get('conclusion','?')} | {r.get('head_sha','?')[:8]}\n"
        with open("/mnt/agents/output/.bg_logs/actions-poll.log", "a") as f: f.write(line)
    except Exception as e:
        with open("/mnt/agents/output/.bg_logs/actions-poll.log", "a") as f: f.write(f"[{time.time()}] ERR {e}\n")
    time.sleep(15)
