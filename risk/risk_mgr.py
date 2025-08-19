# risk/risk_mgr.py
import asyncio
from decimal import Decimal
from config import BASE_QTY, BASE_QTY_USD, MIN_NOTIONAL, EQUITY_RATIO_PER_TRADE

class RiskManager:
    def __init__(self, client):
        self.client = client
        # use float equity ratio internally to avoid Decimal*float issues in earlier errors
        self.equity_ratio = float(EQUITY_RATIO_PER_TRADE)
        self.base_qty_usd = float(BASE_QTY_USD)

    async def get_order_qty(self, symbol):
        """Estimate quantity to order (simple): use base_qty_usd or equity_ratio."""
        equity = await self.client.get_equity()
        if equity and equity > 0:
            usdt_amount = max(self.base_qty_usd, equity * self.equity_ratio)
        else:
            usdt_amount = self.base_qty_usd

        price = await self.client.get_price(symbol)
        if not price or price <= 0:
            return 0.0
        qty = usdt_amount / price
        # round to 6 decimals safe default (later adjust per-asset in production)
        return round(qty, 6)

    async def get_nominal_value(self, symbol, qty):
        price = await self.client.get_price(symbol)
        return float(price * qty)

    async def update_equity(self):
        eq = await self.client.get_equity()
        print(f"[Equity] Current equity: {eq:.6f} USDT")
        return eq

    async def execute_trade(self, symbol, signal):
        """Signal is 'long' or 'short'"""
        signal = signal.lower()
        pos = await self.client.get_position(symbol)
        print(f"[Position] {symbol}: {pos}")
        try:
            qty = await self.get_order_qty(symbol)
            if qty <= 0:
                print(f"[RISK] calculated qty 0 for {symbol}, skip")
                return None
            nominal = await self.get_nominal_value(symbol, qty)
            if nominal < float(MIN_NOTIONAL):
                print(f"[SKIP ORDER] {symbol} 名目價值太低: {nominal:.2f} USDT")
                return None

            if signal == "long" and pos <= 0:
                print(f"[Trade] Entering LONG {symbol}")
                return await self.client.open_long(symbol, qty)
            if signal == "short" and pos >= 0:
                print(f"[Trade] Entering SHORT {symbol}")
                return await self.client.open_short(symbol, qty)
        except Exception as e:
            print(f"[TRADE ERROR] {symbol}: {e}")
            return None

    # stub for exit checks (optional advanced logic)
    async def check_exit_conditions(self, symbol):
        # implement TP/SL or time-based exits in production
        return False
