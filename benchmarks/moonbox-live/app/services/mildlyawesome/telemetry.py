
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from services.mildlyawesome.config import settings
import logging

logger = logging.getLogger("mildlyawesome.telemetry")

def setup_telemetry(app):
    """
    Configure OpenTelemetry for the FastAPI app.
    """
    resource = Resource(attributes={
        "service.name": settings.app_name,
        "service.environment": settings.environment
    })

    provider = TracerProvider(resource=resource)
    
    # Always add Console Exporter in dev for visibility (or make conditional)
    if settings.environment == "development":
        # Be careful not to spam logs in production
        # provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        pass

    # Add OTLP Exporter if endpoint is reachable/configured
    # For now, we assume if it's set to a non-default or we explicitly want it.
    # We'll just try to add it.
    if settings.otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"Telemetry enabled via OTLP: {settings.otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")

    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    logger.info("Telemetry instrumentation applied.")
