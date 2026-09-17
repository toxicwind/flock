
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from services.mildlyawesome.events import event_bus

logger = logging.getLogger("mildlyawesome.middleware")

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            client_ip = request.client.host
            key = f"ratelimit:{client_ip}"
            
            # Using the shared Redis connection from EventBus
            # Note: Orchestrator `startup` connects the bus, so redis should be available.
            redis = event_bus.redis
            
            if redis:
                # Use Redis atomic increment + expire
                current = await redis.incr(key)
                if current == 1:
                    await redis.expire(key, self.window)
                
                if current > self.limit:
                    logger.warning(f"Rate limit exceeded for {client_ip}")
                    return Response(content="Rate limit exceeded", status_code=429)
                    
        except Exception as e:
            # Fail open if Redis is down (or log error)
            logger.error(f"Rate limit check failed: {e}")
            
        return await call_next(request)
