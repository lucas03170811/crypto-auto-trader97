# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio))

    async def get_order_qty(self, symbol: str, min_qty: float = 0.0) -> float:
        equity = await self.client.get_equity()
        price = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0

        usdt_amount = Decimal(str(equity)) * self.equity_ratio
        raw_qty = usdt_amount / Decimal(str(price))

        # 取得交易對的最小單位 (stepSize)
        info = await self.client.get_symbol_info(symbol)
        step_size = Decimal("0.0001")  # default
        if info and "filters" in info:
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    step_size = Decimal(f["stepSize"])
                    break

        # 截斷到允許的最大小數位
        precision = abs(step_size.as_tuple().exponent)
        qty = raw_qty.quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN)

        qty_f = float(qty)
        return qty_f if qty_f >= min_qty else 0.0
