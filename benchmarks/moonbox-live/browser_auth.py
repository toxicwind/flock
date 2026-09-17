import asyncio, json
from playwright.async_api import async_playwright

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell",
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        # Inject the HAR JWT as cookie BEFORE navigation
        await context.add_cookies([{
            "name": "kimi_token",
            "value": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhY2NvdW50IiwiYXVkIjpbImtpbWkuYWkiXSwiZXhwIjoxNzg3NDQzNDgxLCJpYXQiOjE3ODc0NDI1ODEsImp0aSI6ImRhNTNiNWM4azM2N3RwbnZoZGowIiwidHlwIjoiYWNjZXNzIiwiYXBwX2lkIjoia2ltaSIsInN1YiI6ImQ4N2JyMm9oOG5qa3I5MGpmNTIwIiwiYWJzdHJhY3RfdXNlcl9pZCI6ImQ4N2JyMmdoOG5qa3I5MGplOTcwIiwic3NpZCI6IjE3MzE3Mzc0MTA4NDI1NDcwMzMiLCJkZXZpY2VfaWQiOiI3Njc1MTkzNjgxMzYzNzM2ODMzIiwicmVnaW9uIjoib3ZlcnNlYXMiLCJtZW1iZXJzaGlwIjp7ImxldmVsIjoyNX0sImNvZGVfbWVtYmVyc2hpcCI6eyJsZXZlbCI6MjV9fQ.qPYa-ZCz5EiSXx-ldtMdw_9TawYf5bjzdkw-eqWTuUqBeagiYyVfBuM8yOW1_uW0EGTXmtfX0NQ29griMEtzpQ",
            "domain": ".kimi.ai",
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "None"
        }])
        
        page = await context.new_page()
        await page.goto("https://www.kimi.ai/", wait_until="networkidle", timeout=30000)
        print(f"TITLE: {await page.title()}")
        await asyncio.sleep(3)
        
        # Now check for auth state
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        cookies = await context.cookies()
        
        # Try to hit an auth endpoint from the browser
        resp = await page.evaluate("""async () => {
            try {
                const r = await fetch('/apiv2/user', {credentials: 'include'});
                return {status: r.status, text: await r.text()};
            } catch(e) {
                return {error: e.message};
            }
        }""")
        print(f"APIV2/USER: {json.dumps(resp, indent=2)[:500]}")
        
        with open("/mnt/agents/output/browser_auth.json", "w") as f:
            json.dump({
                "local_storage": json.loads(local_storage),
                "cookies": cookies,
                "apiv2_user": resp,
                "url": page.url
            }, f, indent=2, default=str)
        
        await page.screenshot(path="/mnt/agents/output/kimi_auth.png", full_page=True)
        print("SAVED: /mnt/agents/output/browser_auth.json")
        print("SAVED: /mnt/agents/output/kimi_auth.png")
        await browser.close()

asyncio.run(capture())
