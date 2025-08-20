# main.py
import asyncio
import time
from typing import List

# 請確保 config.py 會 export 這些名稱
from config import API_KEY, API_SECRET, SYMBOL_POOL, DEBUG_MODE, EQUITY_RATIO

# 正確路徑：strategies（注意不是 strategy）
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from filters.symbol_filter import shortlist as shortlist_symbols

print("[BOOT] Starting scanner...")

async def scan_once(client, rm, symbols: List[str]):
    print(f"[SCAN] shortlisted: {symbols}")
    for sym in symbols:
        print(f"[SCAN] {sym}")
        # 產生訊號（先用趨勢策略，若沒訊號再用反轉）
        signal = None
        try:
            signal = await generate_trend_signal(sym)  # 假設 generate_trend_signal 可以用 sym 作為唯一引數
        except TypeError:
            # 如果你的 generate_trend_signal 是 sync 就改成 await asyncio.to_thread(...)
            try:
                signal = generate_trend_signal(sym)
            except Exception as e:
                print(f"[WARN] trend signal error {sym}: {e}")
                signal = None
        except Exception as e:
            print(f"[WARN] trend signal error {sym}: {e}")
            signal = None

        if not signal:
            try:
                signal = await generate_revert_signal(sym)
            except TypeError:
                try:
                    signal = generate_revert_signal(sym)
                except Exception as e:
                    print(f"[WARN] revert signal error {sym}: {e}")
                    signal = None
            except Exception as e:
                print(f"[WARN] revert signal error {sym}: {e}")
                signal = None

        if not signal:
            print(f"[SKIP] {sym} 無交易訊號")
            continue

        # 取得下單數量（RiskManager 應提供 get_order_qty）
        qty = await rm.get_order_qty(sym)
        if qty <= 0:
            print(f"[RISK] qty too small: {sym}")
            continue

        # 根據 signal 下單（open_long / open_short）
        try:
            if signal == "LONG":
                res = await client.open_long(sym, qty)
                print(f"[ORDER] Long {sym}: {res}")
            elif signal == "SHORT":
                res = await client.open_short(sym, qty)
                print(f"[ORDER] Short {sym}: {res}")
            else:
                print(f"[UNKNOWN SIGNAL] {sym} -> {signal}")
        except Exception as e:
            print(f"[ERROR] Failed to place order for {sym}: {e}")

async def main_loop():
    # 建立 client / risk manager
    client = BinanceClient(API_KEY, API_SECRET)  # 大部分 binance client 建構子是 (api_key, api_secret)
    rm = RiskManager(client, EQUITY_RATIO)

    # 初次篩選（如果你想每次都用 filters.shortlist，可以在這裡呼叫）
    filtered = await shortlist_symbols(client, max_candidates=len(SYMBOL_POOL))
    if not filtered:
        filtered = SYMBOL_POOL[:6]  # fallback
    # main loop：每分鐘掃描一次
    while True:
        await scan_once(client, rm, filtered)
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("exiting")
