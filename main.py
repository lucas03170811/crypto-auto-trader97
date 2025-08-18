# main.py
import asyncio
import pandas as pd
from exchange.binance_client import BinanceClient
from config import API_KEY, API_SECRET, SYMBOL_POOL, DEBUG_MODE, MIN_NOTIONAL_USDT
from strategies.trend import generate_trend_signal
from strategies.revert import generate_revert_signal

async def scanner():
    client = BinanceClient(API_KEY, API_SECRET)

    print("[BOOT] Starting scanner...")
    for symbol in SYMBOL_POOL:
        print(f"[SCAN] {symbol}")
        try:
            df = client.get_klines(symbol)
            if df is None or df.empty:
                continue

            trend_signal = generate_trend_signal(df)
            revert_signal = generate_revert_signal(df)

            if trend_signal:
                print(f"[SIGNAL] {symbol} 趨勢 {trend_signal}")
                client.order(symbol, trend_signal)

            elif revert_signal:
                print(f"[SIGNAL] {symbol} 反轉 {revert_signal}")
                client.order(symbol, revert_signal)

            else:
                if DEBUG_MODE:
                    print(f"[NO SIGNAL] {symbol}")

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(scanner())
