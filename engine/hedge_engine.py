import asyncio
from strategies.trend import generate_trend_signal  # ✅ 改成 strategies
from strategies.revert import generate_revert_signal  # ✅ 改成 strategies
from strategies.filter import filter_symbols  # ✅ 改成 strategies

class HedgeEngine:
    def __init__(self, client, risk_mgr):
        self.client = client
        self.risk_mgr = risk_mgr

    async def run(self):
        print("[Engine] Running scan...")
        symbols = await filter_symbols(self.client)
        print(f"[Engine] Filtered symbols: {symbols}")

        for symbol in symbols:
            data = await self.client.get_klines(symbol)
            if data is None or len(data) < 50:
                print(f"[SKIP] No valid data for {symbol}")
                continue

            trend_signal = generate_trend_signal(data)
            revert_signal = generate_revert_signal(data)

            signal = trend_signal or revert_signal

            if signal:
                print(f"[SIGNAL] {symbol} -> {signal}")
                await self.risk_mgr.execute_trade(symbol, signal)
            else:
                print(f"[NO SIGNAL] {symbol} passed filter but no entry signal")

        return symbols
