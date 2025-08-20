# config.py
import os
import sys
from typing import List

print("===== [CONFIG] 載入設定 =====")

# 支援 Railway 常見環境變數名稱
API_KEY = os.getenv("API_KEY") or os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_KEY")
API_SECRET = os.getenv("API_SECRET") or os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET")
TESTNET = os.getenv("TESTNET", "false").lower() in ("1", "true", "yes")

if not API_KEY or not API_SECRET:
    print("[ERROR] 請設定 API_KEY / API_SECRET（或 BINANCE_API_KEY / BINANCE_API_SECRET）")
    sys.exit(1)

# 掃描頻率（秒）
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "60"))

# 交易池（保留你之前部署時觀察到的幾個幣對）
SYMBOL_POOL: List[str] = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","1000BONKUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT"
]

# 風控參數（依你原本的命名）
EQUITY_RATIO = float(os.getenv("EQUITY_RATIO", "0.02"))      # 單筆資金使用比例
LEVERAGE = int(os.getenv("LEVERAGE", "30"))                    # 槓桿
MAX_PYRAMID = int(os.getenv("MAX_PYRAMID", "8"))              # 允許加碼層數
TRAILING_GIVEBACK_PCT = float(os.getenv("TRAILING_GIVEBACK_PCT", "0.20"))  # 從高點回落%
MAX_LOSS_PCT = float(os.getenv("MAX_LOSS_PCT", "0.30"))       # 單筆最大虧損%

# K 線與指標
KLINE_INTERVAL = os.getenv("KLINE_INTERVAL", "5m")
KLINE_LIMIT = int(os.getenv("KLINE_LIMIT", "200"))

# 趨勢策略參數（保留 EMA+MACD）
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "12"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# 反轉策略參數（保留 RSI + 布林）
REVERT_RSI_PERIOD = int(os.getenv("REVERT_RSI_PERIOD", "14"))
REVERT_RSI_OVERSOLD = int(os.getenv("REVERT_RSI_OVERSOLD", "40"))   # 放寬條件
REVERT_RSI_OVERBOUGHT = int(os.getenv("REVERT_RSI_OVERBOUGHT", "60"))
BOLL_WINDOW = int(os.getenv("BOLL_WINDOW", "20"))
BOLL_STDDEV = float(os.getenv("BOLL_STDDEV", "2.0"))

# 加碼（突破）設定
PYRAMID_BREAKOUT_ENABLED = os.getenv("PYRAMID_BREAKOUT_ENABLED", "true").lower() in ("1","true","yes")
PYRAMID_BREAKOUT_LOOKBACK = int(os.getenv("PYRAMID_BREAKOUT_LOOKBACK", "20"))

# 篩選（資金量/資金費）
VOLUME_MIN_USD = float(os.getenv("VOLUME_MIN_USD", "3000000"))   # 24h quote volume 門檻
FUNDING_RATE_MIN = float(os.getenv("FUNDING_RATE_MIN", "-0.03"))    # 預設極小，等同關閉門檻

# 其它
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() in ("1","true","yes")

print("=================================")
