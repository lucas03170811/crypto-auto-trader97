import aiohttp
import pandas as pd
from datetime import datetime

class BinanceClient:
    BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def get_klines(self, symbol, interval, limit=200):
        url = f"{self.BASE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            df = pd.DataFrame(data, columns=[
                "time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df

    async def place_order(self, symbol, side, quantity):
        # 測試版本 — 真實下單需加 API Key 與簽名
        print(f"[ORDER] {side} {quantity} {symbol}")

    async def close(self):
        await self.session.close()
