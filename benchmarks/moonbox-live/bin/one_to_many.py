#!/usr/bin/env python3
"""One-to-Many: Broadcast input to multiple parallel processing paths."""
import asyncio, json, sys
from concurrent.futures import ThreadPoolExecutor

async def broadcast(inputs, processors):
    """Broadcast each input to all processors, aggregate results."""
    async def process_one(inp, proc):
        try:
            return await proc(inp)
        except Exception as e:
            return {"error": str(e), "input": inp}

    tasks = []
    for inp in inputs:
        for proc in processors:
            tasks.append(process_one(inp, proc))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "inputs": len(inputs),
        "processors": len(processors),
        "results": results,
        "pattern": "one_to_many"
    }

if __name__ == '__main__':
    print(json.dumps({"status": "one_to_many module loaded", "pattern": "broadcast"}))
