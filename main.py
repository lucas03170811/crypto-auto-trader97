# main.py
import asyncio
from config import API_KEY, API_SECRET, SYMBOL_POOL, DEBUG_MODE
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal

async def main():
    client = BinanceClient(API_KEY, API_SECRET)
    rm = RiskManager(client)

    print("[BOOT] Starting scanner...")

    # 篩選幣種
    shortlisted = SYMBOL_POOL
    print(f"[SCAN] shortlisted: {shortlisted}")

    for sym in shortlisted:
        try:
            signal = await generate_trend_signal(client, sym)
            if not signal:
                signal = await generate_revert_signal(client, sym)

            if not signal:
                print(f"[NO SIGNAL] {sym}")
                continue

            qty = await rm.get_order_qty(sym)
            if qty <= 0:
                print(f"[RISK] qty too small: {sym}")
                continue

            side = signal["side"]
            print(f"[SIGNAL] {sym} → {side} qty={qty}")

            if side == "LONG":
                await client.open_long(sym, qty)
            else:
                await client.open_short(sym, qty)

            # 滾倉加碼檢查
            if await should_pyramid(client, sym, side):
                add_qty = qty * 0.5  # 每次加碼一半倉位
                print(f"[PYRAMID] Adding position {sym} qty={add_qty}")
                if side == "LONG":
                    await client.open_long(sym, add_qty)
                else:
                    await client.open_short(sym, add_qty)

        except Exception as e:
            print(f"[ERROR] {sym}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
