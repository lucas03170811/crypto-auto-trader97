from decimal import Decimal

class RiskManager:
    """
    規則：
    - 名目 = max( 風控名目, 交易所最小名目 × 1.05 )  ；確保不會打到 -4164
    - 數量 = client.adjust_quantity()  ；對齊 stepSize、minQty 並補量至達標
    """
    def __init__(self, client, max_leverage: int = 10, risk_pct: float = 0.02, min_notional_safety: float = 1.05):
        self.client = client
        self.max_leverage = Decimal(str(max_leverage))
        self.risk_pct = Decimal(str(risk_pct))     # 例如 0.02 = 2%
        self.min_notional_safety = Decimal(str(min_notional_safety))

    async def _budget_notional(self, balance: float) -> Decimal:
        # 風控名目：以「保證金」比例計算；名目 = 餘額 × 風控比例 × 槓桿
        return Decimal(str(balance)) * self.risk_pct * self.max_leverage

    async def validate_and_size(self, symbol: str, price: float) -> Decimal:
        if price <= 0:
            print(f"[RISK] {symbol} 價格異常：{price}")
            return Decimal("0")

        balance = await self.client.get_equity()
        if balance <= 0:
            print(f"[RISK] USDT 餘額不足：{balance}")
            return Decimal("0")

        budget = await self._budget_notional(balance)
        min_notional = self.client.get_min_notional(symbol)
        # 至少達到最小名目 × 安全邊際（避免標的瞬變動導致再次低於門檻）
        target_notional = max(budget, min_notional * self.min_notional_safety)

        qty = self.client.adjust_quantity(symbol, float(target_notional), price)
        if qty <= 0:
            return Decimal("0")

        # 最終檢查（理論上不會再出錯）
        if Decimal(str(price)) * qty < min_notional:
            print(f"[RISK] {symbol} 對齊後名目仍 < 最小門檻，放棄下單")
            return Decimal("0")

        print(f"[RISK] {symbol} balance={balance:.4f} budget≈{budget:.4f} "
              f"minNotional={min_notional} target≈{target_notional:.4f} qty={qty}")
        return qty

    async def execute_trade(self, symbol: str, signal: str):
        price = await self.client.get_price(symbol)
        qty = await self.validate_and_size(symbol, price)
        if qty <= 0:
            return None

        if signal == "long":
            return await self.client.open_long(symbol, qty)
        elif signal == "short":
            return await self.client.open_short(symbol, qty)
        else:
            # 無訊號或不支援
            return None
