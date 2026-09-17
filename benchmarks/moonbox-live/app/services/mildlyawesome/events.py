
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import asyncio
from redis import asyncio as aioredis
from redis.asyncio import Redis
from services.mildlyawesome.config import settings

logger = logging.getLogger("event_bus")

class EventBus:
    """
    Centralized Event Bus using Redis Streams.
    Allows services to publish events and subscribe to interest groups.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Redis = None
        self.max_len = 10000 # Keep stream size manageable
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            logger.info("EventBus connected to Redis")
            
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def publish(self, stream: str, event_type: str, payload: Dict[str, Any], source: str = "orchestrator") -> str:
        """
        Publish an event to a specific stream.
        Returns the Redis Stream ID.
        """
        if not self.redis:
            await self.connect()
            
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        message = {
            "id": event_id,
            "type": event_type,
            "source": source,
            "timestamp": timestamp,
            "payload": json.dumps(payload), # Redis streams store flat dicts of strings
        }
        
        try:
            # XADD: Append to stream
            stream_id = await self.redis.xadd(stream, message, maxlen=self.max_len)
            logger.debug(f"Published event {event_type} to {stream}: {stream_id}")
            return stream_id
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def create_group(self, stream: str, group: str):
        """Create a consumer group if it doesn't exist"""
        if not self.redis:
            await self.connect()
        try:
            # MKSTREAM creates stream if missing
            await self.redis.xgroup_create(stream, group, mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def consume(self, stream: str, group: str, consumer: str, handler: Callable, count: int = 10):
        """
        Consume messages from a stream as part of a group.
        This is intended to be run in a loop background task.
        """
        if not self.redis:
            await self.connect()
            
        try:
            # XREADGROUP
            streams = {stream: ">"} # ">" means new messages never delivered to this consumer
            messages = await self.redis.xreadgroup(group, consumer, streams, count=count)
            
            for stream_name, msgs in messages:
                for msg_id, data in msgs:
                    try:
                        # Parse payload back to JSON
                        if 'payload' in data:
                            data['payload'] = json.loads(data['payload'])
                            
                        await handler(msg_id, data)
                        
                        # XACK: Acknowledge processing
                        await self.redis.xack(stream, group, msg_id)
                    except Exception as e:
                        logger.error(f"Error processing message {msg_id}: {e}")
                        # Don't ack so it can be retried or claimed
                        
        except Exception as e:
            logger.error(f"Consume error: {e}")
            await asyncio.sleep(1) # Backoff

# Global singleton
event_bus = EventBus()
