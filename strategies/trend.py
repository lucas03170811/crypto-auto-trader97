# strategies/trend.py
import pandas as pd
import numpy as np
from typing import Optional
import config

# helper to convert klines raw -> DataFrame
def klines_to_df(klines):
    # klines: list of lists from Binance
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
        # fallback minimal
        arr = []
        for k in klines:
            arr.append({
                "open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])
            })
        return pd.DataFrame(arr)

async def generate_trend_signal(symbol: str, client=None) -> Optional[str]:
    """
    Generate 'LONG' or 'SHORT' or None using EMA + MACD loosening criteria.
    client is optional; if provided it should have get_klines method.
    """
    try:
        if client:
            klines = await client.get_klines(symbol, interval=config.KLINE_INTERVAL, limit=config.KLINE_LIMIT)
        else:
            return None
        df = klines_to_df(klines)
        if df is None or len(df) < max(config.TREND_EMA_SLOW, config.MACD_SIGNAL) + 5:
            return None

        close = df["close"]
        ema_fast = close.ewm(span=config.TREND_EMA_FAST, adjust=False).mean()
        ema_slow = close.ewm(span=config.TREND_EMA_SLOW, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=config.MACD_SIGNAL, adjust=False).mean()

        last_idx = -1
        # loosened entry: EMA fast above slow and MACD above signal (for LONG)
        if ema_fast.iloc[last_idx] > ema_slow.iloc[last_idx] and macd.iloc[last_idx] > macd_signal.iloc[last_idx]:
            return "LONG"
        if ema_fast.iloc[last_idx] < ema_slow.iloc[last_idx] and macd.iloc[last_idx] < macd_signal.iloc[last_idx]:
            return "SHORT"
        return None
    except Exception as e:
        print(f"[STRATEGY:trend] error {symbol}: {e}")
        return None

async def should_pyramid(symbol: str, client, position: dict) -> bool:
    """
    Decide if we should pyramid (add) for a current position.
    Rules:
      - If unrealized profit percentage >= PYRAMID_PROFIT_THRESH -> True
      - OR if PYRAMID_BREAKOUT_ENABLED and current price breaks recent high/low -> True
    position: dict returned by client.get_position(symbol) with 'positionAmt' and 'entryPrice'
    """
    try:
        if not position:
            return False
        amount = float(position.get("positionAmt", 0.0))
        if amount == 0:
            return False
        entry = float(position.get("entryPrice", 0.0)) or 0.0
        side_long = amount > 0

        current_price = await client.get_price(symbol)
        if entry <= 0:
            return False
        profit_pct = (current_price - entry) / entry if side_long else (entry - current_price) / entry
        if profit_pct >= config.PYRAMID_PROFIT_THRESH:
            return True

        if config.PYRAMID_BREAKOUT_ENABLED:
            klines = await client.get_klines(symbol, interval=config.KLINE_INTERVAL, limit=config.PYRAMID_BREAKOUT_LOOKBACK+5)
            df = klines_to_df(klines)
            if df is None or len(df) < 5:
                return False
            if side_long:
                prev_high = df["high"].iloc[-(config.PYRAMID_BREAKOUT_LOOKBACK+1):-1].max()
                if current_price > prev_high:
                    return True
            else:
                prev_low = df["low"].iloc[-(config.PYRAMID_BREAKOUT_LOOKBACK+1):-1].min()
                if current_price < prev_low:
                    return True
        return False
    except Exception as e:
        print(f"[STRATEGY:trend] should_pyramid error {symbol}: {e}")
        return False
