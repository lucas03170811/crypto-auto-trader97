# strategies/signal_generator.py
from strategies.trend import generate_trend_signal
from strategies.revert import generate_revert_signal
from strategies.filter import filter_symbols

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self, symbols):
        # ignore provided symbols param; use filter with client
        return await filter_symbols(self.client)

    async def generate_signal(self, symbol):
        data = await self.client.get_klines(symbol)
        if not data or len(data) < 30:
            print(f"[DATA] {symbol} → insufficient kline data")
            return None

        trend = generate_trend_signal(data)
        revert = generate_revert_signal(data)

        # 放寬：只要任一策略回傳方向就採用
        if trend is not None:
            print(f"[SIGNAL] {symbol} → trend={trend.upper()} ✅")
            return trend
        if revert is not None:
            print(f"[SIGNAL] {symbol} → revert={revert.upper()} ✅")
            return revert

        print(f"[NO SIGNAL] {symbol} → trend={trend}, revert={revert}")
        return None
