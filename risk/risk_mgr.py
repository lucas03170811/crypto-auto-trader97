# risk/risk_mgr.py
import math
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
from typing import Optional
import asyncio

from exchange.binance_client import BinanceClient
import config

getcontext().prec = 28

class RiskManager:
    def __init__(self, client: BinanceClient, equity_ratio: float = None):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio if equity_ratio is not None else config.EQUITY_RATIO))

    async def _get_symbol_filters(self, symbol: str):
        info = await self.client.get_symbol_info(symbol)
        if not info:
            return {}
        res = {}
        for f in info.get("filters", []):
            ft = f.get("filterType") or f.get("type")
            if ft == "LOT_SIZE":
                res["stepSize"] = f.get("stepSize") or f.get("tickSize") or f.get("minQty")
            if ft in ("MIN_NOTIONAL", "NOTIONAL"):
                # different exchanges provide different keys
                res["minNotional"] = f.get("minNotional") or f.get("notional") or f.get("minNotional")
        # also try symbol-level 'quantityPrecision' keys if exist
        return res

    def _round_up_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step == 0:
            return Decimal('0')
        n = (qty / step).to_integral_value(rounding=ROUND_UP)
        return (n * step).quantize(step)  # keep step precision

    async def get_order_qty(self, symbol: str, min_notional: float = None) -> float:
        """
        Calculate an order qty that:
        - Uses equity_ratio of account equity (or base order)
        - Aligns to stepSize
        - Ensures notional >= min_notional (or config.MIN_NOTIONAL_USD)
        Returns float qty (or 0.0 if cannot place)
        """
        try:
            price = await self.client.get_price(symbol)
            if price <= 0:
                return 0.0
            equity = await self.client.get_equity()
            if equity is None:
                equity = 0.0

            target_usd = Decimal(str(equity)) * self.equity_ratio
            # ensure minimum base order
            base = Decimal(str(config.BASE_ORDER_USD))
            if target_usd < base:
                target_usd = base

            # allow override min_notional
            min_notional = Decimal(str(min_notional)) if min_notional is not None else Decimal(str(config.MIN_NOTIONAL_USD))

            raw_qty = (target_usd / Decimal(str(price)))
            # get step size
            filters = await self._get_symbol_filters(symbol)
            step = Decimal(str(filters.get("stepSize", "0.0001")))
            if step == 0:
                step = Decimal("0.0001")
            qty = self._round_up_to_step(raw_qty, step)

            # if qty equals 0 (raw < step), bump to one step
            if qty == 0:
                qty = step

            notional = (qty * Decimal(str(price)))
            if notional < min_notional:
                # bump n so notional >= min_notional
                need = (min_notional / Decimal(str(price)))
                need_n = (need / step).to_integral_value(rounding=ROUND_UP)
                qty = (need_n * step).quantize(step)

            # final guard: if qty is zero, return 0.0
            if qty <= 0:
                return 0.0
            return float(qty)
        except Exception as e:
            print(f"[RISK] get_order_qty error {symbol}: {e}")
            return 0.0

    async def execute_trade(self, symbol: str, side: str):
        """Place a market order in the given side ('LONG' or 'SHORT')."""
        try:
            qty = await self.get_order_qty(symbol)
            if qty <= 0:
                print(f"[RISK] qty too small: {symbol}")
                return None
            if side == "LONG":
                return await self.client.open_long(symbol, qty)
            elif side == "SHORT":
                return await self.client.open_short(symbol, qty)
            else:
                print(f"[RISK] Unknown side {side}")
                return None
        except Exception as e:
            print(f"[RISK] execute_trade error {symbol}: {e}")
            return None
