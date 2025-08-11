# exchange/binance_client.py
import os
import asyncio
from decimal import Decimal
import pandas as pd
from binance.um_futures import UMFutures
from typing import Optional
import traceback

from config import TESTNET

# 若你使用 testnet，請在環境變數設定 TESTNET=1 並 key/secret 為 testnet 的
BASE_URL = "https://testnet.binancefuture.com" if TESTNET else "https://fapi.binance.com"

class BinanceClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        # UMFutures is synchronous/blocking, we'll wrap calls in run_in_executor
        self.client = UMFutures(key=key, secret=secret, base_url=BASE_URL)

    async def _run_block(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 200) -> Optional[pd.DataFrame]:
        try:
            res = await self._run_block(self.client.klines, symbol, interval, limit)
            # res is list of lists
            df = pd.DataFrame(res, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","quote_asset_volume","num_trades",
                "taker_buy_base","taker_buy_quote","ignore"
            ])
            df["open"] = pd.to_numeric(df["open"])
            df["high"] = pd.to_numeric(df["high"])
            df["low"] = pd.to_numeric(df["low"])
            df["close"] = pd.to_numeric(df["close"])
            df["volume"] = pd.to_numeric(df["volume"])
            return df
        except Exception as e:
            print(f"[KLINE ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def get_price(self, symbol: str) -> Optional[float]:
        try:
            res = await self._run_block(self.client.ticker_price, symbol)
            return float(res.get("price", 0))
        except Exception as e:
            print(f"[PRICE ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def get_position(self, symbol: str) -> float:
        """回傳該 symbol 當前淨持倉數量（正：多，負：空，0：無持倉）"""
        try:
            res = await self._run_block(self.client.position_information, symbol)
            # position_information returns list (might be single dict)
            if isinstance(res, list):
                for p in res:
                    if p.get("symbol") == symbol:
                        return float(p.get("positionAmt", 0))
            elif isinstance(res, dict):
                return float(res.get("positionAmt", 0))
        except Exception as e:
            print(f"[POSITION ERROR] {symbol}: {e}")
            traceback.print_exc()
        return 0.0

    async def open_long(self, symbol: str, qty: float, positionSide: Optional[str] = None):
        params = {"symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": qty}
        if positionSide:
            params["positionSide"] = positionSide
        try:
            res = await self._run_block(self.client.new_order, **params)
            print(f"[ORDER] LONG {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[OPEN LONG ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def open_short(self, symbol: str, qty: float, positionSide: Optional[str] = None):
        params = {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": qty}
        if positionSide:
            params["positionSide"] = positionSide
        try:
            res = await self._run_block(self.client.new_order, **params)
            print(f"[ORDER] SHORT {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[OPEN SHORT ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def get_equity(self) -> float:
        try:
            bal = await self._run_block(self.client.balance)
            # find USDT
            if isinstance(bal, list):
                for b in bal:
                    if b.get("asset") == "USDT":
                        return float(b.get("balance", 0))
            elif isinstance(bal, dict):
                if bal.get("asset") == "USDT":
                    return float(bal.get("balance", 0))
        except Exception as e:
            print(f"[EQUITY ERROR]: {e}")
            traceback.print_exc()
        return 0.0
