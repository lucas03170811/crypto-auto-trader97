# strategies/revert.py
import pandas as pd
import talib

# 反轉策略（RSI + BOLL）
def generate_revert_signal(df: pd.DataFrame):
    close = df['close'].values

    rsi = talib.RSI(close, timeperiod=14)
    upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

    # 放寬條件
    # 原本 RSI > 70 超買 / < 30 超賣
    # 現在 RSI > 65 超買 / < 35 超賣
    if rsi[-1] > 65 and close[-1] > upper[-1]:
        return "SHORT"
    elif rsi[-1] < 35 and close[-1] < lower[-1]:
        return "LONG"
    return None
