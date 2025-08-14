# risk/risk_mgr.py
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Optional, Dict, Any
getcontext().prec = 18

# 從 config 取不到就用預設
try:
    from config import EQUITY_RATIO as CFG_EQUITY_RATIO
except Exception:
    CFG_EQUITY_RATIO = 0.2  # 預設 20%

# 金字塔參數（可放進 config，自動回退這些預設）
try:
    from config import PYR_ENABLED, PYR_ADD_RATIO, PYR_MAX_ADDS, PYR_TRIGGER_PCT
except Exception:
    PYR_ENABLED = True          # 開啟滾倉
    PYR_ADD_RATIO = 0.5         # 每次加碼為基礎倉位的 50%
    PYR_MAX_ADDS = 3            # 最多加碼 3 次
    PYR_TRIGGER_PCT = 0.006     # 每次有利移動 0.6% 觸發下一次加碼

class RiskManager:
    """
    - 動態計算下單數量：依 equity_ratio
    - 自動補足至最小名義（minNotional）與 LOT_SIZE（stepSize）
    - 單邊趨勢對了滾倉加碼（pyramiding）
    """
    def __init__(self, client, equity_ratio: Optional[float] = None):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio if equity_ratio is not None else CFG_EQUITY_RATIO))
        # 每個 symbol 的加碼狀態
        self._pyr_state: Dict[str, Dict[str, Any]] = {}

    async def _get_filters(self, symbol: str):
        info = await self.client.get_symbol_info(symbol)
        step_size = Decimal("0.0001")
        min_qty = Decimal("0.0")
        min_notional = Decimal("5.0")  # USDT-M futures 常見下限
        tick_size = Decimal("0.01")

        if info and "filters" in info:
            for f in info["filters"]:
                t = f.get("filterType")
                if t == "LOT_SIZE":
                    if f.get("stepSize"):
                        step_size = Decimal(str(f["stepSize"]))
                    if f.get("minQty"):
                        min_qty = Decimal(str(f["minQty"]))
                elif t in ("MIN_NOTIONAL", "NOTIONAL"):
                    # futures 可能回傳 notional 或 minNotional
                    v = f.get("notional") or f.get("minNotional")
                    if v is not None:
                        min_notional = Decimal(str(v))
                elif t == "PRICE_FILTER":
                    if f.get("tickSize"):
                        tick_size = Decimal(str(f["tickSize"]))
        return step_size, min_qty, min_notional, tick_size

    def _round_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        if step == 0:
            return qty
        precision = abs(step.as_tuple().exponent)
        return (qty // step) * step if precision == 0 else qty.quantize(step, rounding=ROUND_DOWN)

    async def _ensure_min_requirements(self, symbol: str, qty: Decimal) -> Decimal:
        """
        依交易所規則補足：最小名義(minNotional)與 LOT_SIZE。
        """
        step, min_qty, min_notional, _ = await self._get_filters(symbol)
        price = Decimal(str(await self.client.get_price(symbol) or 0))
        if price <= 0:
            return Decimal("0")

        # 補到最小名義
        notional = qty * price
        if notional < min_notional:
            needed = (min_notional / price)
            qty = max(qty, needed)

        # 至少達到最小數量
        qty = max(qty, min_qty)

        # 與 step 對齊
        qty = self._round_to_step(qty, step)

        # 再檢查一次（對齊後若略小，補一格）
        if qty * price < min_notional:
            qty = self._round_to_step(qty + step, step)

        # 避免 0
        if qty <= 0:
            return Decimal("0")
        return qty

    async def get_order_qty(self, symbol: str) -> float:
        equity = Decimal(str(await self.client.get_equity() or 0))
        price = Decimal(str(await self.client.get_price(symbol) or 0))
        if price <= 0 or equity <= 0:
            return 0.0
        # 基礎下單金額
        usdt_amt = (equity * self.equity_ratio)
        raw_qty = (usdt_amt / price)
        qty = await self._ensure_min_requirements(symbol, raw_qty)
        return float(qty)

    async def _place(self, symbol: str, side: str, qty: float):
        if qty <= 0:
            print(f"[RISK] qty too small after ensure: {symbol}")
            return None
        if side == "LONG":
            return await self.client.open_long(symbol, qty)
        else:
            return await self.client.open_short(symbol, qty)

    async def _update_pyr_on_fill(self, symbol: str, fill_price: float):
        st = self._pyr_state.setdefault(symbol, {"adds": 0, "last_add_price": None, "base_qty": None, "dir": None})
        st["last_add_price"] = fill_price

    async def _maybe_pyramid(self, symbol: str, direction: str):
        """
        若已有同向倉位，且走勢有利超過觸發百分比，則依 base_qty 的比例加碼。
        """
        if not PYR_ENABLED:
            return

        pos_amt = await self.client.get_position(symbol)
        if (direction == "LONG" and pos_amt <= 0) or (direction == "SHORT" and pos_amt >= 0):
            return  # 無同向倉位

        price = float(await self.client.get_price(symbol) or 0.0)
        if price <= 0:
            return

        st = self._pyr_state.setdefault(symbol, {"adds": 0, "last_add_price": price, "base_qty": None, "dir": direction})
        # 方向一致才加碼；方向改變時重置
        if st.get("dir") and st["dir"] != direction:
            st.update({"adds": 0, "last_add_price": price, "base_qty": None, "dir": direction})

        # 第一次加碼的基礎數量：等於 get_order_qty()
        if st["base_qty"] is None:
            base_qty = await self.get_order_qty(symbol)
            if base_qty <= 0:
                return
            st["base_qty"] = base_qty

        if st["adds"] >= PYR_MAX_ADDS:
            return

        last_price = st.get("last_add_price") or price
        trigger = (1 + PYR_TRIGGER_PCT) if direction == "LONG" else (1 - PYR_TRIGGER_PCT)
        cond = (price >= last_price * trigger) if direction == "LONG" else (price <= last_price * trigger)

        if cond:
            add_qty_raw = Decimal(str(st["base_qty"])) * Decimal(str(PYR_ADD_RATIO))
            add_qty = await self._ensure_min_requirements(symbol, add_qty_raw)
            add_qty_f = float(add_qty)
            if add_qty_f > 0:
                print(f"[PYR] {symbol} {direction} add #{st['adds']+1} qty={add_qty_f} (price {price:.6f})")
                await self._place(symbol, direction, add_qty_f)
                st["adds"] += 1
                st["last_add_price"] = price

    async def execute_trade(self, symbol: str, signal: str):
        """
        - 若無倉位：依 signal 開倉
        - 若已有同向倉位：檢查是否達到加碼條件 -> pyramiding
        - 若反向信號：可在這裡關倉 / 反手（此處先僅示範同向加碼）
        """
        side = "LONG" if signal == "LONG" else "SHORT"
        pos_amt = await self.client.get_position(symbol)

        # 同向：嘗試加碼
        if (side == "LONG" and pos_amt > 0) or (side == "SHORT" and pos_amt < 0):
            await self._maybe_pyramid(symbol, side)
            return

        # 無倉或反向：這裡簡化為僅在無倉時開倉；反向可擴充為平倉再反手
        if pos_amt == 0:
            qty = await self.get_order_qty(symbol)
            if qty <= 0:
                print(f"[RISK] qty too small: {symbol}")
                return
            res = await self._place(symbol, side, qty)
            if res is not None:
                price = float(await self.client.get_price(symbol) or 0.0)
                await self._update_pyr_on_fill(symbol, price)
                self._pyr_state[symbol].update({"dir": side})
