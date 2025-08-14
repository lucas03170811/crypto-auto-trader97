# main.py
import asyncio
import pandas as pd
from config import (
    API_KEY, API_SECRET, SYMBOL_POOL, BASE_QTY, EQUITY_RATIO,
    KLINE_INTERVAL, KLINE_LIMIT, DEBUG_MODE
)
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal

# 全局紀錄持倉最高價 / 最低價，用來計算移動停損
trade_tracker = {}

async def main():
    client = BinanceClient(API_KEY, API_SECRET)
    rm = RiskManager(client, EQUITY_RATIO)

    print("[BOOT] Starting scanner...")

    while True:
        shortlisted = SYMBOL_POOL
        print(f"[SCAN] shortlisted: {shortlisted}")

        for sym in shortlisted:
            klines = await client.get_klines(sym, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
            if not klines:
                continue

            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "_", "__", "___", "____", "_____", "______"
            ])
            df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})

            trend_signal = generate_trend_signal(df)
            revert_signal = generate_revert_signal(df)
            signal = trend_signal or revert_signal

            pos = await client.get_position(sym)
            price = await client.get_price(sym)

            # ===== 有持倉時，檢查風控 =====
            if pos != 0:
                entry_price = trade_tracker.get(sym, {}).get("entry_price", price)
                direction = "LONG" if pos > 0 else "SHORT"

                # 更新最高/最低價
                if direction == "LONG":
                    trade_tracker[sym]["peak_price"] = max(trade_tracker[sym]["peak_price"], price)
                else:
                    trade_tracker[sym]["peak_price"] = min(trade_tracker[sym]["peak_price"], price)

                # 移動停損 - 回吐 15% 停利
                peak = trade_tracker[sym]["peak_price"]
                if direction == "LONG":
                    if price <= peak * 0.85:
                        await client.open_short(sym, abs(pos))  # 平倉
                        print(f"[TRAIL STOP] {sym} LONG exited at {price} (from peak {peak})")
                        trade_tracker.pop(sym, None)
                        continue
                else:  # SHORT
                    if price >= peak * 1.15:
                        await client.open_long(sym, abs(pos))  # 平倉
                        print(f"[TRAIL STOP] {sym} SHORT exited at {price} (from trough {peak})")
                        trade_tracker.pop(sym, None)
                        continue

                # 固定止損 - 虧損達 30%
                if direction == "LONG":
                    if price <= entry_price * 0.7:
                        await client.open_short(sym, abs(pos))
                        print(f"[STOP LOSS] {sym} LONG stopped at {price}")
                        trade_tracker.pop(sym, None)
                        continue
                else:
                    if price >= entry_price * 1.3:
                        await client.open_long(sym, abs(pos))
                        print(f"[STOP LOSS] {sym} SHORT stopped at {price}")
                        trade_tracker.pop(sym, None)
                        continue

                # 單邊趨勢加碼
                if should_pyramid(df, direction):
                    qty = await rm.get_order_qty(sym)
                    if qty > 0:
                        if direction == "LONG":
                            await client.open_long(sym, qty)
                        else:
                            await client.open_short(sym, qty)
                        print(f"[PYRAMID] Added position on {sym}, direction={direction}, qty={qty}")
                continue  # 已有持倉則不開新反向

            # ===== 無持倉時，開倉 =====
            if signal:
                qty = await rm.get_order_qty(sym, min_qty=BASE_QTY)
                if qty <= 0:
                    print(f"[RISK] qty too small: {sym}")
                    continue

                if signal == "LONG":
                    await client.open_long(sym, qty)
                    trade_tracker[sym] = {
                        "entry_price": price,
                        "peak_price": price
                    }
                elif signal == "SHORT":
                    await client.open_short(sym, qty)
                    trade_tracker[sym] = {
                        "entry_price": price,
                        "peak_price": price
                    }

        await asyncio.sleep(60)  # 每分鐘掃描

if __name__ == "__main__":
    asyncio.run(main())
