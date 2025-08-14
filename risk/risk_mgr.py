# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio))

    async def get_order_qty(self, symbol: str) -> float:
        equity = await self.client.get_equity()
        price = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0

        usdt_amount = Decimal(str(equity)) * self.equity_ratio
        raw_qty = usdt_amount / Decimal(str(price))

        # 取得交易對的 stepSize & minNotional
        info = await self.client.get_symbol_info(symbol)
        step_size = Decimal("0.0001")  # 預設精度
        min_notional = Decimal("5")    # 預設 5 USDT
        if info and "filters" in info:
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    step_size = Decimal(f["stepSize"])
                elif f["filterType"] == "MIN_NOTIONAL":
                    min_notional = Decimal(f["notional"])

        # 截斷精度
        precision = abs(step_size.as_tuple().exponent)
        qty = raw_qty.quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN)

        # 檢查名義價值
        if Decimal(str(price)) * qty < min_notional:
            print(f"[RISK] qty too small for {symbol} (notional < {min_notional})")
            return 0.0

        return float(qty)
