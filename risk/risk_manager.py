# risk/risk_manager.py
from decimal import Decimal, getcontext
from config import BASE_QTY, MIN_NOTIONAL, MAX_LEVERAGE
import asyncio

getcontext().prec = 8

class RiskManager:
    def __init__(self, client):
        self.client = client
        # base qty in USDT (config.BASE_QTY)
        self.base_qty = Decimal(BASE_QTY)

    async def get_order_qty(self, symbol: str) -> float:
        # 用 base_qty (USDT) / price => qty (合約張數)
        price = await self.client.get_price(symbol)
        if not price:
            return 0.0
        qty = (self.base_qty / Decimal(price)) * Decimal(MAX_LEVERAGE)
        # 取小數 3 位
        return float(round(qty, 3))

    async def get_nominal_value(self, symbol: str, qty: float) -> Decimal:
        price = await self.client.get_price(symbol)
        if not price:
            return Decimal('0')
        return Decimal(price) * Decimal(qty)

    async def execute_trade(self, symbol: str, side: str):
        # side: 'long' or 'short'
        pos = await self.client.get_position(symbol)
        print(f"[Position] {symbol}: {pos}")
        qty = await self.get_order_qty(symbol)
        notional = await self.get_nominal_value(symbol, qty)
        print(f"[Trade] {symbol} side={side} qty={qty} notional={notional:.2f} USDT")

        if notional < MIN_NOTIONAL:
            print(f"[SKIP ORDER] {symbol} 名目價值太低: {notional:.2f} USDT (min {MIN_NOTIONAL})")
            return

        if side.lower() == "long" and pos <= 0:
            await self.client.open_long(symbol, qty)
        elif side.lower() == "short" and pos >= 0:
            await self.client.open_short(symbol, qty)
        else:
            print(f"[NO ACTION] {symbol} already has position direction or pos != 0")
