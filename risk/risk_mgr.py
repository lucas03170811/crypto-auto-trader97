from decimal import Decimal
from config import MIN_NOTIONAL

class RiskManager:
    def __init__(self, client, equity_ratio):
        self.client = client
        self.equity_ratio = float(equity_ratio)  # ✅ 強制轉成 float 避免 Decimal 衝突

    async def get_order_qty(self, symbol):
        """計算下單數量"""
        equity = await self.client.get_equity()
        equity = float(equity)  # ✅ 保證是 float

        usdt_amount = equity * self.equity_ratio
        price = await self.get_price(symbol)

        if price <= 0:
            print(f"[ERROR] {symbol} 價格取得失敗，無法計算下單數量")
            return 0

        qty = usdt_amount / price
        qty = round(qty, 3)  # ✅ 保留 3 位小數，防止精度錯誤

        print(f"[RISK] {symbol} equity={equity}, price={price}, qty={qty}")
        return qty

    async def get_nominal_value(self, symbol, qty):
        """計算名目價值（price × qty）"""
        price = await self.get_price(symbol)
        nominal_value = price * qty
        return nominal_value

    async def get_price(self, symbol):
        """取得即時價格"""
        try:
            price = await self.client.get_price(symbol)
            return float(price)
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return 0
