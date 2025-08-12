# config.py
import os
from decimal import Decimal

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

TESTNET = os.getenv("TESTNET", "0") == "1"

# 每次下單基礎金額（USDT）
BASE_QTY_USDT = Decimal(os.getenv("BASE_QTY_USDT", "5"))

# 最低名目價值（USDT） — 與交易所 min_notional 對齊
MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))

# 放寬的篩選（讓每日更容易有交易）
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "300000"))  # 放寬至 300k
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))

# 幣種池（可擴張）
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

# 每次下單占 equity 比例（risk manager fallback）
EQUITY_RATIO_PER_TRADE = Decimal(os.getenv("EQUITY_RATIO_PER_TRADE", "0.03"))
