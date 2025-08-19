# strategies/trend.py
import pandas as pd
import pandas_ta as ta
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    if df is None or len(df) < max(TREND_EMA_SLOW+5, 30):
        return None

    df = df.copy()
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low']  = pd.to_numeric(df['low'], errors='coerce')
    df['volume'] = pd.to_numeric(df.get('volume', pd.Series([0]*len(df))), errors='coerce')

    # relaxed volume filter
    try:
        avg_vol = df['volume'].rolling(14).mean().iloc[-1]
        if avg_vol is not None and pd.notna(avg_vol) and float(avg_vol) < 100_000:
            return None
    except Exception:
        pass

    # EMA and MACD
    try:
        df['ema_fast'] = ta.ema(df['close'], length=TREND_EMA_FAST)
        df['ema_slow'] = ta.ema(df['close'], length=TREND_EMA_SLOW)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=MACD_SIGNAL)
    except Exception:
        df['ema_fast'] = df['close'].ewm(span=TREND_EMA_FAST, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=TREND_EMA_SLOW, adjust=False).mean()
        fast = df['close'].ewm(span=12, adjust=False).mean()
        slow = df['close'].ewm(span=26, adjust=False).mean()
        macd = {'MACD_12_26_9': fast - slow, 'MACDs_12_26_9': (fast - slow).ewm(span=MACD_SIGNAL, adjust=False).mean()}

    macd_line = macd.get('MACD_12_26_9')
    signal_line = macd.get('MACDs_12_26_9')

    try:
        ema_f = df['ema_fast'].iloc[-1]
        ema_s = df['ema_slow'].iloc[-1]
        m = macd_line.iloc[-1]
        s = signal_line.iloc[-1]
    except Exception:
        return None

    if pd.notna(ema_f) and pd.notna(ema_s) and pd.notna(m) and pd.notna(s):
        if (ema_f > ema_s) and (m > s):
            return 'long'
        if (ema_f < ema_s) and (m < s):
            return 'short'
    return None

def should_pyramid(df: pd.DataFrame, direction: str) -> bool:
    """
    Decide whether to pyramid (add units) when trend continues.
    direction: 'long' or 'short'
    Heuristic: ADX strong + EMA separation magnitude
    """
    if df is None or len(df) < 20:
        return False
    try:
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14'].iloc[-1]
        ema_fast = ta.ema(df['close'], length=TREND_EMA_FAST).iloc[-1]
        ema_slow = ta.ema(df['close'], length=TREND_EMA_SLOW).iloc[-1]
        sep = abs((ema_fast - ema_slow) / (ema_slow + 1e-9))
        # pyramid if trend momentum decent and ADX indicates trend
        return adx >= 20 and sep >= 0.0015
    except Exception:
        return False
