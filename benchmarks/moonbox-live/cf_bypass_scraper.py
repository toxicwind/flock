#!/usr/bin/env python3
"""
CLOUDFLARE BYPASS SCRAPER
Uses curl_cffi to impersonate real browsers and bypass BotGuard
"""
import sys, json, time, os

try:
    from curl_cffi import requests as cf_requests
except ImportError:
    print("ERROR: curl_cffi not installed")
    print("Install: pip install curl_cffi")
    sys.exit(1)

def fetch_url(url, impersonate="chrome126"):
    """Fetch URL with Cloudflare bypass."""
    try:
        r = cf_requests.get(url, impersonate=impersonate, timeout=30)
        return {
            "status": r.status_code,
            "headers": dict(r.headers),
            "content_length": len(r.content),
            "text_preview": r.text[:500],
            "cookies": dict(r.cookies)
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== CLOUDFLARE BYPASS SCRAPER ===")

    # Test with known Cloudflare-protected sites
    test_urls = [
        "https://annas-archive.org",
        "https://www.researchgate.net",
        "https://github.com",
    ]

    for url in test_urls:
        print(f"
Fetching: {url}")
        result = fetch_url(url)
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Status: {result['status']}")
            print(f"  Content: {result['content_length']} bytes")
            print(f"  Preview: {result['text_preview'][:100]}...")

if __name__ == "__main__":
    main()
