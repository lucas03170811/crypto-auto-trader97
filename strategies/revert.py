# strategies/revert.py
import pandas as pd
import pandas_ta as ta
from typing import Tuple

def generate_revert_signal(df: pd.DataFrame) -> Tuple[str|None, str|None]:
    if df is None or len(df) < 20:
        return None, None

    rsi = ta.rsi(df["close"], length=14)
    bb = ta.bbands(df["close"], length=20, std=2.0)
    lower = bb["BBL_20_2.0"]
    upper = bb["BBU_20_2.0"]

    latest_rsi = rsi.iloc[-1]
    latest_price = df["close"].iloc[-1]

    long = (latest_rsi < 40) and (latest_price < lower.iloc[-1])
    short = (latest_rsi > 60) and (latest_price > upper.iloc[-1])
    return ("long" if long else None, "short" if short else None)
