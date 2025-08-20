import pandas as pd
import pandas_ta as ta
from config import RSI_LEN, BB_LEN, BB_STD, RSI_BUY, RSI_SELL

def generate_revert_signal(df: pd.DataFrame):
    """
    反轉策略：RSI + 布林
    回傳: "BUY" / "SELL" / None
    """
    df["rsi"] = ta.rsi(df["close"], length=RSI_LEN)
    bb = ta.bbands(df["close"], length=BB_LEN, std=BB_STD)
    df["bbl"] = bb[f"BBL_{BB_LEN}_{BB_STD}"]
    df["bbu"] = bb[f"BBU_{BB_LEN}_{BB_STD}"]

    last = df.iloc[-1]
    if last["rsi"] < RSI_BUY and last["close"] < last["bbl"]:
        return "BUY"
    if last["rsi"] > RSI_SELL and last["close"] > last["bbu"]:
        return "SELL"
    return None
