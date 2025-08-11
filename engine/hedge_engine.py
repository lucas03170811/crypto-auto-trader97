# engine/hedge_engine.py
import asyncio
from strategy.signal_generator import SignalGenerator

class HedgeEngine:
    def __init__(self, client, risk_mgr):
        self.client = client
        self.risk_mgr = risk_mgr
        self.sig = SignalGenerator(client)

    async def run(self):
        while True:
            try:
                print("[Engine] Running scan...")
                symbols = await self.sig.get_filtered_symbols()
                print(f"[Engine] Filtered symbols: {symbols}")

                for s in symbols:
                    signal = await self.sig.generate_signal(s)
                    if signal:
                        print(f"[SIGNAL] {s} -> {signal}")
                        await self.risk_mgr.execute_trade(s, signal)
                    else:
                        print(f"[NO SIGNAL] {s} passed filter but no entry signal")

                # print equity
                equity = await self.client.get_equity()
                print(f"[Equity] Current equity: {equity:.2f} USDT")
                await asyncio.sleep(60)

            except Exception as e:
                print(f"[Engine ERROR] {e}")
                await asyncio.sleep(60)
