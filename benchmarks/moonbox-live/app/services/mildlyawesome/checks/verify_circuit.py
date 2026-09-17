
import asyncio
import logging
import os
from redis.asyncio import Redis
from services.mildlyawesome.circuit import CircuitBreaker, CircuitBreakerOpen

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_circuit")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def failing_operation():
    """Simulates an operation that always fails"""
    raise ValueError("Simulated Failure")

async def successful_operation():
    """Simulates a success"""
    return "Success"

async def verify():
    logger.info("--- Testing Circuit Breaker ---")
    redis = Redis.from_url(REDIS_URL)
    
    cb_name = "test-circuit"
    # Ensure clean state
    await redis.delete(f"cb:{cb_name}:failures")
    await redis.delete(f"cb:{cb_name}:open")
    
    cb = CircuitBreaker(redis, cb_name, threshold=3, recovery_timeout=2)
    
    logger.info("1. Tripping the circuit (Threshold: 3)")
    for i in range(3):
        try:
            await cb.call(failing_operation)
        except ValueError:
            logger.info(f"   Failure {i+1} recorded")
        except CircuitBreakerOpen:
            logger.error("❌ Circuit opened too early!")
            exit(1)

    logger.info("2. Verifying Circuit is OPEN")
    try:
        await cb.call(successful_operation)
        logger.error("❌ Circuit should be OPEN but call succeeded!")
        exit(1)
    except CircuitBreakerOpen:
        logger.info("✅ Circuit correctly rejected call (Open state confirmed)")

    logger.info("3. Waiting for Recovery (2s)...")
    await asyncio.sleep(2.1)
    
    logger.info("4. Verifying Recovery")
    try:
        result = await cb.call(successful_operation)
        assert result == "Success"
        logger.info("✅ Circuit recovered and allowed call")
    except Exception as e:
        logger.error(f"❌ Failed to recover: {e}")
        exit(1)

    # Cleanup
    await redis.delete(f"cb:{cb_name}:failures")
    await redis.delete(f"cb:{cb_name}:open")
    await redis.close()
    logger.info("✨ Circuit Breaker Verification Passed")

if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except KeyboardInterrupt:
        pass
