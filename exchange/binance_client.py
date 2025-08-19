import os
from binance.um_futures import UMFutures
from binance.error import ClientError

from config import BINANCE_API_KEY, BINANCE_API_SECRET

class BinanceClient:
    def __init__(self):
        self.client = UMFutures(
            key=BINANCE_API_KEY,
            secret=BINANCE_API_SECRET
        )

    def get_price(self, symbol: str) -> float:
        """
        嘗試抓 markPrice，如果失敗就抓現貨 price
        """
        try:
            data = self.client.ticker_price(symbol=symbol)
            return float(data["price"])
        except Exception:
            # Futures 有時需要用 markPrice
            data = self.client.mark_price(symbol=symbol)
            return float(data["markPrice"])

    def set_leverage(self, symbol: str, leverage: int = 20):
        try:
            self.client.change_leverage(symbol=symbol, leverage=leverage)
            print(f"[INFO] {symbol} 已設定槓桿 = {leverage}x")
        except ClientError as e:
            print(f"[WARN] 設定槓桿失敗 {symbol}: {e}")

    def order(self, symbol: str, side: str, quantity: float):
        """
        建立市價單
        """
        try:
            order = self.client.new_order(
                symbol=symbol,
                side=side.upper(),
                type="MARKET",
                quantity=quantity
            )
            print(f"[ORDER] {symbol} {side} {quantity} 成功: {order}")
            return order
        except ClientError as e:
            print(f"[ERROR] order {symbol}: {e.error_message}")
            return None
