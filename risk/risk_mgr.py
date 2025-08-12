# risk/risk_mgr.py
from decimal import Decimal
from config import BASE_QTY_USDT, MIN_NOTIONAL, EQUITY_RATIO_PER_TRADE
import asyncio

class RiskManager:
    def __init__(self, client):
        self.client = client
        # use Decimal for config, but convert to float when needed
        self.base_qty_usdt = float(BASE_QTY_USDT)
        self.equity_ratio = float(EQUITY_RATIO_PER_TRADE)

    async def get_price(self, symbol):
        return float(await self.client.get_price(symbol))

    async def get_order_qty(self, symbol):
        equity = await self.client.get_equity()
        if equity is None:
            equity = 0.0
        # Use equity ratio if configured; fallback to base qty USDT
        usdt_amount = float(equity) * self.equity_ratio
        if usdt_amount <= 0:
            usdt_amount = self.base_qty_usdt

        price = await self.get_price(symbol)
        if price <= 0:
            return 0.0
        qty = round(usdt_amount / price, 6)  # keep precision
        return qty

    async def get_nominal_value(self, symbol, qty):
        price = await self.get_price(symbol)
        return float(price) * float(qty)

    async def execute_trade(self, symbol, signal):
        # simple one-shot: check current position and open if zero
        pos = await self.client.get_position(symbol)
        print(f"[Position] {symbol}: {pos}")
        qty = await self.get_order_qty(symbol)
        notional = await self.get_nominal_value(symbol, qty)

        if notional < float(MIN_NOTIONAL):
            print(f"[SKIP ORDER] {symbol} notional {notional:.2f} < MIN_NOTIONAL")
            return

        if signal == "long" and float(pos) <= 0:
            print(f"[TRADE] Opening LONG {symbol} qty={qty}")
            await self.client.open_long(symbol, qty, positionSide="LONG")
        elif signal == "short" and float(pos) >= 0:
            print(f"[TRADE] Opening SHORT {symbol} qty={qty}")
            await self.client.open_short(symbol, qty, positionSide="SHORT")
        else:
            print(f"[TRADE] No action for {symbol} (pos={pos}, signal={signal})")
