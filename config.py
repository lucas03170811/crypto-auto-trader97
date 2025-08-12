# config.py
import os
from decimal import Decimal

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

TESTNET = os.getenv("TESTNET", "1") == "1"

BASE_QTY = Decimal(os.getenv("BASE_QTY", "5"))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "10"))
MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))

# 放寬條件以增加每日交易機會
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "500000"))  # 放寬成交量門檻

SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "1000PEPEUSDT","1000BONKUSDT","SUIUSDT","SEIUSDT"
]

# 用於 risk manager
EQUITY_RATIO_PER_TRADE = Decimal(os.getenv("EQUITY_RATIO_PER_TRADE", "0.03"))
