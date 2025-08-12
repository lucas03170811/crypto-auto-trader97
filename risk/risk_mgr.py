# risk/risk_mgr.py
from config import EQUITY_RATIO_PER_TRADE, MIN_NOTIONAL
from decimal import Decimal

class RiskManager:
    def __init__(self, client):
        self.client = client
        # 若 config 裡是 Decimal，轉 float
        try:
            self.equity_ratio = float(EQUITY_RATIO_PER_TRADE)
        except Exception:
            self.equity_ratio = 0.03

    async def get_order_qty(self, symbol):
        equity = await self.client.get_equity()
        equity = float(equity)
        usdt_amount = equity * self.equity_ratio
        price = await self.client.get_price(symbol)
        if not price or price <= 0:
            return 0.0
        qty = usdt_amount / price
        return round(qty, 3)

    async def get_nominal_value(self, symbol, qty):
        price = await self.client.get_price(symbol)
        return float(price) * float(qty)

    async def check_exit_conditions(self, symbol):
        # placeholder: 可依照 PnL 或價格觸發 平倉
        return
