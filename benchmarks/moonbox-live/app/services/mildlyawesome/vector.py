
from typing import List, Optional
from sqlmodel import SQLModel, Field, select
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from services.mildlyawesome.db import engine
import logging

logger = logging.getLogger("vector_store")

class DocumentChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    metadata_json: str = "{}" # JSON string
    embedding: List[float] = Field(sa_column=Column(Vector(1536))) # OpenAI dimension

class VectorStore:
    """
    Manages vector embeddings and semantic search.
    """
    
    async def add_documents(self, documents: List[str], embeddings: List[List[float]], metadatas: List[dict] = None):
        """Add documents and embeddings to store"""
        async with AsyncSession(engine) as session:
            for i, doc in enumerate(documents):
                meta = str(metadatas[i]) if metadatas else "{}"
                chunk = DocumentChunk(
                    content=doc,
                    embedding=embeddings[i],
                    metadata_json=meta
                )
                session.add(chunk)
            await session.commit()
            logger.info(f"Added {len(documents)} documents to vector store.")

    async def search(self, query_embedding: List[float], limit: int = 5) -> List[DocumentChunk]:
        """Semantic search using vector similarity (L2 distance)"""
        async with AsyncSession(engine) as session:
            # Order by L2 distance ( <-> operator )
            statement = select(DocumentChunk).order_by(DocumentChunk.embedding.l2_distance(query_embedding)).limit(limit)
            results = await session.execute(statement)
            return results.scalars().all()
