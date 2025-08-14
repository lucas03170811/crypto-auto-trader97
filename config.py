# config.py

# Binance API 設定（記得替換成你自己的 API Key / Secret）
BINANCE_API_KEY = "YOUR_BINANCE_API_KEY"
BINANCE_API_SECRET = "YOUR_BINANCE_API_SECRET"

# 預設交易參數
BASE_QTY = 0.001  # 每筆下單基礎數量
EQUITY_RATIO = 0.1  # 每次使用資金比例 10%

# 交易幣種池
SYMBOL_POOL = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "MATICUSDT",
    "SUIUSDT", "SEIUSDT", "1000PEPEUSDT", "1000BONKUSDT"
]

# 篩選條件
VOLUME_MIN_USD = 30000000  # 24h 成交量最低 3000 萬 USDT
FUNDING_RATE_MIN = -0.05   # 最低資金費率

# 交易策略參數
TREND_EMA_FAST = 12
TREND_EMA_SLOW = 26
MACD_SIGNAL = 9

REVERT_RSI_OVERBOUGHT = 60
REVERT_RSI_OVERSOLD = 40
BOLL_STD_DEV = 2

# K 線設定
KLINE_INTERVAL = "5m"
KLINE_LIMIT = 100

# Railway / Docker 執行參數
DEBUG_MODE = True

# ===== 風控參數 =====
# 單次交易佔可用資金比例
EQUITY_RATIO = 0.1

# 最大虧損百分比（0.30 = 30%）
MAX_LOSS_PCT = 0.30

# 追蹤停利回吐百分比（0.15 = 15%）
TRAIL_GIVEBACK_PCT = 0.15

# ===== 滾倉加碼設定 =====
# 是否啟用單邊滾倉
PYR_ENABLED = True

# 每次加碼倉位相對於初始倉位的比例
PYR_ADD_RATIO = 0.5

# 最大加碼次數
PYR_MAX_ADDS = 3

# 加碼觸發百分比（0.006 = 0.6% 價格突破/跌破）
PYR_TRIGGER_PCT = 0.006
