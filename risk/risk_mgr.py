# risk/risk_mgr.py
import os
from decimal import Decimal
from config import BASE_QTY  # BASE_QTY 表示每次目標的 USDT 名目值，例如 20
from decimal import Decimal

class RiskManager:
    def __init__(self, client, base_qty_usdt=None):
        self.client = client
        # base_qty_usdt：每次想下單的目標 USDT (notional)
        self.base_qty_usdt = Decimal(str(base_qty_usdt)) if base_qty_usdt is not None else Decimal(str(BASE_QTY))

    async def execute_trade(self, symbol, signal):
        """
        signal: 'long' or 'short'
        執行下單：先計算 qty（考慮 step/minNotional），再呼叫 client 開倉。
        """
        signal = signal.lower()
        position = await self.client.get_position(symbol)
        print(f"[Position] {symbol}: {position}")

        # 只在無倉位時進場（你可以改邏輯）
        if position != 0:
            print(f"[SKIP] {symbol} already has position")
            return

        # 計算 qty（回傳 Decimal qty 與實際 notional）
        qty, notional, info = await self.client.calc_qty_from_usdt(symbol, self.base_qty_usdt)
        if qty is None or qty == 0:
            print(f"[SKIP ORDER] {symbol} 名目價值/數量無法對齊或為 0 (notional={notional})")
            return

        min_not = info.get("minNotional")
        if min_not:
            min_not_d = Decimal(str(min_not))
            if Decimal(str(notional)) < min_not_d:
                print(f"[SKIP ORDER] {symbol} 名目價值 {notional} 低於 minNotional {min_not_d}")
                return

        print(f"[Trade] Entering {signal.upper()} {symbol} — qty={qty} notional={notional}")

        try:
            if signal == "long":
                await self.client.open_long(symbol, qty)
            elif signal == "short":
                await self.client.open_short(symbol, qty)
            else:
                print(f"[ERROR] Unknown signal {signal}")
        except Exception as e:
            print(f"[TRADE ERROR] {symbol}: {e}")
