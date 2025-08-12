# strategies/trend.py
import pandas as pd
import pandas_ta as ta

def generate_trend_signal(df: pd.DataFrame):
    if df is None or len(df) < 30:
        return None

    # 簡單檢查成交量（放寬）
    avg_vol = df["volume"].rolling(14).mean().iloc[-1]
    if avg_vol < 100_000:  # 放寬門檻為 100k
        return None

    df["ema_fast"] = ta.ema(df["close"], length=9)
    df["ema_slow"] = ta.ema(df["close"], length=21)

    adx = ta.adx(df["high"], df["low"], df["close"], length=14)["ADX_14"].iloc[-1]
    rsi = ta.rsi(df["close"], length=14).iloc[-1]

    if df["ema_fast"].iloc[-1] > df["ema_slow"].iloc[-1] and adx >= 12 and 30 <= rsi <= 70:
        return "long"
    if df["ema_fast"].iloc[-1] < df["ema_slow"].iloc[-1] and adx >= 12 and 30 <= rsi <= 70:
        return "short"
    return None
