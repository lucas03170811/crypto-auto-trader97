# risk/risk_mgr.py
from decimal import Decimal, getcontext
getcontext().prec = 28

from config import BASE_QTY  # optional if you still want fixed base
from decimal import Decimal

class RiskManager:
    def __init__(self, client, risk_pct: float = 0.02, max_leverage: int = 10):
        self.client = client
        self.risk_pct = Decimal(str(risk_pct))
        self.max_leverage = Decimal(str(max_leverage))

    async def _budget_notional(self) -> Decimal:
        bal = await self.client.get_equity()
        if bal is None:
            return Decimal("0")
        return Decimal(str(bal)) * self.risk_pct * self.max_leverage

    async def validate_and_size(self, symbol: str, price: float) -> Decimal:
        price_d = Decimal(str(price))
        if price_d <= 0:
            print(f"[RISK] {symbol} price invalid: {price}")
            return Decimal("0")

        budget = await self._budget_notional()
        min_notional = self.client.get_min_notional(symbol)
        # 給一點 safety margin
        target = max(budget, min_notional * Decimal("1.05"))

        # ask client to adjust quantity per exchange rules
        qty = self.client.adjust_quantity(symbol, target, price_d)

        if qty <= 0:
            print(f"[RISK] {symbol} qty invalid after adjust -> 0")
            return Decimal("0")

        # final validation
        if (price_d * qty) < min_notional:
            print(f"[RISK] {symbol} final notional too small after adjust -> {(price_d * qty)} < {min_notional}")
            return Decimal("0")

        print(f"[RISK] {symbol}: balance_budget={budget:.4f} target={target:.4f} qty={qty}")
        return qty

    async def execute_trade(self, symbol: str, signal: str):
        # returns order or None
        price = await self.client.get_price(symbol)
        qty = await self.validate_and_size(symbol, price)
        if qty <= 0:
            return None
        if signal.lower() == "long":
            return await self.client.open_long(symbol, qty)
        if signal.lower() == "short":
            return await self.client.open_short(symbol, qty)
        return None
