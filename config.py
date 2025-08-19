import os
from decimal import Decimal

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
TESTNET = os.getenv("TESTNET", "0") == "1"

# order sizing
BASE_QTY = Decimal(os.getenv("BASE_QTY", "5"))        # Decimal legacy
BASE_QTY_USD = float(os.getenv("BASE_QTY_USD", "20")) # float-based nominal target per trade

MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))
EQUITY_RATIO_PER_TRADE = Decimal(os.getenv("EQUITY_RATIO_PER_TRADE", "0.03"))

# trend params
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "9"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "21"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# filter (relaxed)
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "300000"))  # 放寬成每日可交易機率高

# pools & risk
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

PYRAMID_MAX_LAYERS = int(os.getenv("PYRAMID_MAX_LAYERS", "3"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.04"))

DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"
DB_PATH = os.getenv("DB_PATH", "trade_log.db")
