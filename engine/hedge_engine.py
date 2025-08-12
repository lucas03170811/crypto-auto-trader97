# engine/hedge_engine.py
import asyncio
from strategies.signal_generator import SignalGenerator
from risk.risk_mgr import RiskManager

class HedgeEngine:
    def __init__(self, client):
        self.client = client
        self.signal_gen = SignalGenerator(client)
        self.risk_mgr = RiskManager(client)

    async def run(self):
        print("[Engine] Running scan...")
        symbols = await self.signal_gen.get_filtered_symbols()
        print(f"[Engine] Filtered: {symbols}")

        for symbol in symbols:
            df = await self.client.get_klines(symbol)
            if df is None or len(df) < 30:
                print(f"[SKIP] No valid data for {symbol}")
                continue

            signal = await self.signal_gen.generate_signal(symbol)
            if signal:
                print(f"[SIGNAL] {symbol} -> {signal}")
                await self.risk_mgr.execute_trade(symbol, signal)
            else:
                print(f"[NO SIGNAL] {symbol} no entry")
