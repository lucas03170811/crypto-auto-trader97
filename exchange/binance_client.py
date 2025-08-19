# exchange/binance_client.py
import os
import asyncio
import traceback
from decimal import Decimal, ROUND_DOWN, getcontext
import pandas as pd

from binance.um_futures import UMFutures

# 提高 Decimal 精度，避免對齊誤差
getcontext().prec = 28

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet: bool = False):
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.client = UMFutures(key=key, secret=secret, base_url=base)

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    # -------------- market data --------------
    async def get_klines(self, symbol, interval="15m", limit=100):
        """
        注意：UMFutures.klines 只接受 (symbol, interval) 兩個位置參數，
        其它（包含 limit）要用關鍵字參數傳遞，否則會觸發
        'klines() takes 3 positional arguments but 4 were given'
        """
        try:
            res = await self._run(
                self.client.klines,
                symbol,            # pos-arg 1
                interval,          # pos-arg 2
                limit=limit        # <-- 關鍵字參數，不能當位置參數
            )
            df = pd.DataFrame(res, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","quote_asset_volume","num_trades",
                "taker_buy_base_vol","taker_buy_quote_vol","ignore"
            ])
            for c in ("close","high","low","volume","open"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        try:
            tick = await self._run(self.client.ticker_price, symbol=symbol)
            if isinstance(tick, dict):
                return float(tick.get("price", 0))
            return float(tick)
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return 0.0

    async def get_position(self, symbol):
        try:
            # 有些版本支援不帶 symbol 回傳全部，再自行篩選
            try:
                res = await self._run(self.client.get_position_risk)
            except TypeError:
                res = await self._run(self.client.get_position_risk, symbol=symbol)
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

    # ---------------- exchange info & helpers ----------------
    async def get_symbol_info(self, symbol):
        """回傳 stepSize、minNotional、minQty、tickSize 等資訊"""
        try:
            info = await self._run(self.client.exchange_info)
        except TypeError:
            try:
                info = await self._run(self.client.get_exchange_info)
            except Exception as e:
                print(f"[ERROR] exchange_info fetch failed: {e}")
                return None

        if not info:
            return None

        symbols = info.get("symbols") if isinstance(info, dict) else info
        for s in symbols:
            if s.get("symbol") == symbol:
                filt = {f["filterType"]: f for f in s.get("filters", [])}
                return {
                    "symbol": symbol,
                    "baseAsset": s.get("baseAsset"),
                    "quoteAsset": s.get("quoteAsset"),
                    "tickSize": filt.get("PRICE_FILTER", {}).get("tickSize"),
                    "minPrice": filt.get("PRICE_FILTER", {}).get("minPrice"),
                    "maxPrice": filt.get("PRICE_FILTER", {}).get("maxPrice"),
                    "stepSize": filt.get("LOT_SIZE", {}).get("stepSize"),
                    "minQty": filt.get("LOT_SIZE", {}).get("minQty"),
                    "minNotional": filt.get("MIN_NOTIONAL", {}).get("minNotional"),
                }
        return None

    def _align_qty(self, qty: Decimal, step_str: str) -> Decimal:
        """把數量往下對齊到 stepSize 的整數倍"""
        try:
            step = Decimal(str(step_str))
            if step == 0:
                return qty
            units = (qty / step).to_integral_value(rounding=ROUND_DOWN)
            aligned = (units * step).normalize()
            return aligned
        except Exception:
            return qty

    async def calc_qty_from_usdt(self, symbol, target_usdt: Decimal, auto_bump_min_notional: bool = True):
        """
        回傳 (qty_decimal, notional_decimal, symbol_info)
        若無法計算 qty，回傳 (None, notional, info)
        """
        info = await self.get_symbol_info(symbol)
        if not info:
            return None, None, None

        price = await self.get_price(symbol)
        if not price or price <= 0:
            return None, None, info

        price_d = Decimal(str(price))
        usdt_d = Decimal(str(target_usdt))

        raw_qty = (usdt_d / price_d)
        step = info.get("stepSize") or "1"
        aligned_qty = self._align_qty(raw_qty, step)

        notional = aligned_qty * price_d
        min_notional = Decimal(str(info.get("minNotional"))) if info.get("minNotional") else None
        min_qty = Decimal(str(info.get("minQty"))) if info.get("minQty") else None

        if min_notional and notional < min_notional and auto_bump_min_notional:
            step_d = Decimal(str(step))
            # 需要的最低數量以達到 minNotional
            needed_qty = (min_notional / price_d)
            units = (needed_qty / step_d).to_integral_value(rounding=ROUND_DOWN)
            if units * step_d < needed_qty:
                units = units + 1
            bumped_qty = units * step_d
            # 亦需滿足 minQty
            if min_qty and bumped_qty < min_qty:
                units2 = (min_qty / step_d).to_integral_value(rounding=ROUND_DOWN)
                if units2 * step_d < min_qty:
                    units2 = units2 + 1
                bumped_qty = units2 * step_d
            aligned_qty = bumped_qty
            notional = aligned_qty * price_d

        if aligned_qty == 0:
            return None, notional, info

        return aligned_qty, notional, info

    # ---------------- leverage ----------------
    async def ensure_leverage(self, symbol, leverage: int):
        """嘗試設定槓桿；不同套件版本方法名可能不同，全部嘗試"""
        try:
            try:
                res = await self._run(self.client.change_leverage, symbol=symbol, leverage=leverage)
                print(f"[LEVERAGE] set {symbol} -> {leverage}: {res}")
                return res
            except Exception:
                try:
                    res = await self._run(self.client.set_leverage, symbol=symbol, leverage=leverage)
                    print(f"[LEVERAGE] set {symbol} -> {leverage} (alt): {res}")
                    return res
                except Exception as e:
                    print(f"[LEVERAGE] cannot set leverage for {symbol}: {e}")
                    return None
        except Exception as e:
            print(f"[LEVERAGE ERROR] {e}")
            return None

    # ---------------- place orders ----------------
    async def place_market_order(self, symbol, side: str, qty_decimal: Decimal, positionSide: str = None):
        try:
            qty_str = format(qty_decimal, 'f')
            params = {"symbol": symbol, "side": side, "type": "MARKET", "quantity": qty_str}
            if positionSide:
                params["positionSide"] = positionSide
            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] {side} {symbol} qty={qty_str} resp={resp}")
            return resp
        except Exception as e:
            print(f"[OPEN {side} ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def open_long(self, symbol, qty_decimal: Decimal, positionSide: str = None):
        return await self.place_market_order(symbol, "BUY", qty_decimal, positionSide=positionSide)

    async def open_short(self, symbol, qty_decimal: Decimal, positionSide: str = None):
        return await self.place_market_order(symbol, "SELL", qty_decimal, positionSide=positionSide)

    async def close(self):
        pass
