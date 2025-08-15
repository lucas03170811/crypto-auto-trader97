# config.py
import os
import sys

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# Binance API Key & Secret 從環境變數讀取（Railway 使用 BINANCE_API_KEY / BINANCE_API_SECRET）
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

if not API_KEY or not API_SECRET:
    print("[ERROR] 環境變數 BINANCE_API_KEY 或 BINANCE_API_SECRET 未設定，請到 Railway 設定 Environment Variables")
    sys.exit(1)

print(f"API_KEY: {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
print(f"API_SECRET: {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")

# 交易風控參數
MAX_LOSS_PCT = 0.3               # 固定止損百分比
TRAIL_GIVEBACK_PCT = 0.15        # 獲利回調觸發移動停損
EQUITY_RATIO = 0.1               # 每次下單使用資金比例

# 交易幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# 篩選條件
VOLUME_MIN_USD = 300000
FUNDING_RATE_MIN = -0.05

# 趨勢策略參數
TREND_EMA_FAST = 12
TREND_EMA_SLOW = 26
MACD_SIGNAL = 9

# 反轉策略參數
REVERT_RSI_OVERBOUGHT = 65
REVERT_RSI_OVERSOLD = 35
BOLL_STD_DEV = 2

# K 線設定
KLINE_INTERVAL = "5m"
KLINE_LIMIT = 100

# DEBUG 模式
DEBUG_MODE = True

print("======================================")
