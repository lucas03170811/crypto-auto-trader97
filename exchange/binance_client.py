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
        # UMFutures is synchronous — use run_in_executor wrapper
        self.client = UMFutures(key=key, secret=secret, base_url=base)

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            # try calling as kwargs (some versions accept kwargs)
            try:
                res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
            except TypeError:
                res = await self._run(self.client.klines, symbol, interval, limit)
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
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            try:
                tick = await self._run(self.client.ticker_price, symbol=symbol)
            except TypeError:
                tick = await self._run(self.client.ticker_price, symbol)
            # ticker_price might return {"symbol":..., "price":"..."} or "123.45"
            if isinstance(tick, dict):
                price = tick.get("price") or tick.get("lastPrice") or tick.get("close")
            else:
                price = tick
            return float(price)
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol):
        try:
            # get_position_risk typically returns list
            try:
                res = await self._run(self.client.get_position_risk)
            except TypeError:
                # some versions accept symbol param
                res = await self._run(self.client.get_position_risk, symbol)
            for p in res:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0))
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
