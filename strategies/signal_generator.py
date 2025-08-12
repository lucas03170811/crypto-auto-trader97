from .trend import generate_trend_signal  # ✅ 相對匯入
from .revert import generate_revert_signal
from .filter import filter_symbols

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self, symbols):
        return await filter_symbols(self.client)

    async def generate_signal(self, symbol):
        data = await self.client.get_klines(symbol)
        if not data or len(data) < 30:
            print(f"[DATA] {symbol} → insufficient kline data")
            return None

        trend_sig = generate_trend_signal(data)
        revert_sig = generate_revert_signal(data)

        if trend_sig:
            print(f"[SIGNAL] {symbol} → trend={trend_sig.upper()} ✅")
            return trend_sig

        if revert_sig:
            print(f"[SIGNAL] {symbol} → revert={revert_sig.upper()} ✅")
            return revert_sig

        print(f"[NO SIGNAL] {symbol} → trend={trend_sig}, revert={revert_sig}")
        return None
