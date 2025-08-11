# config.py
import os
from decimal import Decimal

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# 使用 Testnet (1) or Mainnet (0)
TESTNET = os.getenv("TESTNET", "1") == "1"

# 每次下單基礎金額（USDT）
BASE_QTY = Decimal(os.getenv("BASE_QTY", "5"))  

# 下單使用槓桿（若需要）
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "10"))

# 最低名目價值（USDT） — 與交易所 min_notional 對齊
MIN_NOTIONAL = Decimal(os.getenv("MIN_NOTIONAL", "5"))

# 篩選條件（放寬成能每天有交易）
FUNDING_RATE_MIN = Decimal(os.getenv("FUNDING_RATE_MIN", "-0.05"))  # 更寬容
VOLUME_MIN_USD = Decimal(os.getenv("VOLUME_MIN_USD", "500000"))    # 放寬成交量限制

# 幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "1000PEPEUSDT","1000BONKUSUSDT" if False else "1000BONKUSDT"
]

# 風控參數
RISK_SHRINK_THRESHOLD = Decimal("-0.15")
RISK_GROW_THRESHOLD   = Decimal("0.30")
