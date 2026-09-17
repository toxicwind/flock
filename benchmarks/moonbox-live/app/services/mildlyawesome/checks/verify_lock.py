
import asyncio
import logging
from redis.asyncio import Redis
from services.mildlyawesome.lock import distributed_lock
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_lock")

# Use same REDIS_URL logic as events.py or default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def verify():
    logger.info("--- Testing Distributed Lock ---")
    redis = Redis.from_url(REDIS_URL)
    
    lock_name = "test-verification-lock"
    
    try:
        logger.info("Attempting to acquire lock...")
        async with distributed_lock(redis, lock_name, timeout=5) as acquired:
            if acquired:
                logger.info("✅ Lock acquired!")
                # Simulate work
                await asyncio.sleep(0.1)
            else:
                logger.error("❌ Failed to acquire lock (unexpected)")
                exit(1)
        
        logger.info("Lock released.")
        
        # Test Contention (optional)
        # ...
        
    except Exception as e:
        logger.error(f"❌ Lock test failed: {e}")
        exit(1)
    finally:
        await redis.close()

if __name__ == "__main__":
    asyncio.run(verify())
