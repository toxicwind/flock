#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pop Mart Recon v3 — preprod/alpha/preview discovery + Collections/Brand-IP/POP-NOW + CDN hints

What it does:
  1) Discovers product IDs from multi-region New Arrivals.
  2) Sweeps PDPs across many locales + verified dev/beta hosts.
  3) Generates additional env/feature hostnames (preprod/alpha/preview/qa/uat/staging/test/sandbox/canary/int/rc) and probes them.
  4) Enumerates /collection?id=, /brand-ip/{id}/..., and /pop-now/set/{id} for names, dates, and leaks.
  5) Probes cdn-global.popmart.com listing for filenames containing target keywords (English + Chinese).
  6) Emits verbose human-readable progress and JSON/CSV dossiers (UTF-8).

Verified exemplars / references:
  - Live dev/beta hosts (multiple): see inline CITEs in the companion write-up.
  - Collections & Brand-IP leak IDs/titles; POP-NOW exposes release dates; CDN lists keys.
"""

import argparse, asyncio, datetime as dt, json, re, sys
from typing import Dict, List, Optional, Tuple
import httpx
from selectolax.parser import HTMLParser

try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False

DEFAULT_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.7,zh;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
}
TIMEOUT = httpx.Timeout(12.0, connect=12.0)
CONCURRENCY = 28

RE_PRODUCT_ID = re.compile(r"/products/(\d+)")
RE_PRICE = re.compile(r"(?:US|HK|MOP|C)?\$?\s?\d[\d\.]*")
RE_LAUNCH = re.compile(r"(?:Launch\s*Time|Online\s*Release|上线时间)\s*[:：]?\s*([^\n<]+)", re.I)
RE_CH = re.compile(r"[\u4e00-\u9fff]")
RE_XML_KEY = re.compile(r"<Key>([^<]+)</Key>")

def zh(s): return bool(RE_CH.search(s or ""))

def parse_html(url: str, html: str) -> Dict[str, Optional[str]]:
    data = {"title":None,"og_title":None,"h1":None,"meta_description":None,"meta_keywords":None,
            "jsonld_names":[], "price":None, "launch":None, "has_zh":False, "dev_yace":False, "dev_dakey":False}
    try:
        tree = HTMLParser(html)
    except Exception:
        return data
    title = tree.css_first("title"); data["title"] = title.text(strip=True) if title else None
    og = tree.css_first("meta[property='og:title']"); data["og_title"] = og.attrs.get("content").strip() if og and og.attrs.get("content") else None
    h1 = tree.css_first("h1"); data["h1"] = h1.text(strip=True) if h1 else None
    md = tree.css_first("meta[name='description']"); data["meta_description"] = md.attrs.get("content").strip() if md and md.attrs.get("content") else None
    mk = tree.css_first("meta[name='keywords']"); data["meta_keywords"] = mk.attrs.get("content").strip() if mk and mk.attrs.get("content") else None

    # JSON-LD name extractor
    names = []
    for s in tree.css("script[type='application/ld+json']"):
        try:
            blob = json.loads(s.text())
            if isinstance(blob, dict) and isinstance(blob.get("name"), str):
                names.append(blob["name"].strip())
            elif isinstance(blob, list):
                for it in blob:
                    if isinstance(it, dict) and isinstance(it.get("name"), str):
                        names.append(it["name"].strip())
        except Exception:
            pass
    data["jsonld_names"] = sorted(set(names))

    txt = tree.body.text(separator=" ", strip=True) if tree.body else ""
    mp = RE_PRICE.search(txt); ml = RE_LAUNCH.search(txt)
    data["price"] = mp.group(0) if mp else None
    data["launch"] = ml.group(1).strip() if ml else None
    data["has_zh"] = zh(" ".join(filter(None,[data["title"],data["og_title"],data["h1"],data["meta_description"],data["meta_keywords"],txt])))
    data["dev_yace"] = ("压测" in txt)
    data["dev_dakey"] = ("大key压测" in txt)
    return data

async def fetch(client: httpx.AsyncClient, url: str):
    last = None
    for i in range(4):
        try:
            r = await client.get(url, headers=HEADERS, follow_redirects=True)
            return url, r.status_code, r.text or "", dict(r.headers)
        except Exception as e:
            last = e
            await asyncio.sleep(0.5*(i+1))
    return url, 0, f"ERROR: {last}", {}

async def gather(urls: List[str], concurrency: int = CONCURRENCY):
    sem = asyncio.Semaphore(concurrency)
    out = []
    async with httpx.AsyncClient(timeout=TIMEOUT, http2=True) as client:
        async def worker(u):
            async with sem:
                return await fetch(client,u)
        tasks = [asyncio.create_task(worker(u)) for u in urls]
        for t in asyncio.as_completed(tasks):
            try: out.append(await t)
            except Exception as e: out.append(("__ERR__",0,str(e),{}))
    return out

# ---------- Endpoint templates ----------
REGIONS = [
    "us","ca","hk","mo","tw","au","gb","jp","id","es","ms-MY","vi-VN","fi","pt","de"
]
PDP_TMPL = ["https://m.popmart.com/{r}/products/{id}",
            "https://www.popmart.com/{r}/products/{id}"]

# confirmed beta/dev plus generator seeds
VERIFIED_HOSTS = [
    "beta-global.popmart.com",
    "dev-aat-wap.popmart.com",
    "dev-mega-promote-pop.popmart.com",
    "dev-babymolly-pop.popmart.com",
    "dev-eo-code-wap.popmart.com",
    "dev-err-toast-pop.popmart.com",
    "dev-wallet-pop.popmart.com",
    "dev-naus-christmas-pop.popmart.com",
    "dev-naus-box-shake-pop.popmart.com",
    "dev-fixed-spu-api-pop.popmart.com",
    "dev-intl-app-pop.popmart.com",
    "dev-us-box-wap.popmart.com",
    "dev-th-app-wap.popmart.com",
    "dev-profile-picture-wap.popmart.com",
]
ENV_WORDS = ["dev","beta","preprod","staging","alpha","preview","qa","uat","sandbox","canary","int","rc","test"]
FEATURE_WORDS = [
    "wallet","err-toast","naus-box-shake","naus-christmas","profile-picture","intl-app",
    "us-box-wap","th-app","eo-code","mega-promote","aat","risk","replace-box","redeem",
    "recover","inventorylocalfix","lang-seven","my-local-wap","babymolly","fixed-spu-api",
    "naus-dooring-h5"
]
TIERS = ["pop","wap"]

def gen_candidate_hosts() -> List[str]:
    hosts = set(VERIFIED_HOSTS)
    for env in ENV_WORDS:
        for feat in FEATURE_WORDS:
            for tier in TIERS:
                hosts.add(f"{env}-{feat}-{tier}.popmart.com")
    # also add prod-ish special
    hosts.add("prod-naus-dooring-h5.popmart.com")
    return sorted(hosts)

NEW_ARRIVALS = [
    "https://m.popmart.com/us/new-arrivals",
    "https://www.popmart.com/hk/new-arrivals",
    "https://www.popmart.com/my/new-arrivals",
]

COLLECTION_TMPL = [
    "https://www.popmart.com/us/collection?id={cid}",
    "https://m.popmart.com/us/collection?id={cid}",
]
BRAND_IP_TMPL = [
    "https://www.popmart.com/us/brand-ip/{bid}/popIP",
    "https://www.popmart.com/us/brand-ip/{bid}/202401_IP_stresstest_{n}",
]
POPNOW_TMPL = [
    "https://www.popmart.com/us/pop-now/set/{sid}",
    "https://m.popmart.com/us/pop-now/set/{sid}",
]

CDN_ROOT = "https://cdn-global.popmart.com/"

# ---------- Discovery helpers ----------
async def discover_ids_from_new_arrivals():
    print("[*] Discovering IDs via New Arrivals…")
    results = await gather(NEW_ARRIVALS, concurrency=6)
    found = set()
    for url, code, html, _ in results:
        print(f"    [+] {url} → {code}")
        if 200 <= code < 400:
            for s in set(RE_PRODUCT_ID.findall(html)):
                found.add(int(s))
    uniq = sorted(found)
    print(f"[*] New Arrivals surfaced {len(uniq)} unique product IDs")
    return uniq

def build_pdp_urls(ids: List[int]) -> List[str]:
    urls = []
    for pid in ids:
        for r in REGIONS:
            for t in PDP_TMPL:
                urls.append(t.format(r=r,id=pid))
        for host in VERIFIED_HOSTS:
            urls.append(f"https://{host}/us/products/{pid}")
    return urls

def build_generated_host_urls(ids: List[int], sample_id: int) -> List[str]:
    urls = []
    for host in gen_candidate_hosts():
        # Touch a safe route + a PDP sample
        urls.append(f"https://{host}/us")
        urls.append(f"https://{host}/us/products/{sample_id}")
        urls.append(f"https://{host}/us/collection?id=115")
    return urls

def pad_neighbors(ids: List[int], radius=2) -> List[int]:
    s = set()
    for i in ids:
        for j in range(i-radius, i+radius+1):
            if j > 0: s.add(j)
    return sorted(s)

def interesting(rec):
    if rec["http_status"] != 200: return False
    t = " ".join(filter(None, [rec.get("title"),rec.get("og_title"),rec.get("h1")]))
    return bool(rec.get("price") or rec.get("launch") or rec.get("jsonld_names") or (t and "not available" not in t.lower()))

async def scan_urls(urls: List[str], context: str, attach: Dict) -> List[Dict]:
    out = []
    results = await gather(urls)
    for u, code, html, headers in results:
        if u == "__ERR__":
            print(f"[warn] {context} fetch error: {html[:120]}")
            continue
        if code == 200:
            print(f"[ok] {context} {code} {u}")
        elif code in (403,429):
            print(f"[rate] {context} {code} {u}")
        elif code >= 500:
            print(f"[serv] {context} {code} {u}")
        parsed = parse_html(u, html if code==200 else "")
        rec = {
            **attach, "url": u, "http_status": code,
            "title": parsed["title"], "og_title": parsed["og_title"], "h1": parsed["h1"],
            "meta_description": parsed["meta_description"], "meta_keywords": parsed["meta_keywords"],
            "jsonld_names": parsed["jsonld_names"], "found_price": parsed["price"], "launch_hint": parsed["launch"],
            "has_chinese": parsed["has_zh"], "dev_yace": parsed["dev_yace"], "dev_dakey": parsed["dev_dakey"],
            "server": headers.get("server") if headers else None,
            "ts": dt.datetime.now().isoformat(timespec="seconds")
        }
        out.append(rec)
    return out

async def enumerate_collections(c_min, c_max):
    urls = []
    for cid in range(c_min, c_max+1):
        for t in COLLECTION_TMPL: urls.append(t.format(cid=cid))
    return await scan_urls(urls, "collection", {"context":"collection"})

async def enumerate_brandip(b_min, b_max):
    urls = []
    for bid in range(b_min, b_max+1):
        urls.append(BRAND_IP_TMPL[0].format(bid=bid))
        for n in (31, 41, 51, 61, 71, 81, 91, 99, 121):  # common stress slugs seen live
            urls.append(BRAND_IP_TMPL[1].format(bid=bid, n=n))
    return await scan_urls(urls, "brand-ip", {"context":"brand-ip"})

async def enumerate_popnow(s_min, s_max):
    urls = []
    for sid in range(s_min, s_max+1):
        for t in POPNOW_TMPL: urls.append(t.format(sid=sid))
    return await scan_urls(urls, "popnow", {"context":"popnow"})

async def cdn_probe():
    print("[*] Probing CDN index for keyword hints …")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, http2=True) as client:
            r = await client.get(CDN_ROOT, headers={"User-Agent": DEFAULT_UA, "Accept": "application/xml"})
            keys = RE_XML_KEY.findall(r.text or "")
    except Exception as e:
        print(f"[warn] CDN probe failed: {e}")
        return []
    KW = ["pin","love","letter","labubu","lafufu","alphabet","series",
          "字母","别针","爱","拉布布","小拉布","挂件"]
    hits = [k for k in keys if any(w.lower() in k.lower() for w in KW)]
    print(f"    [+] CDN listed {len(keys)} objects; keyword hits: {len(hits)}")
    return [{"context":"cdn","url":CDN_ROOT+k, "http_status":200, "title":k.split('/')[-1],
             "og_title":None,"h1":None,"meta_description":None,"meta_keywords":None,
             "jsonld_names":[], "found_price":None,"launch_hint":None,
             "has_chinese": zh(k),"dev_yace":False,"dev_dakey":False,"server":None,
             "ts": dt.datetime.now().isoformat(timespec='seconds')} for k in hits[:200]]

async def main_async(args):
    print(f"[•] Recon start @ {dt.datetime.now().isoformat(timespec='seconds')}")
    # Phase A: discover via New Arrivals
    discovered = await discover_ids_from_new_arrivals()
    sweep_ids = set(discovered)
    if not args.only_new_arrivals:
        sweep_ids.update(range(args.id_start, args.id_end+1))
    if args.neighbor_pad:
        sweep_ids = set(pad_neighbors(sorted(sweep_ids), radius=2))
    sweep_ids = sorted(sweep_ids)
    print(f"[*] Target PDP ID count: {len(sweep_ids)}")

    # Phase B: PDP sweep (regions + verified dev/beta)
    pdp_urls = build_pdp_urls(sweep_ids)
    pdp_recs = await scan_urls(pdp_urls, "pdp", {"context":"pdp"})
    # Phase C: Generated hostnames (env/feature/tier)
    gen_urls = build_generated_host_urls(sweep_ids[min(len(sweep_ids)//2, len(sweep_ids)-1)] if sweep_ids else 3000,
                                         sample_id=(sweep_ids[0] if sweep_ids else 3000))
    gen_recs = await scan_urls(gen_urls, "hostgen", {"context":"hostgen"})
    # Phase D: Collections / Brand-IP / POP-NOW
    col_recs = await enumerate_collections(args.collection_min, args.collection_max) if args.scan_collections else []
    bip_recs = await enumerate_brandip(args.brandip_min, args.brandip_max) if args.scan_brandip else []
    pop_recs = await enumerate_popnow(args.popnow_min, args.popnow_max) if args.scan_popnow else []
    # Phase E: CDN keyword probe
    cdn_recs = await cdn_probe() if args.probe_cdn else []

    # Combine
    records = []
    records.extend(pdp_recs)
    records.extend(gen_recs)
    records.extend(col_recs)
    records.extend(bip_recs)
    records.extend(pop_recs)
    records.extend(cdn_recs)

    # Output
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f"popmart_recon_v3_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[✓] JSON written → {json_path}")

    if HAVE_PANDAS:
        import pandas as pd
        cols = ["context","http_status","url","title","og_title","h1","jsonld_names",
                "found_price","launch_hint","has_chinese","dev_yace","dev_dakey","server","ts"]
        df = pd.DataFrame.from_records(records)
        for c in cols:
            if c not in df.columns: df[c] = None
        df = df[cols]
        csv_path = f"popmart_recon_v3_{ts}.csv"
        df.to_csv(csv_path, index=False)
        print(f"[✓] CSV written  → {csv_path}")
    else:
        print("[i] pandas not installed → CSV skipped (JSON available).")

    # Human-friendly wrap-up
    live = [r for r in records if r["http_status"]==200]
    zh_live = [r for r in live if r.get("has_chinese")]
    juicy = [r for r in live if interesting(r)]
    print("\n====== SUMMARY ======")
    print(f"Live pages: {len(live)} | CN-signal: {len(zh_live)} | Interesting: {len(juicy)}")
    for r in juicy[:18]:
        bits = " / ".join([b for b in [r.get("title"), r.get("og_title")] if b])[:140] or "(no title)"
        print(f" - {r['context']:>7} | {r['http_status']} | {bits}")
        if r.get("launch_hint"): print(f"     · Launch: {r['launch_hint']}")
        if r.get("found_price"): print(f"     · Price : {r['found_price']}")
        if r.get("jsonld_names"): print(f"     · JSON-LD: {', '.join(r['jsonld_names'][:3])}")
        print(f"     · URL: {r['url']}")
    print("====== DONE ======")

def cli():
    ap = argparse.ArgumentParser(description="Pop Mart Recon v3")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--only-new-arrivals", action="store_true", help="Use only IDs discovered from New Arrivals")
    ap.add_argument("--id-start", type=int, default=3450)
    ap.add_argument("--id-end", type=int, default=3650)
    ap.add_argument("--neighbor-pad", action="store_true", help="Pad PDP IDs ±2 to catch neighbors")
    # Collections/Brand-IP/POP-NOW ranges (tune as needed)
    ap.add_argument("--scan-collections", action="store_true")
    ap.add_argument("--collection-min", type=int, default=1)
    ap.add_argument("--collection-max", type=int, default=260)
    ap.add_argument("--scan-brandip", action="store_true")
    ap.add_argument("--brandip-min", type=int, default=1)
    ap.add_argument("--brandip-max", type=int, default=200)
    ap.add_argument("--scan-popnow", action="store_true")
    ap.add_argument("--popnow-min", type=int, default=1)
    ap.add_argument("--popnow-max", type=int, default=360)
    ap.add_argument("--probe-cdn", action="store_true", help="Probe cdn-global.popmart.com for keyword hits")
    args = ap.parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        sys.exit(130)

if __name__ == "__main__":
    cli()
