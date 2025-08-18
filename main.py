# main.py
import asyncio
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal
from config import SYMBOL_POOL, DEBUG_MODE

async def scanner():
    print("[BOOT] Starting scanner...")
    client = BinanceClient()
    risk_mgr = RiskManager(client)

    while True:
        for symbol in SYMBOL_POOL:
            print(f"[SCAN] {symbol}")
            df = await client.get_klines(symbol)

            if df is None or df.empty:
                continue

            # 趨勢策略
            trend_signal = generate_trend_signal(df)
            # 反轉策略
            revert_signal = generate_revert_signal(df)

            # 下單邏輯
            if trend_signal in ["BUY", "SELL"]:
                await risk_mgr.execute_order(symbol, trend_signal)

                # 加碼判斷
                if should_pyramid(df, trend_signal):
                    print(f"[PYRAMID] {symbol} 符合加碼條件")
                    await risk_mgr.execute_order(symbol, trend_signal, pyramid=True)

            elif revert_signal in ["BUY", "SELL"]:
                await risk_mgr.execute_order(symbol, revert_signal)

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(scanner())
