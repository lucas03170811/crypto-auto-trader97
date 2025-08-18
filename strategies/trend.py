# strategies/trend.py
import pandas_ta as ta
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df):
    df["ema_fast"] = ta.ema(df["close"], length=TREND_EMA_FAST)
    df["ema_slow"] = ta.ema(df["close"], length=TREND_EMA_SLOW)

    macd = ta.macd(df["close"], fast=TREND_EMA_FAST, slow=TREND_EMA_SLOW, signal=MACD_SIGNAL)
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]

    if df["ema_fast"].iloc[-1] > df["ema_slow"].iloc[-1] and df["macd"].iloc[-1] > df["macd_signal"].iloc[-1]:
        return "BUY"
    elif df["ema_fast"].iloc[-1] < df["ema_slow"].iloc[-1] and df["macd"].iloc[-1] < df["macd_signal"].iloc[-1]:
        return "SELL"
    return None

def should_pyramid(df, signal):
    """判斷是否加碼"""
    if signal == "BUY" and df["close"].iloc[-1] > df["ema_fast"].iloc[-1]:
        return True
    if signal == "SELL" and df["close"].iloc[-1] < df["ema_fast"].iloc[-1]:
        return True
    return False
