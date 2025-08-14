# strategies/revert.py
import asyncio
from typing import Optional
import pandas as pd
import numpy as np
from config import KLINE_INTERVAL, KLINE_LIMIT, REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

class RevertStrategy:
    """
    放寬版反轉策略：
    - 多：RSI < (OVERSOLD+5) 且 close 觸及/跌破下布林
    - 空：RSI > (OVERBOUGHT-5) 且 close 觸及/突破上布林
    """
    def __init__(self, client):
        self.client = client

    async def _fetch_klines(self, symbol: str) -> Optional[pd.DataFrame]:
        k = await self.client.get_klines(symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
        if not k or len(k) < 30:
            return None
        df = pd.DataFrame(k, columns=[
            "openTime","open","high","low","close","volume","closeTime","qv","trades","taker_base","taker_quote","ignore"
        ])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df.dropna(subset=["close"], inplace=True)
        return df

    def _rsi(self, close: pd.Series, period=14) -> pd.Series:
        delta = close.diff()
        up = np.where(delta > 0, delta, 0.0)
        down = np.where(delta < 0, -delta, 0.0)
        roll_up = pd.Series(up).ewm(span=period, adjust=False).mean()
        roll_down = pd.Series(down).ewm(span=period, adjust=False).mean()
        rs = roll_up / (roll_down + 1e-8)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi.index = close.index
        return rsi

    async def signal(self, symbol: str) -> Optional[str]:
        df = await self._fetch_klines(symbol)
        if df is None or len(df) < 30:
            return None

        close = df["close"]
        rsi = self._rsi(close, 14)
        ma = close.rolling(20).mean()
        std = close.rolling(20).std().fillna(0.0)
        upper = ma + BOLL_STD_DEV * std
        lower = ma - BOLL_STD_DEV * std

        c, r, u, l = close.iloc[-1], rsi.iloc[-1], upper.iloc[-1], lower.iloc[-1]
        if pd.isna([c, r, u, l]).any():
            return None

        # 放寬：閾值各放寬 5
        if r < (REVERT_RSI_OVERSOLD + 5) and c <= l:
            return "LONG"
        if r > (REVERT_RSI_OVERBOUGHT - 5) and c >= u:
            return "SHORT"
        return None
