import pandas as pd
import pandas_ta as ta
from config import EMA_FAST, EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    """
    趨勢策略：EMA + MACD
    回傳: "BUY" / "SELL" / None
    """
    df["ema_fast"] = ta.ema(df["close"], length=EMA_FAST)
    df["ema_slow"] = ta.ema(df["close"], length=EMA_SLOW)
    macd = ta.macd(df["close"], fast=EMA_FAST, slow=EMA_SLOW, signal=MACD_SIGNAL)
    df["macd"] = macd[f"MACD_{EMA_FAST}_{EMA_SLOW}_{MACD_SIGNAL}"]
    df["macds"] = macd[f"MACDs_{EMA_FAST}_{EMA_SLOW}_{MACD_SIGNAL}"]

    last = df.iloc[-1]
    if last["ema_fast"] > last["ema_slow"] and last["macd"] > last["macds"]:
        return "BUY"
    if last["ema_fast"] < last["ema_slow"] and last["macd"] < last["macds"]:
        return "SELL"
    return None
