
import asyncio
import logging
import os
from services.mildlyawesome.db import init_db
from services.mildlyawesome.vector import VectorStore, DocumentChunk
from sqlmodel import select
from services.mildlyawesome.db import engine
from sqlmodel import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_vector")

async def check():
    logger.info("--- Vector Store Verification ---")
    try:
        # Import models so they are registered
        import services.mildlyawesome.vector 
        
        await init_db()
        
        store = VectorStore()
        
        # Determine dimension - 1536 is default in model
        # Generate dummy embedding
        dummy_embedding = [0.1] * 1536
        
        # Insert
        logger.info("Inserting document...")
        await store.add_documents(
            documents=["Hello Vector World"],
            embeddings=[dummy_embedding],
            metadatas=[{"source": "verification"}]
        )
        
        # Search (need async session or use store.search)
        logger.info("Searching...")
        results = await store.search(dummy_embedding, limit=1)
        
        if results:
            logger.info(f"✅ Found document: {results[0].content}")
        else:
            logger.error("❌ No results found!")
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ Vector verification failed: {e}")
        exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(check())
    except KeyboardInterrupt:
        pass
