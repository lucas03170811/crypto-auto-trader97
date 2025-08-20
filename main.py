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

async def manage_symbol(client, rm, symbol):
    try:
        # 設定槓桿（若已設定過，交易所會忽略）
        await client.change_leverage(symbol, LEVERAGE)

        trend = await generate_trend_signal(client, symbol)
        revert = await generate_revert_signal(client, symbol)
        sig = trend or revert

        if not sig:
            print(f"[SKIP] {symbol} 無交易訊號")
            return

        print(f"[EXEC] {symbol} side={sig}")
        res = await rm.execute_trade(symbol, sig)
        if res:
            print(f"[ORDER OK] {symbol}: {res}")
        else:
            print(f"[ORDER FAIL] {symbol}")

        # 依照你的設計：突破加碼
        if await should_pyramid(client, symbol, side_long=(sig == "LONG")):
            print(f"[PYRAMID] add one more unit {symbol}")
            await rm.execute_trade(symbol, sig)

    except Exception as e:
        print(f"[ERROR] manage_symbol {symbol}: {e}\n{traceback.format_exc()}")

async def scanner():
    client = BinanceClient(API_KEY, API_SECRET, testnet=False)  # 是否用 TESTNET 可改 config.TESTNET
    rm = RiskManager(client)

    while True:
        start = time.time()
        try:
            candidates = await shortlist(client, max_candidates=len(SYMBOL_POOL))
        except Exception as e:
            print(f"[ERROR] shortlist: {e}")
            candidates = SYMBOL_POOL

        try:
            tasks = [ manage_symbol(client, rm, s) for s in candidates ]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"[ERROR] scanner: {e}\n{traceback.format_exc()}")

        elapsed = time.time() - start
        wait = max(1, int(SCAN_INTERVAL - elapsed))
        await asyncio.sleep(wait)

if __name__ == "__main__":
    try:
        asyncio.run(scanner())
    except KeyboardInterrupt:
        print("exiting")
