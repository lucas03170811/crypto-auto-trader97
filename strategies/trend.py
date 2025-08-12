# strategies/trend.py
import pandas as pd
import pandas_ta as ta

def generate_trend_signal(data) -> str | None:
    """
    data: list of klines (same shape as binance kline)
    回傳 "long", "short" 或 None
    """
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)

    if len(df) < 50:
        return None

    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    if avg_vol < 500_000:
        return None

    df['ema_fast'] = ta.ema(df['close'], length=9)
    df['ema_slow'] = ta.ema(df['close'], length=21)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    macd_val = macd['MACD_12_26_9'].iloc[-1]
    macds = macd['MACDs_12_26_9'].iloc[-1]
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14'].iloc[-1]
    rsi = ta.rsi(df['close'], length=14).iloc[-1]

    # 放寬條件
    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] and adx >= 15 and 30 <= rsi <= 70 and macd_val > macds:
        return "long"
    if df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1] and adx >= 15 and 30 <= rsi <= 70 and macd_val < macds:
        return "short"
    return None
