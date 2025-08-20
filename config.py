import os

# ===== API 金鑰（Railway 變數名稱）=====
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# ===== 交易環境 =====
USE_TESTNET = False  # True=測試網, False=正式網

# ===== 掃描節奏（秒）=====
SCAN_INTERVAL_SEC = 60  # ← 每 60 秒掃描一次

# ===== 槓桿 =====
LEVERAGE = 10  # ← 全部幣種套用（若幣種關閉，會自動跳過）

# ===== 交易清單 =====
SYMBOLS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "LINKUSDT","AVAXUSDT","MATICUSDT","SUIUSDT","SEIUSDT",
    "1000PEPEUSDT","1000BONKUSDT",
]

# ===== 策略參數 =====
# 趨勢（EMA + MACD）
EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9

# 反轉（RSI + 布林）
RSI_LEN = 14
BB_LEN = 20
BB_STD = 2.0
RSI_BUY = 30
RSI_SELL = 70

# ===== 風控／加碼參數 =====
# 每個幣最小目標名目金額（USDT），名目不足會自動補到這個值
MIN_NOTIONAL = {
    "BTCUSDT": 100.0,
    "ETHUSDT": 20.0,
    "SOLUSDT": 10.0,
    "XRPUSDT": 10.0,
    "ADAUSDT": 10.0,
    "DOGEUSDT": 5.0,
    "LINKUSDT": 20.0,
    "AVAXUSDT": 20.0,
    "MATICUSDT": 10.0,
    "SUIUSDT": 5.0,
    "SEIUSDT": 5.0,
    "1000PEPEUSDT": 5.0,
    "1000BONKUSDT": 5.0,
}
DEFAULT_MIN_NOTIONAL = 5.0  # 找不到幣時的 fallback

# 加碼（同向）規則
ADD_TRIGGER_PROFIT = 0.40   # 獲利 > 40% 加碼
BREAKOUT_LOOKBACK = 20      # 突破最近 N 根高/低加碼
MAX_PYRAMIDS = 8            # 最多加碼 8 次
ADD_SIZE_MULTIPLIER = 1.0   # 每次加碼量 = 基礎下單量 * 這個倍數

# 追蹤停利／停損
TRAIL_GIVEBACK = 0.20       # 從峰值利潤回落 20% => 全平
STOP_LOSS_PCT = -0.30       # 直接虧損 -30% => 全平

# K 線拉取
KLINE_INTERVAL = "1m"       # ← 每分鐘策略
KLINE_LIMIT = 200
