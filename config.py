import os

# Binance API 設定（從環境變數讀取）
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

if not API_KEY or not API_SECRET:
    raise ValueError(
        "❌ 請在 Railway 環境變數中設定 BINANCE_API_KEY 與 BINANCE_API_SECRET"
    )

# 預設交易參數
BASE_QTY = 0.001  # 每筆下單基礎數量
EQUITY_RATIO = 0.1  # 每次使用資金比例 10%

# 交易幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

# 篩選條件
VOLUME_MIN_USD = 30000000  # 24h 成交量最低 3000 萬 USDT
FUNDING_RATE_MIN = -0.05   # 最低資金費率

# 交易策略參數
TREND_EMA_FAST = 12
TREND_EMA_SLOW = 26
MACD_SIGNAL = 9

REVERT_RSI_OVERBOUGHT = 65
REVERT_RSI_OVERSOLD = 35
BOLL_STD_DEV = 2

# K 線設定
KLINE_INTERVAL = "5m"
KLINE_LIMIT = 100

# Railway / Docker 執行參數
DEBUG_MODE = True
