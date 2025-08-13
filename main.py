# main.py
import os
import asyncio
from statistics import mean
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET,
    API_KEY, API_SECRET,
    BASE_QTY, EQUITY_RATIO,
    KLINE_INTERVAL, KLINE_LIMIT,
    TREND_EMA_FAST, TREND_EMA_SLOW, MACD_SIGNAL,
    DEBUG_MODE
)
from exchange.binance_client import BinanceClient
from filters.symbol_filter import shortlist
from risk.risk_mgr import RiskManager

def ema(values, length):
    if not values or len(values) < length:
        return None
    k = 2 / (length + 1)
    ema_val = mean(values[:length])
    for v in values[length:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

async def gen_trend_signal(closes):
    """簡單 EMA 快慢線 + MACD signal 判斷"""
    if len(closes) < max(TREND_EMA_SLOW + MACD_SIGNAL, 35):
        return None

    fast = ema(closes, TREND_EMA_FAST)
    slow = ema(closes, TREND_EMA_SLOW)
    if fast is None or slow is None:
        return None

    macd_line = fast - slow

    # 粗略做個 signal 線（MACD_LINE 的 EMA）
    # 取最近 TREND_EMA_SLOW 根的 macd 值來算 signal
    macd_series = []
    # 建一組 macd 序列（簡化：以移動窗計算）
    for i in range(TREND_EMA_SLOW, len(closes)):
        sub_fast = ema(closes[:i], TREND_EMA_FAST)
        sub_slow = ema(closes[:i], TREND_EMA_SLOW)
        if sub_fast is None or sub_slow is None:
            macd_series.append(0.0)
        else:
            macd_series.append(sub_fast - sub_slow)

    sig = ema(macd_series, MACD_SIGNAL) if len(macd_series) >= MACD_SIGNAL else None
    if sig is None:
        return None

    if macd_line > sig and fast > slow:
        return "LONG"
    if macd_line < sig and fast < slow:
        return "SHORT"
    return None

async def get_closes(client, symbol):
    kl = await client.get_klines(symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
    if not kl:
        return []
    # UMFutures.klines 回傳：[openTime, open, high, low, close, volume, ...]
    closes = [ float(k[4]) for k in kl if len(k) > 4 ]
    return closes

async def main():
    # 取金鑰：ENV 優先，其次 config 兩種名稱都可
    key = os.getenv("BINANCE_API_KEY") or os.getenv("API_KEY") or BINANCE_API_KEY or API_KEY
    sec = os.getenv("BINANCE_API_SECRET") or os.getenv("API_SECRET") or BINANCE_API_SECRET or API_SECRET

    if not key or not sec:
        print("[FATAL] API key/secret not set. Set env or config.py.")
        return

    client = BinanceClient(key, sec)
    rm = RiskManager(client, EQUITY_RATIO)

    print("[BOOT] Starting scanner...")
    symbols = await shortlist(client, max_candidates=6)
    print(f"[SCAN] shortlisted: {symbols}")

    for sym in symbols:
        closes = await get_closes(client, sym)
        if len(closes) < 30:
            print(f"[SKIP] not enough data: {sym}")
            continue

        sig = await gen_trend_signal(closes)
        if not sig:
            print(f"[NO SIGNAL] {sym}")
            continue

        qty = await rm.get_order_qty(sym, min_qty=BASE_QTY)
        if qty <= 0:
            print(f"[RISK] qty too small: {sym}")
            continue

        if sig == "LONG":
            await client.open_long(sym, qty)
        elif sig == "SHORT":
            await client.open_short(sym, qty)

        await asyncio.sleep(0.5)  # 避免打太快

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
