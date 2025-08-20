# strategies/revert.py
import pandas as pd
import numpy as np
from typing import Optional
import config

def klines_to_df(klines):
    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_asset_volume","num_trades","taker_buy_base","taker_buy_quote","ignore"]
    try:
        df = pd.DataFrame(klines, columns=cols)
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception:
        arr = []
        for k in klines:
            arr.append({"open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])})
        return pd.DataFrame(arr)

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/period, adjust=False).mean()
    ma_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-12)
    return 100 - (100 / (1 + rs))

async def generate_revert_signal(symbol: str, client=None) -> Optional[str]:
    try:
        if client:
            klines = await client.get_klines(symbol, interval=config.KLINE_INTERVAL, limit=config.KLINE_LIMIT)
        else:
            return None
        df = klines_to_df(klines)
        if df is None or len(df) < config.BOLL_WINDOW + 5:
            return None

        close = df["close"]
        r = rsi(close, period=config.REVERT_RSI_PERIOD)
        ma = close.rolling(window=config.BOLL_WINDOW).mean()
        std = close.rolling(window=config.BOLL_WINDOW).std()
        upper = ma + config.BOLL_STDDEV * std
        lower = ma - config.BOLL_STDDEV * std

        last_close = close.iloc[-1]
        last_rsi = r.iloc[-1] if len(r) > 0 else None

        # loose revert entries:
        if last_close <= lower.iloc[-1] and last_rsi is not None and last_rsi <= config.REVERT_RSI_OVERSOLD:
            return "LONG"
        if last_close >= upper.iloc[-1] and last_rsi is not None and last_rsi >= config.REVERT_RSI_OVERBOUGHT:
            return "SHORT"
        return None
    except Exception as e:
        print(f"[STRATEGY:revert] error {symbol}: {e}")
        return None
