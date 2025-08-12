import pandas as pd
import pandas_ta as ta

def generate_trend_signal(df: pd.DataFrame) -> str | None:
    """
    放寬成交量與技術指標門檻的趨勢策略
    回傳 'long' / 'short' / None
    """
    if df is None or len(df) < 50:
        return None
    
    # 放寬成交量門檻
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    if avg_vol < 500_000:
        return None

    # 計算 EMA
    df['ema_fast'] = ta.ema(df['close'], length=9)
    df['ema_slow'] = ta.ema(df['close'], length=21)

    # ADX
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    adx_val = adx['ADX_14'].iloc[-1]

    # RSI
    rsi_val = ta.rsi(df['close'], length=14).iloc[-1]

    # Long 條件
    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and adx_val >= 15 and 35 <= rsi_val <= 65:
        return "long"
    
    # Short 條件
    if df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and adx_val >= 15 and 35 <= rsi_val <= 65:
        return "short"

    return None
