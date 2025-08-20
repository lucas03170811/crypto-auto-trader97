# exchange/binance_client.py
import asyncio
from typing import Any, List, Optional, Dict
from decimal import Decimal, ROUND_UP, ROUND_DOWN, getcontext
import math
import time

from binance.um_futures import UMFutures

getcontext().prec = 28

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://fapi.binance.com", testnet: bool = False):
        if testnet:
            base_url = "https://testnet.binancefuture.com"
        self.client = UMFutures(api_key, api_secret, base_url=base_url)

    async def _run_sync(self, fn, *args, **kwargs):
        """Run blocking sync function in threadpool."""
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    async def _try_calls(self, callables):
        """Try list of zero-arg callables until one succeeds, return result or raise last."""
        last_exc = None
        for c in callables:
            try:
                return await asyncio.to_thread(c)
            except TypeError as e:
                last_exc = e
                continue
            except Exception as e:
                last_exc = e
                continue
        raise last_exc if last_exc is not None else Exception("Unknown call failure")

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get exchange_info and return symbol entry."""
        try:
            fn = getattr(self.client, "exchange_info", None)
            if not fn:
                return None
            data = await self._run_sync(fn)
            if not data:
                return None
            symbols = data.get("symbols") or data.get("result") or []
            for s in symbols:
                if s.get("symbol") == symbol:
                    return s
        except Exception as e:
            print(f"[ERROR] Failed to get symbol info for {symbol}: {e}")
        return None

    async def _parse_filters(self, symbol_info: dict):
        """Return dict with stepSize (Decimal) and min_notional (Decimal) if available."""
        step_size = Decimal("0.0001")
        min_notional = Decimal("5")  # safe default
        try:
            filters = symbol_info.get("filters", []) if symbol_info else []
            for f in filters:
                t = f.get("filterType") or f.get("type")
                if t == "LOT_SIZE":
                    step_size = Decimal(str(f.get("stepSize", step_size)))
                # futures might use "MIN_NOTIONAL" or "NOTIONAL" etc
                if t in ("MIN_NOTIONAL", "NOTIONAL", "NOTIONAL_FILTER"):
                    # key could be minNotional or notional
                    if "minNotional" in f:
                        min_notional = Decimal(str(f.get("minNotional")))
                    elif "notional" in f:
                        min_notional = Decimal(str(f.get("notional")))
        except Exception as e:
            print(f"[WARN] _parse_filters error: {e}")
        return {"step_size": step_size, "min_notional": min_notional}

    async def get_price(self, symbol: str) -> float:
        """Return last price (float) or 0.0 on fail."""
        try:
            fn = getattr(self.client, "ticker_price", None)
            if not fn:
                return 0.0
            res = await self._run_sync(fn, symbol)
            if isinstance(res, dict):
                return float(res.get("price", 0.0))
            if isinstance(res, list) and res:
                return float(res[0].get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
        return 0.0

    async def get_position(self, symbol: str) -> dict:
        """
        Return position dict for symbol or {}.
        This handles multiple SDK signatures for get_position_risk.
        """
        try:
            # try no-arg (most connectors return a list)
            try:
                pos_list = await self._run_sync(self.client.get_position_risk)
            except TypeError:
                # maybe requires no args but is a bound method that still needs call
                try:
                    pos_list = await self._run_sync(lambda: self.client.get_position_risk())
                except Exception:
                    # try passing symbol explicitly
                    pos_list = await self._run_sync(lambda: self.client.get_position_risk(symbol))
            except Exception:
                # fallback try with symbol
                pos_list = await self._run_sync(lambda: self.client.get_position_risk(symbol))
        except Exception as e:
            print(f"[ERROR] Failed to get position for {symbol}: {e}")
            return {}

        try:
            if isinstance(pos_list, list):
                for p in pos_list:
                    if p.get("symbol") == symbol:
                        return p
            if isinstance(pos_list, dict) and pos_list.get("symbol") == symbol:
                return pos_list
        except Exception as e:
            print(f"[WARN] parsing position list failed: {e}")
        return {}

    async def get_equity(self) -> float:
        try:
            bal = await self._run_sync(self.client.balance)
            if isinstance(bal, list):
                for a in bal:
                    if a.get("asset") == "USDT":
                        return float(a.get("balance", 0.0))
            if isinstance(bal, dict):
                # some responses contain totalWalletBalance etc
                if "totalWalletBalance" in bal:
                    return float(bal.get("totalWalletBalance", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0.0

    # helper: ceil qty to step_size
    def _ceil_qty(self, raw_qty: Decimal, step_size: Decimal) -> Decimal:
        if raw_qty <= 0:
            return Decimal("0")
        # number of steps (ceiling)
        n = (raw_qty / step_size).to_integral_value(rounding=ROUND_UP)
        return (n * step_size).normalize()

    # helper: floor qty to step (if you prefer)
    def _floor_qty(self, raw_qty: Decimal, step_size: Decimal) -> Decimal:
        if raw_qty <= 0:
            return Decimal("0")
        n = (raw_qty / step_size).to_integral_value(rounding=ROUND_DOWN)
        return (n * step_size).normalize()

    async def place_market_order(self, symbol: str, side: str, qty: Optional[float] = None, target_notional: Optional[float] = None, max_retries: int = 1) -> Optional[dict]:
        """
        Place market order.
        - If qty provided, we will align it to stepSize and ensure min_notional by increasing qty (ceil).
        - If target_notional provided (USD), compute qty = target_notional / price and ceil to step size & min_notional.
        - returns order dict or None on failure.
        """
        try:
            symbol_info = await self.get_symbol_info(symbol)
            filters = await self._parse_filters(symbol_info)
            step_size = filters["step_size"]
            min_notional = filters["min_notional"]

            price = await self.get_price(symbol)
            if price <= 0:
                print(f"[ERROR] price invalid for {symbol}: {price}")
                return None

            # compute qty if target_notional given
            if target_notional is not None:
                raw_qty = Decimal(str(target_notional)) / Decimal(str(price))
                qty_d = self._ceil_qty(raw_qty, step_size)
            elif qty is not None:
                qty_d = Decimal(str(qty))
                # ceil to step to avoid too small
                qty_d = self._ceil_qty(qty_d, step_size)
            else:
                print("[ERROR] place_market_order needs qty or target_notional")
                return None

            # ensure min_notional satisfied; if not, increase qty by steps until it's >= min_notional
            notional = (qty_d * Decimal(str(price))).quantize(Decimal("0.00000001"))
            attempts = 0
            while notional < min_notional and attempts < 10:
                # increase by one step
                qty_d = qty_d + step_size
                notional = (qty_d * Decimal(str(price))).quantize(Decimal("0.00000001"))
                attempts += 1

            if qty_d <= 0:
                print(f"[WARN] {symbol} qty after align is 0, cancel order (step={step_size})")
                return None

            # format qty as string without scientific notation
            qty_str = format(qty_d, 'f')

            # try placing order
            try:
                res = await self._run_sync(self.client.new_order, symbol=symbol, side=side, type="MARKET", quantity=qty_str)
                return res
            except Exception as e:
                # if minNotional error, try increase a bit and retry up to max_retries
                err = e
                # naive retry: increment qty by one step and try again
                for i in range(max_retries):
                    qty_d = qty_d + step_size
                    qty_str = format(qty_d, 'f')
                    try:
                        print(f"[WARN] retrying market order {symbol} with qty {qty_str} after error {err}")
                        res = await self._run_sync(self.client.new_order, symbol=symbol, side=side, type="MARKET", quantity=qty_str)
                        return res
                    except Exception as e2:
                        err = e2
                print(f"[ERROR] Failed to place market order {symbol}: {err}")
                return None
        except Exception as e:
            print(f"[ERROR] place_market_order unexpected: {e}")
            return None

    async def open_long(self, symbol: str, qty: Optional[float] = None, target_notional: Optional[float] = None):
        res = await self.place_market_order(symbol, "BUY", qty=qty, target_notional=target_notional)
        if res:
            print(f"[ORDER] Opened LONG {symbol} qty={qty or target_notional} -> {res}")
        else:
            print(f"[ERROR] Failed to open LONG {symbol}")
        return res

    async def open_short(self, symbol: str, qty: Optional[float] = None, target_notional: Optional[float] = None):
        res = await self.place_market_order(symbol, "SELL", qty=qty, target_notional=target_notional)
        if res:
            print(f"[ORDER] Opened SHORT {symbol} qty={qty or target_notional} -> {res}")
        else:
            print(f"[ERROR] Failed to open SHORT {symbol}")
        return res
