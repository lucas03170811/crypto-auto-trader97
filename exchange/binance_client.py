from decimal import Decimal, ROUND_FLOOR
from typing import Dict, Any, Optional, Tuple
import time

from binance.um_futures import UMFutures


class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, use_testnet: bool = False):
        base_url = "https://testnet.binancefuture.com" if use_testnet else None
        self.client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)
        self._filters: Dict[str, Dict[str, Decimal]] = {}
        self._closed_symbols = set()

    # --- 基本行情 ---
    def ticker_price(self, symbol: str) -> float:
        r = self.client.ticker_price(symbol=symbol)
        return float(r["price"])

    def klines(self, symbol: str, interval: str, limit: int):
        return self.client.klines(symbol=symbol, interval=interval, limit=limit)

    # --- 交易規格 ---
    def _build_filters_cache(self):
        info = self.client.exchange_info()
        for s in info["symbols"]:
            sym = s["symbol"]
            lot = next((f for f in s["filters"] if f["filterType"] == "LOT_SIZE"), None)
            tick = next((f for f in s["filters"] if f["filterType"] == "PRICE_FILTER"), None)
            step = Decimal(lot["stepSize"]) if lot else Decimal("0.00000001")
            tick_size = Decimal(tick["tickSize"]) if tick else Decimal("0.00000001")
            self._filters[sym] = {"step": step, "tick": tick_size}

    def get_filters(self, symbol: str) -> Dict[str, Decimal]:
        if not self._filters:
            self._build_filters_cache()
        return self._filters.get(symbol, {"step": Decimal("0.00000001"), "tick": Decimal("0.00000001")})

    # --- 槓桿 ---
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        if symbol in self._closed_symbols:
            return False
        try:
            self.client.change_leverage(symbol=symbol, leverage=leverage)
            print(f"[資訊]{symbol} 槓桿已設定為 {leverage}x")
            return True
        except Exception as e:
            if "Symbol is closed" in str(e):
                self._closed_symbols.add(symbol)
            print(f"[WARN] 設定槓桿失敗 {symbol}： {e}")
            return False

    # --- 位置/PNL ---
    def position(self, symbol: str) -> Dict[str, Any]:
        # 回傳單一 symbol 的持倉資訊
        data = self.client.position_risk(symbol=symbol)
        if not data:
            return {"positionAmt": 0.0, "entryPrice": 0.0, "unRealizedProfit": 0.0}
        d = data[0]
        return {
            "positionAmt": float(d["positionAmt"]),
            "entryPrice": float(d["entryPrice"]),
            "unRealizedProfit": float(d["unRealizedProfit"]),
        }

    # --- 下單 ---
    def _align_step(self, qty: float, step: Decimal) -> float:
        if qty <= 0:
            return 0.0
        q = (Decimal(str(qty)) / step).to_integral_value(rounding=ROUND_FLOOR) * step
        q = float(q)
        if q == 0.0:
            q = float(step)
        return q

    def market_order(self, symbol: str, side: str, qty: float, reduce_only: bool = False) -> Optional[Dict[str, Any]]:
        try:
            f = self.get_filters(symbol)
            qty_aligned = self._align_step(qty, f["step"])
            if qty_aligned <= 0:
                print(f"[錯誤]{symbol} qty 對齊步進後為 0，取消下單（step={f['step']}）")
                return None
            r = self.client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=str(qty_aligned),
                reduceOnly="true" if reduce_only else "false",
            )
            return r
        except Exception as e:
            print(f"[ERROR] order {symbol}： {e}")
            return None

    def close_position(self, symbol: str):
        pos = self.position(symbol)
        amt = pos["positionAmt"]
        if abs(amt) < 1e-12:
            return
        side = "SELL" if amt > 0 else "BUY"
        self.market_order(symbol, side, abs(amt), reduce_only=True)
