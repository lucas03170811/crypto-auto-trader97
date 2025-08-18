# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
import config

getcontext().prec = 18

class RiskManager:
    def __init__(self, client, equity_ratio: float = None):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio if equity_ratio is not None else config.EQUITY_RATIO))

    async def get_order_qty(self, symbol: str, min_qty: float = 0.0) -> float:
        """
        Compute order qty (float) that:
          - uses the larger of BASE_QTY_USD or equity * equity_ratio (so you get reasonable size)
          - aligns to stepSize
          - ensures notional >= exchange min_notional (or per-symbol override)
          - returns 0.0 if resulting qty < min_qty
        """
        equity = await self.client.get_equity()
        try:
            equity_d = Decimal(str(equity))
        except Exception:
            equity_d = Decimal("0")

        # desired USD notional: either fixed BASE_QTY_USD or equity_ratio portion
        base_usd = Decimal(str(config.BASE_QTY_USD))
        desire_by_ratio = (equity_d * self.equity_ratio) if equity_d > 0 else base_usd
        desired_usd = max(base_usd, desire_by_ratio)

        price = await self.client.get_price(symbol)
        if price <= 0:
            return 0.0
        price_d = Decimal(str(price))

        # raw qty to achieve desired_usd
        raw_qty = desired_usd / price_d

        # adjust to meet min notional and steps
        adjusted_qty = await self.client.adjust_qty_for_min_notional(symbol, float(raw_qty))

        # enforce min_qty (e.g. BASE_QTY absolute minimal qty)
        if adjusted_qty is None:
            return 0.0
        if float(adjusted_qty) < float(min_qty):
            # qty too small to place a valid order
            return 0.0

        return float(adjusted_qty)
