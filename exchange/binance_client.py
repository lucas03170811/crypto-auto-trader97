# exchange/binance_client.py
import asyncio
from typing import Any, List, Optional, Dict
import math
import time

from binance.um_futures import UMFutures

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://fapi.binance.com", testnet: bool = False):
        if testnet:
            base_url = "https://testnet.binancefuture.com"
        # 建構 SDK client
        self.client = UMFutures(api_key, api_secret, base_url=base_url)

    async def _run_sync(self, fn, *args, **kwargs):
        """Run blocking sync function in threadpool."""
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    async def _try_calls(self, fn, call_attempts):
        """
        helper: call different callables (lambdas) until one succeeds.
        call_attempts: list of callables (no-arg functions) to run in thread.
        """
        last_exc = None
        for call in call_attempts:
            try:
                return await asyncio.to_thread(call)
            except TypeError as e:
                # 參數錯誤多半是簽名不同，嘗試下一種
                last_exc = e
                continue
            except Exception as e:
                last_exc = e
                # 其他錯誤也記錄，繼續嘗試
                continue
        # 所有嘗試都失敗時回傳 None 並印錯誤
        raise last_exc if last_exc is not None else Exception("Unknown call failure")

    async def get_klines(self, symbol: str, interval: str = "5m", limit: int = 200) -> List[Any]:
        """
        Robust fetch klines: try multiple calling signatures because different SDK versions accept
        different positional/keyword args.
        Returns list of klines (or empty list on failure).
        """
        try:
            fn = getattr(self.client, "klines", None)
            attempts = []

            # pattern 1: positional (symbol, interval, limit)
            attempts.append(lambda: fn(symbol, interval, limit))

            # pattern 2: positional with only symbol+interval (some SDKs don't accept limit)
            attempts.append(lambda: fn(symbol, interval))

            # pattern 3: keyword args (symbol=..., interval=..., limit=...)
            attempts.append(lambda: fn(symbol=symbol, interval=interval, limit=limit))

            # pattern 4: some SDK use get_klines name
            alt = getattr(self.client, "get_klines", None)
            if alt:
                attempts.append(lambda: alt(symbol=symbol, interval=interval, limit=limit))
                attempts.append(lambda: alt(symbol, interval, limit))

            # pattern 5: try calling through client.klines with named limit arg 'limit' or 'limit='
            attempts.append(lambda: fn(symbol=symbol, interval=interval, limit=limit))

            res = await self._try_calls(fn, attempts)
            return res if res is not None else []
        except Exception as e:
            print(f"[ERROR] get_klines {symbol}: {e}")
            return []

    async def get_price(self, symbol: str) -> float:
        try:
            # ticker_price may return dict or list
            fn = getattr(self.client, "ticker_price", None)
            if not fn:
                return 0.0
            res = await self._run_sync(fn, symbol)
            if isinstance(res, dict):
                return float(res.get("price", 0.0))
            if isinstance(res, list) and res:
                return float(res[0].get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
        return 0.0

    async def get_24h_stats(self, symbol: str) -> Optional[dict]:
        # try several names used by different SDK versions
        for name in ("ticker_24hr_price_change", "ticker_24hr", "ticker_24hr_price_change_statistics", "ticker_24hr"):
            fn = getattr(self.client, name, None)
            if not fn:
                continue
            try:
                # try keyword style
                try:
                    return await self._run_sync(fn, symbol=symbol)
                except TypeError:
                    return await self._run_sync(fn, symbol, )
            except Exception:
                continue
        return None

    async def get_latest_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            fn = getattr(self.client, "funding_rate", None)
            if not fn:
                return None
            res = await self._run_sync(fn, symbol=symbol, limit=1)
            if isinstance(res, list) and res:
                return float(res[0].get("fundingRate", 0.0))
        except Exception as e:
            # fallback and log
            try:
                res = await self._run_sync(self.client.funding_rate, symbol)
                if isinstance(res, dict):
                    return float(res.get("lastFundingRate", 0.0))
            except Exception:
                pass
            print(f"[ERROR] Failed to get funding rate for {symbol}: {e}")
        return None

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        try:
            info = await self._run_sync(self.client.exchange_info)
            if isinstance(info, dict) and "symbols" in info:
                for s in info["symbols"]:
                    if s.get("symbol") == symbol:
                        return s
        except Exception as e:
            print(f"[ERROR] Failed to get symbol info for {symbol}: {e}")
        return None

    async def get_position(self, symbol: str) -> dict:
        try:
            res = await self._run_sync(self.client.get_position_risk, symbol)
            if isinstance(res, list):
                for p in res:
                    if p.get("symbol") == symbol:
                        return p
            if isinstance(res, dict) and res.get("symbol") == symbol:
                return res
        except Exception as e:
            print(f"[ERROR] Failed to get position for {symbol}: {e}")
        return {}

    async def get_equity(self) -> float:
        try:
            bal = await self._run_sync(self.client.balance)
            if isinstance(bal, list):
                for a in bal:
                    if a.get("asset") == "USDT":
                        return float(a.get("balance", 0.0))
            if isinstance(bal, dict) and "totalWalletBalance" in bal:
                return float(bal.get("totalWalletBalance", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0.0

    async def change_leverage(self, symbol: str, leverage: int):
        for fn_name in ("change_leverage", "set_leverage", "changeInitialLeverage", "leverage"):
            fn = getattr(self.client, fn_name, None)
            if not fn:
                continue
            try:
                # many SDKs want symbol & leverage keyword
                try:
                    await self._run_sync(fn, symbol=symbol, leverage=leverage)
                except TypeError:
                    await self._run_sync(fn, symbol, leverage)
                return True
            except Exception as e:
                last_exc = e
                continue
        print(f"[WARN] failed to set leverage {symbol}: {locals().get('last_exc', None)}")
        return False

    async def new_order(self, symbol: str, side: str, quantity: float):
        try:
            return await self._run_sync(self.client.new_order, symbol=symbol, side=side, type="MARKET", quantity=quantity)
        except Exception as e:
            # bubble up so caller can log more details
            raise

    async def open_long(self, symbol: str, qty: float):
        try:
            res = await self.new_order(symbol=symbol, side="BUY", quantity=qty)
            print(f"[ORDER] Opened LONG {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open LONG {symbol}: {e}")
            return None

    async def open_short(self, symbol: str, qty: float):
        try:
            res = await self.new_order(symbol=symbol, side="SELL", quantity=qty)
            print(f"[ORDER] Opened SHORT {symbol} qty={qty} -> {res}")
            return res
        except Exception as e:
            print(f"[ERROR] Failed to open SHORT {symbol}: {e}")
            return None
