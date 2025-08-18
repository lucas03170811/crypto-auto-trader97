# strategies/revert.py
import pandas as pd
import pandas_ta as ta
from config import REVERT_RSI_OVERSOLD, REVERT_RSI_OVERBOUGHT, BOLL_STD_DEV

def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")
    # RSI
    df["rsi"] = ta.rsi(df["close"], length=14)
    # Bollinger Bands
    bb = ta.bbands(df["close"], length=20, std=BOLL_STD_DEV)
    df["bb_low"]  = bb["BBL_20_2.0"]
    df["bb_high"] = bb["BBU_20_2.0"]
    return df

def generate_revert_signal(df: pd.DataFrame) -> str:
    """
    回傳: 'BUY' / 'SELL' / 'HOLD'
    放寬條件：
      - BUY : RSI < oversold 或 收盤跌破下軌（期待反彈）
      - SELL: RSI > overbought 或 收盤站上上軌（期待回落）
    """
    df = _prep(df)
    if len(df) < 21:
        return "HOLD"

    row = df.iloc[-1]
    cond_buy  = (row["rsi"] <= REVERT_RSI_OVERSOLD) or (row["close"] <= row["bb_low"])
    cond_sell = (row["rsi"] >= REVERT_RSI_OVERBOUGHT) or (row["close"] >= row["bb_high"])

    if cond_buy:
        return "BUY"
    if cond_sell:
        return "SELL"
    return "HOLD"
