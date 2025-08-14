# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
from config import (
    EQUITY_RATIO,
    BASE_QTY,
    MAX_LOSS_PCT,
    TRAIL_GIVEBACK_PCT
)

getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio=EQUITY_RATIO):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio))

    async def get_order_qty(self, symbol: str, min_qty: float = BASE_QTY) -> float:
        """
        計算下單數量，自動補足到 minNotional 要求
        """
        equity = await self.client.get_equity()
        price = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0

        usdt_amount = Decimal(str(equity)) * self.equity_ratio
        raw_qty = usdt_amount / Decimal(str(price))

        # 查詢交易對的最小下單單位與最小名義價值
        info = await self.client.get_symbol_info(symbol)
        step_size = Decimal("0.0001")
        min_notional = Decimal("5")  # 預設值
        if info and "filters" in info:
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    step_size = Decimal(f["stepSize"])
                elif f["filterType"] == "MIN_NOTIONAL":
                    min_notional = Decimal(f["notional"])

        # 對齊交易所允許的小數位
        precision = abs(step_size.as_tuple().exponent)
        qty = raw_qty.quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN)

        # 如果不達到 minNotional，則自動補足
        if (Decimal(str(price)) * qty) < min_notional:
            qty = (min_notional / Decimal(str(price))).quantize(
                Decimal(f"1.{'0'*precision}"), rounding=ROUND_DOWN
            )

        qty_f = float(qty)
        return qty_f if qty_f >= min_qty else 0.0

    async def check_stop_conditions(self, symbol: str, entry_price: float, side: str):
        """
        檢查移動停損與最大虧損停損
        """
        current_price = await self.client.get_price(symbol)
        if current_price <= 0:
            return False

        price_change = (current_price - entry_price) / entry_price
        if side.lower() == "short":
            price_change = -price_change

        # 最大虧損停損
        if price_change <= -MAX_LOSS_PCT:
            print(f"[STOP LOSS] {symbol} hit max loss {MAX_LOSS_PCT*100:.1f}%")
            return True

        # 移動停損
        if price_change > 0:
            peak_profit = price_change
            if price_change <= (peak_profit - TRAIL_GIVEBACK_PCT):
                print(f"[TRAIL STOP] {symbol} profit retraced {TRAIL_GIVEBACK_PCT*100:.1f}% from peak")
                return True

        return False
