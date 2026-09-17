"""
Effusion Labs API Orchestrator
Unified API Gateway for microservices coordination

Architecture:
- BFF (Backend for Frontend) pattern
- Event-driven microservices orchestration
- WebSocket real-time updates
- DayZ server management integration
- MCP gateway integration
- Popmart recon integration
"""

from fastapi import FastAPI, WebSocket, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
import json
import httpx
from datetime import datetime
from enum import Enum
import os
import logging
from services.mildlyawesome.worker import BackgroundWorker

logger = logging.getLogger("orchestrator")
logging.basicConfig(level=logging.INFO)

# OpenTelemetry tracing
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# Redis for pub/sub
import redis.asyncio as redis
from fastapi_websocket_pubsub import PubSubEndpoint

# Configure OpenTelemetry
resource = Resource.create({"service.name": "effusion-orchestrator"})
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
)
trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

from contextlib import asynccontextmanager
from services.mildlyawesome.events import event_bus

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Orchestrator Service Initialized")
    
    # Initialize DB
    from services.mildlyawesome.db import init_db
    await init_db()

    # Connect Event Bus and Redis
    await event_bus.connect()
    
    # Start Background Worker
    worker = BackgroundWorker(event_bus)
    await worker.start()
    
    app.state.redis = event_bus.redis # Reuse connection if possible or create new
    
    # If EventBus manages its own redis, we might still want a separate one or just access it
    # For now, let's keep app.state.redis independent if needed, or link them.
    # But simpler to just use event_bus.redis if we trust it.
    
    await event_bus.publish("system", "SYSTEM_STARTUP", {"version": "2.0.0", "mode": "orchestrator"})
    
    print(f"✓ EventBus Connected")
    print(f"✓ Jaeger tracing enabled: {os.getenv('JAEGER_AGENT_HOST', 'localhost')}:{os.getenv('JAEGER_AGENT_PORT', '6831')}")
    print(f"✓ Prometheus metrics exposed at /metrics")
    
    yield
    
    # Shutdown
    await event_bus.publish("system", "SYSTEM_SHUTDOWN", {})
    await worker.stop()
    await event_bus.disconnect()
    logger.info("Orchestrator Service Shutdown")

app = FastAPI(
    title="Effusion Labs API Orchestrator",
    version="2.0.0",
    description="Unified API gateway with distributed tracing and real-time pub/sub",
    lifespan=lifespan
)

# Import and mount sub-services
from services.mildlyawesome.routers.cannabis import router as cannabis_router
from services.mildlyawesome.routers.popmart import router as popmart_router
from services.mildlyawesome.routers.resume import router as resume_router
from services.mildlyawesome.routers.pipeline_router import router as pipeline_router

app.include_router(cannabis_router, prefix="/api")
app.include_router(popmart_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }
    # Check for artifact marker
    marker_path = "/app/artifacts/.artifact_git_sha"
    if os.path.exists(marker_path):
        with open(marker_path, "r") as f:
            health["artifact_git_sha"] = f.read().strip()
    return health

# Rate Limiting
from services.mildlyawesome.middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, limit=100, window=60)

# Telemetry
from services.mildlyawesome.telemetry import setup_telemetry
setup_telemetry(app)

# Brain Interface
from services.mildlyawesome.brain import brain, Thought
from typing import List

@app.get("/api/brain/recall", response_model=List[Thought])
async def brain_recall(query: str):
    """
    Direct interface to the MildlyAwesome Brain.
    """
    return await brain.recall(query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.orchestrator:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
