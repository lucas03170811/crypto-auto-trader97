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
        self.symbol_meta = {}  # { "BTCUSDT": {"min_notional":D, "step":D, "min_qty":D, "tick":D} }
        self.dual_side = dual_side

        # 初始化：同步一次交易所規則 & 倉位模式
        self._bootstrap_sync()

    # ---------- 基礎工具 ----------
    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    def _floor_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        steps = (qty / step).to_integral_value(rounding=ROUND_DOWN)
        return steps * step

    def _ceil_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return qty
        steps = (qty / step).to_integral_value(rounding=ROUND_UP)
        return steps * step

    # ---------- 啟動時拉取交易所規則 ----------
    def _bootstrap_sync(self):
        # 1) 交易對規則
        try:
            info = self.client.exchange_info()
            for s in info.get("symbols", []):
                sym = s.get("symbol")
                filters = {f["filterType"]: f for f in s.get("filters", [])}
                lot = filters.get("LOT_SIZE", {})
                pricef = filters.get("PRICE_FILTER", {})
                min_notional_f = filters.get("MIN_NOTIONAL", {})

                step = D(lot.get("stepSize", "0"))
                min_qty = D(lot.get("minQty", "0"))
                tick = D(pricef.get("tickSize", "0"))
                # 一些合約沒有給 notional，給預設 5
                min_notional = D(min_notional_f.get("notional", "5"))

                self.symbol_meta[sym] = {
                    "step": step,
                    "min_qty": min_qty,
                    "tick": tick,
                    "min_notional": min_notional,
                }
        except Exception as e:
            print(f"[WARN] 無法拉取 exchange_info：{e}，將使用預設門檻（minNotional=5）")

        # 2) 預設用「單向倉」避免 -4061，若你需要雙向倉請把 dual_side=True
        try:
            self.client.change_position_mode(dualSidePosition="true" if self.dual_side else "false")
        except Exception as e:
            # 有些帳戶/權限不能切，忽略即可
            print(f"[WARN] change_position_mode 失敗：{e}")

    # ---------- 查詢 symbol 規則 ----------
    def get_symbol_meta(self, symbol: str) -> dict:
        return self.symbol_meta.get(symbol, {
            "step": D("0.0001"),
            "min_qty": D("0.0001"),
            "tick": D("0.01"),
            "min_notional": D("5"),
        })

    def get_min_notional(self, symbol: str) -> Decimal:
        return self.get_symbol_meta(symbol)["min_notional"]

    # ---------- K 線 ----------
    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            # 先用位置參數（新版本）
            res = await self._run(self.client.klines, symbol, interval, limit)
        except TypeError:
            # 舊版本 signature
            res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

        try:
            df = pd.DataFrame(res, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "num_trades",
                "taker_buy_base_vol", "taker_buy_quote_vol", "ignore"
            ])
        except Exception:
            df = pd.DataFrame(res)

        for col in ("close", "high", "low", "volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    # ---------- 價格（多來源容錯） ----------
    async def get_price(self, symbol):
        # 1) ticker_price
        try:
            tick = await self._run(self.client.ticker_price, symbol)
            if isinstance(tick, dict) and "price" in tick:
                return float(tick["price"])
            if isinstance(tick, list):
                for t in tick:
                    if t.get("symbol") == symbol and "price" in t:
                        return float(t["price"])
        except Exception:
            pass

        # 2) mark_price
        try:
            mk = await self._run(self.client.mark_price, symbol)
            if isinstance(mk, dict) and "markPrice" in mk:
                return float(mk["markPrice"])
        except Exception:
            pass

        # 3) 24hr ticker
        try:
            t24 = await self._run(self.client.ticker_24hr, symbol)
            if isinstance(t24, dict):
                if "lastPrice" in t24:
                    return float(t24["lastPrice"])
                if "weightedAvgPrice" in t24:
                    return float(t24["weightedAvgPrice"])
        except Exception:
            pass

        print(f"[ERROR] get_price {symbol}: 無法取得價格")
        return 0.0

    # ---------- 餘額 / 持倉 ----------
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

    # ---------- 數量修正：對齊 minNotional / stepSize ----------
    def adjust_quantity(self, symbol: str, target_notional_usdt: float, price: float) -> Decimal:
        meta = self.get_symbol_meta(symbol)
        step = meta["step"]
        min_qty = meta["min_qty"]
        min_notional = meta["min_notional"]

        if price <= 0:
            return D("0")

        notional = D(target_notional_usdt)
        if notional < min_notional:
            notional = min_notional  # 補到最小名目

        raw_qty = notional / D(price)

        # 先向上補量，確保至少達到最小名目，再用 step 對齊
        qty = self._ceil_to_step(raw_qty, step)
        if qty < min_qty:
            qty = min_qty

        # 再次確認補完後是否仍達標
        if (D(price) * qty) < min_notional:
            need = min_notional / D(price)
            qty = self._ceil_to_step(need, step)

        # 防止極端情況為 0
        if qty <= 0:
            print(f"[ADJUST] {symbol} qty 對齊後仍為 0（step={step} / min_qty={min_qty}），取消下單")
            return D("0")

        return qty

    # ---------- 下單（預設單向倉，不送 positionSide） ----------
    async def open_long(self, symbol, qty):
        try:
            resp = await self._run(self.client.new_order,
                                   symbol=symbol, side="BUY", type="MARKET", quantity=str(qty))
            print(f"[ORDER OK] LONG {symbol} qty={qty} resp={resp}")
            return resp
        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            return None

    async def open_short(self, symbol, qty):
        try:
            resp = await self._run(self.client.new_order,
                                   symbol=symbol, side="SELL", type="MARKET", quantity=str(qty))
            print(f"[ORDER OK] SHORT {symbol} qty={qty} resp={resp}")
            return resp
        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            return None

    async def close(self):
        pass
