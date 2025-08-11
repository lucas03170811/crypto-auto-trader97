# strategies/signal_generator.py
from .filter import shortlist
from .trend import generate_trend_signal
from .revert import generate_revert_signal

TIMEFRAMES = ["15m", "5m"]

class SignalGenerator:
    def __init__(self, client):
        self.client = client

    async def get_filtered_symbols(self):
        return await shortlist(self.client)

    async def generate_signal(self, symbol: str):
        for tf in TIMEFRAMES:
            df = await self.client.get_klines(symbol, interval=tf, limit=200)
            if df is None or len(df) < 30:
                continue

            t_long, t_short = generate_trend_signal(df)
            r_long, r_short, rsi_v, bb_pos = generate_revert_signal(df)

            if t_long or r_long:
                print(f"[SIGNAL] {symbol} @ {tf} -> LONG (trend:{t_long} revert:{r_long} rsi={rsi_v:.1f} bbpos={bb_pos:.2f})")
                return "long"
            if t_short or r_short:
                print(f"[SIGNAL] {symbol} @ {tf} -> SHORT (trend:{t_short} revert:{r_short} rsi={rsi_v:.1f} bbpos={bb_pos:.2f})")
                return "short"

        return None
