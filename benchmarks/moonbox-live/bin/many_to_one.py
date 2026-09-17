#!/usr/bin/env python3
"""Many-to-One: Aggregate multiple parallel results into single output."""
import asyncio, json, functools

async def aggregate(results, reducer=None):
    """Aggregate multiple results using monadic reduction."""
    if reducer is None:
        reducer = lambda acc, x: {**acc, **x} if isinstance(x, dict) else acc + [x]

    valid_results = [r for r in results if not isinstance(r, Exception)]

    if not valid_results:
        return {"error": "All results failed", "pattern": "many_to_one"}

    # Monadic fold
    result = functools.reduce(reducer, valid_results)
    return {
        "aggregated": result,
        "sources": len(valid_results),
        "failed": len(results) - len(valid_results),
        "pattern": "many_to_one"
    }

if __name__ == '__main__':
    print(json.dumps({"status": "many_to_one module loaded", "pattern": "aggregate"}))
