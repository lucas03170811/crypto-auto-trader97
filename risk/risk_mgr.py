# risk/risk_mgr.py
from decimal import Decimal, getcontext
from typing import Optional
import config
from exchange.binance_client import BinanceClient

getcontext().prec = 28

class RiskManager:
    def __init__(self, client: BinanceClient, equity_ratio: float = None):
        self.client = client
        self.equity_ratio = Decimal(str(equity_ratio if equity_ratio is not None else config.EQUITY_RATIO))

    async def get_order_qty(self, symbol: str) -> Decimal:
        price = await self.client.get_price(symbol)
        if not price or price <= 0:
            return Decimal("0")

        equity = await self.client.get_equity()
        if equity <= 0:
            return Decimal("0")

        # 名目資金分配與槓桿
        notional = Decimal(str(equity)) * self.equity_ratio
        raw_qty = (notional * Decimal(str(config.LEVERAGE))) / Decimal(str(price))

        # 量化成交易所允許的步進
        q = await self.client._quantize_qty(symbol, raw_qty)
        return q

    async def execute_trade(self, symbol: str, side: str):
        try:
            qty = await self.get_order_qty(symbol)
            if qty <= 0:
                print(f"[RISK] qty too small: {symbol}")
                return None
            if side == "LONG":
                return await self.client.open_long(symbol, qty)
            elif side == "SHORT":
                return await self.client.open_short(symbol, qty)
            else:
                print(f"[RISK] Unknown side {side}")
                return None
        except Exception as e:
            print(f"[RISK] execute_trade error {symbol}: {e}")
            return None
