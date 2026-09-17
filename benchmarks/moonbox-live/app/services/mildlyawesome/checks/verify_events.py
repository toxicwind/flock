
import asyncio
import logging
from services.mildlyawesome.events import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_events")

async def verify():
    logger.info("--- Testing Event Bus ---")
    
    # 1. Connect
    await event_bus.connect()
    
    stream_key = "test:stream"
    event_type = "VERIFY_EVENT"
    payload = {"message": "Hello MildlyAwesome"}
    
    try:
        # Correct Signature: stream, event_type, payload, source
        msg_id = await event_bus.publish(stream_key, event_type, payload, source="verifier")
        logger.info(f"✅ Published event to {stream_key}, ID: {msg_id}")
        
        # Verify read
        # Using a raw redis command to peek
        messages = await event_bus.redis.xrange(stream_key, count=1)
        if messages:
            msg_id_read, msg_data = messages[0]
            # msg_data is a dict of strings. 'payload' is json string.
            logger.info(f"✅ Verified event in stream: {msg_data}")
            assert msg_id_read == msg_id
            assert msg_data['type'] == event_type
        else:
            logger.error("❌ Event not found in stream!")
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ Event Bus test failed: {e}")
        exit(1)
    finally:
        await event_bus.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except KeyboardInterrupt:
        pass
