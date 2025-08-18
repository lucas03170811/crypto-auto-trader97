# strategies/trend.py
import pandas as pd
import talib
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    if len(df) < 50:
        return None

    close = df["close"].astype(float).values

    ema_fast = talib.EMA(close, timeperiod=TREND_EMA_FAST)
    ema_slow = talib.EMA(close, timeperiod=TREND_EMA_SLOW)
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=TREND_EMA_FAST, slowperiod=TREND_EMA_SLOW, signalperiod=MACD_SIGNAL)

    # 放寬條件 → 只要 EMA 有交叉就進場
    if ema_fast[-1] > ema_slow[-1] and macd[-1] > macdsignal[-1]:
        return "LONG"
    elif ema_fast[-1] < ema_slow[-1] and macd[-1] < macdsignal[-1]:
        return "SHORT"

    return None

def should_pyramid(df: pd.DataFrame, direction: str):
    """單邊行情加碼條件"""
    if len(df) < 50:
        return False

    close = df["close"].astype(float).values
    ema_fast = talib.EMA(close, timeperiod=TREND_EMA_FAST)
    ema_slow = talib.EMA(close, timeperiod=TREND_EMA_SLOW)

    if direction == "LONG" and ema_fast[-1] > ema_slow[-1]:
        return True
    if direction == "SHORT" and ema_fast[-1] < ema_slow[-1]:
        return True

    return False
