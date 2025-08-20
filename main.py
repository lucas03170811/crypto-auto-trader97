import asyncio
import time
from decimal import Decimal
import pandas as pd

from config import (
    API_KEY, API_SECRET, USE_TESTNET, SYMBOLS,
    SCAN_INTERVAL_SEC, LEVERAGE,
    KLINE_INTERVAL, KLINE_LIMIT,
    ADD_TRIGGER_PROFIT, BREAKOUT_LOOKBACK, MAX_PYRAMIDS,
    TRAIL_GIVEBACK, STOP_LOSS_PCT
)
from exchange.binance_client import BinanceClient
from risk.risk_mgr import compute_base_qty, compute_add_qty
from position.position_mgr import PositionManager
from strategy.trend import generate_trend_signal
from strategy.revert import generate_revert_signal


def build_df(klines):
    cols = ["open_time","open","high","low","close","volume",
            "close_time","qav","num_trades","taker_base","taker_quote","ignore"]
    df = pd.DataFrame(klines, columns=cols)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    return df[["open","high","low","close"]]


def profit_pct(entry: float, price: float, side: str) -> float:
    """
    side: 'LONG' or 'SHORT'
    回傳相對 entry 的收益率（不乘槓桿）
    """
    if entry <= 0:
        return 0.0
    raw = (price - entry) / entry
    return raw if side == "LONG" else -raw


async def main():
    # === 啟動 ===
    print("===== [CONFIG DEBUG] 載入設定檔 =====")
    print(f"API_KEY： {'✅ 已讀取' if API_KEY else '❌ 未讀取'}")
    print(f"API_SECRET： {'✅ 已讀取' if API_SECRET else '❌ 未讀取'}")
    print(f"交易幣種數量: {len(SYMBOLS)}")
    print("======================================")

    client = BinanceClient(API_KEY, API_SECRET, use_testnet=USE_TESTNET)
    pm = PositionManager()

    # 設定槓桿
    for s in SYMBOLS:
        client.set_leverage(s, LEVERAGE)

    print("[開機]正在啟動掃描器...")

    while True:
        loop_start = time.time()
        try:
            for symbol in SYMBOLS:
                try:
                    # 拉 K 線 & 指標
                    kl = client.klines(symbol, KLINE_INTERVAL, KLINE_LIMIT)
                    df = build_df(kl)

                    # 產生入場訊號（任一策略觸發即可）
                    side_sig = generate_trend_signal(df) or generate_revert_signal(df)

                    # 取得當前持倉
                    pos = client.position(symbol)
                    amt = pos["positionAmt"]
                    entry = pos["entryPrice"]
                    mark = client.ticker_price(symbol)
                    side_now = "LONG" if amt > 0 else ("SHORT" if amt < 0 else None)

                    # 取得步進
                    f = client.get_filters(symbol)
                    step = f["step"]

                    # 讀取／初始化倉位狀態
                    st = pm.get(symbol)

                    # === 沒有倉位：看是否入場 ===
                    if side_now is None:
                        if side_sig is None:
                            print(f"[跳過]{symbol} 無交易訊號")
                            continue
                        # 計算下單數量
                        base_qty = compute_base_qty(symbol, mark, step)
                        # 下單方向
                        order_side = "BUY" if side_sig == "BUY" else "SELL"
                        r = client.market_order(symbol, order_side, base_qty, reduce_only=False)
                        if r:
                            print(f"[入場]{symbol} {order_side} x {base_qty}")
                            pm.reset(symbol)  # 進場後清空狀態
                        continue

                    # === 有倉位：風控與加碼 ===
                    pnl = profit_pct(entry, mark, side_now)

                    # 更新峰值利潤
                    if pnl > st.peak_profit_pct:
                        st.peak_profit_pct = pnl

                    # 1) 停損：-30%
                    if pnl <= STOP_LOSS_PCT:
                        print(f"[停損]{symbol} pnl={pnl:.2%} <= {STOP_LOSS_PCT:.0%}，全平")
                        client.close_position(symbol)
                        pm.reset(symbol)
                        continue

                    # 2) 追蹤停利：回落 20%（相對峰值）
                    if st.peak_profit_pct > 0:
                        threshold = st.peak_profit_pct * (1 - TRAIL_GIVEBACK)
                        if pnl < threshold:
                            print(f"[追蹤停利]{symbol} pnl {pnl:.2%} < 閾值 {threshold:.2%}（峰值 {st.peak_profit_pct:.2%} 回落）=> 全平")
                            client.close_position(symbol)
                            pm.reset(symbol)
                            continue

                    # 3) 同向加碼條件
                    #   a) 利潤 > 40%
                    #   b) 突破前高/低
                    if st.add_count < MAX_PYRAMIDS:
                        base_qty = compute_base_qty(symbol, mark, step)
                        add_qty = compute_add_qty(symbol, base_qty)

                        do_add = False
                        reason = ""

                        # a) 利潤門檻
                        if pnl >= ADD_TRIGGER_PROFIT:
                            do_add = True
                            reason = f"利潤 {pnl:.2%} >= {ADD_TRIGGER_PROFIT:.0%}"

                        # b) 突破前高/低（看最後一根是否突破前 N 根的極值）
                        hh = df["high"].iloc[-(BREAKOUT_LOOKBACK+1):-1].max()
                        ll = df["low"].iloc[-(BREAKOUT_LOOKBACK+1):-1].min()
                        last_close = df["close"].iloc[-1]

                        if side_now == "LONG" and last_close > hh and last_close > st.last_breakout_price:
                            do_add = True
                            reason = f"突破 {BREAKOUT_LOOKBACK} 根最高價 {hh:.6f}"
                            st.last_breakout_price = last_close
                        elif side_now == "SHORT" and last_close < ll and (st.last_breakout_price == 0.0 or last_close < st.last_breakout_price):
                            do_add = True
                            reason = f"跌破 {BREAKOUT_LOOKBACK} 根最低價 {ll:.6f}"
                            st.last_breakout_price = last_close

                        if do_add:
                            add_side = "BUY" if side_now == "LONG" else "SELL"
                            r = client.market_order(symbol, add_side, add_qty, reduce_only=False)
                            if r:
                                st.add_count += 1
                                print(f"[加碼]{symbol} {add_side} x {add_qty}｜原因：{reason}｜已加碼 {st.add_count}/{MAX_PYRAMIDS}")
                            else:
                                print(f"[加碼失敗]{symbol}（{reason}）")

                    # 4) 若反向訊號也可考慮反手（本版依你原始需求：僅依規則加碼/停損/停利，不自動反手）

                except Exception as e:
                    print(f"[ERROR] {symbol} 掃描/下單例外：{e}")

        except Exception as e:
            print(f"[FATAL] 主循環例外：{e}")

        # 固定週期掃描
        elapsed = time.time() - loop_start
        sleep_left = max(0.0, SCAN_INTERVAL_SEC - elapsed)
        await asyncio.sleep(sleep_left)


if __name__ == "__main__":
    asyncio.run(main())
