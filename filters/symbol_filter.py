# filters/symbol_filter.py
import asyncio
from decimal import Decimal
from config import SYMBOL_POOL, VOLUME_MIN_USD, FUNDING_RATE_MIN

async def _fetch_metrics(client, symbol):
    """回傳 (symbol, funding(Decimal), volume(Decimal))；任何取不到就回 0"""
    try:
        # 24h 量（以 quoteVolume）
        volume = Decimal("0")
        stats = await client.get_24h_stats(symbol)
        if stats and "quoteVolume" in stats:
            volume = Decimal(str(stats["quoteVolume"]))

        # 最新 funding（取最後一筆）
        funding = Decimal("0")
        fr = await client.get_latest_funding_rate(symbol)
        if fr is not None:
            funding = Decimal(str(fr))

        return symbol, funding, volume
    except Exception as e:
        print(f"[FILTER] fetch error {symbol}: {e}")
        return symbol, Decimal("0"), Decimal("0")

async def shortlist(client, max_candidates=8):
    tasks = [ _fetch_metrics(client, s) for s in SYMBOL_POOL ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    approved = []
    for sym, funding, volume in results:
        if (funding >= Decimal(str(FUNDING_RATE_MIN))) and (volume >= Decimal(str(VOLUME_MIN_USD))):
            approved.append(sym)

    if approved:
        return approved[:max_candidates]

    # fallback：只按量排序
    sorted_by_volume = sorted(results, key=lambda x: x[2], reverse=True)
    if sorted_by_volume:
        chosen = [s for s,_,_ in sorted_by_volume[:max_candidates]]
        print(f"[FILTER] fallback by volume: {chosen}")
        return chosen

    return SYMBOL_POOL[:max_candidates]
