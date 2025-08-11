# strategies/trend_signal.py
import pandas as pd
import pandas_ta as ta

def trend_signal(df: pd.DataFrame) -> bool:
    """
    簡化版趨勢策略，放寬成交量 & 技術指標門檻
    """
    if df is None or len(df) < 50:
        return False
    
    # 放寬成交量門檻
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    if avg_vol < 1_000_000:  # 原本可能是 5_000_000
        return False

    # EMA 趨勢
    df['ema_fast'] = ta.ema(df['close'], length=9)
    df['ema_slow'] = ta.ema(df['close'], length=21)

    # ADX 判斷趨勢
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    adx_val = adx['ADX_14'].iloc[-1]

    # RSI
    rsi = ta.rsi(df['close'], length=14).iloc[-1]

    # 放寬條件：ADX >= 15 (原本可能 25)，RSI 不在極端區間即可
    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and adx_val >= 15 and 40 <= rsi <= 60:
        return True

    return False
