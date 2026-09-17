
from sqlmodel import SQLModel, create_engine, Session, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger("db")

# Connection String
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://effusion:password@localhost:5432/effusion_db")

# Async Engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def init_db():
    """Initialize database tables"""
    logger.info("Initializing Database...")
    async with engine.begin() as conn:
        # Enable pgvector
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # await conn.run_sync(SQLModel.metadata.drop_all) # Uncomment to reset
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database initialized.")

async def get_session() -> AsyncSession:
    """Dependency for getting async session"""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
