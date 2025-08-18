# strategies/revert.py
import pandas as pd
import pandas_ta as ta

from config import (
    REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV
)

def generate_revert_signal(df: pd.DataFrame):
    """
    放寬版反轉訊號（均值回歸）：
    - 多：RSI < oversold 或 close < BB 下緣（留有 0.5% 緩衝）
    - 空：RSI > overbought 或 close > BB 上緣（留有 0.5% 緩衝）
    """
    close = df["close"]
    rsi = ta.rsi(close, length=14)
    bb = ta.bbands(close, length=20, std=BOLL_STD_DEV)
    low = bb["BBL_20_2.0"]
    high = bb["BBU_20_2.0"]

    long_ok = (rsi.iloc[-1] <= REVERT_RSI_OVERSOLD) or (close.iloc[-1] <= low.iloc[-1] * 1.005)
    short_ok = (rsi.iloc[-1] >= REVERT_RSI_OVERBOUGHT) or (close.iloc[-1] >= high.iloc[-1] * 0.995)

    if long_ok and not short_ok:
        return "LONG"
    if short_ok and not long_ok:
        return "SHORT"
    return None
