# exchange/binance_client.py
import asyncio
from typing import Any, List, Optional, Dict
import math

from binance.um_futures import UMFutures

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://fapi.binance.com", testnet: bool = False):
        if testnet:
            # testnet endpoint if required (user can change)
            base_url = "https://testnet.binancefuture.com"
        self.client = UMFutures(api_key, api_secret, base_url=base_url)

    async def _run_sync(self, fn, *args, **kwargs):
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    async def get_klines(self, symbol: str, interval: str = "5m", limit: int = 200):
        try:
            raw = await self._run_sync(self.client.klines, symbol, interval, limit)
            # raw: list of lists -> convert to pandas in strategy; here return raw (simpler)
            return raw
        except Exception as e:
            print(f"[ERROR] get_klines {symbol}: {e}")
            return []

    async def get_price(self, symbol: str) -> float:
        try:
            res = await self._run_sync(self.client.ticker_price, symbol)
            if isinstance(res, dict):
                return float(res.get("price", 0.0))
            # sometimes returns list
            if isinstance(res, list) and res:
                return float(res[0].get("price", 0.0))
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
        return 0.0

    async def get_24h_stats(self, symbol: str) -> Optional[dict]:
        for name in ("ticker_24hr_price_change", "ticker_24hr", "ticker_24hr_price_change_statistics", "ticker_24hr"):
            try:
                fn = getattr(self.client, name, None)
                if fn:
                    res = await self._run_sync(fn, symbol)
                    return res
            except Exception:
                continue
        return None

    async def get_latest_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            res = await self._run_sync(self.client.funding_rate, symbol=symbol, limit=1)
            if isinstance(res, list) and res:
                return float(res[0].get("fundingRate", 0.0))
        except Exception as e:
            # fallback
            try:
                res = await self._run_sync(self.client.funding_rate, symbol=symbol)
                if isinstance(res, dict):
                    return float(res.get("lastFundingRate", 0.0))
            except Exception:
                pass
            print(f"[ERROR] get_latest_funding_rate {symbol}: {e}")
        return None

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Return symbol info (from exchangeInfo)."""
        try:
            info = await self._run_sync(self.client.exchange_info)
            # exchange_info may return dict with 'symbols'
            if isinstance(info, dict) and "symbols" in info:
                for s in info["symbols"]:
                    if s.get("symbol") == symbol:
                        return s
        except Exception as e:
            print(f"[ERROR] get_symbol_info {symbol}: {e}")
        return None

    async def get_position(self, symbol: str) -> dict:
        """
        Return position dict with keys: positionAmt (float), entryPrice (float), unrealizedProfit (float)
        """
        try:
            res = await self._run_sync(self.client.get_position_risk, symbol)
            # some client returns list
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
            if isinstance(bal, dict):
                return float(bal.get("totalWalletBalance", 0.0))
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0.0

    async def change_leverage(self, symbol: str, leverage: int):
        """Try multiple method names (depends on SDK)."""
        for fn_name in ("change_leverage", "set_leverage", "changeInitialLeverage", "leverage"):
            fn = getattr(self.client, fn_name, None)
            if not fn:
                continue
            try:
                await self._run_sync(fn, symbol=symbol, leverage=leverage)
                return True
            except Exception as e:
                # ignore and continue trying others
                last_exc = e
                continue
        print(f"[WARN] failed to set leverage {symbol}: {locals().get('last_exc', None)}")
        return False

    async def new_order(self, symbol: str, side: str, quantity: float):
        try:
            return await self._run_sync(self.client.new_order, symbol=symbol, side=side, type="MARKET", quantity=quantity)
        except Exception as e:
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
