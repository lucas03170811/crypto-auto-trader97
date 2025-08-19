# exchange/binance_client.py
import asyncio
from decimal import Decimal
from binance.um_futures import UMFutures

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        base_url = "https://testnet.binancefuture.com" if testnet else None
        self.client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)
        self.symbol_info = {}

    async def load_exchange_info(self):
        """載入交易對資訊 (精度、最小交易數量等)"""
        info = await self.client.exchange_info()
        for symbol_data in info["symbols"]:
            symbol = symbol_data["symbol"]
            filters = {f["filterType"]: f for f in symbol_data["filters"]}
            self.symbol_info[symbol] = {
                "pricePrecision": symbol_data["pricePrecision"],
                "quantityPrecision": symbol_data["quantityPrecision"],
                "minNotional": Decimal(filters["MIN_NOTIONAL"]["notional"])
                if "MIN_NOTIONAL" in filters
                else Decimal("5"),  # 預設至少 5 USDT
            }

    async def get_price(self, symbol: str) -> float:
        """獲取交易對最新價格，兼容 ticker_price / futures_ticker"""
        try:
            res = await self.client.ticker_price(symbol=symbol)
            # 情況 1: 回傳字典 {"symbol": "BTCUSDT", "price": "63000.12"}
            if isinstance(res, dict) and "price" in res:
                return float(res["price"])
            # 情況 2: 有些版本直接回傳字串或 float
            elif isinstance(res, str) or isinstance(res, float):
                return float(res)
            # 備援: 使用 futures_ticker
            stats = await self.client.ticker_24hr_price_change(symbol=symbol)
            return float(stats["lastPrice"])
        except Exception as e:
            print(f"[ERROR] get_price {symbol}: {e}")
            return None

    async def get_balance(self) -> Decimal:
        acc = await self.client.account()
        usdt_bal = next((a for a in acc["assets"] if a["asset"] == "USDT"), None)
        return Decimal(usdt_bal["walletBalance"]) if usdt_bal else Decimal("0")

    async def order_market(self, symbol: str, side: str, quantity: Decimal, position_side: str = "BOTH"):
        """市價單下單"""
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": float(quantity),
                "positionSide": position_side,
            }
            order = await self.client.new_order(**params)
            print(f"[ORDER] {side} {symbol} {quantity} 成功 @ 市價")
            return order
        except Exception as e:
            print(f"[ERROR] order_market {symbol}: {e}")
            return None

    def adjust_quantity(self, symbol: str, usdt_amount: Decimal, price: float) -> Decimal:
        """依照精度與最小名目價值調整下單數量"""
        if symbol not in self.symbol_info:
            return Decimal("0")

        q_precision = self.symbol_info[symbol]["quantityPrecision"]
        min_notional = self.symbol_info[symbol]["minNotional"]

        qty = usdt_amount / Decimal(price)
        qty = qty.quantize(Decimal(10) ** -q_precision)  # 依精度修正

        # 檢查是否達到最小名目價值
        if qty * Decimal(price) < min_notional:
            print(f"[RISK] {symbol} 下單金額 {qty*Decimal(price)} 低於最小名目 {min_notional}")
            return Decimal("0")
        return qty
