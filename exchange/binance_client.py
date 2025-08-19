# exchange/binance_client.py
import os
import asyncio
import traceback
from decimal import Decimal, getcontext, ROUND_DOWN, ROUND_UP

import pandas as pd
from binance.um_futures import UMFutures

getcontext().prec = 28

def D(x) -> Decimal:
    return Decimal(str(x))

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet=False, dual_side=False):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=key, secret=secret, base_url=base)
        self.symbol_meta = {}
        self.dual_side = dual_side
        # 同步抓一次 exchange_info（若失敗則使用預設）
        try:
            self._bootstrap_sync()
        except Exception as e:
            print(f"[WARN] bootstrap exchange info fail: {e}")

    # ---------- util ----------
    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    def _ceil_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        steps = (qty / step).to_integral_value(rounding=ROUND_UP)
        return steps * step

    def _floor_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        steps = (qty / step).to_integral_value(rounding=ROUND_DOWN)
        return steps * step

    def _meta_precimals(self, step: Decimal) -> int:
        # 計算 stepSize 小數位數，例如 0.001 -> 3
        s = format(step.normalize(), 'f')
        if '.' in s:
            return len(s.split('.')[1])
        return 0

    # ---------- bootstrap ----------
    def _bootstrap_sync(self):
        info = self.client.exchange_info()
        for s in info.get("symbols", []):
            sym = s.get("symbol")
            filters = {f["filterType"]: f for f in s.get("filters", [])}
            lot = filters.get("LOT_SIZE", {})
            pricef = filters.get("PRICE_FILTER", {})
            mn = filters.get("MIN_NOTIONAL", {})
            step = D(lot.get("stepSize", "0"))
            min_qty = D(lot.get("minQty", "0"))
            tick = D(pricef.get("tickSize", "0"))
            min_notional = D(mn.get("notional", "5"))
            self.symbol_meta[sym] = {
                "step": step,
                "min_qty": min_qty,
                "tick": tick,
                "min_notional": min_notional,
                "prec": self._meta_precimals(step),
            }
        # 切換倉位模式（盡量設單向或雙向依你設定）
        try:
            self.client.change_position_mode(dualSidePosition="true" if self.dual_side else "false")
        except Exception:
            pass

    def get_symbol_meta(self, symbol: str):
        return self.symbol_meta.get(symbol, {
            "step": D("0.0001"),
            "min_qty": D("0.0001"),
            "tick": D("0.01"),
            "min_notional": D("5"),
            "prec": 4
        })

    def get_min_notional(self, symbol: str):
        return self.get_symbol_meta(symbol)["min_notional"]

    # ---------- market data ----------
    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            res = await self._run(self.client.klines, symbol, interval, limit)
        except TypeError:
            res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None
        try:
            df = pd.DataFrame(res, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","quote_asset_volume","num_trades",
                "taker_buy_base_vol","taker_buy_quote_vol","ignore"
            ])
        except Exception:
            df = pd.DataFrame(res)
        for col in ("close","high","low","volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    async def get_price(self, symbol):
        # 嘗試多個 endpoint（容錯）
        try:
            t = await self._run(self.client.ticker_price, symbol)
            # tick 可能為 dict / list / string
            if isinstance(t, dict) and "price" in t:
                return float(t["price"])
            if isinstance(t, (list, tuple)):
                for e in t:
                    if isinstance(e, dict) and e.get("symbol") == symbol and "price" in e:
                        return float(e["price"])
            if isinstance(t, str) or isinstance(t, (int,float)):
                try:
                    return float(t)
                except Exception:
                    pass
        except Exception:
            pass
        # fallback mark price
        try:
            mk = await self._run(self.client.mark_price, symbol)
            if isinstance(mk, dict) and "markPrice" in mk:
                return float(mk["markPrice"])
        except Exception:
            pass
        # fallback 24hr ticker
        try:
            t24 = await self._run(self.client.ticker_24hr, symbol)
            if isinstance(t24, dict):
                if "lastPrice" in t24:
                    return float(t24["lastPrice"])
                if "weightedAvgPrice" in t24:
                    return float(t24["weightedAvgPrice"])
        except Exception:
            pass

        print(f"[ERROR] get_price {symbol}: 無法取得價格 or key missing")
        return 0.0

    # ---------- account ----------
    async def get_equity(self):
        try:
            bal = await self._run(self.client.balance)
            for b in bal:
                if b.get("asset") == "USDT":
                    return float(b.get("balance", 0))
        except Exception as e:
            print(f"[ERROR] get_equity: {e}")
        return 0.0

    async def get_position(self, symbol):
        try:
            res = await self._run(self.client.get_position_risk)
            for p in res:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0))
        except TypeError:
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

    # ---------- qty adjust & format ----------
    def adjust_quantity(self, symbol: str, target_notional_usdt: Decimal, price: Decimal) -> Decimal:
        meta = self.get_symbol_meta(symbol)
        step = meta["step"]
        min_qty = meta["min_qty"]
        min_notional = meta["min_notional"]

        if price <= 0:
            return D("0")

        # Make sure target notional as Decimal
        target_notional = D(target_notional_usdt)
        if target_notional < min_notional:
            target_notional = min_notional

        raw_qty = (target_notional / D(price))
        # ceil to step so that notional >= target_notional
        qty = self._ceil_to_step(raw_qty, step)
        if qty < min_qty:
            qty = min_qty

        # Final safety check: if still not reach min_notional, increase
        if (D(price) * qty) < min_notional:
            need = (min_notional / D(price))
            qty = self._ceil_to_step(need, step)
            if qty < min_qty:
                qty = min_qty

        # If qty still zero or extremely small -> cancel
        if qty <= 0:
            print(f"[ADJUST] {symbol} qty 對齊後為 0，取消下單（step={step})")
            return D("0")

        # Quantize to allowed decimal places (avoid precision error)
        prec = meta.get("prec", self._meta_precimals(step))
        quant = Decimal(1).scaleb(-prec)  # e.g. prec=3 -> Decimal('0.001')
        try:
            qty = qty.quantize(quant, rounding=ROUND_DOWN)  # ensure not exceed allowed precision
            # After rounding down, make sure notional still >= min_notional; if not, then ceil up one step
            if (D(price) * qty) < min_notional:
                qty = self._ceil_to_step(qty + quant, step)
        except Exception:
            pass

        if qty <= 0:
            print(f"[ADJUST] {symbol} qty 結果為 0 (after quantize) -> cancel")
            return D("0")

        return qty

    def _format_qty(self, qty: Decimal, symbol: str) -> str:
        meta = self.get_symbol_meta(symbol)
        prec = meta.get("prec", 8)
        fmt = f"{{0:.{prec}f}}"
        # Avoid scientific notation: format into fixed decimals, then strip trailing zeros
        s = fmt.format(float(qty))
        s = s.rstrip('0').rstrip('.') if '.' in s else s
        return s

    # ---------- orders ----------
    async def open_long(self, symbol, qty: Decimal):
        try:
            qty_s = self._format_qty(qty, symbol)
            resp = await self._run(self.client.new_order,
                                   symbol=symbol, side="BUY", type="MARKET", quantity=qty_s)
            print(f"[ORDER OK] LONG {symbol} qty={qty_s} resp={resp}")
            return resp
        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            traceback.print_exc()
            return None

    async def open_short(self, symbol, qty: Decimal):
        try:
            qty_s = self._format_qty(qty, symbol)
            resp = await self._run(self.client.new_order,
                                   symbol=symbol, side="SELL", type="MARKET", quantity=qty_s)
            print(f"[ORDER OK] SHORT {symbol} qty={qty_s} resp={resp}")
            return resp
        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            traceback.print_exc()
            return None

    async def close(self):
        pass
