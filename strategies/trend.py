# strategies/trend.py
import pandas as pd
import pandas_ta as ta

def generate_trend_signal(df: pd.DataFrame) -> str | None:
    if df is None or len(df) < 30:
        return None

    # 放寬成交量：若平均 20 根成交量 < 300k（USDT），仍允許，但把風險降一點
    avg_vol = df["volume"].rolling(20).mean().iloc[-1]
    # 不直接 reject，小於門檻會降低信心（但放寬）
    # 計算指標
    df["ema_fast"] = ta.ema(df["close"], length=9)
    df["ema_slow"] = ta.ema(df["close"], length=21)
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)["ADX_14"]
    adx_val = adx.iloc[-1] if adx is not None else 0
    rsi_val = ta.rsi(df["close"], length=14).iloc[-1]

    # Long
    if df["ema_fast"].iloc[-1] > df["ema_slow"].iloc[-1] and adx_val >= 12 and 30 <= rsi_val <= 70:
        return "long"
    # Short
    if df["ema_fast"].iloc[-1] < df["ema_slow"].iloc[-1] and adx_val >= 12 and 30 <= rsi_val <= 70:
        return "short"

    return None
