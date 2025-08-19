# exchange/binance_client.py
import os
import asyncio
import traceback
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
import pandas as pd
from binance.um_futures import UMFutures

# 增加 Decimal 預設精度（夠用即可）
getcontext().prec = 28
D = Decimal

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None, testnet: bool = False):
        """
        使用同步的 UMFutures client （library 提供的是同步呼叫）。
        所有網路 I/O 會透過 run_in_executor 呼叫以免阻塞 event loop。
        """
        key = api_key or os.getenv("BINANCE_API_KEY")
        secret = api_secret or os.getenv("BINANCE_API_SECRET")
        base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"

        # 初始化 sync client（我們會在 async context 用 run_in_executor 呼叫它）
        self.client = UMFutures(key=key, secret=secret, base_url=base_url)

        # symbol metadata cache (stepSize, minQty, tickSize, minNotional, prec)
        self.symbol_meta = {}

        # bootstrap 立刻抓一次 exchange_info（同步呼叫），並印 debug
        try:
            self._bootstrap_sync()
        except Exception as e:
            print("[BOOT WARN] bootstrap failed:", e)
            traceback.print_exc()

    # -------------------------
    # Bootstrap / meta helpers
    # -------------------------
    def _meta_precimals(self, step: Decimal) -> int:
        """根據 stepSize 決定小數位數 (eg. 0.001 -> 3)"""
        if step is None or step == D("0"):
            return 8
        s = format(step.normalize(), 'f')
        if '.' in s:
            return len(s.split('.')[1].rstrip('0'))
        return 0

    def _get_filter(self, filters, ftype):
        for f in filters:
            if f.get("filterType") == ftype:
                return f
        return {}

    def _bootstrap_sync(self):
        """同步抓 exchange_info 並填 symbol_meta，並印 debug"""
        try:
            info = self.client.exchange_info()
            print("[BOOT] exchange_info fetched")
        except Exception as e:
            print(f"[BOOT WARN] exchange_info fetch fail: {e}")
            info = {"symbols": []}

        for s in info.get("symbols", []):
            sym = s.get("symbol")
            filters = s.get("filters", [])
            lot = self._get_filter(filters, "LOT_SIZE")
            pricef = self._get_filter(filters, "PRICE_FILTER")
            mn = self._get_filter(filters, "MIN_NOTIONAL")

            step = D(str(lot.get("stepSize", "0"))) if lot else D("0")
            min_qty = D(str(lot.get("minQty", "0"))) if lot else D("0")
            tick = D(str(pricef.get("tickSize", "0"))) if pricef else D("0")
            min_notional = D(str(mn.get("notional", "5"))) if mn else D("5")
            prec = self._meta_precimals(step)

            self.symbol_meta[sym] = {
                "step": step,
                "min_qty": min_qty,
                "tick": tick,
                "min_notional": min_notional,
                "prec": prec,
            }

        # debug: 印出 sample 幾個常見幣的 meta（方便你貼 log）
        samples = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SUIUSDT", "MATICUSDT"]
        for sample in samples:
            m = self.symbol_meta.get(sample)
            print(f"[BOOT META] {sample}: {m}")

    def get_symbol_meta(self, symbol: str):
        return self.symbol_meta.get(symbol, {
            "step": D("0"),
            "min_qty": D("0"),
            "tick": D("0"),
            "min_notional": D("5"),
            "prec": 8,
        })

    # -------------------------
    # Async wrapper for sync client calls
    # -------------------------
    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    # -------------------------
    # Market data helpers
    # -------------------------
    async def get_klines(self, symbol, interval="15m", limit=100):
        """
        回傳 pandas DataFrame（欄位至少需要 close/high/low/volume）
        處理不同版本 client 的參數差異
        """
        try:
            res = await self._run(self.client.klines, symbol, interval, limit)
        except TypeError:
            # 部分版本需要 kwargs
            try:
                res = await self._run(self.client.klines, symbol=symbol, interval=interval, limit=limit)
            except Exception as e:
                print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return None

        try:
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
            # fallback: maybe res already DataFrame-like
            try:
                return pd.DataFrame(res)
            except Exception:
                print(f"[ERROR] Building DataFrame for {symbol}: {e}")
                return None

    async def get_price(self, symbol):
        """
        嘗試多種 ticker 功能取價，並回傳 float 或 0.0
        """
        try:
            # 一些版本 ticker_price(symbol) 回 dict / str
            tick = await self._run(self.client.ticker_price, symbol)
            if isinstance(tick, dict):
                p = tick.get("price") or tick.get("lastPrice") or tick.get("close")
                return float(p)
            try:
                return float(tick)
            except Exception:
                # fallback to ticker_24hr
                info = await self._run(self.client.ticker_24hr, symbol)
                p = info.get("lastPrice") or info.get("close") or info.get("price")
                return float(p)
        except Exception as e:
            # debug 用詳細印出
            print(f"[ERROR] get_price {symbol}: {e}")
            try:
                traceback.print_exc()
            except Exception:
                pass
        return 0.0

    async def get_position(self, symbol):
        """回傳 positionAmt (float)。嘗試不同 signature"""
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

    async def get_equity(self):
        """回傳 USDT 餘額（float）"""
        try:
            bal = await self._run(self.client.balance)
            for b in bal:
                if b.get("asset") == "USDT":
                    return float(b.get("balance", 0))
        except Exception as e:
            print(f"[ERROR] get_equity: {e}")
        return 0.0

    # -------------------------
    # Quantity adjust / format helpers
    # -------------------------
    def adjust_quantity(self, symbol: str, target_notional_usdt: Decimal, price: Decimal) -> Decimal:
        """
        給定目標名目價值（USDT）與價格，回傳符合市場 step/min_qty/min_notional 的 qty (Decimal)。
        若無法達成（會變 0 或名目不足），回傳 Decimal('0')。
        此實作傾向 **向上對齊** (ROUND_UP)，以避免 qty 被 quantize 成 0。
        同時會印出 debug：
         - [ADJUST DBG] 原始 raw_qty
         - [ADJUST OK] 成功 qty 與最終名目
         - [ADJUST] 若失敗
        """
        meta = self.get_symbol_meta(symbol)
        step = meta["step"]
        min_qty = meta["min_qty"]
        min_notional = meta["min_notional"]

        print(f"[ADJUST DBG] {symbol} meta step={step} min_qty={min_qty} min_notional={min_notional}")

        price_d = D(str(price))
        if price_d <= 0:
            print(f"[ADJUST DBG] {symbol} price invalid: {price_d}")
            return D("0")

        target = D(str(target_notional_usdt))
        if target < min_notional:
            target = min_notional

        raw_qty = (target / price_d)
        print(f"[ADJUST DBG] {symbol} raw_qty={raw_qty} (target_notional={target}, price={price_d})")

        if step > 0:
            steps_needed = (raw_qty / step).to_integral_value(rounding=ROUND_UP)
            qty = steps_needed * step
        else:
            qty = raw_qty

        if qty < min_qty:
            qty = min_qty

        print(f"[ADJUST DBG] {symbol} after ceil step qty={qty}")

        # 量化到允許的小數位數（使用 ROUND_UP 以避免變 0）
        prec = meta.get("prec", self._meta_precimals(step))
        quant = D(1).scaleb(-prec)
        try:
            qty = qty.quantize(quant, rounding=ROUND_UP)
        except Exception:
            pass

        # 再次確保對齊 step（向上）
        if step > 0:
            steps_needed = (qty / step).to_integral_value(rounding=ROUND_UP)
            qty = steps_needed * step

        final_notional = (D(price_d) * qty)
        if qty <= 0 or final_notional < min_notional:
            print(f"[ADJUST] {symbol} qty 對齊後為 0 或名目不足 (price*qty={final_notional}), cancel (step={step})")
            return D("0")

        print(f"[ADJUST OK] {symbol} final qty={qty} notional={final_notional}")
        return qty

    def _format_qty(self, qty: Decimal, symbol: str) -> str:
        """把 Decimal qty 格式化成字串，去掉多餘 0 並依 meta 小數位數修正"""
        meta = self.get_symbol_meta(symbol)
        prec = meta.get("prec", 8)
        quant = D(1).scaleb(-prec)
        try:
            q = qty.quantize(quant, rounding=ROUND_DOWN)
        except Exception:
            q = qty
        s = format(q, 'f')
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s

    # -------------------------
    # Trading (orders)
    # -------------------------
    async def open_long(self, symbol, qty, positionSide: str | None = None):
        """市場單做多（qty: Decimal 或 float）"""
        try:
            if isinstance(qty, Decimal):
                qty_s = self._format_qty(qty, symbol)
            else:
                qty_s = str(qty)

            params = {"symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": qty_s}
            if positionSide:
                params["positionSide"] = positionSide

            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] LONG {symbol} qty={qty_s} resp={resp}")
            return resp
        except Exception as e:
            print(f"[OPEN LONG ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def open_short(self, symbol, qty, positionSide: str | None = None):
        """市場單做空（qty: Decimal 或 float）"""
        try:
            if isinstance(qty, Decimal):
                qty_s = self._format_qty(qty, symbol)
            else:
                qty_s = str(qty)

            params = {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": qty_s}
            if positionSide:
                params["positionSide"] = positionSide

            resp = await self._run(self.client.new_order, **params)
            print(f"[ORDER] SHORT {symbol} qty={qty_s} resp={resp}")
            return resp
        except Exception as e:
            print(f"[OPEN SHORT ERROR] {symbol}: {e}")
            traceback.print_exc()
            return None

    async def close(self):
        """UMFutures 沒有 async close"""
        pass
