# strategies/trend.py
import pandas as pd
import numpy as np
import ta
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    df['ema_fast'] = ta.trend.EMAIndicator(df['close'], TREND_EMA_FAST).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(df['close'], TREND_EMA_SLOW).ema_indicator()

    macd = ta.trend.MACD(df['close'], window_slow=TREND_EMA_SLOW,
                         window_fast=TREND_EMA_FAST, window_sign=MACD_SIGNAL)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 放寬進場條件：只要均線方向一致 + MACD 同方向
    if last['ema_fast'] > last['ema_slow'] and last['macd'] > last['macd_signal']:
        return "LONG"
    elif last['ema_fast'] < last['ema_slow'] and last['macd'] < last['macd_signal']:
        return "SHORT"

    return None

def should_pyramid(df: pd.DataFrame, direction: str):
    """
    判斷是否加碼（滾倉）：方向一致且漲幅超過 1% 再加碼
    """
    price_change = (df['close'].iloc[-1] / df['close'].iloc[-5]) - 1
    if direction == "LONG" and price_change > 0.01:
        return True
    if direction == "SHORT" and price_change < -0.01:
        return True
    return False
