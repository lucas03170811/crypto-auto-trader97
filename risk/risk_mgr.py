# risk/risk_mgr.py
from decimal import Decimal

class RiskManager:
    def __init__(self, client, max_leverage: int = 10, risk_pct: float = 0.02):
        """
        client: BinanceClient 實例
        max_leverage: 最大槓桿倍數
        risk_pct: 單筆下單佔用帳戶資金比例 (例如 0.02 = 2%)
        """
        self.client = client
        self.max_leverage = max_leverage
        self.risk_pct = Decimal(str(risk_pct))

    async def get_trade_quantity(self, symbol: str, price: float) -> Decimal:
        """
        根據帳戶餘額與風控規則，計算可下單數量
        """
        balance = await self.client.get_balance()
        if balance <= 0:
            print(f"[RISK] 帳戶 USDT 餘額不足: {balance}")
            return Decimal("0")

        # 依資金比例算出下單金額
        usdt_amount = balance * self.risk_pct * self.max_leverage
        qty = self.client.adjust_quantity(symbol, usdt_amount, price)

        if qty <= 0:
            print(f"[RISK] {symbol} 無法計算出有效下單數量 (可能小於最小名目門檻)")
        return qty

    async def validate_order(self, symbol: str, price: float, side: str) -> Decimal:
        """
        風控檢查，返回最終下單數量，0 表示不允許下單
        """
        qty = await self.get_trade_quantity(symbol, price)
        if qty <= 0:
            return Decimal("0")

        # 基本風控檢查，可以在這裡擴充 (例如: 最大持倉限制、槓桿檢查)
        print(f"[RISK] {symbol} 通過風控檢查，允許 {side} {qty} @ {price}")
        return qty
