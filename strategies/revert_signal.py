import pandas as pd
import pandas_ta as ta

def revert_signal(df: pd.DataFrame):
    rsi = ta.rsi(df["close"], length=14)
    bb = ta.bbands(df["close"], length=20)
    bb_upper = bb["BBU_20_2.0"]
    bb_lower = bb["BBL_20_2.0"]
    close = df["close"]

    long = (rsi.iloc[-1] < 30) and (close.iloc[-1] < bb_lower.iloc[-1])
    short = (rsi.iloc[-1] > 70) and (close.iloc[-1] > bb_upper.iloc[-1])
    return long, short, rsi.iloc[-1], (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])