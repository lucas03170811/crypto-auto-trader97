# strategies/revert.py
import pandas as pd
import pandas_ta as ta

def generate_revert_signal(data) -> str | None:
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    df['close'] = df['close'].astype(float)

    if len(df) < 30:
        return None

    df.ta.bbands(length=20, append=True)
    df.ta.rsi(length=14, append=True)

    price = df["close"].iloc[-1]
    lower = df["BBL_20_2.0"].iloc[-1]
    upper = df["BBU_20_2.0"].iloc[-1]
    rsi = df["RSI_14"].iloc[-1]

    if price < lower and rsi < 40:
        return "long"
    if price > upper and rsi > 60:
        return "short"
    return None
