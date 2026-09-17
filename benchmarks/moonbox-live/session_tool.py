#!/usr/bin/env python3
"""session_tool.py - Working toolkit using GitHub API and local resources."""
import os, subprocess, json, time, pathlib, requests

TOKEN = os.environ["GITHUB_PAT"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_api(path):
    """GitHub API call with rate limit awareness."""
    try:
        r = requests.get(f"https://api.github.com{path}", headers=HEADERS, timeout=10)
        return r.status_code, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return -1, str(e)

def list_repos():
    """List all repos."""
    status, data = gh_api("/user/repos?per_page=100&affiliation=owner")
    if status == 200:
        return [r["name"] for r in data if r.get("owner",{}).get("login") == "toxicwind"]
    return []

def frun(cmd, t=8, cwd=None):
    """Fast subprocess run."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, cwd=cwd)
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except:
        return False, "", "TIMEOUT"

if __name__ == "__main__":
    print("§SESSION_TOOL_LOADED§")
    repos = list_repos()
    print(f"Repos: {len(repos)}")
