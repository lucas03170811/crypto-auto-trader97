# strategies/filter.py
import asyncio
from decimal import Decimal
from typing import List
from config import FUNDING_RATE_MIN, VOLUME_MIN_USD, SYMBOL_POOL

async def _fetch(client, symbol: str):
    try:
        prem = await client._run_blocking(client.client.futures_premium_index, symbol)
        fund = Decimal(prem.get("lastFundingRate", "0"))
        stats = await client._run_blocking(client.client.futures_ticker, symbol)
        vol = Decimal(stats.get("quoteVolume", "0"))
        return symbol, fund, vol
    except Exception as e:
        print(f"[FILTER] fetch error {symbol}: {e}")
        return symbol, None, None

async def filter_symbols(client, max_candidates: int = 10) -> List[str]:
    tasks = [ _fetch(client, s) for s in SYMBOL_POOL ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    approved = []
    for symbol, funding, volume in results:
        if funding is None or volume is None:
            continue
        if funding >= FUNDING_RATE_MIN and volume >= VOLUME_MIN_USD:
            approved.append(symbol)

    if approved:
        return approved[:max_candidates]

    # 放寬條件 fallback
    relaxed_volume = VOLUME_MIN_USD / Decimal("3")
    relaxed_funding = FUNDING_RATE_MIN * Decimal("0.5")
    fallback = [s for s,fv,vol in results if vol is not None and vol >= relaxed_volume][:max_candidates]
    if fallback:
        print("[FILTER] Fallback using relaxed volume.")
        return fallback

    # 最後回傳 pool 頂部
    return SYMBOL_POOL[:max_candidates]
