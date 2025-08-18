# strategies/revert.py
import pandas as pd
import talib
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

def generate_revert_signal(df: pd.DataFrame):
    if len(df) < 50:
        return None

    close = df["close"].astype(float).values

    rsi = talib.RSI(close, timeperiod=14)
    upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=BOLL_STD_DEV, nbdevdn=BOLL_STD_DEV, matype=0)

    # 放寬條件 → RSI 與 BOLL 同時觸發才進場
    if rsi[-1] < REVERT_RSI_OVERSOLD and close[-1] < lower[-1]:
        return "LONG"
    elif rsi[-1] > REVERT_RSI_OVERBOUGHT and close[-1] > upper[-1]:
        return "SHORT"

    return None
