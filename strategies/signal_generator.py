# strategies/signal_generator.py
from .trend import generate_trend_signal
from .revert import generate_revert_signal
from .filter import filter_symbols

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self):
        return await filter_symbols(self.client)

    async def generate_signal(self, symbol):
        df = await self.client.get_klines(symbol)
        if df is None or len(df) < 20:
            return None
        trend = generate_trend_signal(df)
        rlong, rshort = generate_revert_signal(df)
        if trend:
            return trend
        if rlong:
            return "long"
        if rshort:
            return "short"
        return None
