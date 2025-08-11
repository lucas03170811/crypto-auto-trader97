from binance.um_futures import UMFutures

print("[DEBUG] 正確版本 binance_client.py 被載入 ✅")

class BinanceClient:
    def __init__(self, api_key, api_secret):
        self.client = UMFutures(api_key, api_secret, base_url="https://fapi.binance.com")

    async def get_position(self, symbol):
        try:
            positions = self.client.get_position_risk(symbol=symbol)
            for p in positions:
                if p["symbol"] == symbol:
                    return float(p["positionAmt"])
        except Exception as e:
            print(f"[ERROR] Failed to get position for {symbol}: {e}")
        return 0

    async def get_equity(self):
        try:
            balance = self.client.balance()
            for asset in balance:
                if asset["asset"] == "USDT":
                    return float(asset["balance"])
        except Exception as e:
            print(f"[ERROR] Failed to get equity: {e}")
        return 0

    async def get_price(self, symbol):
        try:
            ticker = self.client.ticker_price(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
        return 0

    async def open_long(self, symbol, qty):
        try:
            resp = self.client.new_order(symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened LONG position on {symbol}")
            print(f"[ORDER RESPONSE] {resp}")  # ✅ 顯示回傳結果
        except Exception as e:
            print(f"[ERROR] Failed to open LONG on {symbol}: {e}")

    async def open_short(self, symbol, qty):
        try:
            resp = self.client.new_order(symbol=symbol, side="SELL", type="MARKET", quantity=qty)
            print(f"[ORDER] Opened SHORT position on {symbol}")
            print(f"[ORDER RESPONSE] {resp}")  # ✅ 顯示回傳結果
        except Exception as e:
            print(f"[ERROR] Failed to open SHORT on {symbol}: {e}")

    async def get_klines(self, symbol, interval="15m", limit=100):
        try:
            return self.client.klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to fetch klines for {symbol}: {e}")
            return []
