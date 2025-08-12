import os
from decimal import Decimal

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

TESTNET = os.getenv("TESTNET", "0") == "1"

# 每次下單基礎金額（USDT）
BASE_QTY = Decimal(os.getenv("BASE_QTY", "5"))

# 最低名目價值（USDT）
MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))

# 單筆倉位使用總資產百分比（risk mgr 會轉 float）
EQUITY_RATIO_PER_TRADE = Decimal(os.getenv("EQUITY_RATIO_PER_TRADE", "0.03"))

# 放寬篩選條件（為了能每天交易）
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "300000"))  # 放寬為 300k

SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "1000PEPEUSDT","1000BONKUSDT","SUIUSDT","SEIUSDT"
]
