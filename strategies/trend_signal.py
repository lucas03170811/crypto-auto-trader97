import pandas as pd
import pandas_ta as ta

def trend_signal(df: pd.DataFrame) -> bool:
    """
    放寬成交量與技術指標門檻的趨勢策略
    """
    if df is None or len(df) < 50:
        return False
    
    # 放寬成交量門檻（原本可能是 5M，現在改 500K）
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    if avg_vol < 500_000:
        return False

    # 計算 EMA
    df['ema_fast'] = ta.ema(df['close'], length=9)
    df['ema_slow'] = ta.ema(df['close'], length=21)

    # ADX 趨勢判斷（放寬到 >= 15）
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    adx_val = adx['ADX_14'].iloc[-1]

    # RSI 範圍放寬到 35~65
    rsi = ta.rsi(df['close'], length=14).iloc[-1]

    # 條件：短 EMA 高於長 EMA，ADX >= 15，RSI 不極端
    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and adx_val >= 15 and 35 <= rsi <= 65:
        return True

    return False
