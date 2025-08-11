# main.py
import asyncio
import os
from exchange.binance_client import BinanceClient
from risk.risk_manager import RiskManager
from engine.hedge_engine import HedgeEngine
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = BinanceClient()
    risk_mgr = RiskManager(client)
    engine = HedgeEngine(client, risk_mgr)
    try:
        await engine.run()
    finally:
        # no-op placeholder
        if hasattr(client, "close"):
            try:
                await client.close()
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(main())
