# exchange/binance_client.py
import asyncio
from typing import Any, List, Optional
from binance.um_futures import UMFutures

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://fapi.binance.com"):
        self.client = UMFutures(api_key, api_secret, base_url=base_url)

    async def _run_sync(self, fn, *args, **kwargs):
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    # Kline
    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Any]:
        try:
            return await self._run_sync(self.client.klines, symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return []

    # 現價
    async def get_price(self, symbol: str) -> float:
        try:
            res = await self._run_sync(self.client.ticker_price, symbol=symbol)
            return float(res.get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return 0.0

    # 24h 資訊（拿 quoteVolume）
    async def get_24h_stats(self, symbol: str) -> Optional[dict]:
        try:
            return await self._run_sync(self.client.ticker_24hr, symbol=symbol)
        except Exception as e:
            print(f"[ERROR] Failed to get 24h stats for {symbol}: {e}")
            return None

    # 最新 funding rate（拿最後一筆）
    async def get_latest_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            data = await self._run_sync(self.client.funding_rate, symbol=symbol, limit=1)
            if isinstance(data, list) and data:
                return float(data[0].get("fundingRate", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get funding rate for {symbol}: {e}")
        return None

    async def get_position(self, symbol: str) -> float:
        try:
            pos_list = await self._run_sync(self.client.get_position_risk, symbol=symbol)
            for p in pos_list:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get position for {symbol}: {e}")
        return 0.0

    async def get_equity(self) -> float:
        try:
            bal = await self._run_sync(self.client.balance)
            for a in bal:
                if a.get("asset") == "USDT":
                    return float(a.get("balance", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0.0

    async def open_long(self, symbol: str, qty: float):
        try:
            res = await self._run_sync(self.client.new_order,
                                       symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened LONG {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open LONG {symbol}: {e}")
            return None

    async def open_short(self, symbol: str, qty: float):
        try:
            res = await self._run_sync(self.client.new_order,
                                       symbol=symbol, side="SELL", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened SHORT {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open SHORT {symbol}: {e}")
            return None
