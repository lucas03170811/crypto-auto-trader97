# strategies/revert.py
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD

def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss.replace(0, 1e-12))
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_revert_signal(df):
    if df is None or df.empty:
        return None
    rsi = _rsi(df["close"])
    if rsi.iloc[-1] <= REVERT_RSI_OVERSOLD:
        return "LONG"
    if rsi.iloc[-1] >= REVERT_RSI_OVERBOUGHT:
        return "SHORT"
    return None
