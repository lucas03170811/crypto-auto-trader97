# risk/risk_mgr.py
import math
import time
import requests

from config import (
    MIN_NOTIONAL_USDT, FORCE_MIN_NOTIONAL, EQUITY_RATIO, LEVERAGE, DEBUG_MODE
)

FAPI_BASE = "https://fapi.binance.com"

class RiskManager:
    def __init__(self, client):
        self.client = client
        self._exchange_info_cache = None
        self._filters = {}  # symbol -> dict

    # ---------- Exchange Info & Filters ----------
    def _load_exchange_info(self):
        if self._exchange_info_cache is None:
            url = f"{FAPI_BASE}/fapi/v1/exchangeInfo"
            self._exchange_info_cache = requests.get(url, timeout=10).json()
        return self._exchange_info_cache

    def _parse_filters(self, symbol):
        if symbol in self._filters:
            return self._filters[symbol]
        info = self._load_exchange_info()
        symbols = {s["symbol"]: s for s in info["symbols"]}
        if symbol not in symbols:
            raise ValueError(f"[RISK] exchangeInfo 無此交易對: {symbol}")

        entry = symbols[symbol]
        lot = next(f for f in entry["filters"] if f["filterType"] == "LOT_SIZE")
        pricef = next(f for f in entry["filters"] if f["filterType"] == "PRICE_FILTER")
        # MIN_NOTIONAL 在 U 本位永續有時叫 "MIN_NOTIONAL" 且鍵為 "notional"
        min_notional_f = next((f for f in entry["filters"] if f["filterType"] == "MIN_NOTIONAL"), None)

        filters = {
            "stepSize": float(lot["stepSize"]),
            "minQty": float(lot["minQty"]),
            "tickSize": float(pricef["tickSize"]),
            "minNotional": float(min_notional_f.get("notional", MIN_NOTIONAL_USDT)) if min_notional_f else MIN_NOTIONAL_USDT
        }
        self._filters[symbol] = filters
        return filters

    # ---------- Helpers ----------
    @staticmethod
    def _floor_to_step(qty, step):
        # 依 stepSize 向下取整，避免 LOT_SIZE 錯誤
        return math.floor(qty / step) * step

    def _get_price(self, symbol):
        url = f"{FAPI_BASE}/fapi/v1/ticker/price?symbol={symbol}"
        return float(requests.get(url, timeout=5).json()["price"])

    def _get_equity(self):
        # 優先使用 client 的方法（若有）
        if hasattr(self.client, "get_equity"):
            try:
                return float(self.client.get_equity())
            except Exception:
                pass
        return None

    def ensure_leverage(self, symbol):
        # 能設就設，不行就略過
        if hasattr(self.client, "set_leverage"):
            try:
                self.client.set_leverage(symbol, LEVERAGE)
            except Exception:
                if DEBUG_MODE:
                    print(f"[RISK] set_leverage 跳過: {symbol}")

    # ---------- Public: 計算下單數量（強制滿足 minNotional） ----------
    def get_order_qty(self, symbol, price=None, base_qty=None):
        """
        回傳對齊 stepSize、且 notional >= minNotional 的數量。
        - 若設 EQUITY_RATIO 且能讀到 equity，取 max( equity*ratio , minNotional ) / price
        - 若無法讀 equity 或 FORCE_MIN_NOTIONAL=True，至少補到 minNotional。
        """
        filters = self._parse_filters(symbol)
        step = filters["stepSize"]
        min_qty = filters["minQty"]
        min_notional = max(filters["minNotional"], MIN_NOTIONAL_USDT)

        price = price or self._get_price(symbol)

        # 目標名目金額
        target_notional = min_notional
        eq = self._get_equity()
        if eq is not None and EQUITY_RATIO > 0:
            target_notional = max(min_notional, eq * EQUITY_RATIO)

        # 若有傳入 base_qty（例如加碼比率），在底線上再放大
        if base_qty:
            target_notional = max(target_notional, base_qty * price)

        raw_qty = target_notional / price
        qty = self._floor_to_step(raw_qty, step)

        # 強制對齊 minQty
        if qty < min_qty:
            qty = min_qty

        # 再檢查 notional（避免浮點誤差）
        notional = qty * price
        if FORCE_MIN_NOTIONAL and notional < min_notional:
            # 向上補到 minNotional
            need_qty = (min_notional / price)
            # 用 ceil 以確保 >= minNotional，再對齊 step
            k = math.ceil(need_qty / step)
            qty = k * step

        # 最終保險：不允許成為 0
        qty = max(qty, min_qty)

        if DEBUG_MODE:
            print(f"[RISK] {symbol} price={price:.6f} step={step} minQty={min_qty} "
                  f"minNotional={min_notional} -> qty={qty} notional≈{qty*price:.4f}")
        return qty
