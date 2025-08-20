# main.py
import asyncio
import time
import traceback

from config import (
    API_KEY, API_SECRET, SYMBOL_POOL, SCAN_INTERVAL, DEBUG_MODE,
    LEVERAGE, MAX_PYRAMID, TRAILING_GIVEBACK_PCT, MAX_LOSS_PCT
)
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from filters.symbol_filter import shortlist
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal

print("[BOOT] Starting scanner...")

async def safe_call(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        print(f"[SAFE_CALL] error {func}: {e}")
        traceback.print_exc()
        return None

async def manage_symbol(client, rm, symbol):
    try:
        # Ensure leverage set (best-effort)
        try:
            await client.change_leverage(symbol, LEVERAGE)
        except Exception:
            pass

        # Decide signal: trend first then revert
        signal = await generate_trend_signal(symbol, client)
        if not signal:
            signal = await generate_revert_signal(symbol, client)
        if not signal:
            print(f"[SKIP] {symbol} 無交易訊號")
            return

        # check current position
        pos = await client.get_position(symbol)
        pos_amt = float(pos.get("positionAmt", 0.0)) if pos else 0.0

        # if already position in same direction: consider pyramid
        if pos_amt != 0:
            # same side?
            same_side = (pos_amt > 0 and signal == "LONG") or (pos_amt < 0 and signal == "SHORT")
            if same_side:
                # see if we should pyramid
                if await should_pyramid(symbol, client, pos):
                    print(f"[PYRAMID] {symbol} triggers pyramid")
                    await rm.execute_trade(symbol, signal)
                else:
                    print(f"[HOLD] {symbol} already position and no pyramid condition")
            else:
                # opposite side: you may want to close first - for safety skip
                print(f"[OPPOSITE] {symbol} has opposite position; skipping new entry")
        else:
            # no position -> open new
            print(f"[ENTRY] {symbol} -> {signal}")
            await rm.execute_trade(symbol, signal)
    except Exception as e:
        print(f"[ERROR] manage_symbol {symbol}: {e}")
        traceback.print_exc()

async def scanner():
    client = BinanceClient(API_KEY, API_SECRET)
    rm = RiskManager(client)

    # initial shortlist
    candidates = await shortlist(client, max_candidates=len(SYMBOL_POOL))
    if not candidates:
        candidates = SYMBOL_POOL[:6]

    while True:
        start = time.time()
        # refresh shortlist periodically (optional)
        try:
            candidates = await shortlist(client, max_candidates=len(SYMBOL_POOL))
        except Exception:
            pass
        tasks = []
        for s in candidates:
            tasks.append(manage_symbol(client, rm, s))
        # run concurrently but protect each task
        await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        wait = max(1, SCAN_INTERVAL - elapsed)
        await asyncio.sleep(wait)

if __name__ == "__main__":
    try:
        asyncio.run(scanner())
    except KeyboardInterrupt:
        print("exiting")
