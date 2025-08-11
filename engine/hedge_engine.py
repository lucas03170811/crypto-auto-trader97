import asyncio
from strategies.trend_signal import trend_signal

class HedgeEngine:
    def __init__(self, client):
        self.client = client

    async def run(self):
        while True:
            try:
                symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]  # 可自行擴充交易對
                for symbol in symbols:
                    df = await self.client.get_klines(symbol, "15m", limit=200)
                    if df is not None and trend_signal(df):
                        print(f"[SIGNAL] {symbol} 發現交易信號，準備下單")
                        await self.client.place_order(symbol, side="BUY", quantity=0.01)  # 測試用數量

                await asyncio.sleep(60)  # 每 1 分鐘檢查一次
            except Exception as e:
                print(f"執行錯誤: {e}")
                await asyncio.sleep(5)
