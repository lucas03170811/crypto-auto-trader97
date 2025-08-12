# strategies/revert.py
import pandas as pd
import numpy as np
from typing import Tuple

def rsi(series: pd.Series, length=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/length, adjust=False).mean()
    ma_down = down.ewm(alpha=1/length, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def bbands(series: pd.Series, length=20, std=2.0):
    ma = series.rolling(length).mean()
    sd = series.rolling(length).std()
    upper = ma + (sd * std)
    lower = ma - (sd * std)
    return lower, ma, upper

def generate_revert_signal(df) -> Tuple[str|None, str|None, float, float]:
    if not isinstance(df, pd.DataFrame):
        return None, None, 0.0, 0.5

    close = df["close"].astype(float)

    r = rsi(close, 14)
    lower, ma, upper = bbands(close, 20, 2.0)

    try:
        idx = -1
        r_v = float(r.iloc[idx])
        price = float(close.iloc[idx])
        lower_v = float(lower.iloc[idx])
        upper_v = float(upper.iloc[idx])
    except Exception:
        return None, None, 0.0, 0.5

    long_cond = (r_v < 40) and (price < lower_v)
    short_cond = (r_v > 60) and (price > upper_v)
    bb_pos = 0.5
    if upper_v != lower_v:
        bb_pos = (price - lower_v) / (upper_v - lower_v)

    return ("long" if long_cond else None, "short" if short_cond else None, r_v, bb_pos)
