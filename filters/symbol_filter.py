import asyncio
from decimal import Decimal
from config import FUNDING_RATE_MIN, VOLUME_MIN_USD, SYMBOL_POOL

class SymbolFilter:
    def __init__(self, client):
        self.client = client

    async def fetch_metrics(self, symbol: str):
        premium = await self.client.client.futures_premium_index(symbol=symbol)
        funding = Decimal(premium["lastFundingRate"])
        stats = await self.client.client.futures_ticker(symbol=symbol)
        volume = Decimal(stats["quoteVolume"])
        return funding, volume

    async def shortlist(self):
        tasks = [self.fetch_metrics(s) for s in SYMBOL_POOL]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        approved = []
        for sym, res in zip(SYMBOL_POOL, results):
            if isinstance(res, Exception):
                continue
            funding, volume = res
            if funding >= FUNDING_RATE_MIN and volume >= VOLUME_MIN_USD:
                approved.append(sym)
        return approved[:6]