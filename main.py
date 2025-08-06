import asyncio
from engine.hedge_engine import HedgeEngine
from exchange.binance_client import BinanceClient

async def main():
    client = BinanceClient()
    await client.init()
    engine = HedgeEngine(client)
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())
finally:
    await client.close()
