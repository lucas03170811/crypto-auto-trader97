# strategies/revert.py
import pandas_ta as ta
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

def generate_revert_signal(df):
    df["rsi"] = ta.rsi(df["close"], length=14)
    bbands = ta.bbands(df["close"], length=20, std=BOLL_STD_DEV)

    df["bb_lower"] = bbands["BBL_20_2.0"]
    df["bb_upper"] = bbands["BBU_20_2.0"]

    if df["rsi"].iloc[-1] < REVERT_RSI_OVERSOLD and df["close"].iloc[-1] < df["bb_lower"].iloc[-1]:
        return "BUY"
    elif df["rsi"].iloc[-1] > REVERT_RSI_OVERBOUGHT and df["close"].iloc[-1] > df["bb_upper"].iloc[-1]:
        return "SELL"
    return None
