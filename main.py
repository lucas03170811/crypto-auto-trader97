import exchange.binance_client
print("[DEBUG] binance_client module path:", exchange.binance_client.__file__)

import config
print("[DEBUG] MIN_NOTIONAL:", config.MIN_NOTIONAL)

import asyncio
from strategies.signal_generator import SignalGenerator
from risk.risk_mgr import RiskManager
from exchange.binance_client import BinanceClient
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    SYMBOL_POOL,
    MIN_NOTIONAL,
    EQUITY_RATIO_PER_TRADE,
)
import os

# ✅ 部署時檢查 trend.py 存在
trend_path = os.path.join(os.path.dirname(__file__), "strategies", "trend.py")
print(f"[DEBUG] Checking for {trend_path} ... Exists? {os.path.exists(trend_path)}")

async def main():
    print("\n[Engine] Initializing...\n")

    client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    signal_generator = SignalGenerator(client)
    risk_mgr = RiskManager(client, EQUITY_RATIO_PER_TRADE)

    print("[Engine] Running scan...\n")
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
                print(f"[SKIP ORDER] {symbol} 名目價值過低：{notional:.2f} USDT（低於最低限制）\n")
                continue

            if signal == "long":
                await client.open_long(symbol, qty)
            elif signal == "short":
                await client.open_short(symbol, qty)
        else:
            print(f"[NO SIGNAL] {symbol} passed filter but no entry signal\n")

    equity = await client.get_equity()
    print(f"\n[Equity] Current equity: {equity:.2f} USDT\n")

if __name__ == "__main__":
    asyncio.run(main())
