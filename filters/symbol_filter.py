# filters/symbol_filter.py
import asyncio
from typing import List
from decimal import Decimal
import config

async def shortlist(client, max_candidates: int = 8) -> List[str]:
    """
    Simple async shortlist: try to fetch 24h stats and pick top by quoteVolume,
    fallback to config.SYMBOL_POOL head.
    """
    tasks = []
    for s in config.SYMBOL_POOL:
        tasks.append(client.get_24h_stats(s))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    volumes = []
    for s, res in zip(config.SYMBOL_POOL, results):
        try:
            if isinstance(res, dict):
                qv = res.get("quoteVolume") or res.get("quoteVolume", 0)
                qv_f = float(qv)
            else:
                qv_f = 0.0
        except Exception:
            qv_f = 0.0
        volumes.append((s, qv_f))
    volumes.sort(key=lambda x: x[1], reverse=True)
    chosen = [s for s,_ in volumes[:max_candidates]]
    if chosen:
        return chosen
    return config.SYMBOL_POOL[:max_candidates]
