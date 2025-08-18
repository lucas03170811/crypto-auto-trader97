# strategies/trend.py
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def _ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return macd, sig, hist, ema_fast, ema_slow

def generate_trend_signal(df):
    """
    回傳: "LONG" / "SHORT" / None
    放寬條件：EMA_fast > EMA_slow 且 MACD hist > 0 -> LONG；反之 -> SHORT
    """
    if df is None or df.empty:
        return None
    close = df["close"]
    _, _, hist, ema_f, ema_s = _macd(close, TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL)
    if ema_f.iloc[-1] > ema_s.iloc[-1] and hist.iloc[-1] > 0:
        return "LONG"
    if ema_f.iloc[-1] < ema_s.iloc[-1] and hist.iloc[-1] < 0:
        return "SHORT"
    return None

def should_pyramid(side, price, last_add_price, add_every_pct, layers_done, max_layers):
    """
    當價格相對於最後一次加碼價，往有利方向移動 add_every_pct 就回 True。
    """
    if layers_done >= max_layers:
        return False
    if last_add_price is None:
        last_add_price = price
        # 首筆進場後的下一次比較基準就是進場價
        return False

    if side == "LONG":
        return price >= last_add_price * (1 + add_every_pct)
    else:  # SHORT
        return price <= last_add_price * (1 - add_every_pct)
