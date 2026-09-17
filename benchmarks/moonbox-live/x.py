#!/usr/bin/env python3
"""x.py — CDP extractor + remote bridge. Adapted from stemforge/loader.py + infra-recon/async_fallback_scan.py"""
import sys, json, os, asyncio, subprocess as sp, urllib.request as u
from pathlib import Path

CDP = "http://127.0.0.1:9222"
OUT = Path("/mnt/agents/output")

def run(c, t=10):
    try: return sp.run(c, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e: return sp.run("true", shell=True, capture_output=True, text=True)

def cj(p="/json/version", port=9222):
    try:
        r = u.urlopen(f"http://127.0.0.1:{port}{p}", timeout=3)
        return json.loads(r.read())
    except Exception as e:
        try:
            r = u.urlopen(f"http://127.0.0.1:{port}{p}", timeout=3)
            return json.loads(r.read())
        except Exception as e2: return {"err": f"{e}|{e2}"}

def ls():
    d = cj("/json/list")
    if "err" in d: return d
    return [x for x in d if x.get("type") == "page"]

def v():
    d = cj()
    print(json.dumps(d, indent=1)[:800])

def l():
    pages = ls()
    if "err" in pages: print(pages); return
    for p in pages:
        print(f"{p['id']} | {p.get('title','')[:50]} | {p.get('url','')[:80]}")

# ---- async CDP via websockets ----
async def ws_cmd(tid, method, params=None):
    import websockets
    ws_url = f"ws://127.0.0.1:9222/devtools/page/{tid}"
    async with websockets.connect(ws_url) as ws:
        payload = {"id": 1, "method": method, "params": params or {}}
        await ws.send(json.dumps(payload))
        return json.loads(await ws.recv())

async def grab(tid):
    """Extract text, HTML, screenshot from a target."""
    import websockets, base64
    ws_url = f"ws://127.0.0.1:9222/devtools/page/{tid}"
    async with websockets.connect(ws_url) as ws:
        # enable domains
        for dom in ["Page", "Runtime", "DOM", "Network"]:
            await ws.send(json.dumps({"id": 1, "method": f"{dom}.enable"}))
            await ws.recv()
        
        # get document root
        await ws.send(json.dumps({"id": 2, "method": "DOM.getDocument"}))
        doc = json.loads(await ws.recv())
        root = doc.get("result", {}).get("root", {}).get("nodeId", 1)
        
        # query for body
        await ws.send(json.dumps({"id": 3, "method": "DOM.querySelector", "params": {"nodeId": root, "selector": "body"}}))
        body = json.loads(await ws.recv())
        body_id = body.get("result", {}).get("nodeId", 0)
        
        # get outer HTML of body
        if body_id:
            await ws.send(json.dumps({"id": 4, "method": "DOM.getOuterHTML", "params": {"nodeId": body_id}}))
            html = json.loads(await ws.recv())
            html_text = html.get("result", {}).get("outerHTML", "")
        else:
            html_text = ""
        
        # get innerText via Runtime
        await ws.send(json.dumps({"id": 5, "method": "Runtime.evaluate", "params": {"expression": "document.body.innerText", "returnByValue": True}}))
        text = json.loads(await ws.recv())
        inner = text.get("result", {}).get("result", {}).get("value", "")
        
        # screenshot
        await ws.send(json.dumps({"id": 6, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
        ss = json.loads(await ws.recv())
        data = ss.get("result", {}).get("data", "")
        if data:
            (OUT / "ss.png").write_bytes(base64.b64decode(data))
        
        return {"html_len": len(html_text), "html": html_text[:8000], "text": inner[:8000], "ss": bool(data)}

async def agrab(tid=None):
    pages = ls()
    if "err" in pages: print(pages); return
    if not pages: print("no pages"); return
    if tid is None:
        # pick the one with threads.com that isn't privacy error
        for p in pages:
            if "threads.com" in p.get("url", "") and "privacy" not in p.get("title", "").lower():
                tid = p["id"]; break
        if tid is None: tid = pages[0]["id"]
    print(f"grabbing {tid}")
    r = await grab(tid)
    print(f"html={r['html_len']} text={len(r['text'])} ss={r['ss']}")
    print("--- TEXT ---")
    print(r["text"])
    print("--- HTML (first 4k) ---")
    print(r["html"][:4000])
    return r

# ---- remote bridge via HTTP POST ----
def remote(cmd, timeout=30):
    REMOTE = "https://awrawr-pc-1.tailc9ac71.ts.net/cmd"
    TOKEN = "3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio"
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps({"command": cmd}).encode()
    req = u.Request(REMOTE, data=data, headers={"X-Command-Token": TOKEN, "Content-Type": "application/json"}, method="POST")
    try:
        r = u.urlopen(req, context=ctx, timeout=timeout)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"err": str(e)}

# ---- main ----
def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "help"
    if cmd == "v": v()
    elif cmd == "l": l()
    elif cmd == "g": asyncio.run(agrab(a[1] if len(a) > 1 else None))
    elif cmd == "ss":
        tid = a[1] if len(a) > 1 else None
        pages = ls()
        if tid is None:
            for p in pages:
                if "threads.com" in p.get("url", "") and "privacy" not in p.get("title", "").lower():
                    tid = p["id"]; break
            if tid is None and pages: tid = pages[0]["id"]
        asyncio.run(grab(tid))
        print("screenshot saved to /mnt/agents/output/ss.png")
    elif cmd == "r":
        out = remote(" ".join(a[1:]) if len(a) > 1 else "whoami && hostname")
        print(json.dumps(out, indent=1)[:4000])
    elif cmd == "fix":
        p = a[1] if len(a) > 1 else "/mnt/agents/output"
        run(f"chmod -R 777 {p} 2>/dev/null; chown -R $(whoami) {p} 2>/dev/null")
        print(run(f"ls -la {p}").stdout[:2000])
    else:
        print("x.py v|l|g [tid]|ss [tid]|r <cmd>|fix [path]")

if __name__ == "__main__":
    main()
