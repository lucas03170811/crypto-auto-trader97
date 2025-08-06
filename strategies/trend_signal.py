import pandas as pd
import pandas_ta as ta

def trend_signal(df: pd.DataFrame):
    ema_fast = ta.ema(df["close"], length=10)
    ema_slow = ta.ema(df["close"], length=30)
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)["ADX_14"]

    long  = (ema_fast.iloc[-1] > ema_slow.iloc[-1]) and (adx.iloc[-1] > 18)
    short = (ema_fast.iloc[-1] < ema_slow.iloc[-1]) and (adx.iloc[-1] > 18)
    return long, short, adx.iloc[-1]