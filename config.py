# config.py
import os
from decimal import Decimal

# ===== Binance API (use Railway / env variables) =====
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# Use testnet? (set TESTNET=1 to use testnet)
TESTNET = os.getenv("TESTNET", "0") == "1"

# ===== Order / size defaults =====
# Many parts of your code referenced BASE_QTY (Decimal) and BASE_QTY_USD etc.
BASE_QTY = Decimal(os.getenv("BASE_QTY", "5"))         # default each order nominal USDT (legacy)
BASE_QTY_USD = float(os.getenv("BASE_QTY_USD", "20"))  # alternative float-based size

# Minimum notional enforced by exchange (fallback)
MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))

# If some code expects % of equity per trade:
EQUITY_RATIO_PER_TRADE = Decimal(os.getenv("EQUITY_RATIO_PER_TRADE", "0.03"))

# ===== Strategy params (trend) =====
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "9"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "21"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# ===== Pyramiding / scaling =====
PYRAMID_MAX_LAYERS = int(os.getenv("PYRAMID_MAX_LAYERS", "3"))
PYRAMID_SCALE = Decimal(os.getenv("PYRAMID_SCALE", "1.5"))

# ===== Risk params =====
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))    # 2% stop loss
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.04"))# 4% take profit

# ===== Filtering defaults (relaxed for daily trades) =====
# Make these looser so your filter allows more trades
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "300000"))  # lowered

# Symbol pool (modify as you like)
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

# DEBUG / misc
DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"

# DB path (if other modules use it)
DB_PATH = os.getenv("DB_PATH", "trade_log.db")
