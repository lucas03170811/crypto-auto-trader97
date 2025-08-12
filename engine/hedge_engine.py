# engine/hedge_engine.py
import asyncio
from strategies.filter import filter_symbols
from strategies.trend import generate_trend_signal
from strategies.revert import generate_revert_signal

class HedgeEngine:
    def __init__(self, client, risk_mgr):
        self.client = client
        self.risk_mgr = risk_mgr

    async def run(self):
        print("[Engine] Running scan...")
        symbols = await filter_symbols(self.client)
        print(f"[Engine] Filtered: {symbols}")

        for symbol in symbols:
            df = await self.client.get_klines(symbol)
            if df is None or len(df) < 30:
                print(f"[SKIP] No valid data for {symbol}")
                continue

            trend_sig = generate_trend_signal(df)
            revert_sig = generate_revert_signal(df)

            signal = trend_sig or revert_sig

            if signal:
                print(f"[SIGNAL] {symbol} -> {signal}")
                await self.risk_mgr.execute_trade(symbol, signal)
            else:
                print(f"[NO SIGNAL] {symbol} no entry")
