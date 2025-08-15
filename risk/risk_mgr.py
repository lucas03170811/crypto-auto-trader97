# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
from config import EQUITY_RATIO, MAX_LOSS_PCT, TRAIL_GIVEBACK_PCT

getcontext().prec = 18

class RiskManager:
    def __init__(self, client):
        self.client = client
        self.equity_ratio = Decimal(str(EQUITY_RATIO))

    async def get_order_qty(self, symbol: str, min_qty: float = 0.0) -> float:
        equity = await self.client.get_equity()
        price = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0

        usdt_amount = Decimal(str(equity)) * self.equity_ratio
        raw_qty = usdt_amount / Decimal(str(price))

        info = await self.client.get_symbol_info(symbol)
        step_size = Decimal("0.0001")  # default
        min_notional = Decimal("5.0")  # default

        if info and "filters" in info:
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    step_size = Decimal(f["stepSize"])
                if f["filterType"] == "MIN_NOTIONAL":
                    min_notional = Decimal(f["notional"])

        precision = abs(step_size.as_tuple().exponent)
        qty = raw_qty.quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN)

        # 確保達到最小名義價值
        if qty * Decimal(str(price)) < min_notional:
            qty = (min_notional / Decimal(str(price))).quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN)

        qty_f = float(qty)
        return qty_f if qty_f >= min_qty else 0.0

    def get_stop_loss_price(self, entry_price: float, side: str) -> float:
        """固定止損價格"""
        if side == "LONG":
            return entry_price * (1 - MAX_LOSS_PCT)
        else:
            return entry_price * (1 + MAX_LOSS_PCT)

    def get_trailing_stop_price(self, peak_price: float, side: str) -> float:
        """移動停損價格"""
        if side == "LONG":
            return peak_price * (1 - TRAIL_GIVEBACK_PCT)
        else:
            return peak_price * (1 + TRAIL_GIVEBACK_PCT)
