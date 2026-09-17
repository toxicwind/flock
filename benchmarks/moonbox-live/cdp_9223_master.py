#!/usr/bin/env python3
"""
CDP 9223 MASTER SCRIPT
Connects to Chrome DevTools Protocol on port 9223
Uses playwright for CDP automation (no websocket dependency)
"""
import sys, json, time, os, subprocess

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed")
    print("Install: pip install playwright && playwright install chromium")
    sys.exit(1)

CDP_PORT = 9223
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

def check_cdp_running():
    """Check if CDP endpoint is responding."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=5) as r:
            data = json.loads(r.read().decode())
            return True, data
    except Exception as e:
        return False, str(e)

def list_pages():
    """List all open pages/tabs via CDP."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/list", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"ERROR listing pages: {e}")
        return []

def navigate_to_url(page_url, target_url):
    """Navigate a page to a URL via CDP."""
    import urllib.request
    try:
        req = urllib.request.Request(
            page_url,
            data=json.dumps({"url": target_url}).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"ERROR navigating: {e}")
        return None

def main():
    print("=== CDP 9223 MASTER ===")

    # Check if CDP is running
    ok, info = check_cdp_running()
    if not ok:
        print(f"CDP not running on port {CDP_PORT}: {info}")
        print("Start Chrome with: google-chrome --remote-debugging-port=9223")
        sys.exit(1)

    print(f"CDP ready: {info.get('Browser', 'unknown')}")
    print(f"Version: {info.get('Protocol-Version', 'unknown')}")

    # List pages
    pages = list_pages()
    print(f"
Open pages: {len(pages)}")
    for p in pages:
        print(f"  [{p.get('type', '?')}] {p.get('url', '?')[:60]}")

    # Example: navigate first page to a URL
    if pages:
        target = input("
Enter URL to navigate to (or 'quit'): ").strip()
        if target and target.lower() != "quit":
            result = navigate_to_url(pages[0]["webSocketDebuggerUrl"].replace("ws://", "http://"), target)
            print(f"Navigation result: {result}")

if __name__ == "__main__":
    main()
