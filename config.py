import os
import sys

def _truthy(v: str) -> bool:
    if v is None:
        return False
    return v.strip().lower() in ("1", "true", "yes", "on")

print("===== [CONFIG DEBUG] 載入設定檔 =====")

# 支援兩組環境變數名稱
BINANCE_API_KEY = (
    os.getenv("BINANCE_API_KEY")
    or os.getenv("API_KEY")
)
BINANCE_API_SECRET = (
    os.getenv("BINANCE_API_SECRET")
    or os.getenv("API_SECRET")
)

TESTNET = _truthy(os.getenv("TESTNET") or os.getenv("BINANCE_TESTNET", "0"))

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    print("API_KEY： ❌ 未讀取")
    print("API_SECRET： ❌ 未讀取")
    print("[ERROR] 請在 Railway 設定環境變數：BINANCE_API_KEY / BINANCE_API_SECRET（或 API_KEY / API_SECRET）")
    sys.exit(1)

print(f"API_KEY： ✅ 已讀取")
print(f"API_SECRET： ✅ 已讀取")

# 槓桿（若策略/下單前要動態設定，可在 main 內逐幣種呼叫）
LEVERAGE = int(os.getenv("LEVERAGE", "10"))

# 交易幣種池
SYMBOL_POOL = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "MATICUSDT",
    "SUIUSDT", "SEIUSDT", "1000PEPEUSDT", "1000BONKUSDT",
]
print(f"交易幣種數量: {len(SYMBOL_POOL)}")

# 預設每筆「期望名目」(USD)；實際會自動「至少滿足 minNotional」
# 小幣對預設 6U；大幣對讓風控邏輯自動跳過（如果餘額不足）
DESIRED_TRADE_USD_DEFAULT = float(os.getenv("DESIRED_TRADE_USD_DEFAULT", "6"))

# 若交易所查詢 minNotional 失敗，使用這個後備表
# （BTC/ETH/LINK 在 Binance USDⓈ-M Futures 上常見 minNotional 分別為 100 / 20 / 20）
FALLBACK_MIN_NOTIONAL = {
    "BTCUSDT": 100.0,
    "ETHUSDT": 20.0,
    "LINKUSDT": 20.0,
}
FALLBACK_MIN_NOTIONAL_DEFAULT = 5.0

DEBUG_MODE = _truthy(os.getenv("DEBUG_MODE", "1"))

print("======================================")
