import os
import asyncio
import time
from strategies.signal_generator import SignalGenerator
from risk.risk_mgr import RiskManager
from exchange.binance_client import BinanceClient
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    SYMBOL_POOL,
    BASE_QTY,
    MIN_NOTIONAL,
    EQUITY_RATIO_PER_TRADE,
)

async def run_bot():
    client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    signal_generator = SignalGenerator(client)
    risk_mgr = RiskManager(client, EQUITY_RATIO_PER_TRADE)

    while True:
        print(f"\n[Engine] Scan start {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        try:
            filtered_symbols = await signal_generator.get_filtered_symbols(SYMBOL_POOL)
            print(f"[Engine] Filtered symbols: {filtered_symbols}\n")

            for symbol in filtered_symbols:
                signal = await signal_generator.generate_signal(symbol)
                pos = await client.get_position(symbol)
                print(f"[Position] {symbol}: {pos}")

                if signal in ["long", "short"] and pos == 0:
                    print(f"[Trade] Entering {signal.upper()} {symbol}")
                    qty = await risk_mgr.get_order_qty(symbol)
                    notional = await risk_mgr.get_nominal_value(symbol, qty)

                    if notional < MIN_NOTIONAL:
                        print(f"[SKIP ORDER] {symbol} 名目價值過低：{notional:.2f} USDT\n")
                        continue

                    if signal == "long":
                        await client.open_long(symbol, qty)
                    elif signal == "short":
                        await client.open_short(symbol, qty)
                else:
                    print(f"[NO SIGNAL] {symbol} passed filter but no entry signal\n")

            equity = await client.get_equity()
            print(f"\n[Equity] Current equity: {equity:.2f} USDT\n")

        except Exception as e:
            print(f"[ERROR] {e}")

        await asyncio.sleep(60)  # 每分鐘掃描一次

if __name__ == "__main__":
    asyncio.run(run_bot())
