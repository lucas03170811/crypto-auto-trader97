# main.py
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from exchange.binance_client import BinanceClient
from engine.hedge_engine import HedgeEngine
from risk.risk_mgr import RiskManager
from config import TESTNET

async def main():
    client = BinanceClient(testnet=TESTNET)
    risk_mgr = RiskManager(client)
    engine = HedgeEngine(client, risk_mgr)
    try:
        while True:
            await engine.run()
            await asyncio.sleep(60)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
