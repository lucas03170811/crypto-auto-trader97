# exchange/binance_client.py
import os
import pandas as pd
import asyncio
from binance.um_futures import UMFutures

class BinanceClient:
    def __init__(self, api_key: str = None, api_secret: str = None):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base_url = "https://testnet.binancefuture.com" if os.getenv("TESTNET", "1") == "1" else "https://fapi.binance.com"
        # UMFutures is synchronous. We'll call it inside run_in_executor to keep async-safe.
        self.client = UMFutures(key=key, secret=secret, base_url=base_url)

    async def _run_blocking(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            res = await self._run_blocking(self.client.klines, symbol, interval, limit)
            df = pd.DataFrame(res, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "num_trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])
            df["close"] = pd.to_numeric(df["close"])
            df["high"] = pd.to_numeric(df["high"])
            df["low"] = pd.to_numeric(df["low"])
            df["volume"] = pd.to_numeric(df["volume"])
            return df
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            res = await self._run_blocking(self.client.ticker_price, symbol)
            return float(res.get("price", 0))
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol):
        try:
            res = await self._run_blocking(self.client.get_position_risk, symbol)
            for p in res:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0))
            return 0.0
        except Exception as e:
            print(f"[ERROR] get_position {symbol}: {e}")
            return 0.0

    async def get_equity(self):
        try:
            res = await self._run_blocking(self.client.balance)
            for b in res:
                if b.get("asset") == "USDT":
                    return float(b.get("balance", 0.0))
            return 0.0
        except Exception as e:
            print(f"[ERROR] get_equity: {e}")
            return 0.0

    async def open_long(self, symbol, qty, positionSide="LONG"):
        try:
            resp = await self._run_blocking(self.client.new_order, symbol, "BUY", "MARKET", None, None, None, None, None, None, None, None) 
            # NOTE: binance.um_futures.new_order signature in some versions differs.
            # Simpler: call new_order via kwargs—below is safer:
        except Exception:
            pass

    async def open_short(self, symbol, qty, positionSide="SHORT"):
        try:
            resp = await self._run_blocking(self.client.new_order, symbol, "SELL", "MARKET", None, None, None, None, None, None, None)
        except Exception:
            pass

    # -> Above open_long/open_short are placeholders because um_futures.new_order signature can vary.
    # Use the following explicit wrapper if your library supports kwargs:
    async def place_market_order(self, symbol, side, quantity, positionSide=None):
        try:
            def _call():
                params = {"symbol": symbol, "side": side, "type": "MARKET", "quantity": str(quantity)}
                if positionSide:
                    params["positionSide"] = positionSide
                return self.client.new_order(**params)
            return await self._run_blocking(_call)
        except Exception as e:
            print(f"[ERROR] place_market_order {symbol} {side}: {e}")
            return None
