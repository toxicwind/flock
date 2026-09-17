#!/usr/bin/env python3
"""gh_async_client.py - Parallel async GitHub API with streaming & dynamic resources."""
import asyncio, aiohttp, psutil, os, json, time
from typing import List, Dict, Any, Optional

TOKEN = os.environ["GITHUB_PAT"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def get_resources():
    mem = psutil.virtual_memory()
    cpu = os.cpu_count() or 4
    concurrency = min(cpu * 3, 32)
    return {"cpu": cpu, "ram_mb": mem.available // 1024 // 1024, "concurrency": concurrency}

class GHAsyncClient:
    def __init__(self):
        self.resources = get_resources()
        self.semaphore = asyncio.Semaphore(self.resources["concurrency"])
        self.session = None

    async def __aenter__(self):
        conn = aiohttp.TCPConnector(limit=self.resources["concurrency"], limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=8, connect=3)
        self.session = aiohttp.ClientSession(headers=HEADERS, connector=conn, timeout=timeout)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get(self, url: str) -> Dict[str, Any]:
        async with self.semaphore:
            t0 = time.time()
            try:
                async with self.session.get(url) as resp:
                    body = await resp.json() if resp.content_type == "application/json" else await resp.text()
                    dt = (time.time() - t0) * 1000
                    return {"url": url, "status": resp.status, "ms": round(dt, 2), "body": body}
            except Exception as e:
                dt = (time.time() - t0) * 1000
                return {"url": url, "status": -1, "ms": round(dt, 2), "body": str(e)}

    async def stream_tree(self, repo: str, branch: str = "main") -> List[Dict]:
        """Stream file tree with pagination."""
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        r = await self.get(url)
        if r["status"] == 200:
            return r["body"].get("tree", [])
        return []

    async def batch_repos(self, repos: List[str]) -> List[Dict]:
        """Parallel fetch multiple repos."""
        tasks = []
        for repo in repos:
            tasks.append(self.get(f"https://api.github.com/repos/{repo}"))
            tasks.append(self.get(f"https://api.github.com/repos/{repo}/branches"))
        return await asyncio.gather(*tasks)

async def main():
    resources = get_resources()
    print(f"§RES§ CPU:{resources['cpu']} RAM:{resources['ram_mb']}MB CONCURRENCY:{resources['concurrency']}")

    repos = [
        "toxicwind/sovereign-rebrand",
        "toxicwind/kimi-multi-kernel",
        "toxicwind/effusion-labs",
    ]

    t0 = time.time()
    async with GHAsyncClient() as client:
        results = await client.batch_repos(repos)
    dt = (time.time() - t0) * 1000

    print(f"§BATCH§ {len(results)} requests in {dt:.1f}ms ({dt/len(results):.1f}ms avg)")
    for r in results:
        status = "OK" if r["status"] == 200 else f"ERR:{r['status']}"
        print(f"  [{status}] {r['ms']}ms {r['url'].split('/')[-1]}")

if __name__ == "__main__":
    asyncio.run(main())
