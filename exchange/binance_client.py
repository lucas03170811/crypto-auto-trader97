# exchange/binance_client.py
import math
import pandas as pd

# 兼容官方 binance-connector 與某些「futures connector」分支
try:
    from binance.um_futures import UMFutures
except Exception:
    # 若你的 requirements 用的是 binance-futures-connector，它也提供相同 import 路徑
    from binance.um_futures import UMFutures  # 保留同一路徑

from config import (
    API_KEY, API_SECRET,
    MIN_NOTIONAL_USDT, FORCE_MIN_NOTIONAL, DEBUG_MODE
)

class BinanceClient:
    def __init__(self, api_key=API_KEY, api_secret=API_SECRET):
        self.client = UMFutures(key=api_key, secret=api_secret)
        self._filters = {}   # 快取交易規格
        print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

    # ---------- 市場資料 ----------
    def get_klines(self, symbol, interval="5m", limit=200):
        try:
            kl = self.client.klines(symbol, interval=interval, limit=limit)
            df = pd.DataFrame(kl, columns=[
                "ts","open","high","low","close","volume",
                "_","quote","trades","tb_base","tb_quote","ignore"
            ])
            for c in ("open","high","low","close","volume"):
                df[c] = df[c].astype(float)
            return df[["ts","open","high","low","close","volume"]]
        except Exception as e:
            print(f"[ERROR] get_klines {symbol}: {e}")
            return None

    def get_price(self, symbol):
        try:
            t = self.client.ticker_price(symbol=symbol)
            return float(t["price"])
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return None

    # ---------- 交易規格 ----------
    def _load_filters(self, symbol):
        if symbol in self._filters:
            return self._filters[symbol]
        try:
            info = self.client.exchange_info()
            for s in info["symbols"]:
                if s["symbol"] == symbol:
                    f = {f["filterType"]: f for f in s["filters"]}
                    step = float(f.get("LOT_SIZE",{}).get("stepSize","0.0001"))
                    tick = float(f.get("PRICE_FILTER",{}).get("tickSize","0.01"))
                    min_notional = float(f.get("MIN_NOTIONAL",{}).get("notional", str(MIN_NOTIONAL_USDT)))
                    self._filters[symbol] = {"step": step, "tick": tick, "min_notional": min_notional}
                    return self._filters[symbol]
        except Exception as e:
            print(f"[WARN] exchange_info 失敗 {symbol}: {e}")
        # fallback
        self._filters[symbol] = {"step": 0.0001, "tick": 0.01, "min_notional": MIN_NOTIONAL_USDT}
        return self._filters[symbol]

    def _quant(self, x, step):
        # 向下對齊到 stepSize
        if step <= 0:
            return x
        return math.floor(x / step) * step

    # ---------- 下單 ----------
    def order(self, symbol, side, qty, reduce_only=False):
        """
        市價單下單；會自動補足最小 notional 並對齊 stepSize。
        side: "BUY" / "SELL"
        """
        try:
            px = self.get_price(symbol)
            if not px:
                print(f"[ERROR] 無法取得 {symbol} 價格，下單取消")
                return None

            f = self._load_filters(symbol)
            step = f["step"]
            min_notional = max(MIN_NOTIONAL_USDT, f["min_notional"])

            # 自動補足最小名目金額
            notional = px * qty
            if notional < min_notional:
                if FORCE_MIN_NOTIONAL:
                    qty = (min_notional / px) * 1.001  # 多加一點避免邊界
                    print(f"[ADJUST] {symbol} 名目不足，自動補至 ~{min_notional} USDT，qty≈{qty}")
                else:
                    print(f"[RISK] qty too small: {symbol} notional={notional:.2f} < {min_notional}")
                    return None

            # 對齊交易步進
            qty = self._quant(qty, step)
            if qty <= 0:
                print(f"[ERROR] {symbol} qty 對齊步進後為 0，取消下單（step={step})")
                return None

            if DEBUG_MODE:
                print(f"[ORDER-DEBUG] {side} {symbol} x {qty} (px≈{px})")
                return {"debug": True, "symbol": symbol, "side": side, "qty": qty, "price": px}

            params = dict(symbol=symbol, side=side, type="MARKET", quantity=qty)
            if reduce_only:
                params["reduceOnly"] = "true"

            od = self.client.new_order(**params)
            print(f"[ORDER] {side} {symbol} x {qty} 成功 ✅")
            return od

        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            return None
