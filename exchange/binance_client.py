# exchange/binance_client.py
import os
import asyncio
import traceback
from decimal import Decimal, ROUND_DOWN, getcontext
import pandas as pd

# 使用 UMFutures (binance-futures-connector)
from binance.um_futures import UMFutures

# 設高精度計算（量化時用）
getcontext().prec = 18

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=key, secret=secret, base_url=base)

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            res = await self._run(self.client.klines, symbol, interval, limit)
            df = pd.DataFrame(res, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","quote_asset_volume","num_trades",
                "taker_buy_base_vol","taker_buy_quote_vol","ignore"
            ])
            # 強制數值轉換
            for c in ("close","high","low","volume"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            tick = await self._run(self.client.ticker_price, symbol)
            # ticker_price sometimes returns {'symbol':..., 'price': '...'} or a string
            if isinstance(tick, dict):
                return float(tick.get("price", 0))
            try:
                return float(tick)
            except Exception:
                return 0.0
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol):
        try:
            # get_position_risk sometimes accepts no args, sometimes symbol param
            try:
                res = await self._run(self.client.get_position_risk)
            except TypeError:
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

    # ---------------- symbols / filters helpers ----------------
    async def get_symbol_info(self, symbol):
        """return parsed symbol info dict with LOT_SIZE & MIN_NOTIONAL etc."""
        try:
            info = await self._run(self.client.exchange_info)
        except TypeError:
            # fallback name
            try:
                info = await self._run(self.client.get_exchange_info)
            except Exception as e:
                print(f"[ERROR] exchange_info fetch failed: {e}")
                return None

        if not info:
            return None

        symbols = info.get("symbols") if isinstance(info, dict) else None
        if symbols is None:
            # some connector returns a list
            symbols = info

        for s in symbols:
            if s.get("symbol") == symbol:
                # parse filters
                f = {filt["filterType"]: filt for filt in s.get("filters", [])}
                return {
                    "symbol": symbol,
                    "baseAsset": s.get("baseAsset"),
                    "quoteAsset": s.get("quoteAsset"),
                    "tickSize": f.get("PRICE_FILTER", {}).get("tickSize"),
                    "minPrice": f.get("PRICE_FILTER", {}).get("minPrice"),
                    "maxPrice": f.get("PRICE_FILTER", {}).get("maxPrice"),
                    "stepSize": f.get("LOT_SIZE", {}).get("stepSize"),
                    "minQty": f.get("LOT_SIZE", {}).get("minQty"),
                    "minNotional": f.get("MIN_NOTIONAL", {}).get("minNotional")
                }
        return None

    def _decimal_quantize(self, value, step_str):
        """Align Decimal value DOWN to stepSize (step_str like '0.001')."""
        v = Decimal(str(value))
        step = Decimal(str(step_str))
        # determine number of decimals
        exp = -step.as_tuple().exponent
        # quant = Decimal('1e-{exp}')
        quant_str = "1."  # we'll use quantize with rounding
        # compute multiplier
        # Use: quantize to multiple: floor(v / step) * step
        units = (v / step).to_integral_value(rounding=ROUND_DOWN)
        aligned = (units * step).normalize()
        return aligned

    async def calc_qty_from_usdt(self, symbol, usdt_amount):
        """
        given desired USD notional, compute qty aligned to stepSize and check minNotional.
        Returns (qty_decimal, notional_decimal, symbol_info) or (None, None, info) if impossible.
        """
        info = await self.get_symbol_info(symbol)
        if not info:
            print(f"[WARN] No symbol info for {symbol}")
            return None, None, None

        price = await self.get_price(symbol)
        if price is None or price == 0:
            print(f"[WARN] Cannot get price for {symbol}")
            return None, None, info

        price_d = Decimal(str(price))
        usdt_d = Decimal(str(usdt_amount))

        # compute raw qty
        raw_qty = (usdt_d / price_d)
        # align to stepSize
        step = info.get("stepSize") or "1"
        aligned_qty = self._decimal_quantize(raw_qty, step)

        # compute notional with aligned qty
        notional = (aligned_qty * price_d)

        # minNotional check (if present)
        min_not = info.get("minNotional")
        if min_not:
            min_not_d = Decimal(str(min_not))
            if notional < min_not_d:
                # can't place unless you bump up aligned_qty to reach min_notional
                # try to bump aligned_qty up to minimal qty that gives notional >= minNotional
                needed_qty = (min_not_d / price_d)
                # align up by step:
                # units = ceil(needed_qty / step) -> implement by integer division
                step_d = Decimal(str(step))
                units = (needed_qty / step_d).to_integral_value(rounding=ROUND_DOWN)
                if units * step_d < needed_qty:
                    units = units + 1
                bumped_qty = units * step_d
                # ensure bumped_qty respects minQty too
                min_qty = info.get("minQty")
                if min_qty:
                    min_qty_d = Decimal(str(min_qty))
                    if bumped_qty < min_qty_d:
                        bumped_qty = ((min_qty_d / step_d).to_integral_value(rounding=ROUND_DOWN) + 1) * step_d
                aligned_qty = bumped_qty
                notional = aligned_qty * price_d

        # final checks
        if aligned_qty == 0:
            return None, notional, info

        return aligned_qty, notional, info

    # ---------------- placing orders ----------------
    async def place_market_order(self, symbol, side, qty_decimal, positionSide=None):
        """Generic place market order, qty_decimal is Decimal"""
        try:
            qty = float(qty_decimal) if isinstance(qty_decimal, Decimal) else qty_decimal
            params = {"symbol": symbol, "side": side, "type": "MARKET", "quantity": qty}
            if positionSide:
                params["positionSide"] = positionSide
            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] {side} {symbol} qty={qty} resp={resp}")
            return resp
        except Exception as e:
            print(f"[ORDER ERROR] {symbol}: {e}")
            # attempt to print rich error details if present
            try:
                import traceback as _tb
                _tb.print_exc()
            except:
                pass
            return None

    async def open_long(self, symbol, qty_decimal, positionSide=None):
        return await self.place_market_order(symbol, "BUY", qty_decimal, positionSide=positionSide)

    async def open_short(self, symbol, qty_decimal, positionSide=None):
        return await self.place_market_order(symbol, "SELL", qty_decimal, positionSide=positionSide)

    async def close(self):
        # nothing to close for UMFutures (sync client)
        pass
