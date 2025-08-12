# strategies/filter.py
import asyncio
from decimal import Decimal
from config import SYMBOL_POOL, VOLUME_MIN_USD, FUNDING_RATE_MIN

async def _fetch_metrics(client, symbol):
    try:
        # premium / funding: try premium_index (some connector versions)
        try:
            prem = await client._run(client.client.premium_index, symbol)
            funding = Decimal(str(prem.get("lastFundingRate", "0")))
        except Exception:
            funding = Decimal("0")

        try:
            stats = await client._run(client.client.ticker_price, symbol)
            # ticker_price may return dict or str; try quoteVolume fallback via ticker_24hr
            # Use futures_ticker / ticker_24hr
            info = await client._run(client.client.ticker_24hr, symbol)
            volume = Decimal(str(info.get("quoteVolume", "0")))
        except Exception:
            volume = Decimal("0")

        return symbol, funding, volume
    except Exception as e:
        print(f"[FILTER] fetch error {symbol}: {e}")
        return symbol, None, None

async def filter_symbols(client, max_candidates=10):
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

    # 放寬：若沒有通過，選成交量前幾名（fallback）
    sorted_by_volume = sorted([ (s, v) for s,v,f in results if v is not None ], key=lambda x: x[1], reverse=True)
    fallback = [s for s,_ in sorted_by_volume[:max_candidates]]
    return fallback
