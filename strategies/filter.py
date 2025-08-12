# strategies/filter.py
import asyncio
from decimal import Decimal
from typing import List, Tuple

from config import FUNDING_RATE_MIN, VOLUME_MIN_USD, SYMBOL_POOL

async def _fetch_metrics(client, symbol: str) -> Tuple[str, Decimal | None, Decimal | None]:
    try:
        premium = await client.client.futures_premium_index(symbol=symbol)
        funding = Decimal(premium.get("lastFundingRate", "0"))
        stats = await client.client.futures_ticker(symbol=symbol)
        volume = Decimal(stats.get("quoteVolume", "0"))
        return symbol, funding, volume
    except Exception as e:
        print(f"[FILTER] 無法抓取 {symbol} 指標: {e}")
        return symbol, None, None

async def filter_symbols(client, max_candidates: int = 8) -> List[str]:
    tasks = [_fetch_metrics(client, s) for s in SYMBOL_POOL]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    approved = []
    for symbol, funding, volume in results:
        if funding is None or volume is None:
            continue
        if funding >= FUNDING_RATE_MIN and volume >= VOLUME_MIN_USD:
            approved.append((symbol, volume, funding))

    if approved:
        approved_sorted = sorted(approved, key=lambda x: x[1], reverse=True)
        chosen = [s for s, _, __ in approved_sorted[:max_candidates]]
        print(f"[FILTER] 初篩通過：{chosen}")
        return chosen

    relaxed_volume = (VOLUME_MIN_USD / Decimal("3"))
    relaxed_funding = (FUNDING_RATE_MIN * Decimal("2"))
    print(f"[FILTER] 初篩無結果，放寬條件：VOLUME>={relaxed_volume} FUNDING>={relaxed_funding}")

    approved_relaxed = []
    for symbol, funding, volume in results:
        if funding is None or volume is None:
            continue
        if funding >= relaxed_funding and volume >= relaxed_volume:
            approved_relaxed.append((symbol, volume, funding))

    if approved_relaxed:
        approved_relaxed_sorted = sorted(approved_relaxed, key=lambda x: x[1], reverse=True)
        chosen = [s for s, _, __ in approved_relaxed_sorted[:max_candidates]]
        print(f"[FILTER] 放寬後通過：{chosen}")
        return chosen

    valid_by_volume = [(s, v, f) for s, v, f in results if v is not None]
    if not valid_by_volume:
        print("[FILTER] 無任何可用成交量資料，回傳 SYMBOL_POOL 的前幾項")
        return SYMBOL_POOL[:max_candidates]

    valid_by_volume_sorted = sorted(valid_by_volume, key=lambda x: x[1], reverse=True)
    chosen = [s for s, _, __ in valid_by_volume_sorted[:max_candidates]]
    print(f"[FILTER] Fallback (top by volume)：{chosen}")
    return chosen
