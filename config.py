# config.py
import os
import sys

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# --- API 環境變數容錯（任一命名都可） ---
def _get_any(keys):
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None

API_KEY = _get_any([
    "API_KEY",
    "BINANCE_API_KEY",
    "BINANCE_FUTURES_API_KEY",
])

API_SECRET = _get_any([
    "API_SECRET",
    "BINANCE_API_SECRET",
    "BINANCE_FUTURES_API_SECRET",
])

if not API_KEY or not API_SECRET:
    print("[ERROR] 環境變數未設定：請在 Railway 設定 API_KEY/API_SECRET（或 BINANCE_* 對應變數）")
    sys.exit(1)

print(f"API_KEY: ✅ 已讀取")
print(f"API_SECRET: ✅ 已讀取")

# --- 交易幣種池 ---
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]
print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# --- K 線設定 ---
KLINE_INTERVAL = os.getenv("KLINE_INTERVAL", "5m")
KLINE_LIMIT = int(os.getenv("KLINE_LIMIT", "200"))

# --- 風控參數 ---
EQUITY_RATIO = float(os.getenv("EQUITY_RATIO", "0.10"))        # 每筆下單使用資金比例
MAX_LOSS_PCT = float(os.getenv("MAX_LOSS_PCT", "0.30"))        # 固定止損百分比（可供擴充用）
TRAIL_GIVEBACK_PCT = float(os.getenv("TRAIL_GIVEBACK_PCT", "0.15"))  # 漲幅回吐百分比（可供擴充用）
PYRAMID_ADD_RATIO = float(os.getenv("PYRAMID_ADD_RATIO", "0.50"))     # 金字塔加碼比例（相對首筆）
MIN_NOTIONAL_USDT = float(os.getenv("MIN_NOTIONAL_USDT", "5"))        # 交易所最小名義金額（USDT）

# --- 策略參數（pandas_ta）---
# 趨勢策略
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "12"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# 反轉策略
REVERT_RSI_OVERBOUGHT = int(os.getenv("REVERT_RSI_OVERBOUGHT", "65"))
REVERT_RSI_OVERSOLD  = int(os.getenv("REVERT_RSI_OVERSOLD", "35"))
BOLL_STD_DEV = float(os.getenv("BOLL_STD_DEV", "2"))

# 一般設定
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

print("======================================")
