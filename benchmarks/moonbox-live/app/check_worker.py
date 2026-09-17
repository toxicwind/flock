
import asyncio
import logging
import os
from services.mildlyawesome.orchestrator import lifespan
from fastapi import FastAPI

# Configure logging to show up in stdout
logging.basicConfig(level=logging.INFO)

async def test_worker():
    print("--- Starting Worker Verification ---")
    app = FastAPI()
    
    # Run lifespan
    async with lifespan(app):
        print(">>> Orchestrator running. Waiting for events...")
        await asyncio.sleep(5)
        print(">>> Stopping...")
        
    print("--- Verification Complete ---")

if __name__ == "__main__":
    try:
        asyncio.run(test_worker())
    except KeyboardInterrupt:
        pass
