
import logging
from redis.asyncio import Redis
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger("mildlyawesome.circuit")

class CircuitBreakerOpen(Exception):
    pass

class CircuitBreaker:
    def __init__(self, redis: Redis, name: str, threshold: int = 5, recovery_timeout: int = 30):
        self.redis = redis
        self.name = f"cb:{name}"
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if open
        is_open = await self.redis.get(f"{self.name}:open")
        if is_open:
            logger.warning(f"Circuit {self.name} is OPEN. Failing fast.")
            raise CircuitBreakerOpen(f"Circuit {self.name} is open")

        try:
            result = await func(*args, **kwargs)
            # Success -> Reset count
            # await self.redis.delete(f"{self.name}:failures") # Optional: aggressive reset
            return result
        except Exception as e:
            # Failure -> Increment
            failures = await self.redis.incr(f"{self.name}:failures")
            if failures >= self.threshold:
                # Open circuit
                logger.error(f"Circuit {self.name} reached threshold ({failures}). Opening for {self.recovery_timeout}s.")
                await self.redis.setex(f"{self.name}:open", self.recovery_timeout, "1")
                await self.redis.delete(f"{self.name}:failures") # Reset failures for next cycle
            raise e
