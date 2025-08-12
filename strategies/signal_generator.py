# strategies/signal_generator.py
from .trend import generate_trend_signal
from .revert import generate_revert_signal
from .filter import filter_symbols

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self, pool=None):
        return await filter_symbols(self.client)

    async def generate_signal(self, symbol):
        df = await self.client.get_klines(symbol)
        if df is None or len(df) < 30:
            return None
        t = generate_trend_signal(df)
        if t:
            return t
        r = generate_revert_signal(df)
        return r
