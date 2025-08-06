import aiohttp
import pandas as pd
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
import asyncio
import os

class BinanceClient:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.client = UMFutures(
            key=os.getenv("BINANCE_API_KEY"),
            secret=os.getenv("BINANCE_API_SECRET"),
            session=self.session,
            base_url="https://testnet.binancefuture.com" if os.getenv("TESTNET") == "1" else "https://fapi.binance.com"
        )

    async def get_klines(self, symbol, interval="15m", limit=100):
        loop = asyncio.get_running_loop()
        klines = await loop.run_in_executor(None, lambda: self.client.klines(symbol=symbol, interval=interval, limit=limit))
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        return df

    async def close(self):
        await self.session.close()
