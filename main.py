import asyncio
from config import (
    SYMBOL_POOL,
    LEVERAGE,
    DEBUG_MODE,
    TESTNET,
)
from exchange.binance_client import BinanceClient
from risk.risk_mgr import plan_final_qty

# 策略模組（存在才匯入，不存在就跳過）
try:
    from strategies.trend import generate_trend_signal
except Exception:
    def generate_trend_signal(*_, **__): return None

try:
    from strategies.revert import generate_revert_signal
except Exception:
    def generate_revert_signal(*_, **__): return None


async def main():
    print("[BOOT] Starting scanner...")

    client = BinanceClient(testnet=TESTNET)

    # 設定槓桿
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

        # --- 呼叫策略，支援舊版/新版 ---
        side = None
        try:
            side = generate_trend_signal(symbol=symbol)
        except TypeError:
            try:
                side = generate_trend_signal(symbol)
            except Exception:
                pass

        if not side:
            try:
                side = generate_revert_signal(symbol=symbol)
            except TypeError:
                try:
                    side = generate_revert_signal(symbol)
                except Exception:
                    pass

        if side not in ("BUY", "SELL"):
            if DEBUG_MODE:
                print(f"[SKIP] {symbol} 無交易訊號")
            continue

        # --- 數量計算 ---
        qty = plan_final_qty(client, symbol, price)
        if not qty or qty <= 0:
            if DEBUG_MODE:
                print(f"[SKIP] {symbol} 無法得到有效數量")
            continue

        # --- 下單 ---
        client.order_market(symbol, side, qty)
        await asyncio.sleep(0.2)  # 降頻，避免過快觸發 API 限制

    print("[DONE] 掃描完成")


if __name__ == "__main__":
    asyncio.run(main())
