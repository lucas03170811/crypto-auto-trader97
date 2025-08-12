# strategies/signal_generator.py
from strategies.trend import generate_trend_signal
from strategies.revert import generate_revert_signal
from strategies.filter import filter_symbols

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

        trend_signal = generate_trend_signal(data)
        revert_long, revert_short, r_val, bb_pos = generate_revert_signal(data)

        if trend_signal is not None:
            print(f"[SIGNAL] {symbol} → trend={trend_signal.upper()} ✅")
            return trend_signal

        if revert_long:
            print(f"[SIGNAL] {symbol} → revert=LONG ✅ (RSI={r_val:.2f}, BB={bb_pos:.2f})")
            return "long"

        if revert_short:
            print(f"[SIGNAL] {symbol} → revert=SHORT ✅ (RSI={r_val:.2f}, BB={bb_pos:.2f})")
            return "short"

        print(f"[NO SIGNAL] {symbol} → trend={trend_signal}, revert_long={revert_long}, revert_short={revert_short}")
        return None
