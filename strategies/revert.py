# strategies/revert.py
import pandas as pd
import pandas_ta as ta

def generate_revert_signal(df: pd.DataFrame):
    if df is None or len(df) < 30:
        return None

    rsi = ta.rsi(df["close"], length=14).iloc[-1]
    bb = ta.bbands(df["close"], length=20, std=2)
    lower = bb["BBL_20_2.0"].iloc[-1]
    upper = bb["BBU_20_2.0"].iloc[-1]
    price = df["close"].iloc[-1]

    if rsi < 40 and price < lower:
        return "long"
    if rsi > 60 and price > upper:
        return "short"
    return None
