import asyncio
from config import (
    SYMBOL_POOL,
    LEVERAGE,
    DEBUG_MODE,
    TESTNET,
)
from exchange.binance_client import BinanceClient
from risk.risk_mgr import plan_final_qty

# 盡量不動你的策略：存在就用；沒有就略過
try:
    from strategies.trend import generate_trend_signal  # -> "BUY"/"SELL"/None
except Exception:
    def generate_trend_signal(*_, **__): return None

try:
    from strategies.revert import generate_revert_signal  # -> "BUY"/"SELL"/None
except Exception:
    def generate_revert_signal(*_, **__): return None


async def main():
    print("[BOOT] Starting scanner...")

    # 支援 main.py 傳 testnet=... 的舊寫法
    client = BinanceClient(testnet=TESTNET)

    # 槓桿初始化（失敗不致命）
    for s in SYMBOL_POOL:
        try:
            client.set_leverage(s, LEVERAGE)
        except Exception:
            pass

    for symbol in SYMBOL_POOL:
        print(f"[SCAN] {symbol}")
        try:
            price = client.get_price(symbol)
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            continue

        # 產生訊號（任何一個策略回覆 "BUY"/"SELL" 即採用；都沒有就跳過）
        side = generate_trend_signal(symbol=symbol) or generate_revert_signal(symbol=symbol)
        if side not in ("BUY", "SELL"):
            if DEBUG_MODE:
                print(f"[SKIP] {symbol} 無交易訊號")
            continue

        qty = plan_final_qty(client, symbol, price)
        if not qty or qty <= 0:
            if DEBUG_MODE:
                print(f"[SKIP] {symbol} 無法得到有效數量")
            continue

        # 最終下單
        client.order_market(symbol, side, qty)
        await asyncio.sleep(0.2)  # 稍微降頻，避免打太快

    print("[DONE] 掃描完成")

if __name__ == "__main__":
    asyncio.run(main())
