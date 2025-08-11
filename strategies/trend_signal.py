# strategy/trend.py
import pandas as pd
import numpy as np
from typing import Tuple

def ema(series: pd.Series, span: int):
    return series.ewm(span=span, adjust=False).mean()

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def generate_trend_signal(df) -> Tuple[str | None, str | None]:
    # df: pandas dataframe with close, high, low
    if not isinstance(df, pd.DataFrame):
        return None, None

    close = df["close"].astype(float)

    ema_short = ema(close, 8)
    ema_long  = ema(close, 21)
    macd_line, signal_line = macd(close)
    # simple adx approximation skipped — we'll use macd+ema with low adx threshold

    try:
        idx = -1
        s = ema_short.iloc[idx]
        l = ema_long.iloc[idx]
        m = macd_line.iloc[idx]
        sgn = signal_line.iloc[idx]
    except Exception:
        return None, None

    adx_ok = True  # we removed strict ADX to increase trades
    long_cond = (s > l) and (m > sgn) and adx_ok
    short_cond = (s < l) and (m < sgn) and adx_ok

    return ("long" if long_cond else None, "short" if short_cond else None)
