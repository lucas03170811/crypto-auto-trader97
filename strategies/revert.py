# strategies/revert.py
import pandas as pd
import talib
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

def generate_revert_signal(df: pd.DataFrame):
    """產生反轉交易信號"""
    rsi = talib.RSI(df['close'], timeperiod=14)
    upper, middle, lower = talib.BBANDS(df['close'], nbdevup=BOLL_STD_DEV, nbdevdn=BOLL_STD_DEV, timeperiod=20)

    if rsi.iloc[-1] > REVERT_RSI_OVERBOUGHT and df['close'].iloc[-1] > upper.iloc[-1]:
        return "SHORT"
    elif rsi.iloc[-1] < REVERT_RSI_OVERSOLD and df['close'].iloc[-1] < lower.iloc[-1]:
        return "LONG"
    else:
        return None
