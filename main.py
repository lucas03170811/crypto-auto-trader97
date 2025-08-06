import asyncio
from engine.hedge_engine import HedgeEngine
from exchange.binance_client import BinanceClient

async def main():
    client = BinanceClient()
    engine = HedgeEngine(client)
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())