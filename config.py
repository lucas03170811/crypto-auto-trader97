# config.py
import os
import sys
from decimal import Decimal

def _env_first(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# 支援多種 env name，優先順序：API_KEY/API_SECRET -> BINANCE_API_KEY/BINANCE_API_SECRET
API_KEY = _env_first("API_KEY", "BINANCE_API_KEY", "BINANCE_APIKEY", "BINANCE_API")
API_SECRET = _env_first("API_SECRET", "BINANCE_API_SECRET", "BINANCE_APISECRET", "BINANCE_SECRET")

if not API_KEY or not API_SECRET:
    print("[ERROR] 環境變數 API_KEY / API_SECRET (或 BINANCE_API_KEY / BINANCE_API_SECRET) 未設定")
    # 不直接 sys.exit(1) — 因為在某些測試情境你可能要 mock，改成提示並繼續（如需強制退出可解除下面註解）
    # sys.exit(1)

print(f"API_KEY： {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
print(f"API_SECRET： {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")

# 基本參數
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("1", "true", "yes")

# 每筆下單基礎美元金額（可在 Railway 用 BASE_QTY_USD 設定）
BASE_QTY_USD = float(_env_first("BASE_QTY_USD", "BASE_NOTIONAL_USD") or 20.0)

# 風控參數
EQUITY_RATIO = float(_env_first("EQUITY_RATIO") or 0.1)   # 若要用 equity ratio
LEVERAGE = int(_env_first("LEVERAGE") or 1)

# 若交易所最小名目不足時的預設最小值（USDT）
MIN_NOTIONAL_DEFAULT = Decimal(str(_env_first("MIN_NOTIONAL_DEFAULT") or "5"))

# 針對個別幣種 override 最小名目（USDT） —— 可擴充
PER_SYMBOL_MIN_NOTIONAL = {
    "ETHUSDT": Decimal("20"),
    "BTCUSDT": Decimal("5"),
    # 若你要為特定 symbol 設定更高閾值，放在這裡
    # "SOLUSDT": Decimal("5"),
}

# 幣種池
SYMBOL_POOL = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "DOGEUSDT","LINKUSDT","AVAXUSDT","MATICUSDT",
    "SUIUSDT","SEIUSDT","1000PEPEUSDT","1000BONKUSDT"
]

print(f"交易幣種數量: {len(SYMBOL_POOL)}")
print(f"BASE_QTY_USD: {BASE_QTY_USD}, MIN_NOTIONAL_DEFAULT: {MIN_NOTIONAL_DEFAULT}, DEBUG_MODE: {DEBUG_MODE}")
print("======================================")
