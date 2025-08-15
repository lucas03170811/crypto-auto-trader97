# main.py
import asyncio
from exchange.binance_client import BinanceClient
from risk.risk_mgr import RiskManager
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal
from config import SYMBOL_POOL, DEBUG_MODE, TRAIL_GIVEBACK_PCT, MAX_LOSS_PCT

async def manage_position(client, symbol, side):
    """監控倉位，觸發移動停損與固定止損"""
    position = await client.get_position(symbol)
    if not position or float(position["positionAmt"]) == 0:
        return

    entry_price = float(position["entryPrice"])
    mark_price = float(await client.get_price(symbol))
    qty = abs(float(position["positionAmt"]))

    profit_pct = (mark_price - entry_price) / entry_price if side == "LONG" else (entry_price - mark_price) / entry_price

    # 固定止損
    if profit_pct <= -MAX_LOSS_PCT:
        print(f"[STOP LOSS] {symbol} 達到固定止損 {profit_pct:.2%}，平倉")
        await client.close_position(symbol)
        return

    # 移動停損
    if profit_pct >= TRAIL_GIVEBACK_PCT:
        trail_price = entry_price * (1 + profit_pct - TRAIL_GIVEBACK_PCT) if side == "LONG" else entry_price * (1 - profit_pct + TRAIL_GIVEBACK_PCT)
        if (side == "LONG" and mark_price <= trail_price) or (side == "SHORT" and mark_price >= trail_price):
            print(f"[TRAIL STOP] {symbol} 回調超過 {TRAIL_GIVEBACK_PCT:.2%}，平倉")
            await client.close_position(symbol)

async def main():
    client = BinanceClient()
    rm = RiskManager(client)

    print("[BOOT] Starting scanner...")

    for symbol in SYMBOL_POOL:
        try:
            trend_signal = await generate_trend_signal(client, symbol)
            revert_signal = await generate_revert_signal(client, symbol)

            signal = trend_signal or revert_signal
            if not signal:
                if DEBUG_MODE:
                    print(f"[NO SIGNAL] {symbol}")
                continue

            side = signal["side"]

            # 加碼判斷
            if await should_pyramid(client, symbol, side):
                print(f"[PYRAMID] {symbol} 單邊行情持續，加碼進場")
                qty = await rm.get_order_qty(symbol)
                await client.open_position(symbol, side, qty)
                continue

            # 一般開倉
            qty = await rm.get_order_qty(symbol)
            if qty:
                await client.open_position(symbol, side, qty)

            # 監控倉位
            await manage_position(client, symbol, side)

        except Exception as e:
            print(f"[ERROR] {symbol} - {e}")

if __name__ == "__main__":
    asyncio.run(main())
