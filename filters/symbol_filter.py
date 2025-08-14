# filters/symbol_filter.py
import asyncio
from decimal import Decimal
from config import SYMBOL_POOL, VOLUME_MIN_USD, FUNDING_RATE_MIN

async def _fetch_metrics(client, symbol):
    """Fetch funding rate & 24h quoteVolume."""
    try:
        # 新版 24h 成交量
        try:
            info = await client.get_24h_stats(symbol)
            volume = Decimal(str(info.get("quoteVolume", "0")))
        except Exception:
            volume = Decimal("0")

        # 資金費率
        try:
            funding = await client.get_latest_funding_rate(symbol)
            funding = Decimal(str(funding)) if funding is not None else Decimal("0")
        except Exception:
            funding = Decimal("0")

        return symbol, funding, volume
    except Exception as e:
        print(f"[FILTER] fetch error {symbol}: {e}")
        return symbol, None, None

async def shortlist(client, max_candidates=8):
    tasks = [_fetch_metrics(client, s) for s in SYMBOL_POOL]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    approved = []
    for sym, funding, volume in results:
        if funding is None or volume is None:
            continue
        if funding >= FUNDING_RATE_MIN and volume >= VOLUME_MIN_USD:
            approved.append(sym)

    if approved:
        return approved[:max_candidates]

    # fallback：按成交量排序
    sorted_by_volume = sorted(
        [(s, v) for s, _, v in results if v is not None],
        key=lambda x: x[1],
        reverse=True
    )
    if sorted_by_volume:
        chosen = [s for s, _ in sorted_by_volume[:max_candidates]]
        print(f"[FILTER] fallback by volume: {chosen}")
        return chosen

    return SYMBOL_POOL[:max_candidates]
