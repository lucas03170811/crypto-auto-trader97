# main.py
import os
import time
import asyncio
import requests
import pandas as pd

from config import (
    API_KEY, API_SECRET, SYMBOL_POOL, DEBUG_MODE,
    KLINE_INTERVAL, KLINE_LIMIT,
    MAX_LOSS_PCT, TRAIL_GIVEBACK_PCT,
    PYRAMID_MAX_LAYERS
)

from strategies.trend import generate_trend_signal, should_pyramid, pyramid_addon_qty
from strategies.revert import generate_revert_signal

from risk.risk_mgr import RiskManager
from binance_client import BinanceClient  # 你原本專案的 wrapper（保留）

FAPI_BASE = "https://fapi.binance.com"

def fetch_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    url = f"{FAPI_BASE}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url, timeout=10).json()
    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_asset_volume","num_trades","taker_base_vol","taker_quote_vol","ignore"]
    df = pd.DataFrame(data, columns=cols)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df[["open","high","low","close","volume"]]

async def scanner():
    print("[BOOT] Starting scanner...")

    client = BinanceClient(API_KEY, API_SECRET)
    rm = RiskManager(client)

    # 嘗試預先設槓桿（失敗就略過）
    for sym in SYMBOL_POOL:
        rm.ensure_leverage(sym)

    # 簡單單輪掃描（你也可改成 while True 持續跑）
    for sym in SYMBOL_POOL:
        print(f"[SCAN] {sym}")
        try:
            df = fetch_klines(sym, KLINE_INTERVAL, KLINE_LIMIT)
            if len(df) < 50:
                if DEBUG_MODE: print(f"[DEBUG] {sym} kline 不足，跳過")
                continue

            # 先用趨勢訊號，沒訊號再嘗試反轉訊號
            sig = generate_trend_signal(df)
            if sig is None:
                sig = generate_revert_signal(df)

            if sig is None:
                if DEBUG_MODE: print(f"[NO SIGNAL] {sym}")
                continue

            # 取現價
            price = float(requests.get(f"{FAPI_BASE}/fapi/v1/ticker/price?symbol={sym}", timeout=5).json()["price"])

            # 取得基礎數量（強制滿足 minNotional）
            qty = rm.get_order_qty(sym, price=price)
            if qty <= 0:
                if DEBUG_MODE: print(f"[RISK] 無法計算有效下單數量: {sym}")
                continue

            # 下單
            if sig == "LONG":
                if hasattr(client, "open_long"):
                    client.open_long(sym, qty)
                else:
                    client.market_order(sym, "BUY", qty)  # 若 wrapper 用此介面
                print(f"[ORDER] OPEN LONG {sym} qty={qty}")
            elif sig == "SHORT":
                if hasattr(client, "open_short"):
                    client.open_short(sym, qty)
                else:
                    client.market_order(sym, "SELL", qty)
                print(f"[ORDER] OPEN SHORT {sym} qty={qty}")

            # ====== 簡易風控（若你的 wrapper 有相關方法可改為服務端掛單）======
            # 固定止損 / 追蹤停利：此處僅記錄，實作通常需：
            # - 1) 用 reduceOnly 的止損單/追蹤單直接掛出去；或
            # - 2) 在 while 迴圈中輪詢倉位與 MFE/UPnL 來主動平倉。
            if DEBUG_MODE:
                print(f"[RISK] 固定止損={MAX_LOSS_PCT*100:.1f}%  追蹤停利回撤={TRAIL_GIVEBACK_PCT*100:.1f}%")

            # ====== 單邊加碼（示意）======
            # 實務上要讀 position/UPnL 與已加碼層數（可存在 DB 或檔案）
            # 這裡示範：若 wrapper 能取 upnl_pct 與當前已加碼層數 layers
            try:
                layers = 0
                upnl_pct = None
                if hasattr(client, "get_position"):
                    pos = client.get_position(sym)  # 需回傳包含 entryPrice/positionAmt/unrealizedProfit 等
                    # upnl_pct 簡化估算：未實現 / (abs(notional) / leverage?) -> 這裡僅示意
                    # 若你的 wrapper 已有 upnlPct 直接取用
                    upnl_pct = None

                if upnl_pct is not None and should_pyramid(upnl_pct, layers):
                    addon_notional = pyramid_addon_qty(qty) * price
                    addon_qty = rm.get_order_qty(sym, price=price, base_qty=addon_notional/price)
                    if addon_qty > 0:
                        if pos and float(pos.get("positionAmt", 0)) > 0:
                            # 多單加碼
                            if hasattr(client, "open_long"):
                                client.open_long(sym, addon_qty)
                            else:
                                client.market_order(sym, "BUY", addon_qty)
                            print(f"[PYRAMID] LONG 加碼 {sym} addon_qty={addon_qty}")
                        elif pos and float(pos.get("positionAmt", 0)) < 0:
                            # 空單加碼
                            if hasattr(client, "open_short"):
                                client.open_short(sym, addon_qty)
                            else:
                                client.market_order(sym, "SELL", addon_qty)
                            print(f"[PYRAMID] SHORT 加碼 {sym} addon_qty={addon_qty}")
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[PYRAMID] 例外略過 {sym}: {e}")

            # 每個 symbol 稍作間隔，避免連線池過滿
            await asyncio.sleep(0.2)

        except Exception as e:
            print(f"[ERROR] {sym}: {e}")
            await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(scanner())
