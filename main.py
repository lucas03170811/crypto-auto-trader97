# main.py
import asyncio
from config import API_KEY, API_SECRET, SYMBOL_POOL, DEBUG_MODE
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal

async def main():
    print("[BOOT] Starting scanner...")
    for symbol in SYMBOL_POOL:
        print(f"[SCAN] {symbol}")
        # 假資料測試
        # 實際情況應該抓 K 線資料並傳入策略
    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
