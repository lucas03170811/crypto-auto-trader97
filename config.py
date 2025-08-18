# config.py
import os
import sys

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# 允許兩種命名：BINANCE_API_KEY / BINANCE_API_SECRET 或 API_KEY / API_SECRET
API_KEY = os.getenv("BINANCE_API_KEY") or os.getenv("API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET") or os.getenv("API_SECRET")

print(f"API_KEY: {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
print(f"API_SECRET: {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")

if not API_KEY or not API_SECRET:
    print("[ERROR] 請在 Railway 設定環境變數：BINANCE_API_KEY / BINANCE_API_SECRET（或 API_KEY / API_SECRET）")
    sys.exit(1)

# 是否實單（false = 真的下單 / true = 只列印不下單）
def _to_bool(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "y")

DEBUG_MODE = _to_bool(os.getenv("DEBUG_MODE"), default=False)

# 最小下單名目金額（Binance Futures 預設 5 USDT）
MIN_NOTIONAL_USDT = float(os.getenv("MIN_NOTIONAL_USDT", "5"))
# 若金額不足是否強制補足
FORCE_MIN_NOTIONAL = _to_bool(os.getenv("FORCE_MIN_NOTIONAL"), default=True)

# 基礎下單金額（以 USDT 計）
BASE_QTY_USD = float(os.getenv("BASE_QTY_USD", "5"))

# 幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]
print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# K 線設定
KLINE_INTERVAL = os.getenv("KLINE_INTERVAL", "5m")
KLINE_LIMIT = int(os.getenv("KLINE_LIMIT", "200"))

# 趨勢策略（放寬）
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "12"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# 反轉策略（放寬）
REVERT_RSI_OVERBOUGHT = float(os.getenv("REVERT_RSI_OVERBOUGHT", "65"))
REVERT_RSI_OVERSOLD  = float(os.getenv("REVERT_RSI_OVERSOLD",  "35"))
BOLL_STD_DEV = float(os.getenv("BOLL_STD_DEV", "2"))

# 加碼（單邊趨勢正確時滾倉加碼）
PYRAMID_ENABLE = _to_bool(os.getenv("PYRAMID_ENABLE"), default=True)
PYRAMID_ADD_EVERY_PCT = float(os.getenv("PYRAMID_ADD_EVERY_PCT", "0.01"))  # 每上/下 1% 加一次
PYRAMID_MAX_LAYERS = int(os.getenv("PYRAMID_MAX_LAYERS", "3"))

# 風控
TRAIL_GIVEBACK_PCT = float(os.getenv("TRAIL_GIVEBACK_PCT", "0.15"))  # 獲利回吐 15% 停利
MAX_LOSS_PCT = float(os.getenv("MAX_LOSS_PCT", "0.30"))              # 固定回撤 30% 停損

print("======================================")
