# strategies/trend.py
import talib
import numpy as np
from config import TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL

async def generate_trend_signal(client, symbol):
    """放寬條件的趨勢判斷"""
    klines = await client.get_klines(symbol)
    closes = np.array([float(k[4]) for k in klines])

    ema_fast = talib.EMA(closes, timeperiod=TREND_EMA_FAST)
    ema_slow = talib.EMA(closes, timeperiod=TREND_EMA_SLOW)
    macd, macdsignal, _ = talib.MACD(closes, fastperiod=TREND_EMA_FAST, slowperiod=TREND_EMA_SLOW, signalperiod=MACD_SIGNAL)

    if ema_fast[-1] > ema_slow[-1] and macd[-1] > macdsignal[-1]:
        return {"side": "LONG"}
    elif ema_fast[-1] < ema_slow[-1] and macd[-1] < macdsignal[-1]:
        return {"side": "SHORT"}
    return None

async def should_pyramid(client, symbol, side):
    """判斷是否繼續加碼（單邊趨勢）"""
    position = await client.get_position(symbol)
    if not position or float(position["positionAmt"]) == 0:
        return False

    entry_price = float(position["entryPrice"])
    mark_price = float(await client.get_price(symbol))

    profit_pct = (mark_price - entry_price) / entry_price if side == "LONG" else (entry_price - mark_price) / entry_price

    return profit_pct >= 0.03  # 獲利達 3% 觸發加碼
