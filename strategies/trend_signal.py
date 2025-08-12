# strategies/trend_signal.py
import pandas as pd
import pandas_ta as ta

def generate_trend_signal(df: pd.DataFrame):
    if df is None or len(df) < 30:
        return None

    # ensure numeric columns exist
    if 'close' not in df.columns:
        return None

    # volume check (放寬)
    if 'volume' in df.columns:
        avg_vol = df['volume'].rolling(14).mean().iloc[-1]
        if avg_vol < 50_000:  # 更寬鬆：50k 成交量門檻
            return None

    df['ema_fast'] = ta.ema(df['close'], length=9)
    df['ema_slow'] = ta.ema(df['close'], length=21)

    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    adx_val = adx['ADX_14'].iloc[-1] if 'ADX_14' in adx else 0
    rsi_val = ta.rsi(df['close'], length=14).iloc[-1]

    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and adx_val >= 12 and 30 <= rsi_val <= 70:
        return "long"
    if df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and adx_val >= 12 and 30 <= rsi_val <= 70:
        return "short"
    return None
