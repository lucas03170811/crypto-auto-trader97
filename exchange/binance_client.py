# exchange/binance_client.py
import asyncio
from decimal import Decimal, ROUND_UP, ROUND_DOWN, getcontext
from typing import Any, Optional, Dict

# 本模組會讀 config（不會反向 import）
import config

# 使用 binance futures connector (sync style). 如果你用不同 SDK 則需微調
from binance.um_futures import UMFutures

getcontext().prec = 18

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, base_url: str = "https://fapi.binance.com"):
        # 若呼叫端未傳入 key/secret，從 config 拿（支援多種變數命名）
        self.api_key = api_key or config.API_KEY
        self.api_secret = api_secret or config.API_SECRET
        self.base_url = base_url

        # UMFutures 建構：key, secret
        self.client = UMFutures(self.api_key, self.api_secret, base_url=self.base_url)
        # Cache exchange_info / symbol info
        self._symbol_info_cache: Dict[str, dict] = {}

    async def _run_sync(self, fn, *args, **kwargs):
        """Run blocking sync SDK call in threadpool"""
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> Any:
        try:
            return await self._run_sync(self.client.klines, symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"[ERROR] get_klines {symbol}: {e}")
            return []

    async def get_price(self, symbol: str) -> float:
        try:
            res = await self._run_sync(self.client.ticker_price, symbol=symbol)
            return float(res.get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return 0.0

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get exchange_info -> symbol object, cached."""
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]
        try:
            info = await self._run_sync(self.client.exchange_info)
            if isinstance(info, dict) and "symbols" in info:
                for s in info["symbols"]:
                    if s.get("symbol") == symbol:
                        self._symbol_info_cache[symbol] = s
                        return s
        except Exception as e:
            print(f"[ERROR] Failed to fetch exchange_info for {symbol}: {e}")
        return None

    async def get_step_size(self, symbol: str) -> Decimal:
        """Return stepSize as Decimal (LOT_SIZE filter). default 0.0001"""
        info = await self.get_symbol_info(symbol)
        default = Decimal("0.0001")
        try:
            if info and "filters" in info:
                for f in info["filters"]:
                    if f.get("filterType") == "LOT_SIZE":
                        step = f.get("stepSize") or f.get("step_size")
                        if step:
                            return Decimal(str(step))
        except Exception:
            pass
        return default

    async def get_min_notional(self, symbol: str) -> Decimal:
        """
        Read min notional from exchange info filters if present,
        else use PER_SYMBOL_MIN_NOTIONAL or MIN_NOTIONAL_DEFAULT.
        """
        # first check override
        if symbol in config.PER_SYMBOL_MIN_NOTIONAL:
            return Decimal(config.PER_SYMBOL_MIN_NOTIONAL[symbol])

        info = await self.get_symbol_info(symbol)
        if info and "filters" in info:
            for f in info["filters"]:
                # try multiple key names
                for k in ("minNotional", "min_notional", "minNotional", "notional", "minQty"):
                    if k in f and f[k] is not None:
                        try:
                            return Decimal(str(f[k]))
                        except Exception:
                            pass
        # fallback
        return Decimal(config.MIN_NOTIONAL_DEFAULT)

    def _precision_from_step(self, step: Decimal) -> int:
        # step like Decimal('0.001') => precision 3
        tup = step.normalize().as_tuple()
        return max(-tup.exponent, 0)

    def round_up_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        """Round UP qty to nearest step (so resulting notional >= requested)."""
        if step <= 0:
            return qty
        precision = self._precision_from_step(step)
        quant = Decimal(f"1e-{precision}")
        return ( (qty / quant).to_integral_value(rounding=ROUND_UP) * quant )

    def round_down_to_step(self, qty: Decimal, step: Decimal) -> Decimal:
        """Round DOWN qty to nearest step."""
        if step <= 0:
            return qty
        precision = self._precision_from_step(step)
        quant = Decimal(f"1e-{precision}")
        return ( (qty / quant).to_integral_value(rounding=ROUND_DOWN) * quant )

    async def adjust_qty_for_min_notional(self, symbol: str, desired_qty: float) -> float:
        """
        Ensure qty is aligned to step and that notional >= min_notional.
        If desired_qty too small, compute the minimum qty that satisfies min_notional.
        Returns float qty aligned to step, or 0 if cannot satisfy.
        """
        price = await self.get_price(symbol)
        if price <= 0:
            return 0.0
        price_d = Decimal(str(price))
        step = await self.get_step_size(symbol)
        min_notional = await self.get_min_notional(symbol)

        qty_d = Decimal(str(desired_qty))
        notional = (qty_d * price_d).quantize(Decimal("0.00000001"))

        if notional >= min_notional:
            # align down to step (so we don't exceed intended too much)
            aligned = self.round_down_to_step(qty_d, step)
            # if alignment yields 0, try rounding up once
            if aligned <= 0:
                aligned = self.round_up_to_step(qty_d, step)
            return float(aligned) if aligned > 0 else 0.0
        else:
            # need to increase qty to reach min_notional
            required_qty = (min_notional / price_d)
            required_aligned = self.round_up_to_step(required_qty, step)
            # final sanity check
            if required_aligned <= 0:
                return 0.0
            return float(required_aligned)

    # positions / balance / orders
    async def get_equity(self) -> float:
        try:
            bal = await self._run_sync(self.client.balance)
            for a in bal:
                if a.get("asset") == "USDT":
                    return float(a.get("balance", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0.0

    async def get_position(self, symbol: str) -> float:
        try:
            pos_list = await self._run_sync(self.client.get_position_risk, symbol=symbol)
            for p in pos_list:
                if p.get("symbol") == symbol:
                    return float(p.get("positionAmt", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get position for {symbol}: {e}")
        return 0.0

    async def open_long(self, symbol: str, qty: float):
        try:
            res = await self._run_sync(self.client.new_order,
                                       symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened LONG {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open LONG {symbol}: {e}")
            return None

    async def open_short(self, symbol: str, qty: float):
        try:
            res = await self._run_sync(self.client.new_order,
                                       symbol=symbol, side="SELL", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened SHORT {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open SHORT {symbol}: {e}")
            return None
