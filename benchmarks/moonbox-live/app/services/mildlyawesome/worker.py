
import asyncio
import logging
import uuid
import json
from typing import Dict, Any, Callable
from .events import EventBus

logger = logging.getLogger("worker")

class BackgroundWorker:
    """
    Background worker that consumes events from Redis Streams.
    Replaces legacy Arq worker with native EventBus consumption.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False
        self.consumer_name = f"worker-{str(uuid.uuid4())[:8]}"
        self.group_name = "orchestrator_workers"
        self.stream_name = "system"
        self._task = None
        
    async def start(self):
        """Start the background worker"""
        self.running = True
        
        # Ensure group exists
        await self.event_bus.create_group(self.stream_name, self.group_name)
        
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"BackgroundWorker started: {self.consumer_name}")
        
    async def stop(self):
        """Stop the background worker"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BackgroundWorker stopped")
            
    async def _run_loop(self):
        """Main consumption loop"""
        logger.info(f"Worker loop starting for stream: {self.stream_name}")
        while self.running:
            try:
                # Consume messages
                await self.event_bus.consume(
                    stream=self.stream_name,
                    group=self.group_name,
                    consumer=self.consumer_name,
                    handler=self.handle_event,
                    count=5
                )
                await asyncio.sleep(0.1) # Prevent tight loop
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, msg_id: str, data: Dict[str, Any]):
        """Process a single event"""
        event_type = data.get("type", "UNKNOWN")
        payload = data.get("payload", {})
        
        logger.info(f"⚡ [WORKER] Processing {event_type} ({msg_id})")
        
        if event_type == "SYSTEM_STARTUP":
            await self.handle_system_startup(payload)
        elif event_type == "SYSTEM_SHUTDOWN":
            await self.handle_system_shutdown(payload)
        elif event_type == "TRIGGER_DEPLOY":
            logger.info("🚀 Deployment trigger received! Initiating sequence...")
        
    async def handle_system_startup(self, payload: Dict):
        logger.info(f"System Startup Procedure: Verifying payload: {payload}")
        # Could trigger initial cache warming here
        
    async def handle_system_shutdown(self, payload: Dict):
        logger.info("System Shutdown Procedure: Cleaning up resources...")
