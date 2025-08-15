# strategies/revert.py
import talib
import numpy as np
from config import REVERT_RSI_OVERBOUGHT, REVERT_RSI_OVERSOLD, BOLL_STD_DEV

async def generate_revert_signal(client, symbol):
    """放寬條件的反轉策略"""
    klines = await client.get_klines(symbol)
    closes = np.array([float(k[4]) for k in klines])

    rsi = talib.RSI(closes, timeperiod=14)
    upper, middle, lower = talib.BBANDS(closes, nbdevup=BOLL_STD_DEV, nbdevdn=BOLL_STD_DEV, timeperiod=20)

    if rsi[-1] > REVERT_RSI_OVERBOUGHT and closes[-1] >= upper[-1]:
        return {"side": "SHORT"}
    elif rsi[-1] < REVERT_RSI_OVERSOLD and closes[-1] <= lower[-1]:
        return {"side": "LONG"}
    return None
