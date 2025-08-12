# risk/risk_mgr.py
from decimal import Decimal
from config import BASE_QTY, MIN_NOTIONAL, EQUITY_RATIO_PER_TRADE

class RiskManager:
    def __init__(self, client):
        self.client = client
        # equity ratio as float
        self.equity_ratio = float(EQUITY_RATIO_PER_TRADE)

    async def execute_trade(self, symbol, signal):
        signal = signal.lower()
        pos = await self.client.get_position(symbol)
        print(f"[Position] {symbol}: {pos}")

        # compute qty via base qty converted to symbol qty (simpler)
        # Option A: use BASE_QTY in USDT to compute qty (BASE_QTY / price)
        price = await self.client.get_price(symbol)
        if price <= 0:
            print(f"[ERROR] Price unavailable for {symbol}")
            return

        # order qty computed from BASE_QTY USDT
        qty = float(Decimal(BASE_QTY) / Decimal(str(price)))
        qty = round(qty, 3)
        notional = price * qty

        if Decimal(str(notional)) < MIN_NOTIONAL:
            print(f"[SKIP ORDER] {signal.upper()} {symbol} 名目價值太低: {notional:.2f} USDT")
            return

        try:
            if signal == "long" and pos <= 0:
                print(f"[Trade] Entering LONG {symbol}, qty={qty}, notional={notional:.2f}")
                await self.client.open_long(symbol, qty)
            elif signal == "short" and pos >= 0:
                print(f"[Trade] Entering SHORT {symbol}, qty={qty}, notional={notional:.2f}")
                await self.client.open_short(symbol, qty)
            else:
                print(f"[Trade] No action for {symbol} (pos={pos}, signal={signal})")
        except Exception as e:
            print(f"[TRADE ERROR] {symbol}: {e}")
