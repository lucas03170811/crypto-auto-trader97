import asyncio
from strategies.trend_signal import trend_signal
from strategies.revert_signal import revert_signal
from filters.symbol_filter import SymbolFilter

class HedgeEngine:
    def __init__(self, client):
        self.client = client
        self.filter = SymbolFilter(client)

    async def run(self):
        while True:
            approved = await self.filter.shortlist()
            print(f"[INFO] 符合條件的幣種: {approved}", flush=True)

            for symbol in approved:
                df = await self.client.get_klines(symbol)
                trend_long, trend_short, adx = trend_signal(df)
                revert_long, revert_short, rsi, bb_pos = revert_signal(df)

                if trend_long or revert_long:
                    print(f"✅ 做多訊號 {symbol} | ADX={adx:.2f} RSI={rsi:.2f}", flush=True)
                    # TODO: 實作做多下單邏輯
                elif trend_short or revert_short:
                    print(f"🔻 做空訊號 {symbol} | ADX={adx:.2f} RSI={rsi:.2f}", flush=True)
                    # TODO: 實作做空下單邏輯

            print("等待 60 秒...", flush=True)
            await asyncio.sleep(60)
