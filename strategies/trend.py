# strategies/trend.py
import pandas as pd
import pandas_ta as ta

from config import (
    TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL, TREND_MIN_SLOPE,
    PYRAMID_MAX_LAYERS, PYRAMID_ADD_RATIO, PYRAMID_TRIGGER_UPNL
)

def generate_trend_signal(df: pd.DataFrame):
    """
    放寬版趨勢訊號：
    - 多：EMA 快 > EMA 慢 且 MACD 直方圖>0 或者 close > EMA 慢 * (1 + TREND_MIN_SLOPE)
    - 空：EMA 快 < EMA 慢 且 MACD 直方圖<0 或者 close < EMA 慢 * (1 - TREND_MIN_SLOPE)
    """
    close = df["close"]
    ema_fast = ta.ema(close, length=TREND_EMA_FAST)
    ema_slow = ta.ema(close, length=TREND_EMA_SLOW)
    macd = ta.macd(close, fast=TREND_EMA_FAST, slow=TREND_EMA_SLOW, signal=MACD_SIGNAL)
    hist = macd["MACDh_12_26_9"]

    if ema_fast.iloc[-1] > ema_slow.iloc[-1] and hist.iloc[-1] > 0:
        return "LONG"
    if ema_fast.iloc[-1] < ema_slow.iloc[-1] and hist.iloc[-1] < 0:
        return "SHORT"

    # 放寬：靠近慢線的一個微斜率突破也可
    if close.iloc[-1] > ema_slow.iloc[-1] * (1 + TREND_MIN_SLOPE):
        return "LONG"
    if close.iloc[-1] < ema_slow.iloc[-1] * (1 - TREND_MIN_SLOPE):
        return "SHORT"

    return None

def should_pyramid(upnl_pct: float, layers_opened: int) -> bool:
    """
    單邊滾倉觸發：
    - 浮盈超過 PYRAMID_TRIGGER_UPNL（例如 2%）
    - 已開層數 < PYRAMID_MAX_LAYERS
    """
    return (upnl_pct >= PYRAMID_TRIGGER_UPNL) and (layers_opened < PYRAMID_MAX_LAYERS)

def pyramid_addon_qty(base_qty: float) -> float:
    """
    每層在基礎倉位上增加的比例（例如 0.5 表示再加 50% 基礎倉位）
    """
    return base_qty * PYRAMID_ADD_RATIO
