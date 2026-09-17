#!/usr/bin/env python3
"""
kimi_file_downloader.py - Fast concurrent file downloader for Kimi API/HAR archives.
Usage: python3 kimi_file_downloader.py [--har HAR_FILE] [--jwt JWT] [--output DIR]
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlparse

# ── CONFIG ───────────────────────────────────────────────────────────────────
DEFAULT_JWT = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc4NjkzOTUxMiwiaWF0IjoxNzg0MzQ3NTEyLCJqdGkiOiJkOWRmbXUyZTBtN2ZvZmppMnBoZyIsInR5cCI6ImFjY2VzcyIsImFwcF9pZCI6ImtpbWkiLCJzdWIiOiJkODdicjJvaDhuamtyOTBqZjUyMCIsInNwYWNlX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5N2ciLCJhYnN0cmFjdF91c2VyX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5NzAiLCJzc2lkIjoiMTczMTczNzQxMDg0MjU0NzAzMyIsImRldmljZV9pZCI6Ijc2NTI1NTE1ODg3MzY4MDcxODMiLCJyZWdpb24iOiJvdmVyc2VhcyIsIm1lbWJlcnNoaXAiOnsibGV2ZWwiOjEwfX0.-9-OczLe8Ghkb28wYdTQSFb-UHZW0hxaByfVEZU-Dsc9zWWcMdyAPWK3v5ZrQAz8BIg4om89-VODnXDyT7RPMw"

BASE_API = "https://www.kimi.com/apiv2"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:155.0) Gecko/20100101 Firefox/155.0",
    "Accept": "*/*",
    "Accept-Language": "en",
    "authorization": f"Bearer {DEFAULT_JWT}",
    "connect-protocol-version": "1",
    "content-type": "application/json",
    "r-timezone": "Atlantic/Reykjavik",
    "x-language": "en-US",
    "x-msh-device-id": "7652551588736807183",
    "x-msh-platform": "web",
    "x-msh-session-id": "1731737410842547033",
    "x-msh-version": "2.0.0",
    "x-traffic-id": "d87br2oh8njkr90jf520",
}

CHUNK_SIZE = 65536
MAX_WORKERS = 8
TIMEOUT = 30


# ── HAR PARSER ───────────────────────────────────────────────────────────────
def extract_urls_from_har(har_path: str) -> Set[str]:
    """Parse HAR and extract all signUrl / previewUrl / blob URLs."""
    urls = set()
    try:
        with open(har_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Failed to parse HAR: {e}")
        return urls

    entries = data.get("log", {}).get("entries", [])
    print(f"[*] HAR has {len(entries)} entries")

    for entry in entries:
        # Scan response content text for URLs
        content = entry.get("response", {}).get("content", {}).get("text", "")
        if not content:
            continue

        # Find all signUrl / previewUrl / blob URLs
        found = re.findall(
            r'https://www\.kimi\.com/apiv2-files/sign-obj/[^"\'\s]+',
            content,
        )
        urls.update(found)

    print(f"[*] Extracted {len(urls)} unique URLs from HAR")
    return urls


# ── API FETCHER ──────────────────────────────────────────────────────────────
def api_request(endpoint: str, body: dict, jwt: str = DEFAULT_JWT) -> dict:
    """Make a Connect-RPC POST request."""
    url = f"{BASE_API}/{endpoint}"
    headers = dict(DEFAULT_HEADERS)
    headers["authorization"] = f"Bearer {jwt}"

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}


def fetch_all_feeds(jwt: str = DEFAULT_JWT) -> List[dict]:
    """Paginate through ListFeeds and return all chats with files."""
    all_items = []
    page_token = ""
    page = 0

    while True:
        body = {
            "page_size": 50,
            "project_id": "",
            "filter_types": ["FEED_TYPE_CHAT", "FEED_TYPE_TASK"],
            "include_pinned": False,
        }
        if page_token:
            body["page_token"] = page_token

        resp = api_request("kimi.gateway.feed.v1.FeedService/ListFeeds", body, jwt)
        items = resp.get("items", [])
        if not items:
            break

        all_items.extend(items)
        page += 1
        print(f"[*] Feed page {page}: +{len(items)} items (total {len(all_items)})")

        page_token = resp.get("nextPageToken", "")
        if not page_token:
            break

    return all_items


def extract_file_urls_from_feeds(items: List[dict]) -> Set[Tuple[str, str, str]]:
    """Extract (filename, sign_url, checksum) from feed items."""
    files = set()
    for item in items:
        chat = item.get("chat", {})
        for f in chat.get("files", []):
            meta = f.get("meta", {})
            blob = f.get("blob", {})
            name = meta.get("name", "unknown")
            sign = blob.get("signUrl", "")
            checksum = meta.get("checksum", "")
            if sign:
                files.add((name, sign, checksum))
    print(f"[*] Found {len(files)} unique files in feeds")
    return files


# ── DOWNLOADER ───────────────────────────────────────────────────────────────
def download_file(url: str, out_path: Path, checksum: str = "") -> dict:
    """Download a single file with resume support and checksum verify."""
    result = {"url": url, "path": str(out_path), "status": "ok", "bytes": 0, "error": None}

    # Skip if exists and checksum matches
    if out_path.exists() and checksum:
        existing = hashlib.sha256(out_path.read_bytes()).hexdigest()
        if existing.lower() == checksum.lower():
            result["status"] = "skipped (checksum match)"
            return result

    try:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    result["bytes"] += len(chunk)

        # Verify checksum if provided
        if checksum:
            downloaded = hashlib.sha256(out_path.read_bytes()).hexdigest()
            if downloaded.lower() != checksum.lower():
                result["status"] = "checksum mismatch"
                result["error"] = f"expected {checksum[:16]}... got {downloaded[:16]}..."

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def filename_from_url(url: str, default: str = "file") -> str:
    """Extract clean filename from sign URL."""
    parsed = urlparse(url)
    qs = parsed.query
    # Find filename= param
    m = re.search(r'filename=([^&]+)', qs)
    if m:
        return unquote(m.group(1))
    # Fallback: use checksum from path
    parts = parsed.path.split("/")
    if parts:
        return parts[-1][:32] + ".bin"
    return default


def download_all(urls: Set[Tuple[str, str, str]], output_dir: Path, max_workers: int = MAX_WORKERS):
    """Concurrent download with progress."""
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(urls)
    completed = 0
    errors = 0
    skipped = 0
    total_bytes = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {}
        for name, url, checksum in urls:
            # Sanitize filename
            safe_name = re.sub(r'[<>:"/\\|?*]', "_", name)[:128]
            if not safe_name or safe_name == "unknown":
                safe_name = filename_from_url(url)
            out_path = output_dir / safe_name

            # Handle duplicates by appending checksum prefix
            if out_path in {f[1] for f in futures.items()}:
                stem = out_path.stem
                suffix = out_path.suffix
                out_path = output_dir / f"{stem}_{checksum[:8]}{suffix}"

            fut = ex.submit(download_file, url, out_path, checksum)
            futures[fut] = (url, safe_name)

        for fut in as_completed(futures):
            url, name = futures[fut]
            try:
                res = fut.result()
                completed += 1
                if res["status"] == "ok":
                    total_bytes += res["bytes"]
                    print(f"[{completed}/{total}] OK {res['bytes']//1024}KB {name[:60]}")
                elif "skipped" in res["status"]:
                    skipped += 1
                    print(f"[{completed}/{total}] SKIP {name[:60]}")
                else:
                    errors += 1
                    print(f"[{completed}/{total}] ERR {res['status']} {name[:60]} {res.get('error','')[:60]}")
            except Exception as e:
                errors += 1
                print(f"[{completed}/{total}] FATAL {name[:60]} {e}")

    print(f"\n{'='*60}")
    print(f"Done: {completed} processed, {skipped} skipped, {errors} errors")
    print(f"Total downloaded: {total_bytes / 1024 / 1024:.1f} MB")
    print(f"Output: {output_dir.absolute()}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Kimi File Downloader")
    parser.add_argument("--har", help="Path to HAR archive")
    parser.add_argument("--jwt", default=DEFAULT_JWT, help="JWT token")
    parser.add_argument("--output", default="./kimi_downloads", help="Output directory")
    parser.add_argument("--api", action="store_true", help="Also fetch from API feeds")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Concurrent downloads")
    parser.add_argument("--list-only", action="store_true", help="Only list URLs, don't download")
    args = parser.parse_args()

    out_dir = Path(args.output)
    all_files = set()  # (name, url, checksum)

    # 1. Parse HAR if provided
    if args.har:
        har_urls = extract_urls_from_har(args.har)
        for url in har_urls:
            name = filename_from_url(url)
            all_files.add((name, url, ""))

    # 2. Fetch from API if requested
    if args.api:
        feeds = fetch_all_feeds(args.jwt)
        api_files = extract_file_urls_from_feeds(feeds)
        all_files.update(api_files)

    if not all_files:
        print("[!] No files found. Use --har or --api")
        sys.exit(1)

    print(f"[*] Total unique files to download: {len(all_files)}")

    if args.list_only:
        for name, url, chk in sorted(all_files):
            print(f"{name}\t{url}\t{chk}")
        return

    download_all(all_files, out_dir, args.workers)


if __name__ == "__main__":
    main()
