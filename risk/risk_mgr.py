# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Optional, Dict, Any
getcontext().prec = 28  # 高精度避免小數誤差

# 參數（可放 config.py；若無則使用預設）
try:
    from config import EQUITY_RATIO as CFG_EQUITY_RATIO
except Exception:
    CFG_EQUITY_RATIO = 0.2

try:
    from config import PYR_ENABLED, PYR_ADD_RATIO, PYR_MAX_ADDS, PYR_TRIGGER_PCT
except Exception:
    PYR_ENABLED = True
    PYR_ADD_RATIO = 0.5
    PYR_MAX_ADDS = 3
    PYR_TRIGGER_PCT = 0.006  # 0.6%

# 追蹤停損 / 最大虧損（可搬到 config）
try:
    from config import TRAIL_GIVEBACK_PCT, MAX_LOSS_PCT
except Exception:
    TRAIL_GIVEBACK_PCT = Decimal("0.15")  # 獲利回吐 15%
    MAX_LOSS_PCT = Decimal("0.30")        # 最大虧損 30%

class RiskManager:
    """
    - 以 equity_ratio 計算下單金額
    - 對齊 LOT_SIZE、補到 minNotional，杜絕 -1111 / -4164
    - 單邊滾倉（pyramiding）
    - 追蹤停利（獲利回吐 15%）與最大虧損 30%
    """
    def __init__(self, client, equity_ratio: Optional[float] = None):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio if equity_ratio is not None else CFG_EQUITY_RATIO))
        # 追蹤狀態：每個 symbol
        # entry 進場價、peak 高點（long）/ trough 低點（short）、adds 加碼次數、base_qty 基礎倉位、dir 方向
        self._state: Dict[str, Dict[str, Any]] = {}

    async def _get_filters(self, symbol: str):
        info = await self.client.get_symbol_info(symbol)
        step = Decimal("0.0001")
        min_qty = Decimal("0")
        min_notional = Decimal("5")
        tick = Decimal("0.01")
        if info and "filters" in info:
            for f in info["filters"]:
                t = f.get("filterType")
                if t == "LOT_SIZE":
                    if f.get("stepSize"): step = Decimal(str(f["stepSize"]))
                    if f.get("minQty"):   min_qty = Decimal(str(f["minQty"]))
                elif t in ("MIN_NOTIONAL", "NOTIONAL"):
                    v = f.get("notional") or f.get("minNotional")
                    if v is not None:
                        min_notional = Decimal(str(v))
                elif t == "PRICE_FILTER" and f.get("tickSize"):
                    tick = Decimal(str(f["tickSize"]))
        return step, min_qty, min_notional, tick

    def _floor_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        """
        正確對齊 LOT_SIZE：floor(qty/step)*step，確保為 stepSize 的整數倍。
        """
        if step <= 0:
            return qty
        units = (qty / step).to_integral_value(rounding=ROUND_DOWN)
        return (units * step).normalize()

    async def _ensure_min_requirements(self, symbol: str, qty: Decimal) -> Decimal:
        step, min_qty, min_notional, _ = await self._get_filters(symbol)
        price = Decimal(str(await self.client.get_price(symbol) or 0))
        if price <= 0:
            return Decimal("0")

        # 先補到 minNotional
        notional = qty * price
        if notional < min_notional:
            qty = (min_notional / price)

        # 至少達到 minQty
        if qty < min_qty:
            qty = min_qty

        # 對齊 step
        qty = self._floor_to_step(qty, step)

        # 對齊後若仍小於 minNotional，再補一個 step
        if qty * price < min_notional:
            qty = self._floor_to_step(qty + step, step)

        return Decimal("0") if qty <= 0 else qty

    async def get_order_qty(self, symbol: str) -> float:
        equity = Decimal(str(await self.client.get_equity() or 0))
        price = Decimal(str(await self.client.get_price(symbol) or 0))
        if price <= 0 or equity <= 0:
            return 0.0
        usdt = equity * self.equity_ratio
        raw = usdt / price
        qty = await self._ensure_min_requirements(symbol, raw)
        return float(qty)

    async def _place(self, symbol: str, side: str, qty: float):
        if qty <= 0:
            print(f"[RISK] qty too small after ensure: {symbol}")
            return None
        if side == "LONG":
            return await self.client.open_long(symbol, qty)
        else:
            return await self.client.open_short(symbol, qty)

    async def _init_state_if_needed(self, symbol: str, direction: str, entry_price: float, base_qty: Optional[float] = None):
        st = self._state.setdefault(symbol, {"dir": direction, "entry": None, "peak": None, "trough": None, "adds": 0, "base_qty": base_qty})
        st["dir"] = direction
        if st["entry"] is None:
            st["entry"] = float(entry_price)
        if direction == "LONG":
            st["peak"] = max(st.get("peak") or entry_price, entry_price)
            st["trough"] = st.get("trough") or entry_price
        else:
            st["trough"] = min(st.get("trough") or entry_price, entry_price)
            st["peak"] = st.get("peak") or entry_price
        if st["base_qty"] is None and base_qty is not None:
            st["base_qty"] = float(base_qty)

    async def _update_peaks(self, symbol: str):
        st = self._state.get(symbol)
        if not st:
            return
        price = float(await self.client.get_price(symbol) or 0.0)
        if price <= 0:
            return
        if st["dir"] == "LONG":
            if st.get("peak") is None or price > st["peak"]:
                st["peak"] = price
        else:
            if st.get("trough") is None or price < st["trough"]:
                st["trough"] = price

    async def _check_trailing_and_maxloss(self, symbol: str) -> bool:
        """
        回傳 True 表示已平倉。
        """
        pos = await self.client.get_position(symbol)
        if pos == 0:
            return False

        st = self._state.get(symbol)
        if not st or st.get("entry") is None:
            # 若無狀態，建立一個基礎 entry 狀態
            entry_guess = float(await self.client.get_price(symbol) or 0.0)
            await self._init_state_if_needed(symbol, "LONG" if pos > 0 else "SHORT", entry_guess)

        await self._update_peaks(symbol)
        st = self._state[symbol]
        price = float(await self.client.get_price(symbol) or 0.0)
        entry = float(st["entry"])
        if price <= 0 or entry <= 0:
            return False

        # 最大虧損
        if pos > 0:  # LONG
            if price <= entry * float(Decimal("1") - MAX_LOSS_PCT):
                print(f"[STOP] {symbol} MAX LOSS triggered (LONG).")
                await self.client.close_position(symbol)
                self._state.pop(symbol, None)
                return True
        else:  # SHORT
            if price >= entry * float(Decimal("1") + MAX_LOSS_PCT):
                print(f"[STOP] {symbol} MAX LOSS triggered (SHORT).")
                await self.client.close_position(symbol)
                self._state.pop(symbol, None)
                return True

        # 追蹤停利（獲利回吐 15%）
        if pos > 0 and st.get("peak") is not None and st["peak"] > entry:
            peak = float(st["peak"])
            trail_line = entry + (1.0 - float(TRAIL_GIVEBACK_PCT)) * (peak - entry)  # entry + 0.85*(peak-entry)
            if price <= trail_line:
                print(f"[TRAIL] {symbol} LONG trailing stop hit. price={price:.6f} <= {trail_line:.6f}")
                await self.client.close_position(symbol)
                self._state.pop(symbol, None)
                return True
        if pos < 0 and st.get("trough") is not None and st["trough"] < entry:
            trough = float(st["trough"])
            trail_line = entry - (1.0 - float(TRAIL_GIVEBACK_PCT)) * (entry - trough)  # entry - 0.85*(entry-trough)
            if price >= trail_line:
                print(f"[TRAIL] {symbol} SHORT trailing stop hit. price={price:.6f} >= {trail_line:.6f}")
                await self.client.close_position(symbol)
                self._state.pop(symbol, None)
                return True

        return False

    async def _maybe_pyramid(self, symbol: str, direction: str):
        if not PYR_ENABLED:
            return
        pos_amt = await self.client.get_position(symbol)
        if (direction == "LONG" and pos_amt <= 0) or (direction == "SHORT" and pos_amt >= 0):
            return

        price = float(await self.client.get_price(symbol) or 0.0)
        if price <= 0:
            return

        st = self._state.setdefault(symbol, {"dir": direction, "entry": price, "peak": price, "trough": price, "adds": 0, "base_qty": None})
        if st["dir"] != direction:
            # 方向切換時重置
            st.update({"dir": direction, "entry": price, "peak": price, "trough": price, "adds": 0, "base_qty": None})

        if st["base_qty"] is None:
            base_qty = await self.get_order_qty(symbol)
            if base_qty <= 0:
                return
            st["base_qty"] = base_qty

        if st["adds"] >= PYR_MAX_ADDS:
            return

        last_ref = st.get("peak") if direction == "LONG" else st.get("trough")
        trigger_mult = (1 + PYR_TRIGGER_PCT) if direction == "LONG" else (1 - PYR_TRIGGER_PCT)
        cond = (price >= last_ref * trigger_mult) if direction == "LONG" else (price <= last_ref * trigger_mult)

        if cond:
            add_qty = await self._ensure_min_requirements(symbol, Decimal(str(st["base_qty"])) * Decimal(str(PYR_ADD_RATIO)))
            add_qty_f = float(add_qty)
            if add_qty_f > 0:
                print(f"[PYR] {symbol} {direction} add #{st['adds']+1} qty={add_qty_f} at {price:.6f}")
                await self._place(symbol, direction, add_qty_f)
                st["adds"] += 1
                # 更新參考極值
                if direction == "LONG":
                    st["peak"] = price
                else:
                    st["trough"] = price

    async def execute_trade(self, symbol: str, signal: str):
        side = "LONG" if signal == "LONG" else "SHORT"
        # 先檢查風控（已有倉位時會可能直接平倉）
        stopped = await self._check_trailing_and_maxloss(symbol)
        if stopped:
            return

        pos_amt = await self.client.get_position(symbol)

        # 同向倉：嘗試加碼
        if (side == "LONG" and pos_amt > 0) or (side == "SHORT" and pos_amt < 0):
            await self._maybe_pyramid(symbol, side)
            # 每輪都更新一下峰/谷；停利條件會在下次輪詢時判斷
            await self._update_peaks(symbol)
            return

        # 無倉：開倉
        if pos_amt == 0:
            qty = await self.get_order_qty(symbol)
            if qty <= 0:
                print(f"[RISK] qty too small: {symbol}")
                return
            res = await self._place(symbol, side, qty)
            if res is not None:
                price = float(await self.client.get_price(symbol) or 0.0)
                await self._init_state_if_needed(symbol, side, price, base_qty=qty)
                # 開倉後也先更新一下峰/谷
                await self._update_peaks(symbol)
