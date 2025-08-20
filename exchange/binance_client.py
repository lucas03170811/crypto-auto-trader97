# exchange/binance_client.py
import os
import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal, getcontext

from binance.um_futures import UMFutures
import config

getcontext().prec = 28

class BinanceClient:
    """
    輕量 async 包裝 binance-futures-connector 的 UMFutures。
    修復重點：
    1) get_klines 使用「關鍵字參數」呼叫，避免位置參數錯誤。
    2) 統一所有交易所呼叫都用關鍵字參數。
    3) 以 asyncio.Semaphore 做併發限流，避免連線池爆滿。
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)
        # 併發上限（可用環境變數 BINANCE_MAX_CONCURRENCY 調整）
        self._sem = asyncio.Semaphore(int(os.getenv("BINANCE_MAX_CONCURRENCY", "5")))

    # ---------- utils ----------
    async def _run(self, fn, *args, **kwargs):
        # 所有對交易所的呼叫都經過限流
        async with self._sem:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    @staticmethod
    def _D(x) -> Decimal:
        return Decimal(str(x))

    @staticmethod
    def _floor_step(value: Decimal, step: Decimal) -> Decimal:
        if step == 0:
            return value
        return (value // step) * step

    # ---------- info ----------
    async def exchange_info(self) -> Dict[str, Any]:
        return await self._run(self.client.exchange_info)

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        try:
            info = await self.exchange_info()
            for s in info.get("symbols", []):
                if s.get("symbol") == symbol:
                    return s
        except Exception:
            pass
        return None

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        try:
            res = await self._run(self.client.ticker_price, symbol=symbol)
            return self._D(res.get("price"))
        except Exception:
            return None

    async def get_24h_stats(self, symbol: str) -> Optional[dict]:
        """給 shortlist 使用的 24hr 統計（含 quoteVolume）。"""
        try:
            return await self._run(self.client.ticker_24hr, symbol=symbol)
        except Exception:
            return None

    async def get_premium_index(self, symbol: str) -> Optional[dict]:
        """取得資金費等 premium index 資訊。"""
        try:
            return await self._run(self.client.premium_index, symbol=symbol)
        except Exception:
            return None

    # ---------- market data ----------
    async def get_klines(self, symbol: str, interval: str = None, limit: int = None):
        """
        關鍵修復：一律使用關鍵字參數呼叫 UMFutures.klines
        """
        interval = interval or config.KLINE_INTERVAL
        limit = limit or config.KLINE_LIMIT
        return await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)

    # ---------- account ----------
    async def get_equity(self) -> Decimal:
        try:
            balances = await self._run(self.client.balance)
            for b in balances:
                if b.get("asset") == "USDT":
                    return self._D(b.get("balance"))
        except Exception:
            pass
        return Decimal("0")

    async def change_leverage(self, symbol: str, leverage: int):
        try:
            return await self._run(self.client.change_leverage, symbol=symbol, leverage=leverage)
        except Exception:
            return None

    # ---------- order helpers ----------
    async def _lot_size_constraints(self, symbol_info: dict):
        stepSize = minQty = minNotional = Decimal("0")
        for f in symbol_info.get("filters", []):
            ft = f.get("filterType")
            if ft == "LOT_SIZE":
                stepSize = self._D(f.get("stepSize"))
                minQty = self._D(f.get("minQty"))
            if ft == "MIN_NOTIONAL":
                minNotional = self._D(f.get("notional", f.get("minNotional", "0")))
        return stepSize, minQty, minNotional

    async def _quantize_qty(self, symbol: str, qty: Decimal) -> Decimal:
        info = await self.get_symbol_info(symbol)
        if not info:
            return qty
        step, minQty, _ = await self._lot_size_constraints(info)
        q = self._floor_step(qty, step)
        if q < minQty:
            return Decimal("0")
        return q

    async def open_long(self, symbol: str, qty: Decimal):
        q = await self._quantize_qty(symbol, qty)
        if q <= 0:
            return None
        return await self._run(
            self.client.new_order,
            symbol=symbol, side="BUY", type="MARKET", quantity=str(q)
        )

    async def open_short(self, symbol: str, qty: Decimal):
        q = await self._quantize_qty(symbol, qty)
        if q <= 0:
            return None
        return await self._run(
            self.client.new_order,
            symbol=symbol, side="SELL", type="MARKET", quantity=str(q)
        )
