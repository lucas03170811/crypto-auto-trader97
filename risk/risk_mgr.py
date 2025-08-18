# risk/risk_mgr.py
import math
from typing import Optional
from config import (
    EQUITY_RATIO,
    PYRAMID_ADD_RATIO,
    MIN_NOTIONAL_USDT,
    DEBUG_MODE,
)

class RiskManager:
    def __init__(self, client):
        self.client = client

    async def _safe_price(self, symbol: str) -> Optional[float]:
        try:
            return float(await self.client.get_price(symbol))
        except Exception as e:
            print(f"[ERROR] get_price {symbol} failed: {e}")
            return None

    async def _safe_equity(self) -> Optional[float]:
        try:
            return float(await self.client.get_equity())
        except Exception as e:
            print(f"[ERROR] get_equity failed: {e}")
            return None

    async def _order_qty(self, symbol: str, price: float, pyramid: bool) -> float:
        equity = await self._safe_equity()
        if equity is None or equity <= 0:
            return 0.0

        usd = equity * EQUITY_RATIO
        if pyramid:
            usd *= (1.0 + PYRAMID_ADD_RATIO)

        qty = usd / max(price, 1e-9)
        # 粗略名義金額檢查（部分交易所要求 >= 5 USDT）
        if qty * price < MIN_NOTIONAL_USDT:
            if DEBUG_MODE:
                print(f"[RISK] qty too small: {symbol} notional={qty*price:.2f} < {MIN_NOTIONAL_USDT}")
            return 0.0

        # 四捨五入到 6 位，避免過細數量
        qty = math.floor(qty * 1e6) / 1e6
        return max(qty, 0.0)

    async def execute_order(self, symbol: str, side: str, pyramid: bool = False):
        """
        side: 'LONG' or 'SHORT'
        """
        price = await self._safe_price(symbol)
        if price is None:
            return

        qty = await self._order_qty(symbol, price, pyramid)
        if qty <= 0:
            return

        try:
            if side.upper() == "LONG":
                await self.client.open_long(symbol, qty)
                print(f"[ORDER] LONG {symbol} qty={qty}")
            elif side.upper() == "SHORT":
                await self.client.open_short(symbol, qty)
                print(f"[ORDER] SHORT {symbol} qty={qty}")
            else:
                print(f"[WARN] Unknown side: {side}")
        except Exception as e:
            print(f"[ERROR] execute_order {symbol} {side} failed: {e}")
