#!/usr/bin/env python3
"""
GITHUB REPO FINDER
Finds scraper repos using GitHub API via curl_cffi (bypasses rate limits)
"""
import sys, json, time

try:
    from curl_cffi import requests as cf_requests
except ImportError:
    print("ERROR: curl_cffi not installed")
    sys.exit(1)

GITHUB_API = "https://api.github.com"

def search_repos(query, per_page=10):
    """Search GitHub repos with Cloudflare bypass."""
    url = f"{GITHUB_API}/search/repositories"
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": per_page}

    try:
        r = cf_requests.get(url, params=params, impersonate="chrome126", timeout=15)
        if r.status_code == 200:
            return r.json().get("items", [])
        else:
            print(f"API error: {r.status_code} {r.text[:200]}")
            return []
    except Exception as e:
        print(f"Request error: {e}")
        return []

def main():
    print("=== GITHUB REPO FINDER ===")

    queries = [
        "uber scraper",
        "annas archive scraper",
        "researchgate scraper",
        "cloudflare bypass scraper",
        "cdp automation 9223",
    ]

    for q in queries:
        print(f"
Searching: {q}")
        repos = search_repos(q, per_page=5)
        for repo in repos:
            print(f"  {repo['full_name']}")
            print(f"    {repo.get('description', 'No description')[:80]}")
            print(f"    Updated: {repo['updated_at'][:10]} | Stars: {repo['stargazers_count']}")
            print(f"    URL: {repo['html_url']}")

if __name__ == "__main__":
    main()
