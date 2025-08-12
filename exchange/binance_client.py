# exchange/binance_client.py
import asyncio
from typing import Any, List
from binance.um_futures import UMFutures

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://fapi.binance.com"):
        # UMFutures constructor: pass key, secret as positional
        self.client = UMFutures(api_key, api_secret, base_url=base_url)

    async def _run_sync(self, fn, *args, **kwargs):
        """Helper: run blocking sync function in threadpool."""
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    # 抓取 kline（同步 SDK -> 放到 thread）
    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Any]:
        try:
            return await self._run_sync(self.client.klines, symbol, interval, limit)
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return []

    async def get_price(self, symbol: str) -> float:
        try:
            res = await self._run_sync(self.client.ticker_price, symbol)
            return float(res.get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol: str) -> float:
        try:
            pos_list = await self._run_sync(self.client.get_position_risk, symbol)
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
