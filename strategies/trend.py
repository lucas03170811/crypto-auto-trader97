# strategies/trend.py
import pandas as pd
import talib

# 單邊趨勢判斷（EMA + MACD）
def generate_trend_signal(df: pd.DataFrame):
    close = df['close'].values

    ema_fast = talib.EMA(close, timeperiod=12)
    ema_slow = talib.EMA(close, timeperiod=26)

    macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

    # 放寬進場條件
    # 原本要明顯的 EMA 排列才進場，現在只要差距大於 0.05% 就進
    if ema_fast[-1] > ema_slow[-1] * 1.0005 and macd[-1] > signal[-1]:
        return "LONG"
    elif ema_fast[-1] < ema_slow[-1] * 0.9995 and macd[-1] < signal[-1]:
        return "SHORT"
    return None

# 單邊加碼判斷
def should_pyramid(df: pd.DataFrame, direction: str):
    """
    判斷是否應該在單邊行情中加碼
    條件：
    1. 方向一致（LONG → EMA 快線 > 慢線；SHORT → EMA 快線 < 慢線）
    2. 價格比上一筆加碼時高（LONG）或低（SHORT）
    """
    close = df['close'].values
    ema_fast = talib.EMA(close, timeperiod=12)
    ema_slow = talib.EMA(close, timeperiod=26)

    if direction == "LONG":
        return ema_fast[-1] > ema_slow[-1] and close[-1] > close[-3]
    elif direction == "SHORT":
        return ema_fast[-1] < ema_slow[-1] and close[-1] < close[-3]
    return False
