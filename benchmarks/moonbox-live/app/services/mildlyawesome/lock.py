
from redis.asyncio import Redis
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("mildlyawesome.lock")

@asynccontextmanager
async def distributed_lock(redis: Redis, name: str, timeout: int = 10, blocking_timeout: int = 2):
    """
    Robust distributed locking using Redis.
    timeout: How long the lock is held (TTL) in seconds.
    blocking_timeout: How long to wait to acquire the lock.
    """
    key = f"lock:{name}"
    lock = redis.lock(key, timeout=timeout, blocking_timeout=blocking_timeout)
    
    acquired = await lock.acquire()
    
    if not acquired:
        logger.warning(f"Could not acquire lock: {name} (waited {blocking_timeout}s)")
        try:
            yield False
        except Exception:
            pass # Swallow exception if lock wasn't acquired to prevent confusing caller
        return
        
    try:
        logger.debug(f"Acquired lock: {name}")
        yield True
    finally:
        try:
            # Check ownership before releasing (handled by redis-py mainly, but safe practice)
            await lock.release()
        except Exception as e:
            # Lock might have expired or been stolen
            logger.debug(f"Lock release skipped/failed for {name}: {e}")
