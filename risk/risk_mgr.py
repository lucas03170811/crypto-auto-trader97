# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio))

    async def get_order_qty(self, symbol: str, min_qty: float = 0.0) -> float:
        equity = await self.client.get_equity()
        price  = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0
        usdt_amount = Decimal(str(equity)) * self.equity_ratio
        qty = (usdt_amount / Decimal(str(price))).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        qf = float(qty)
        return qf if qf >= min_qty else 0.0
