# config.py
import os
import sys
from typing import List

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# 支援多種 env var 名稱（Railway 可能用 BINANCE_API_KEY）
API_KEY = os.getenv("API_KEY") or os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_KEY")
API_SECRET = os.getenv("API_SECRET") or os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET")

if not API_KEY or not API_SECRET:
    print("[ERROR] 環境變數未設定。請在 Railway 設定 Environment Variables：API_KEY / API_SECRET (或 BINANCE_API_KEY / BINANCE_API_SECRET)")
    # 退出會讓容器停止，避免無 API key 下單
    sys.exit(1)

print(f"API_KEY: {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
print(f"API_SECRET: {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")

# 基本掃描設定
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "60"))  # 每 60 秒掃描一次，可用 env var 調整

# 交易池 (可更換)
SYMBOL_POOL: List[str] = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","1000BONKUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT", 
]
print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# 風控 & 下單設定
EQUITY_RATIO = float(os.getenv("EQUITY_RATIO", "0.05"))   # 每次下單使用總資產比例 (預設 5%)
BASE_ORDER_USD = float(os.getenv("BASE_ORDER_USD", "10"))  # 當 equity 太小時，補足的最小名目 (USD)
MIN_NOTIONAL_USD = float(os.getenv("MIN_NOTIONAL_USD", "5.0"))  # 交易所要求最小名目 (常見 5)
LEVERAGE = int(os.getenv("LEVERAGE", "30"))  # 設定槓桿倍數（合約）
MAX_PYRAMID = int(os.getenv("MAX_PYRAMID", "8"))  # 最多加碼次數

# 加碼策略
PYRAMID_PROFIT_THRESH = float(os.getenv("PYRAMID_PROFIT_THRESH", "0.4"))  # 40% 獲利時允許加碼
PYRAMID_BREAKOUT_ENABLED = os.getenv("PYRAMID_BREAKOUT_ENABLED", "true").lower() in ("1","true","yes")
PYRAMID_BREAKOUT_LOOKBACK = int(os.getenv("PYRAMID_BREAKOUT_LOOKBACK", "20"))  # 用於突破前高/低計算

# 移動停利 & 固定停損
TRAILING_GIVEBACK_PCT = float(os.getenv("TRAILING_GIVEBACK_PCT", "0.20"))  # 從高點回落 20% 則平倉
MAX_LOSS_PCT = float(os.getenv("MAX_LOSS_PCT", "0.30"))  # 單筆最大虧損 30%

# K線與指標
KLINE_INTERVAL = os.getenv("KLINE_INTERVAL", "5m")
KLINE_LIMIT = int(os.getenv("KLINE_LIMIT", "200"))

# 趨勢策略參數
TREND_EMA_FAST = int(os.getenv("TREND_EMA_FAST", "12"))
TREND_EMA_SLOW = int(os.getenv("TREND_EMA_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# 反轉策略參數
REVERT_RSI_PERIOD = int(os.getenv("REVERT_RSI_PERIOD", "14"))
REVERT_RSI_OVERSOLD = int(os.getenv("REVERT_RSI_OVERSOLD", "40"))   # 放寬條件
REVERT_RSI_OVERBOUGHT = int(os.getenv("REVERT_RSI_OVERBOUGHT", "60"))
BOLL_WINDOW = int(os.getenv("BOLL_WINDOW", "20"))
BOLL_STDDEV = float(os.getenv("BOLL_STDDEV", "2.0"))

# 其它
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() in ("1","true","yes")

print("======================================")
