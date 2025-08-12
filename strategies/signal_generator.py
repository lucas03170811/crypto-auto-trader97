# strategies/signal_generator.py
from .trend_signal import generate_trend_signal
from .revert_signal import generate_revert_signal
from filters.symbol_filter import shortlist as filter_symbols

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self):
        return await filter_symbols(self.client)

    async def generate_signal(self, symbol):
        df = await self.client.get_klines(symbol)
        if df is None or len(df) < 30:
            print(f"[DATA] {symbol} insufficient kline data")
            return None

        t = generate_trend_signal(df)
        if t:
            print(f"[SIGNAL] {symbol} -> trend {t}")
            return t

        r = generate_revert_signal(df)
        if r:
            print(f"[SIGNAL] {symbol} -> revert {r}")
            return r

        return None
