# main.py
import asyncio
import pandas as pd

from config import (
    API_KEY, API_SECRET,
    SYMBOL_POOL, DEBUG_MODE,
    KLINE_INTERVAL, KLINE_LIMIT
)
from exchange.binance_client import BinanceClient
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal
from risk.risk_mgr import RiskManager

async def fetch_df(client: BinanceClient, symbol: str) -> pd.DataFrame:
    kl = await client.get_klines(symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
    if not kl or len(kl) == 0:
        return pd.DataFrame()

    cols = [
        "open_time","open","high","low","close","volume",
        "close_time","qav","trades","tbav","tbqav","ignore"
    ]
    df = pd.DataFrame(kl, columns=cols)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df.dropna(inplace=True)
    return df

async def process_symbol(symbol: str, client: BinanceClient, risk: RiskManager):
    df = await fetch_df(client, symbol)
    if df.empty or len(df) < 50:
        if DEBUG_MODE:
            print(f"[SKIP] {symbol} insufficient data")
        return

    t_sig = generate_trend_signal(df)      # 'LONG' / 'SHORT' / 'HOLD'
    r_sig = generate_revert_signal(df)     # 'BUY' / 'SELL' / 'HOLD'

    # 訊號合併（先趨勢，後反轉）
    final_side = None
    pyramid = False

    if t_sig in ("LONG", "SHORT"):
        final_side = t_sig
        pyramid = should_pyramid(df)
    elif r_sig in ("BUY", "SELL"):
        final_side = "LONG" if r_sig == "BUY" else "SHORT"
        pyramid = False

    if final_side:
        await risk.execute_order(symbol, final_side, pyramid=pyramid)
    else:
        if DEBUG_MODE:
            print(f"[HOLD] {symbol}")

async def scanner():
    print("[BOOT] Starting scanner...")
    # **關鍵修正：把 API KEY / SECRET 傳進去**
    client = BinanceClient(api_key=API_KEY, api_secret=API_SECRET)
    risk = RiskManager(client)

    # 串行處理，避免超量併發打爆權重（你也可以改成限速的併發）
    for sym in SYMBOL_POOL:
        print(f"[SCAN] {sym}")
        try:
            await process_symbol(sym, client, risk)
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")

if __name__ == "__main__":
    asyncio.run(scanner())
