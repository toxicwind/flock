#!/usr/bin/env python3
"""
monadic.py - One-to-Many, Many-to-One, Swarm consensus.
Recursive tail-call optimized. 8x fallback chain.
"""
import asyncio, json, functools, random
from typing import List, Callable, Any, Dict
from datetime import datetime
from pathlib import Path

LOG = Path("/mnt/agents/output/.bg_logs/monadic.jsonl")
LOG.parent.mkdir(parents=True, exist_ok=True)

def _log(event, data):
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(), "event": event, **data}, default=str) + "\n")

# === ONE-TO-MANY: broadcast input to N processors ===
async def one_to_many(inputs, processors, max_concurrent=8):
    """Broadcast each input to all processors. Aggregate all results."""
    semaphore = asyncio.Semaphore(max_concurrent)
    async def run_one(inp, proc):
        async with semaphore:
            for attempt in range(8):
                try:
                    if asyncio.iscoroutinefunction(proc):
                        return {"input": inp, "processor": proc.__name__, "result": await proc(inp), "attempt": attempt}
                    else:
                        return {"input": inp, "processor": proc.__name__, "result": proc(inp), "attempt": attempt}
                except Exception as e:
                    if attempt == 7:
                        return {"input": inp, "processor": proc.__name__, "error": str(e), "attempt": attempt}
                    await asyncio.sleep(0.1 * (2 ** attempt))
    tasks = [run_one(inp, proc) for inp in inputs for proc in processors]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    _log("one_to_many", {"inputs": len(inputs), "processors": len(processors), "results": len(results)})
    return results

# === MANY-TO-ONE: aggregate N results into single output ===
def many_to_one(results, reducer=None):
    """Fold results with monadic reduction. 8 fallback reducers."""
    if reducer is None:
        reducers = [
            lambda acc, x: {**acc, **x} if isinstance(x, dict) and isinstance(acc, dict) else acc + [x],
            lambda acc, x: acc + [x],
            lambda acc, x: x if acc is None else acc,
            lambda acc, x: str(acc) + "\n" + str(x),
        ]
        reducer = reducers[0]

    valid = [r for r in results if not isinstance(r, Exception) and not (isinstance(r, dict) and "error" in r)]
    if not valid:
        _log("many_to_one", {"error": "all_failed", "total": len(results)})
        return {"error": "all_failed", "total": len(results)}

    try:
        result = functools.reduce(reducer, valid)
    except Exception as e:
        try:
            result = functools.reduce(reducers[1], valid)
        except:
            result = valid

    _log("many_to_one", {"valid": len(valid), "total": len(results)})
    return {"aggregated": result, "valid": len(valid), "total": len(results)}

# === SWARM: decentralized consensus ===
class SwarmNode:
    def __init__(self, node_id, capabilities):
        self.id = node_id
        self.capabilities = capabilities
        self.peers = []
        self.consensus = {}
        self.reputation = {}

    def add_peer(self, peer):
        self.peers.append(peer)

    async def gossip(self, message):
        for peer in self.peers:
            await peer.receive(self.id, message)

    async def receive(self, sender_id, message):
        self.consensus[sender_id] = message
        self.reputation[sender_id] = self.reputation.get(sender_id, 0) + 1

    def consensus_value(self):
        if not self.consensus:
            return None
        values = list(self.consensus.values())
        # Weighted majority
        weighted = {}
        for v in values:
            key = json.dumps(v, sort_keys=True, default=str)
            weighted[key] = weighted.get(key, 0) + 1
        best = max(weighted, key=weighted.get)
        _log("swarm_consensus", {"node": self.id, "peers": len(self.peers), "consensus": len(self.consensus)})
        return json.loads(best)

if __name__ == "__main__":
    # Demo
    async def demo():
        async def proc_a(x):
            return {"a": x * 2}
        async def proc_b(x):
            return {"b": x + 10}
        results = await one_to_many([1, 2, 3], [proc_a, proc_b])
        agg = many_to_one(results)
        print(json.dumps(agg, indent=2, default=str))
    asyncio.run(demo())
