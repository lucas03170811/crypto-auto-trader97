# exchange/binance_client.py
import os
import asyncio
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
from typing import Dict, Any, Optional
import pandas as pd
from binance.um_futures import UMFutures

getcontext().prec = 28

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        key = api_key or os.getenv("BINANCE_API_KEY") or os.getenv("API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET") or os.getenv("API_SECRET")
        base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=key, secret=secret, base_url=base)
        self._exchange_info = None  # lazy cache: full exchange info
        self._symbol_info: Dict[str, Dict[str, Any]] = {}  # parsed per-symbol filters
        self._dual_side: Optional[bool] = None

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    # ----------------- Market Data -----------------
    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(res, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","quote_asset_volume","num_trades",
                "taker_buy_base_vol","taker_buy_quote_vol","ignore"
            ])
            for col in ["open","high","low","close","volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        except Exception as e:
            print(f"[ERROR] klines {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            tick = await self._run(self.client.ticker_price, symbol=symbol)
            if isinstance(tick, dict):
                return float(tick.get("price") or tick.get("p") or 0.0)
            if isinstance(tick, (str, float, int)):
                return float(tick)
            info = await self._run(self.client.ticker_24hr, symbol=symbol)
            return float(info.get("lastPrice") or info.get("lastprice") or 0.0)
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    # ----------------- Account/Exchange Info -----------------
    async def _load_exchange_info(self):
        if self._exchange_info is None:
            self._exchange_info = await self._run(self.client.exchange_info)
        return self._exchange_info

    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Return per-symbol filters: stepSize, minQty, maxQty, minNotional, qtyPrecision."""
        sym = symbol.upper()
        if sym in self._symbol_info:
            return self._symbol_info[sym]

        ex = await self._load_exchange_info()
        data = {}
        for s in ex.get("symbols", []):
            if s.get("symbol") == sym:
                data["quantityPrecision"] = int(s.get("quantityPrecision", s.get("baseAssetPrecision", 6)))
                step = Decimal("0.000001")
                min_qty = Decimal("0")
                max_qty = Decimal("1000000000")
                min_notional = Decimal("5")

                for f in s.get("filters", []):
                    ftype = f.get("filterType")
                    if ftype in ("MARKET_LOT_SIZE", "LOT_SIZE"):
                        step = Decimal(str(f.get("stepSize", "0.000001")))
                        min_qty = Decimal(str(f.get("minQty", "0")))
                        max_qty = Decimal(str(f.get("maxQty", "1000000000")))
                    elif ftype in ("NOTIONAL","MIN_NOTIONAL"):
                        mn = f.get("minNotional") or f.get("notional")
                        if mn is not None:
                            min_notional = Decimal(str(mn))
                data.update(stepSize=step, minQty=min_qty, maxQty=max_qty, minNotional=min_notional)
                self._symbol_info[sym] = data
                break

        if sym not in self._symbol_info:
            self._symbol_info[sym] = dict(
                quantityPrecision=6, stepSize=Decimal("0.000001"),
                minQty=Decimal("0"), maxQty=Decimal("1000000000"), minNotional=Decimal("5")
            )
        return self._symbol_info[sym]

    async def get_dual_side(self) -> bool:
        """True => Hedge mode (dualSidePosition), False => One-way. Cache result."""
        if self._dual_side is not None:
            return self._dual_side
        try:
            res = await self._run(self.client.get_position_mode)
            self._dual_side = bool(res.get("dualSidePosition") in (True, "true", "TRUE"))
        except Exception:
            try:
                acc = await self._run(self.client.account)
                self._dual_side = bool(acc.get("dualSidePosition") in (True, "true", "TRUE"))
            except Exception:
                self._dual_side = False
        return self._dual_side

    async def set_leverage(self, symbol: str, leverage: int = 10):
        try:
            await self._run(self.client.change_leverage, symbol=symbol, leverage=leverage)
        except Exception as e:
            print(f"[WARN] set_leverage {symbol} -> {leverage} failed: {e}")

    async def get_position_amt(self, symbol):
        try:
            risks = await self._run(self.client.get_position_risk)
            for r in risks:
                if r.get("symbol") == symbol:
                    amt = r.get("positionAmt") or r.get("positionamt") or 0
                    return float(amt)
        except Exception as e:
            print(f"[ERROR] get_position_amt {symbol}: {e}")
        return 0.0

    # ----------------- Order helpers -----------------
    @staticmethod
    def _ceil_to_step(qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        return ((qty / step).to_integral_value(rounding=ROUND_UP)) * step

    @staticmethod
    def _floor_to_step(qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        return ((qty / step).to_integral_value(rounding=ROUND_DOWN)) * step

    def _apply_precision(self, qty: Decimal, precision: int) -> Decimal:
        if precision < 0:
            precision = 0
        fmt = Decimal(10) ** (-precision)
        return qty.quantize(fmt, rounding=ROUND_DOWN)

    async def adjust_market_qty(self, symbol: str, target_usd: Decimal, price: float) -> Decimal:
        info = await self.get_symbol_info(symbol)
        step = info["stepSize"]
        min_qty = info["minQty"]
        min_notional = info["minNotional"]
        precision = info["quantityPrecision"]

        p = Decimal(str(price))
        need_usd = max(target_usd, (min_notional * Decimal("1.02")))
        raw = need_usd / p

        qty = self._ceil_to_step(raw, step)
        if qty < step:
            qty = step

        if qty < min_qty:
            qty = self._ceil_to_step(min_qty, step)

        if (qty * p) < min_notional:
            qty = self._ceil_to_step(min_notional / p, step)

        qty = self._apply_precision(qty, precision)

        if qty <= 0:
            qty = step

        return qty

    async def new_market_order(self, symbol: str, side: str, quantity: Decimal):
        try:
            params = dict(symbol=symbol, side=side.upper(), type="MARKET", quantity=str(quantity))
            if await self.get_dual_side():
                pass  # hedge mode: omit positionSide to reduce -4061
            else:
                params.pop("positionSide", None)

            resp = await self._run(self.client.new_order, **params)
            oid = resp.get("orderId") if isinstance(resp, dict) else "ok"
            print(f"[ORDER OK] {symbol} {side} qty={quantity} -> {oid}")
            return resp
        except Exception as e:
            print(f"[ERROR] new_market_order {symbol} {side} qty={quantity}: {e}")
            return None
