from __future__ import annotations
import math
from typing import Dict, Optional

from binance.um_futures import UMFutures
from binance.error import ClientError

from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    TESTNET,
    DEBUG_MODE,
    FALLBACK_MIN_NOTIONAL,
    FALLBACK_MIN_NOTIONAL_DEFAULT,
)

_TESTNET_UMF_URL = "https://testnet.binancefuture.com"  # USDT-M Testnet

class BinanceClient:
    """
    包一層，統一處理：
    - testnet 切換
    - 報價抓取（price -> markPrice fallback）
    - 交易規則快取（stepSize/minQty/minNotional）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: Optional[bool] = None,
        base_url: Optional[str] = None,
    ):
        self._testnet = TESTNET if testnet is None else bool(testnet)
        key = api_key or BINANCE_API_KEY
        sec = api_secret or BINANCE_API_SECRET

        if self._testnet and base_url is None:
            base_url = _TESTNET_UMF_URL

        if base_url:
            self.client = UMFutures(key=key, secret=sec, base_url=base_url)
        else:
            self.client = UMFutures(key=key, secret=sec)

        self._filters_cache: Dict[str, Dict[str, float]] = {}

    # ---------- Exchange Info / Filters ----------

    def _load_symbol_filters(self, symbol: str) -> Dict[str, float]:
        if symbol in self._filters_cache:
            return self._filters_cache[symbol]

        info = self.client.exchange_info(symbol=symbol)
        # 期貨回傳格式含 symbols 陣列
        symbols = info.get("symbols") or []
        target = None
        for s in symbols:
            if s.get("symbol") == symbol:
                target = s
                break
        if target is None:
            raise RuntimeError(f"[FILTER] 找不到 {symbol} 的交易規則")

        step_size = None
        min_qty = None
        min_notional = None

        for f in target.get("filters", []):
            ftype = f.get("filterType") or f.get("filter_type")
            # 不同版本 key 名稱可能不同，耐性處理
            if ftype in ("LOT_SIZE", "MARKET_LOT_SIZE", "LOT_SIZE_FILTER", "marketLotSize", "lotSize"):
                step_size = float(f.get("stepSize") or f.get("step_size") or f.get("step") or 0)
                min_qty = float(f.get("minQty") or f.get("min_qty") or 0)
            elif ftype in ("NOTIONAL", "MIN_NOTIONAL"):
                # 期貨一般是 NOTIONAL -> minNotional
                mn = f.get("minNotional") or f.get("min_notional") or f.get("notional") or f.get("minValue")
                if mn is not None:
                    min_notional = float(mn)

        # 後備預設
        if min_notional is None:
            min_notional = FALLBACK_MIN_NOTIONAL.get(symbol, FALLBACK_MIN_NOTIONAL_DEFAULT)

        if step_size is None:
            # 萬一 LOT_SIZE 沒抓到，就給個極小步進避免 0
            step_size = 0.000001

        if min_qty is None:
            min_qty = step_size

        parsed = {
            "step_size": step_size,
            "min_qty": min_qty,
            "min_notional": min_notional,
        }
        self._filters_cache[symbol] = parsed
        if DEBUG_MODE:
            print(f"[FILTER] {symbol} step={step_size}, minQty={min_qty}, minNotional={min_notional}")
        return parsed

    def get_symbol_filters(self, symbol: str) -> Dict[str, float]:
        return self._load_symbol_filters(symbol)

    # ---------- Prices ----------

    def get_price(self, symbol: str) -> float:
        """
        先嘗試 ticker_price，再退到 mark_price
        """
        try:
            data = self.client.ticker_price(symbol=symbol)
            return float(data["price"])
        except Exception:
            data = self.client.mark_price(symbol=symbol)
            return float(data["markPrice"])

    # ---------- Account ----------

    def get_available_usdt(self) -> float:
        """
        從期貨餘額抓可用保證金 USDT（availableBalance）
        """
        try:
            balances = self.client.balance()
            for b in balances:
                if b.get("asset") == "USDT":
                    # 有些欄位叫 availableBalance、有些叫 availableBalance/availableBalance
                    val = b.get("availableBalance") or b.get("availableBalance")
                    return float(val)
        except Exception as e:
            if DEBUG_MODE:
                print(f"[WARN] 無法取得餘額：{e}")
        return 0.0

    # ---------- Leverage ----------

    def set_leverage(self, symbol: str, leverage: int):
        try:
            self.client.change_leverage(symbol=symbol, leverage=leverage)
            if DEBUG_MODE:
                print(f"[INFO] {symbol} 槓桿已設定為 {leverage}x")
        except ClientError as e:
            print(f"[WARN] 設定槓桿失敗 {symbol}: {e}")

    # ---------- Ordering ----------

    @staticmethod
    def _ceil_step(x: float, step: float) -> float:
        if step <= 0:
            return x
        return math.ceil(x / step) * step

    def align_qty_up(self, qty: float, step_size: float) -> float:
        return round(self._ceil_step(qty, step_size), 8)

    def ensure_min_notional(self, qty: float, price: float, min_notional: float, step_size: float) -> float:
        """
        若名目不足 -> 直接把數量拉到滿足 min_notional（再向上對齊 stepSize）
        """
        if price <= 0:
            return 0.0
        need_qty = min_notional / price
        if qty * price < min_notional:
            qty = need_qty
        qty = self.align_qty_up(qty, step_size)
        # 最後再檢查一次，避免浮點誤差
        if qty * price < min_notional:
            qty = self.align_qty_up(need_qty, step_size)
        return qty

    def order_market(self, symbol: str, side: str, quantity: float):
        try:
            od = self.client.new_order(
                symbol=symbol,
                side=side.upper(),
                type="MARKET",
                quantity=quantity,
                newOrderRespType="RESULT",
            )
            print(f"[ORDER] {symbol} {side} {quantity} 成功: {od.get('orderId')}")
            return od
        except ClientError as e:
            print(f"[ERROR] order {symbol}: ({e.status_code}, {e.error_code}, {e.error_message}, {e.headers})")
            return None
