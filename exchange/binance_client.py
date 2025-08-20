# exchange/binance_client.py
import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal, getcontext

from binance.um_futures import UMFutures
import config

getcontext().prec = 28

class BinanceClient:
    """
    輕量 async 包裝 binance-futures-connector 的 UMFutures。
    修復重點：補上 get_klines，並提供本專案其餘模組會用到的介面。
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)

    # ---------- utils ----------
    async def _run(self, fn, *args, **kwargs):
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
            res = await self._run(self.client.ticker_price, symbol)
            return self._D(res.get("price"))
        except Exception:
            return None

    async def get_24h_stats(self, symbol: str) -> Optional[dict]:
        """給 shortlist 使用的 24hr 統計（含 quoteVolume）。"""
        try:
            return await self._run(self.client.ticker_24hr, symbol)
        except Exception:
            return None

    # ---------- market data ----------
    async def get_klines(self, symbol: str, interval: str = None, limit: int = None):
        """
        關鍵修復：補上 get_klines，對齊策略模組的呼叫。
        回傳為 binance 原始 list[list]（策略會自行轉成 DataFrame）
        """
        interval = interval or config.KLINE_INTERVAL
        limit = limit or config.KLINE_LIMIT
        return await self._run(self.client.klines, symbol, interval, limit)

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
                # 新舊欄位名稱兼容
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
