# strategies/trend.py
import pandas as pd
import pandas_ta as ta
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")
    # EMA
    df["ema_fast"] = ta.ema(df["close"], length=TREND_EMA_FAST)
    df["ema_slow"] = ta.ema(df["close"], length=TREND_EMA_SLOW)
    # MACD
    macd = ta.macd(df["close"], fast=TREND_EMA_FAST, slow=TREND_EMA_SLOW, signal=MACD_SIGNAL)
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    return df

def generate_trend_signal(df: pd.DataFrame) -> str:
    """
    回傳: 'LONG' / 'SHORT' / 'HOLD'
    條件（放寬版）：
      - LONG: ema_fast > ema_slow 且 MACD > 0
      - SHORT: ema_fast < ema_slow 且 MACD < 0
    """
    df = _prep(df)
    if len(df) < max(TREND_EMA_SLOW, 50):
        return "HOLD"

    row = df.iloc[-1]
    if pd.notna(row["ema_fast"]) and pd.notna(row["ema_slow"]) and pd.notna(row["macd"]):
        if row["ema_fast"] > row["ema_slow"] and row["macd"] > 0:
            return "LONG"
        if row["ema_fast"] < row["ema_slow"] and row["macd"] < 0:
            return "SHORT"
    return "HOLD"

def should_pyramid(df: pd.DataFrame) -> bool:
    """
    加碼判斷（簡化）：
      - 最近 5 根 K 線漲幅合計 > 1% 或 跌幅合計 < -1% 時，允許加碼
    """
    if len(df) < 6:
        return False
    closes = df["close"].astype(float)
    # 5 根 K 收益率合計
    ret = (closes.iloc[-5:] / closes.shift(1).iloc[-5:] - 1.0).fillna(0).sum()
    return ret > 0.01 or ret < -0.01
