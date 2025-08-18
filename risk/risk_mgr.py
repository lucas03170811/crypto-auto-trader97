    async def get_order_qty(self, symbol: str, min_qty: float = 0.0) -> float:
        """
        Compute order qty and ensure notional >= min_notional.
        Includes DEBUG prints for troubleshooting.
        """
        equity = await self.client.get_equity()
        try:
            equity_d = Decimal(str(equity))
        except Exception:
            equity_d = Decimal("0")

        base_usd = Decimal(str(config.BASE_QTY_USD))
        desire_by_ratio = (equity_d * Decimal(str(config.EQUITY_RATIO))) if equity_d > 0 else Decimal("0")
        desired_usd = max(base_usd, desire_by_ratio)

        price = await self.client.get_price(symbol)
        if price <= 0:
            print(f"[DEBUG][{symbol}] price invalid: {price}")
            return 0.0
        price_d = Decimal(str(price))

        raw_qty = desired_usd / price_d
        print(f"[DEBUG][{symbol}] equity={equity_d}, base_usd={base_usd}, ratio_usd={desire_by_ratio}, chosen_usd={desired_usd}, price={price_d}, raw_qty={raw_qty}")

        adjusted_qty = await self.client.adjust_qty_for_min_notional(symbol, float(raw_qty))

        if adjusted_qty is None or adjusted_qty <= 0:
            min_notional = await self.client.get_min_notional(symbol)
            required_qty = (min_notional / price_d)
            print(f"[DEBUG][{symbol}] fallback required_qty={required_qty} for min_notional={min_notional}")
            adjusted_qty2 = await self.client.adjust_qty_for_min_notional(symbol, float(required_qty))
            if adjusted_qty2 is None:
                return 0.0
            adjusted_qty = adjusted_qty2

        if float(adjusted_qty) < float(min_qty):
            print(f"[DEBUG][{symbol}] adjusted_qty={adjusted_qty} < min_qty={min_qty} ❌ skip")
            return 0.0

        print(f"[DEBUG][{symbol}] FINAL_QTY={adjusted_qty}, FINAL_NOTIONAL={(Decimal(str(adjusted_qty))*price_d)} ✅ ready")
        return float(adjusted_qty)
