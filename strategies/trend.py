# strategies/trend.py
import pandas as pd
import talib
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    """產生趨勢交易信號"""
    df['ema_fast'] = talib.EMA(df['close'], timeperiod=TREND_EMA_FAST)
    df['ema_slow'] = talib.EMA(df['close'], timeperiod=TREND_EMA_SLOW)
    macd, macd_signal, _ = talib.MACD(df['close'], fastperiod=TREND_EMA_FAST, slowperiod=TREND_EMA_SLOW, signalperiod=MACD_SIGNAL)

    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and macd.iloc[-1] > macd_signal.iloc[-1]:
        return "LONG"
    elif df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and macd.iloc[-1] < macd_signal.iloc[-1]:
        return "SHORT"
    else:
        return None

def should_pyramid(df: pd.DataFrame, position_side: str):
    """判斷是否加碼（滾倉）"""
    return generate_trend_signal(df) == position_side
