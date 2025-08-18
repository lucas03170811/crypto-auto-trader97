# main.py
import asyncio
import pandas as pd
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from config import SYMBOL_POOL, DEBUG_MODE, BASE_QTY
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal

client = BinanceClient()
risk = RiskManager(client)

async def scanner():
    print("[BOOT] Starting scanner...")
    while True:
        for sym in SYMBOL_POOL:
            print(f"[SCAN] {sym}")
            try:
                df = await client.get_klines_df(sym)
                if df is None or df.empty:
                    print(f"[NO DATA] {sym}")
                    continue

                # 產生交易信號
                signal = generate_trend_signal(df) or generate_revert_signal(df)

                if signal:
                    print(f"[SIGNAL] {sym} -> {signal}")

                    # 取得下單數量
                    qty = risk.get_order_qty(sym, BASE_QTY)
                    if qty <= 0:
                        print(f"[RISK] qty too small: {sym}")
                        continue

                    # 根據訊號下單
                    if signal == "LONG":
                        await client.open_long(sym, qty)
                    elif signal == "SHORT":
                        await client.open_short(sym, qty)

                    # 加碼判斷
                    if should_pyramid(df, signal):
                        print(f"[PYRAMID] {sym} 加碼 {signal}")
                        await client.open_long(sym, qty) if signal == "LONG" else await client.open_short(sym, qty)

                else:
                    print(f"[NO SIGNAL] {sym}")

            except Exception as e:
                print(f"[ERROR] {sym}: {e}")

        await asyncio.sleep(60)  # 每分鐘掃描一次

if __name__ == "__main__":
    asyncio.run(scanner())
