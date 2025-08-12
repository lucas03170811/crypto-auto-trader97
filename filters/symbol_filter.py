# filters/symbol_filter.py
import asyncio
from decimal import Decimal
from config import SYMBOL_POOL, VOLUME_MIN_USD, FUNDING_RATE_MIN

async def _fetch_metrics(client, symbol):
    """Try to fetch funding (fallback to 0) and 24h quoteVolume. Returns tuple (symbol, funding, volume)"""
    try:
        # Get 24h stats for volume
        try:
            info = await client._run(client.client.ticker_24hr, symbol)  # using underlying sync method via _run
            volume = Decimal(str(info.get("quoteVolume", "0")))
        except Exception:
            # fallback to ticker_price -> volume unknown -> return 0
            volume = Decimal("0")

        # Funding / premium might not be available; try markPrice or funding endpoint
        try:
            # Some connectors expose funding endpoint names differently; try a couple
            fd = await client._run(client.client.futures_funding_rate, symbol)
            funding = Decimal(str(fd.get("lastFundingRate", "0")))
        except Exception:
            funding = Decimal("0")

        return symbol, funding, volume
    except Exception as e:
        print(f"[FILTER] fetch error {symbol}: {e}")
        return symbol, None, None

async def shortlist(client, max_candidates=8):
    tasks = [ _fetch_metrics(client, s) for s in SYMBOL_POOL ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    approved = []
    for sym, funding, volume in results:
        if funding is None or volume is None:
            continue
        if funding >= FUNDING_RATE_MIN and volume >= VOLUME_MIN_USD:
            approved.append(sym)

    if approved:
        return approved[:max_candidates]

    # 放寬條件 fallback：只用成交量前 N
    sorted_by_volume = sorted([ (s, v) for s,v,f in results if v is not None ], key=lambda x: x[1], reverse=True)
    if sorted_by_volume:
        chosen = [s for s,_ in sorted_by_volume[:max_candidates]]
        print(f"[FILTER] fallback by volume: {chosen}")
        return chosen

    # final fallback: just return pool head
    return SYMBOL_POOL[:max_candidates]
