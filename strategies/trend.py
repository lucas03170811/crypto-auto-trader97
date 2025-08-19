# strategies/trend.py
import pandas as pd
import pandas_ta as ta
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

def generate_trend_signal(df: pd.DataFrame):
    """
    Input: pandas.DataFrame with at least columns: ['close','high','low','volume']
    Output: 'long' / 'short' / None
    - Uses EMA crossover + MACD signal with relaxed thresholds for daily trades.
    """
    if df is None:
        return None

    # require minimum rows
    if len(df) < max(TREND_EMA_SLOW + 5, 30):
        return None

    # Ensure numeric
    df = df.copy()
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low']  = pd.to_numeric(df['low'], errors='coerce')
    df['volume'] = pd.to_numeric(df.get('volume', pd.Series([0]*len(df))), errors='coerce')

    # relaxed avg volume filter (prevent tiny illiquid coins)
    avg_vol = df['volume'].rolling(14).mean().iloc[-1]
    try:
        if avg_vol is not None and pd.notna(avg_vol) and float(avg_vol) < 100_000:
            # If volume too low, skip — tweak threshold if you need even more signals
            return None
    except Exception:
        # if volume data problematic, don't let it crash
        pass

    # EMA
    try:
        df['ema_fast'] = ta.ema(df['close'], length=TREND_EMA_FAST)
        df['ema_slow'] = ta.ema(df['close'], length=TREND_EMA_SLOW)
    except Exception:
        # fallback using pandas ewm if pandas_ta fails
        df['ema_fast'] = df['close'].ewm(span=TREND_EMA_FAST, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=TREND_EMA_SLOW, adjust=False).mean()

    # MACD
    macd = ta.macd(df['close'], fast=12, slow=26, signal=MACD_SIGNAL)
    macd_line = macd.get('MACD_12_26_9') if 'MACD_12_26_9' in macd else macd.get('MACD_12_26_9')  # attempt keys
    signal_line = macd.get('MACDs_12_26_9') if 'MACDs_12_26_9' in macd else macd.get('MACDs_12_26_9')

    # fallback: compute simple MACD differences if no pandas_ta
    if macd_line is None or signal_line is None:
        try:
            fast = df['close'].ewm(span=12, adjust=False).mean()
            slow = df['close'].ewm(span=26, adjust=False).mean()
            macd_line = fast - slow
            signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
        except Exception:
            return None

    # take last values
    try:
        ema_f = df['ema_fast'].iloc[-1]
        ema_s = df['ema_slow'].iloc[-1]
        m = macd_line.iloc[-1]
        s = signal_line.iloc[-1]
    except Exception:
        return None

    # relaxed thresholds for daily signals
    # If EMAs crossing and MACD above/below its signal -> trend
    if pd.notna(ema_f) and pd.notna(ema_s) and pd.notna(m) and pd.notna(s):
        if (ema_f > ema_s) and (m > s):
            return 'long'
        if (ema_f < ema_s) and (m < s):
            return 'short'

    return None
