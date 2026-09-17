
import asyncio
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from selectolax.parser import HTMLParser

try:
    from playwright.async_api import async_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False

logger = logging.getLogger("popmart_scraper")

class PopmartScraper:
    """
    Popmart Scraper Service
    Discovers new drops, checks stock, and gathers intelligence.
    """
    
    BASE_URL = "https://www.popmart.com/us"
    MOBILE_URL = "https://m.popmart.com/us"
    
    def __init__(self):
        self.results = []
        
    async def discover_new_arrivals(self) -> List[Dict[str, Any]]:
        """Fetch new arrivals via HTTP/HTML parsing"""
        logger.info("Discovering new arrivals...")
        
        async with httpx.AsyncClient(http2=True) as client:
            try:
                resp = await client.get(f"{self.BASE_URL}/new-arrivals")
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch new arrivals: {resp.status_code}")
                    return []
                
                # Parse HTML for product IDs (simple regex fallback)
                # In a real scenario, we'd use Selectolax to parse the DOM
                html = resp.text
                product_ids = set(re.findall(r"/products/(\d+)", html))
                
                logger.info(f"Found {len(product_ids)} potential product IDs")
                
                products = []
                for pid in list(product_ids)[:10]: # Limit for demo
                     products.append({
                         "id": pid,
                         "source": "new-arrivals",
                         "timestamp": datetime.utcnow().isoformat()
                     })
                
                return products
                
            except Exception as e:
                logger.error(f"Error in discover_new_arrivals: {e}")
                return []

    async def check_stock_level(self, product_id: str) -> Dict[str, Any]:
        """Check stock using Playwright (if available) for dynamic content"""
        if not HAVE_PLAYWRIGHT:
            logger.warning("Playwright not installed, skipping dynamic stock check")
            return {"status": "unknown", "method": "http-fallback"}
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                url = f"{self.BASE_URL}/products/{product_id}"
                await page.goto(url, timeout=30000)
                
                # Check for "Add to Cart" or "Sold Out" buttons
                # Selectors would need to be actual site selectors
                # Using generic pseudo-selectors for this example
                
                content = await page.content()
                is_sold_out = "Sold Out" in content or "sold-out" in content
                
                title = await page.title()
                
                return {
                    "product_id": product_id,
                    "title": title,
                    "in_stock": not is_sold_out,
                    "status": "sold_out" if is_sold_out else "available",
                    "checked_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Playwright error: {e}")
                return {"error": str(e)}
            finally:
                await browser.close()
                
    async def run_recon_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for full recon task"""
        logger.info(f"Starting recon task with params: {params}")
        
        # 1. Discover
        new_items = await self.discover_new_arrivals()
        
        # 2. Detail Check (concurrent)
        tasks = []
        for item in new_items:
            tasks.append(self.check_stock_level(item['id']))
            
        details = await asyncio.gather(*tasks)
        
        return {
            "summary": {
                "discovered": len(new_items),
                "timestamp": datetime.utcnow().isoformat()
            },
            "items": details
        }
