# strategies/trend.py
import asyncio
from typing import Optional, List
import pandas as pd
import numpy as np
from config import KLINE_INTERVAL, KLINE_LIMIT, TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

class TrendStrategy:
    """
    放寬版趨勢策略：
    - 多：EMA_fast > EMA_slow，且 close > EMA_slow（不用嚴格 MACD 轉正）
    - 空：EMA_fast < EMA_slow，且 close < EMA_slow
    - 額外微濾網：MACD 柱狀體 > -0.05 * 平均真實波幅的比例（避免太逆勢）
    """
    def __init__(self, client):
        self.client = client

    async def _fetch_klines(self, symbol: str) -> Optional[pd.DataFrame]:
        k = await self.client.get_klines(symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
        if not k or len(k) < max(TREND_EMA_SLOW, 35):
            return None
        # UMFutures.klines 回傳 [openTime, open, high, low, close, volume, closeTime, ...]
        df = pd.DataFrame(k, columns=[
            "openTime","open","high","low","close","volume","closeTime","qv","trades","taker_base","taker_quote","ignore"
        ])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"]  = pd.to_numeric(df["low"], errors="coerce")
        df.dropna(subset=["close","high","low"], inplace=True)
        return df

    def _ema(self, s: pd.Series, n: int) -> pd.Series:
        return s.ewm(span=n, adjust=False).mean()

    def _atr(self, df: pd.DataFrame, n: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(n).mean()

    def _macd_hist(self, close: pd.Series, fast=12, slow=26, signal=9) -> pd.Series:
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd - signal_line

    async def signal(self, symbol: str) -> Optional[str]:
        df = await self._fetch_klines(symbol)
        if df is None or len(df) < TREND_EMA_SLOW + 5:
            return None

        close = df["close"]
        ema_fast = self._ema(close, TREND_EMA_FAST)
        ema_slow = self._ema(close, TREND_EMA_SLOW)
        atr = self._atr(df, 14)
        hist = self._macd_hist(close, TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL)

        c, ef, es, h, a = close.iloc[-1], ema_fast.iloc[-1], ema_slow.iloc[-1], hist.iloc[-1], atr.iloc[-1]
        if pd.isna([c, ef, es, h, a]).any():
            return None

        # 放寬：只要均線順序 + close 在慢均線一側，MACD 柱狀體不要太負即可
        # 允許輕微背離，幅度控制在 ATR 的 5%
        macd_guard = (-0.05 * max(a, 1e-8))
        if ef > es and c > es and h > macd_guard:
            return "LONG"
        if ef < es and c < es and h < -macd_guard:
            return "SHORT"
        return None
