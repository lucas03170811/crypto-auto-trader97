# strategies/revert.py
import pandas as pd
import ta
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

def generate_revert_signal(df: pd.DataFrame):
    rsi = ta.momentum.RSIIndicator(df['close'], window=14)
    df['rsi'] = rsi.rsi()

    boll = ta.volatility.BollingerBands(df['close'], window=20, window_dev=BOLL_STD_DEV)
    df['boll_high'] = boll.bollinger_hband()
    df['boll_low'] = boll.bollinger_lband()

    last = df.iloc[-1]

    # 放寬條件：RSI 觸及極值區 + 收盤價在布林帶外
    if last['rsi'] > REVERT_RSI_OVERBOUGHT and last['close'] > last['boll_high']:
        return "SHORT"
    elif last['rsi'] < REVERT_RSI_OVERSOLD and last['close'] < last['boll_low']:
        return "LONG"

    return None
