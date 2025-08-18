# main.py
import time
from exchange.binance_client import BinanceClient
from strategies.trend import generate_trend_signal, should_pyramid
from strategies.revert import generate_revert_signal
from config import (
    SYMBOL_POOL, DEBUG_MODE, BASE_QTY_USD, MIN_NOTIONAL_USDT,
    PYRAMID_ENABLE, PYRAMID_ADD_EVERY_PCT, PYRAMID_MAX_LAYERS,
    TRAIL_GIVEBACK_PCT, MAX_LOSS_PCT,
    KLINE_INTERVAL, KLINE_LIMIT
)

# 簡單的持倉追蹤（記憶體）
positions = {
    # symbol: {
    #   "side": "LONG"/"SHORT",
    #   "entry": float,
    #   "last_add_price": float,
    #   "layers": int,
    #   "peak": float,    # 多單最高價
    #   "trough": float   # 空單最低價
    # }
}

def open_or_add_position(client, symbol, side, price):
    """ 進場或加碼 """
    usd = max(BASE_QTY_USD, MIN_NOTIONAL_USDT)
    qty = usd / price
    od = client.order(symbol, "BUY" if side=="LONG" else "SELL", qty)
    if od is None:
        return False

    if symbol not in positions or positions[symbol].get("side") != side:
        # 新倉
        positions[symbol] = {
            "side": side,
            "entry": price,
            "last_add_price": price,
            "layers": 1,
            "peak": price if side=="LONG" else None,
            "trough": price if side=="SHORT" else None
        }
    else:
        # 加碼
        positions[symbol]["layers"] += 1
        positions[symbol]["last_add_price"] = price

    print(f"[POS] {symbol} {side} layers={positions[symbol]['layers']} entry≈{positions[symbol]['entry']:.4f}")
    return True

def maybe_trailing_or_stop(client, symbol, price):
    """ 觸發移動停利或固定止損就平倉（reduceOnly） """
    if symbol not in positions:
        return
    pos = positions[symbol]
    side = pos["side"]
    entry = pos["entry"]

    if side == "LONG":
        # 更新高點
        pos["peak"] = max(pos.get("peak", price), price)
        # 固定止損（相對 entry）
        if price <= entry * (1 - MAX_LOSS_PCT):
            print(f"[STOP] {symbol} LONG hit -{int(MAX_LOSS_PCT*100)}% 固定止損")
            client.order(symbol, "SELL", qty= (BASE_QTY_USD / price), reduce_only=True)
            positions.pop(symbol, None)
            return
        # 移動停利（回吐）
        if pos["peak"] and price <= pos["peak"] * (1 - TRAIL_GIVEBACK_PCT):
            print(f"[TRAIL] {symbol} LONG 回吐 {int(TRAIL_GIVEBACK_PCT*100)}%，停利出場")
            client.order(symbol, "SELL", qty= (BASE_QTY_USD / price), reduce_only=True)
            positions.pop(symbol, None)
            return
    else:  # SHORT
        # 更新低點
        pos["trough"] = min(pos.get("trough", price), price)
        # 固定止損（相對 entry）
        if price >= entry * (1 + MAX_LOSS_PCT):
            print(f"[STOP] {symbol} SHORT hit -{int(MAX_LOSS_PCT*100)}% 固定止損")
            client.order(symbol, "BUY", qty= (BASE_QTY_USD / price), reduce_only=True)
            positions.pop(symbol, None)
            return
        # 移動停利（回吐）
        if pos["trough"] and price >= pos["trough"] * (1 + TRAIL_GIVEBACK_PCT):
            print(f"[TRAIL] {symbol} SHORT 回吐 {int(TRAIL_GIVEBACK_PCT*100)}%，停利出場")
            client.order(symbol, "BUY", qty= (BASE_QTY_USD / price), reduce_only=True)
            positions.pop(symbol, None)
            return

def scan_once(client):
    for sym in SYMBOL_POOL:
        print(f"[SCAN] {sym}")
        df = client.get_klines(sym, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
        if df is None or df.empty:
            continue

        # 先跑趨勢，沒有訊號再跑反轉
        signal = generate_trend_signal(df)
        if signal is None:
            signal = generate_revert_signal(df)

        price = client.get_price(sym)
        if not price:
            continue

        # 風控檢查（移動停利/固定止損）
        maybe_trailing_or_stop(client, sym, price)

        if signal is None:
            continue

        # 開倉 / 反向轉倉（簡化：若方向不同就視為換邊）
        if sym not in positions:
            open_or_add_position(client, sym, signal, price)
            continue

        cur = positions[sym]
        if cur["side"] != signal:
            print(f"[REV] {sym} 方向反轉 {cur['side']} -> {signal}，先平再反向")
            # 先平舊倉
            client.order(sym, "SELL" if cur["side"]=="LONG" else "BUY", qty=(BASE_QTY_USD/price), reduce_only=True)
            positions.pop(sym, None)
            # 再開新倉
            open_or_add_position(client, sym, signal, price)
            continue

        # 同向單邊加碼
        if PYRAMID_ENABLE:
            ok_to_add = should_pyramid(
                side=cur["side"],
                price=price,
                last_add_price=cur.get("last_add_price"),
                add_every_pct=PYRAMID_ADD_EVERY_PCT,
                layers_done=cur.get("layers", 1),
                max_layers=PYRAMID_MAX_LAYERS
            )
            if ok_to_add:
                print(f"[PYR] {sym} 單邊加碼觸發 (+{int(PYRAMID_ADD_EVERY_PCT*100)}%)")
                open_or_add_position(client, sym, cur["side"], price)

def main_loop():
    client = BinanceClient()
    print("[BOOT] Starting scanner...")
    # 單次掃描（若需常駐，改成 while True 並加 sleep）
    scan_once(client)

if __name__ == "__main__":
    main_loop()
