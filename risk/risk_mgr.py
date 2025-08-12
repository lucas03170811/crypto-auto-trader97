# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Union

# 提升精度
getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio: Union[float, Decimal]):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio))

    async def get_order_qty(self, symbol: str) -> float:
        """
        計算應下單的數量（回傳 float，方便直接餵給 exchange）。
        假設以現貨等價或合約 qty = (equity * ratio) / price
        """
        equity = await self.client.get_equity()  # float
        equity_d = Decimal(str(equity))
        usdt_amount = (equity_d * self.equity_ratio).quantize(Decimal("0.00000001"))
        price = await self.client.get_price(symbol)  # float
        if price == 0:
            return 0.0
        price_d = Decimal(str(price))
        qty = (usdt_amount / price_d).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        return float(qty)

    async def get_nominal_value(self, symbol: str, qty: float) -> float:
        price = await self.client.get_price(symbol)
        return float(Decimal(str(price)) * Decimal(str(qty)))
