# risk/risk_mgr.py
from decimal import Decimal
from config import BASE_QTY_USD, DEFAULT_LEVERAGE

class RiskManager:
    def __init__(self, client):
        self.client = client

    async def _ensure_leverage(self, symbol: str):
        await self.client.set_leverage(symbol, DEFAULT_LEVERAGE)

    async def execute_trade(self, symbol: str, signal: str):
        price = await self.client.get_price(symbol)
        if not price or price <= 0:
            print(f"[SKIP] {symbol} 無法取得價格")
            return

        await self._ensure_leverage(symbol)

        target_usd = BASE_QTY_USD
        qty = await self.client.adjust_market_qty(symbol, target_usd, price)

        info = await self.client.get_symbol_info(symbol)
        if (qty * Decimal(str(price))) < info["minNotional"]:
            qty = await self.client.adjust_market_qty(symbol, info["minNotional"]*Decimal("1.05"), price)

        if qty <= 0:
            print(f"[SKIP] {symbol} qty 無效")
            return

        side = "BUY" if signal == "long" else "SELL"
        print(f"[TRADE] {symbol} {side} qty={qty} (price≈{price})")
        await self.client.new_market_order(symbol, side, qty)
