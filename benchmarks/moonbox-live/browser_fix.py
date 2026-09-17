import asyncio, json, sys
from playwright.async_api import async_playwright

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell",
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        await page.goto("https://www.kimi.ai/", wait_until="networkidle", timeout=30000)
        print(f"TITLE: {await page.title()}")
        await asyncio.sleep(3)
        
        # Extract tokens from all storage
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        session_storage = await page.evaluate("() => JSON.stringify(sessionStorage)")
        cookies = await context.cookies()
        
        # Save everything
        with open("/mnt/agents/output/browser_tokens.json", "w") as f:
            json.dump({
                "local_storage": json.loads(local_storage),
                "session_storage": json.loads(session_storage),
                "cookies": cookies,
                "url": page.url,
                "title": await page.title()
            }, f, indent=2, default=str)
        
        # Screenshot
        await page.screenshot(path="/mnt/agents/output/kimi_homepage.png", full_page=True)
        print("SAVED: /mnt/agents/output/browser_tokens.json")
        print("SAVED: /mnt/agents/output/kimi_homepage.png")
        await browser.close()

asyncio.run(capture())
