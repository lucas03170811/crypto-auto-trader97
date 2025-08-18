# config.py
import os, sys

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# 優先讀 API_KEY / API_SECRET，若沒有則用 BINANCE_API_KEY / BINANCE_API_SECRET
API_KEY = os.getenv("API_KEY") or os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("API_SECRET") or os.getenv("BINANCE_API_SECRET")

print(f"API_KEY: {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
print(f"API_SECRET: {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")

if not API_KEY or not API_SECRET:
    print("[ERROR] 請在 Railway 設定 Environment Variables: API_KEY/API_SECRET 或 BINANCE_API_KEY/BINANCE_API_SECRET")
    sys.exit(1)

# 幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]
print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# 風控 / 下單
LEVERAGE              = int(os.getenv("LEVERAGE", "5"))
EQUITY_RATIO          = float(os.getenv("EQUITY_RATIO", "0.2"))
MIN_NOTIONAL_USDT     = float(os.getenv("MIN_NOTIONAL_USDT", "5.05"))
FORCE_MIN_NOTIONAL    = os.getenv("FORCE_MIN_NOTIONAL", "true").lower() == "true"

MAX_LOSS_PCT          = float(os.getenv("MAX_LOSS_PCT", "0.30"))
TRAIL_GIVEBACK_PCT    = float(os.getenv("TRAIL_GIVEBACK_PCT", "0.15"))
TP_MULTIPLIER         = float(os.getenv("TP_MULTIPLIER", "1.5"))

KLINE_INTERVAL        = os.getenv("KLINE_INTERVAL", "5m")
KLINE_LIMIT           = int(os.getenv("KLINE_LIMIT", "300"))

TREND_EMA_FAST        = int(os.getenv("TREND_EMA_FAST", "12"))
TREND_EMA_SLOW        = int(os.getenv("TREND_EMA_SLOW", "26"))
MACD_SIGNAL           = int(os.getenv("MACD_SIGNAL", "9"))
TREND_MIN_SLOPE       = float(os.getenv("TREND_MIN_SLOPE", "0.0005"))

REVERT_RSI_OVERBOUGHT = int(os.getenv("REVERT_RSI_OVERBOUGHT", "65"))
REVERT_RSI_OVERSOLD   = int(os.getenv("REVERT_RSI_OVERSOLD", "35"))
BOLL_STD_DEV          = float(os.getenv("BOLL_STD_DEV", "2"))

PYRAMID_MAX_LAYERS    = int(os.getenv("PYRAMID_MAX_LAYERS", "3"))
PYRAMID_ADD_RATIO     = float(os.getenv("PYRAMID_ADD_RATIO", "0.5"))
PYRAMID_TRIGGER_UPNL  = float(os.getenv("PYRAMID_TRIGGER_UPNL", "0.02"))

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
print("======================================")
