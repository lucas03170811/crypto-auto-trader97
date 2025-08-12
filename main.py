# main.py
import os
import asyncio
import exchange.binance_client
print("[DEBUG] binance_client module path:", exchange.binance_client.__file__)

from strategies.signal_generator import SignalGenerator
from risk.risk_mgr import RiskManager
from exchange.binance_client import BinanceClient
from config import MIN_NOTIONAL

async def main():
    print("[Engine] Initializing...")
    client = BinanceClient()
    sig = SignalGenerator(client)
    risk = RiskManager(client)

    symbols = await sig.get_filtered_symbols()
    print("[Engine] Filtered:", symbols)

    for s in symbols:
        signal = await sig.generate_signal(s)
        pos = await client.get_position(s)
        print(f"[Position] {s}: {pos}")
        if signal and pos == 0:
            print(f"[Trade] {s} -> {signal}")
            qty = await risk.get_order_qty(s)
            if qty <= 0:
                print("[SKIP] qty 0")
                continue
            notional = await risk.get_nominal_value(s, qty)
            if notional < float(MIN_NOTIONAL):
                print(f"[SKIP ORDER] {s} 名目價值過低: {notional}")
                continue
            # 實際下單（使用 place_market_order）
            if signal == "long":
                await client.place_market_order(s, "BUY", qty, positionSide="LONG")
            else:
                await client.place_market_order(s, "SELL", qty, positionSide="SHORT")

    equity = await client.get_equity()
    print(f"[Equity] {equity}")

if __name__ == "__main__":
    asyncio.run(main())
