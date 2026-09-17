
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Effusion Labs Orchestrator"
    environment: str = "development"
    
    # Database & Redis
    database_url: str = "postgresql+asyncpg://effusion:password@localhost:5432/effusion_db"
    redis_url: str = "redis://localhost:6379/0"
    
    # External APIs
    mcp_gateway_url: str = "http://localhost:37100"
    openai_api_key: str = ""
    otlp_endpoint: str = "http://localhost:4317" # Default URL for Jaeger/Honeycomb
    
    # Feature Flags
    enable_brain: bool = True
    enable_worker: bool = True

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
