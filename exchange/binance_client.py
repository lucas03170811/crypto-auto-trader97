# exchange/binance_client.py
import os
import asyncio
import traceback
import pandas as pd
from decimal import Decimal
from binance.um_futures import UMFutures

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        # UMFutures is synchronous — we will call it inside run_in_executor
        self.client = UMFutures(key=key, secret=secret, base_url=base)

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            res = await self._run(self.client.klines, symbol, interval, limit)
            # res is list of lists (like Binance)
            df = pd.DataFrame(res, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "num_trades",
                "taker_buy_base_vol", "taker_buy_quote_vol", "ignore"
            ])
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            return df
        except TypeError as e:
            # different UMFutures signature — try calling with kwargs
            try:
                res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
                df = pd.DataFrame(res)
                return df
            except Exception as e2:
                print(f"[ERROR] Failed to fetch klines for {symbol}: {e2}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            tick = await self._run(self.client.ticker_price, symbol)
            return float(tick.get("price") if isinstance(tick, dict) else tick)
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol):
        try:
            # get_position_risk returns list — filter by symbol
            res = await self._run(self.client.get_position_risk)
            for p in res:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0))
        except TypeError:
            # some versions expect symbol param
            try:
                res = await self._run(self.client.get_position_risk, symbol)
                for p in res:
                    if p.get("symbol") == symbol:
                        return float(p.get("positionAmt", 0))
            except Exception as e:
                print(f"[ERROR] get_position {symbol}: {e}")
        except Exception as e:
            print(f"[ERROR] get_position {symbol}: {e}")
        return 0.0

    async def get_equity(self):
        try:
            bal = await self._run(self.client.balance)
            for b in bal:
                if b.get("asset") == "USDT":
                    return float(b.get("balance", 0))
        except Exception as e:
            print(f"[ERROR] get_equity: {e}")
        return 0.0

    async def open_long(self, symbol, qty, positionSide=None):
        try:
            params = {"symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": qty}
            if positionSide:
                params["positionSide"] = positionSide
            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] LONG {symbol} qty={qty} resp={resp}")
            return resp
        except Exception as e:
            print(f"[OPEN LONG ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def open_short(self, symbol, qty, positionSide=None):
        try:
            params = {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": qty}
            if positionSide:
                params["positionSide"] = positionSide
            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] SHORT {symbol} qty={qty} resp={resp}")
            return resp
        except Exception as e:
            print(f"[OPEN SHORT ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def close(self):
        # UMFutures has no async close; nothing to do
        pass
