# exchange/binance_client.py
import pandas as pd
from binance.um_futures import UMFutures
from config import (
    API_KEY, API_SECRET,
    MIN_NOTIONAL_USDT, LEVERAGE, FORCE_MIN_NOTIONAL, DEBUG_MODE
)

class BinanceClient:
    def __init__(self, api_key=API_KEY, api_secret=API_SECRET):
        self.client = UMFutures(key=api_key, secret=api_secret)
        print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

    def get_klines(self, symbol, interval="5m", limit=200):
        """取得K線資料"""
        try:
            klines = self.client.klines(symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=[
                "timestamp","open","high","low","close","volume",
                "_","quote","trades","taker_base","taker_quote","ignore"
            ])
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df
        except Exception as e:
            print(f"[ERROR] get_klines {symbol}: {e}")
            return None

    def get_price(self, symbol):
        """取得最新價格"""
        try:
            ticker = self.client.ticker_price(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return None

    def order(self, symbol, side, qty=0.01):
        """建立市價單，會檢查 notional >= 最小金額"""
        try:
            price = self.get_price(symbol)
            if not price:
                print(f"[ERROR] 無法取得 {symbol} 價格，下單取消")
                return None

            notional = price * qty
            if notional < MIN_NOTIONAL_USDT:
                if FORCE_MIN_NOTIONAL:
                    qty = round(MIN_NOTIONAL_USDT / price, 3)  # 自動補足數量
                    print(f"[ADJUST] {symbol} 下單數量過小，自動補足至 {qty} (~{MIN_NOTIONAL_USDT} USDT)")
                else:
                    print(f"[RISK] qty too small: {symbol} notional={notional:.2f} < {MIN_NOTIONAL_USDT}")
                    return None

            if DEBUG_MODE:
                print(f"[ORDER-DEBUG] {side} {symbol} x {qty}")
                return {"symbol": symbol, "side": side, "qty": qty, "debug": True}

            # 真正送單
            order = self.client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=qty
            )
            print(f"[ORDER] {side} {symbol} x {qty} 成功 ✅")
            return order

        except Exception as e:
            print(f"[ERROR] order {symbol}: {e}")
            return None
